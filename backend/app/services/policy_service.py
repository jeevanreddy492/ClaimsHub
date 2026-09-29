import logging

from sqlalchemy.orm import Session

from app.core.security import CurrentUser
from app.domain.exceptions import ConflictError, NotFoundError
from app.models import Employer, Policy
from app.repositories.simple import AuditRepository, EmployerRepository, PolicyRepository
from app.schemas.policy import EmployerCreate, PolicyCreate

log = logging.getLogger(__name__)


class PolicyService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.employers = EmployerRepository(session)
        self.policies = PolicyRepository(session)
        self.audit = AuditRepository(session)

    def create_employer(self, data: EmployerCreate, user: CurrentUser) -> Employer:
        if any(e.name.lower() == data.name.lower() for e in self.employers.list_all()):
            raise ConflictError(f"Employer '{data.name}' already exists")
        employer = self.employers.add(Employer(name=data.name, tax_id=data.tax_id))
        self.audit.record("EMPLOYER", employer.employer_id, "CREATE", user.username)
        self.session.commit()
        log.info(
            "employer_created",
            extra={"event": "employer_created", "employer_id": employer.employer_id},
        )
        return employer

    def list_employers(self) -> list[Employer]:
        return self.employers.list_all()

    def create_policy(self, data: PolicyCreate, user: CurrentUser) -> Policy:
        if self.employers.get(data.employer_id) is None:
            raise NotFoundError(f"Employer {data.employer_id} not found")
        seq = self.policies.count_for(data.employer_id, data.product_type.value) + 1
        number = f"{data.product_type.value}-{data.employer_id:04d}-{seq:03d}"
        policy = self.policies.add(
            Policy(policy_number=number, **data.model_dump(exclude_none=True))
        )
        self.audit.record("POLICY", policy.policy_id, "CREATE", user.username, number)
        self.session.commit()
        log.info("policy_created", extra={"event": "policy_created", "policy_id": policy.policy_id})
        return policy

    def list_policies(self, employer_id: int | None, product_type: str | None) -> list[Policy]:
        return self.policies.list(employer_id, product_type)
