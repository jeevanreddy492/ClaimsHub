"""Claim data access.

Simple reads and inserts use SQLAlchemy. Business-critical writes (status changes,
benefit calculation, Life payouts) call the CLAIMS_PKG PL/SQL package so the rules
run in one transaction inside Oracle, no matter which app calls them.

When tests run on SQLite there is no PL/SQL, so ``LocalClaimRules`` does the same
steps in Python. It is a test double only; production always uses Oracle.
"""

from datetime import date
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import selectinload

from app.core.logging import correlation_id_var
from app.models import (
    Claim,
    ClaimStatusHistory,
    IdempotencyKey,
    Payment,
    claim_number_seq,
)
from app.repositories.base import Repository, translate_db_error
from app.repositories.local_rules import LocalClaimRules


class ClaimRepository(Repository[Claim]):
    model = Claim

    # ---------- reads ----------
    def get_full(self, claim_id: int) -> Claim | None:
        stmt = (
            select(Claim)
            .where(Claim.claim_id == claim_id)
            .options(
                selectinload(Claim.std_detail),
                selectinload(Claim.life_detail),
                selectinload(Claim.beneficiaries),
                selectinload(Claim.history),
                selectinload(Claim.payments),
            )
            .execution_options(populate_existing=True)
        )
        return self.session.scalar(stmt)

    def search(
        self,
        *,
        status: str | None = None,
        claim_type: str | None = None,
        claimant_id: int | None = None,
        claim_number: str | None = None,
        received_from: date | None = None,
        received_to: date | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Claim], int]:
        stmt = select(Claim)
        if status:
            stmt = stmt.where(Claim.status == status)
        if claim_type:
            stmt = stmt.where(Claim.claim_type == claim_type)
        if claimant_id is not None:
            stmt = stmt.where(Claim.claimant_id == claimant_id)
        if claim_number:
            stmt = stmt.where(Claim.claim_number == claim_number.upper())
        if received_from:
            stmt = stmt.where(Claim.received_date >= received_from)
        if received_to:
            stmt = stmt.where(Claim.received_date <= received_to)
        total = self.session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        rows = self.session.scalars(
            stmt.order_by(Claim.received_date.desc(), Claim.claim_id.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(rows), total

    def stats(self) -> tuple[dict[str, int], dict[str, int]]:
        by_status = {
            str(k): int(v)
            for k, v in self.session.execute(
                select(Claim.status, func.count()).group_by(Claim.status)
            ).tuples()
        }
        by_type = {
            str(k): int(v)
            for k, v in self.session.execute(
                select(Claim.claim_type, func.count()).group_by(Claim.claim_type)
            ).tuples()
        }
        return by_status, by_type

    def payments(self, claim_id: int) -> list[Payment]:
        return list(
            self.session.scalars(
                select(Payment).where(Payment.claim_id == claim_id).order_by(Payment.payment_id)
            )
        )

    def history(self, claim_id: int) -> list[ClaimStatusHistory]:
        return list(
            self.session.scalars(
                select(ClaimStatusHistory)
                .where(ClaimStatusHistory.claim_id == claim_id)
                .order_by(ClaimStatusHistory.history_id)
            )
        )

    # ---------- writes ----------
    def next_claim_number(self, claim_type: str, year: int) -> str:
        if self.is_oracle:
            seq = self.session.scalar(claim_number_seq.next_value().select())
        else:
            seq = (self.session.scalar(select(func.max(Claim.claim_id))) or 0) + 1
        return f"{claim_type}-{year}-{int(seq or 0):06d}"

    def add_history(
        self, claim_id: int, from_status: str | None, to_status: str, reason: str, user: str
    ) -> None:
        self.session.add(
            ClaimStatusHistory(
                claim_id=claim_id,
                from_status=from_status,
                to_status=to_status,
                reason=reason,
                changed_by=user,
            )
        )

    def find_idempotency(self, key: str) -> IdempotencyKey | None:
        return self.session.get(IdempotencyKey, key)

    def save_idempotency(self, key: str, request_hash: str, claim_id: int) -> None:
        self.session.add(IdempotencyKey(idem_key=key, request_hash=request_hash, claim_id=claim_id))

    def change_status(
        self, claim_id: int, to_status: str, reason: str, expected_version: int, user: str
    ) -> None:
        """Calls CLAIMS_PKG.change_claim_status (locks row, checks rules, writes history)."""
        correlation_id = correlation_id_var.get()
        if not self.is_oracle:
            LocalClaimRules(self.session).change_claim_status(
                claim_id, to_status, reason, expected_version, user, correlation_id
            )
            return
        self._call(
            "BEGIN claims_pkg.change_claim_status(:claim_id, :to_status, :reason, "
            ":expected_version, :changed_by, :correlation_id); END;",
            {
                "claim_id": claim_id,
                "to_status": to_status,
                "reason": reason,
                "expected_version": expected_version,
                "changed_by": user,
                "correlation_id": correlation_id,
            },
        )

    def calculate_std_benefit(self, claim_id: int, user: str) -> None:
        """Calls CLAIMS_PKG.calculate_std_benefit and stores the result on the claim."""
        if not self.is_oracle:
            LocalClaimRules(self.session).calculate_std_benefit(claim_id, user)
            return
        self._call(
            "BEGIN claims_pkg.calculate_std_benefit(:claim_id, :changed_by); END;",
            {"claim_id": claim_id, "changed_by": user},
        )

    def _call(self, plsql: str, params: dict[str, Any]) -> None:
        try:
            self.session.execute(text(plsql), params)
        except DBAPIError as exc:
            domain_error = translate_db_error(exc)
            if domain_error:
                raise domain_error from exc
            raise
