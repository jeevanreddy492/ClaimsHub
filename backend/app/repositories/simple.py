"""Repositories for reference data: users, employers, policies, claimants, audit."""

from sqlalchemy import func, or_, select

from app.core.logging import correlation_id_var
from app.models import AppUser, AuditLog, Claimant, Employer, Policy
from app.repositories.base import Repository


class UserRepository(Repository[AppUser]):
    model = AppUser

    def by_username(self, username: str) -> AppUser | None:
        return self.session.scalar(select(AppUser).where(AppUser.username == username))


class EmployerRepository(Repository[Employer]):
    model = Employer

    def list_all(self) -> list[Employer]:
        return list(self.session.scalars(select(Employer).order_by(Employer.name)))


class PolicyRepository(Repository[Policy]):
    model = Policy

    def list(self, employer_id: int | None = None, product_type: str | None = None) -> list[Policy]:
        stmt = select(Policy).order_by(Policy.policy_id)
        if employer_id is not None:
            stmt = stmt.where(Policy.employer_id == employer_id)
        if product_type is not None:
            stmt = stmt.where(Policy.product_type == product_type)
        return list(self.session.scalars(stmt))

    def count_for(self, employer_id: int, product_type: str) -> int:
        stmt = select(func.count()).where(
            Policy.employer_id == employer_id, Policy.product_type == product_type
        )
        return self.session.scalar(stmt) or 0


class ClaimantRepository(Repository[Claimant]):
    model = Claimant

    def search(
        self, q: str | None, employer_id: int | None, limit: int, offset: int
    ) -> tuple[list[Claimant], int]:
        stmt = select(Claimant)
        if employer_id is not None:
            stmt = stmt.where(Claimant.employer_id == employer_id)
        if q:
            like = f"%{q.lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(Claimant.last_name).like(like),
                    func.lower(Claimant.first_name).like(like),
                    func.lower(Claimant.employee_number).like(like),
                )
            )
        total = self.session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        rows = self.session.scalars(
            stmt.order_by(Claimant.last_name, Claimant.claimant_id).limit(limit).offset(offset)
        )
        return list(rows), total


class AuditRepository(Repository[AuditLog]):
    model = AuditLog

    def record(
        self, entity: str, entity_id: int, action: str, user: str, details: str | None = None
    ) -> None:
        self.session.add(
            AuditLog(
                entity=entity,
                entity_id=entity_id,
                action=action,
                details=(details or "")[:1000] or None,
                changed_by=user,
                correlation_id=correlation_id_var.get(),
            )
        )
