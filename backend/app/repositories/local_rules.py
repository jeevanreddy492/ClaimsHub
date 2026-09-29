"""Python copy of CLAIMS_PKG for SQLite test runs ONLY.

Production uses Oracle, where db/plsql/claims_pkg_body.sql does this work.
Keep both in step: the integration tests (tests/integration) run the same
scenarios against real Oracle in CI.
"""

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.benefits import LifeBenefitCalculator, StdBenefitCalculator
from app.domain.claim_rules import can_transition
from app.domain.enums import ClaimStatus, ClaimType
from app.domain.exceptions import (
    InvalidStatusTransitionError,
    NotFoundError,
    ValidationError,
    VersionConflictError,
)
from app.models import (
    AuditLog,
    Beneficiary,
    Claim,
    Claimant,
    ClaimStatusHistory,
    Payment,
    Policy,
    StdClaimDetail,
    utcnow,
)


class LocalClaimRules:
    def __init__(self, session: Session) -> None:
        self.session = session

    def change_claim_status(
        self,
        claim_id: int,
        to_status: str,
        reason: str,
        expected_version: int,
        changed_by: str,
        correlation_id: str,
    ) -> None:
        claim = self.session.get(Claim, claim_id, populate_existing=True)
        if claim is None:
            raise NotFoundError(f"Claim {claim_id} not found")
        if claim.version != expected_version:
            raise VersionConflictError(
                f"Claim {claim_id} was changed by someone else (version {claim.version})"
            )
        current = ClaimStatus(claim.status)
        target = ClaimStatus(to_status)
        if not can_transition(current, target):
            raise InvalidStatusTransitionError(f"Cannot move claim from {current} to {target}")

        if claim.claim_type == ClaimType.LIFE and target == ClaimStatus.APPROVED:
            self._approve_life(claim)

        claim.status = target.value
        if target == ClaimStatus.CLOSED:
            claim.closed_date = utcnow().date()
        self.session.add(
            ClaimStatusHistory(
                claim_id=claim_id,
                from_status=current.value,
                to_status=target.value,
                reason=reason,
                changed_by=changed_by,
            )
        )
        self.session.add(
            AuditLog(
                entity="CLAIM",
                entity_id=claim_id,
                action="STATUS_CHANGE",
                details=f"{current.value} -> {target.value}: {reason}",
                changed_by=changed_by,
                correlation_id=correlation_id,
            )
        )
        self.session.flush()

    def _approve_life(self, claim: Claim) -> None:
        bens = list(
            self.session.scalars(
                select(Beneficiary)
                .where(Beneficiary.claim_id == claim.claim_id)
                .order_by(Beneficiary.beneficiary_id)
            )
        )
        shares = [b.share_pct for b in bens]
        if not bens or sum(shares) != Decimal(100):
            raise ValidationError("Beneficiary shares must add up to 100 before approval")
        assert claim.life_detail is not None
        amounts = LifeBenefitCalculator().split(claim.life_detail.payout_amount, shares)
        for ben, amount in zip(bens, amounts, strict=True):
            self.session.add(
                Payment(claim_id=claim.claim_id, beneficiary_id=ben.beneficiary_id, amount=amount)
            )

    def calculate_std_benefit(self, claim_id: int, changed_by: str) -> None:
        claim = self.session.get(Claim, claim_id)
        if claim is None:
            raise NotFoundError(f"Claim {claim_id} not found")
        detail = self.session.get(StdClaimDetail, claim_id)
        if claim.claim_type != ClaimType.STD or detail is None:
            raise ValidationError("Benefit calculation is only for STD claims")
        claimant = self.session.get(Claimant, claim.claimant_id)
        policy = self.session.get(Policy, claim.policy_id)
        assert claimant is not None and policy is not None
        if policy.benefit_pct is None or policy.max_weekly_benefit is None:
            raise ValidationError("Policy is missing STD benefit terms")
        result = StdBenefitCalculator().calculate(
            claimant.weekly_salary,
            policy.benefit_pct,
            policy.max_weekly_benefit,
            detail.disability_start_date,
            detail.elimination_days,
        )
        detail.weekly_benefit = result.weekly_benefit
        detail.benefit_start_date = result.benefit_start_date
        self.session.add(
            AuditLog(
                entity="CLAIM",
                entity_id=claim_id,
                action="BENEFIT_CALCULATED",
                details=f"weekly_benefit={result.weekly_benefit}",
                changed_by=changed_by,
            )
        )
        self.session.flush()
