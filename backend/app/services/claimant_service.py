import logging

from sqlalchemy.orm import Session

from app.core.security import CurrentUser
from app.domain.exceptions import ConflictError, NotFoundError
from app.models import Claimant
from app.repositories.simple import AuditRepository, ClaimantRepository, EmployerRepository
from app.schemas.claimant import ClaimantCreate, ClaimantUpdate

log = logging.getLogger(__name__)


class ClaimantService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.claimants = ClaimantRepository(session)
        self.employers = EmployerRepository(session)
        self.audit = AuditRepository(session)

    def create(self, data: ClaimantCreate, user: CurrentUser) -> Claimant:
        if self.employers.get(data.employer_id) is None:
            raise NotFoundError(f"Employer {data.employer_id} not found")
        existing, _ = self.claimants.search(data.employee_number, data.employer_id, 50, 0)
        if any(c.employee_number == data.employee_number for c in existing):
            raise ConflictError(
                f"Employee number {data.employee_number} already exists for this employer"
            )
        claimant = self.claimants.add(Claimant(**data.model_dump()))
        self.audit.record("CLAIMANT", claimant.claimant_id, "CREATE", user.username)
        self.session.commit()
        log.info(
            "claimant_created",
            extra={"event": "claimant_created", "claimant_id": claimant.claimant_id},
        )
        return claimant

    def get(self, claimant_id: int) -> Claimant:
        claimant = self.claimants.get(claimant_id)
        if claimant is None:
            raise NotFoundError(f"Claimant {claimant_id} not found")
        return claimant

    def search(
        self, q: str | None, employer_id: int | None, limit: int, offset: int
    ) -> tuple[list[Claimant], int]:
        return self.claimants.search(q, employer_id, limit, offset)

    def update(self, claimant_id: int, data: ClaimantUpdate, user: CurrentUser) -> Claimant:
        claimant = self.get(claimant_id)
        changes = data.model_dump(exclude_unset=True, exclude_none=True)
        for key, value in changes.items():
            setattr(claimant, key, value)
        self.audit.record(
            "CLAIMANT", claimant_id, "UPDATE", user.username, ",".join(sorted(changes))
        )
        self.session.commit()
        return claimant
