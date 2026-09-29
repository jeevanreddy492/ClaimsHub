"""Claim use cases: intake, search, status changes, benefits and payments."""

import hashlib
import json
import logging
from datetime import date, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.core.security import CurrentUser
from app.domain.claim_rules import can_transition, role_can_set
from app.domain.enums import ClaimStatus, ClaimType, ProductType
from app.domain.exceptions import (
    ConflictError,
    ForbiddenError,
    InvalidStatusTransitionError,
    NotFoundError,
    ValidationError,
    VersionConflictError,
)
from app.models import (
    Beneficiary,
    Claim,
    Claimant,
    LifeClaimDetail,
    Payment,
    Policy,
    StdClaimDetail,
)
from app.repositories.claim_repository import ClaimRepository
from app.repositories.simple import AuditRepository, ClaimantRepository, PolicyRepository
from app.schemas.claim import (
    LifeClaimCreate,
    ReturnToWorkRequest,
    StatusChangeRequest,
    StdClaimCreate,
)

log = logging.getLogger(__name__)

MAX_FUTURE_DISABILITY_DAYS = 30  # e.g. a planned surgery can be filed up to 30 days ahead


def _request_hash(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


class ClaimService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.claims = ClaimRepository(session)
        self.claimants = ClaimantRepository(session)
        self.policies = PolicyRepository(session)
        self.audit = AuditRepository(session)

    # ---------- intake ----------
    def file_std(
        self, data: StdClaimCreate, user: CurrentUser, idempotency_key: str | None = None
    ) -> tuple[Claim, bool]:
        """Returns (claim, created). created=False when an idempotent retry is replayed."""
        replay = self._check_idempotency(idempotency_key, data.model_dump())
        if replay:
            return replay, False

        claimant, policy = self._load_claimant_and_policy(
            data.claimant_id, data.policy_id, ProductType.STD
        )
        today = date.today()
        if data.disability_start_date > today + timedelta(days=MAX_FUTURE_DISABILITY_DAYS):
            raise ValidationError(
                f"disability_start_date cannot be more than {MAX_FUTURE_DISABILITY_DAYS} days ahead"
            )
        if data.disability_start_date < claimant.hire_date:
            raise ValidationError("disability_start_date is before the employee's hire date")
        if data.disability_start_date < policy.effective_date:
            raise ValidationError("disability_start_date is before the policy effective date")

        open_claims, _ = self.claims.search(
            claimant_id=claimant.claimant_id, claim_type="STD", limit=100
        )
        for existing in open_claims:
            if (
                existing.status != ClaimStatus.CLOSED
                and existing.std_detail
                and (existing.std_detail.disability_start_date == data.disability_start_date)
            ):
                raise ConflictError(
                    f"Claim {existing.claim_number} already covers this disability start date"
                )

        claim = self._new_claim(ClaimType.STD, claimant, policy, data.received_date, user)
        claim.std_detail = StdClaimDetail(
            disability_start_date=data.disability_start_date,
            condition_category=data.condition_category.upper(),
            elimination_days=policy.elimination_days or 0,
        )
        return self._finish_intake(claim, user, idempotency_key, data.model_dump()), True

    def file_life(
        self, data: LifeClaimCreate, user: CurrentUser, idempotency_key: str | None = None
    ) -> tuple[Claim, bool]:
        replay = self._check_idempotency(idempotency_key, data.model_dump())
        if replay:
            return replay, False

        claimant, policy = self._load_claimant_and_policy(
            data.claimant_id, data.policy_id, ProductType.LIFE
        )
        if data.date_of_death > date.today():
            raise ValidationError("date_of_death cannot be in the future")
        if data.date_of_death < policy.effective_date:
            raise ValidationError("date_of_death is before the policy effective date")
        existing, _ = self.claims.search(
            claimant_id=claimant.claimant_id, claim_type="LIFE", limit=10
        )
        if any(c.status != ClaimStatus.DENIED for c in existing):
            raise ConflictError("A Life claim already exists for this claimant")

        assert policy.face_amount is not None
        claim = self._new_claim(ClaimType.LIFE, claimant, policy, data.received_date, user)
        claim.life_detail = LifeClaimDetail(
            date_of_death=data.date_of_death,
            cause_category=data.cause_category.upper(),
            payout_amount=policy.face_amount,
        )
        claim.beneficiaries = [
            Beneficiary(
                full_name=b.full_name,
                relationship_type=b.relationship.upper(),
                share_pct=b.share_pct,
            )
            for b in data.beneficiaries
        ]
        return self._finish_intake(claim, user, idempotency_key, data.model_dump()), True

    # ---------- reads ----------
    def get(self, claim_id: int) -> Claim:
        claim = self.claims.get_full(claim_id)
        if claim is None:
            raise NotFoundError(f"Claim {claim_id} not found")
        return claim

    def search(self, **filters: Any) -> tuple[list[Claim], int]:
        return self.claims.search(**filters)

    def payments(self, claim_id: int) -> list[Payment]:
        self.get(claim_id)
        return self.claims.payments(claim_id)

    def stats(self) -> dict:
        by_status, by_type = self.claims.stats()
        return {"by_status": by_status, "by_type": by_type, "total": sum(by_status.values())}

    # ---------- changes ----------
    def change_status(self, claim_id: int, req: StatusChangeRequest, user: CurrentUser) -> Claim:
        claim = self.get(claim_id)
        from_status = claim.status
        if not role_can_set(user.role, req.to_status):
            raise ForbiddenError(f"Role {user.role} cannot set status {req.to_status}")
        # Fast checks in Python; Oracle checks again under a row lock.
        if claim.version != req.expected_version:
            raise VersionConflictError(
                f"Claim {claim.claim_number} was changed by someone else. Reload and try again."
            )
        if not can_transition(ClaimStatus(claim.status), req.to_status):
            raise InvalidStatusTransitionError(
                f"Cannot move claim from {claim.status} to {req.to_status}"
            )
        self.claims.change_status(
            claim_id, req.to_status.value, req.reason, req.expected_version, user.username
        )
        self.session.commit()
        log.info(
            "claim_status_changed",
            extra={
                "event": "claim_status_changed",
                "claim_id": claim_id,
                "from_status": from_status,
                "to_status": req.to_status.value,
            },
        )
        return self.get(claim_id)

    def calculate_benefit(self, claim_id: int, user: CurrentUser) -> Claim:
        claim = self.get(claim_id)
        if claim.claim_type != ClaimType.STD:
            raise ValidationError("Benefit calculation is only for STD claims")
        self.claims.calculate_std_benefit(claim_id, user.username)
        self.session.commit()
        log.info("benefit_calculated", extra={"event": "benefit_calculated", "claim_id": claim_id})
        return self.get(claim_id)

    def set_return_to_work(
        self, claim_id: int, req: ReturnToWorkRequest, user: CurrentUser
    ) -> Claim:
        claim = self.get(claim_id)
        if claim.std_detail is None:
            raise ValidationError("Return-to-work date is only for STD claims")
        if req.return_to_work_date < claim.std_detail.disability_start_date:
            raise ValidationError("return_to_work_date is before the disability start date")
        claim.std_detail.return_to_work_date = req.return_to_work_date
        self.audit.record(
            "CLAIM", claim_id, "RETURN_TO_WORK", user.username, str(req.return_to_work_date)
        )
        self.session.commit()
        return self.get(claim_id)

    # ---------- helpers ----------
    def _load_claimant_and_policy(
        self, claimant_id: int, policy_id: int, product: ProductType
    ) -> tuple[Claimant, Policy]:
        claimant = self.claimants.get(claimant_id)
        if claimant is None:
            raise NotFoundError(f"Claimant {claimant_id} not found")
        policy = self.policies.get(policy_id)
        if policy is None:
            raise NotFoundError(f"Policy {policy_id} not found")
        if policy.product_type != product:
            raise ValidationError(f"Policy {policy.policy_number} is not a {product} policy")
        if policy.employer_id != claimant.employer_id:
            raise ValidationError("Policy does not belong to the claimant's employer")
        return claimant, policy

    def _new_claim(
        self,
        claim_type: ClaimType,
        claimant: Claimant,
        policy: Policy,
        received: date | None,
        user: CurrentUser,
    ) -> Claim:
        received = received or date.today()
        return Claim(
            claim_number=self.claims.next_claim_number(claim_type.value, received.year),
            claimant_id=claimant.claimant_id,
            policy_id=policy.policy_id,
            claim_type=claim_type.value,
            status=ClaimStatus.RECEIVED.value,
            received_date=received,
            assigned_to=user.username,
            created_by=user.username,
        )

    def _finish_intake(
        self, claim: Claim, user: CurrentUser, idem_key: str | None, payload: dict
    ) -> Claim:
        self.claims.add(claim)
        self.claims.add_history(
            claim.claim_id, None, ClaimStatus.RECEIVED.value, "Claim filed", user.username
        )
        self.audit.record("CLAIM", claim.claim_id, "CREATE", user.username, claim.claim_number)
        if idem_key:
            self.claims.save_idempotency(idem_key, _request_hash(payload), claim.claim_id)
        self.session.commit()
        log.info(
            "claim_filed",
            extra={
                "event": "claim_filed",
                "claim_id": claim.claim_id,
                "claim_number": claim.claim_number,
                "claim_type": claim.claim_type,
            },
        )
        return self.get(claim.claim_id)

    def _check_idempotency(self, key: str | None, payload: dict) -> Claim | None:
        if not key:
            return None
        found = self.claims.find_idempotency(key)
        if found is None:
            return None
        if found.request_hash != _request_hash(payload):
            raise ConflictError("Idempotency-Key was already used with a different request")
        log.info(
            "idempotent_replay", extra={"event": "idempotent_replay", "claim_id": found.claim_id}
        )
        return self.get(found.claim_id)
