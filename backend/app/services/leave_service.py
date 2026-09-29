"""Employee leave use cases (FMLA-style leave periods, optionally linked to an STD claim)."""

import logging

from sqlalchemy.orm import Session

from app.core.security import CurrentUser
from app.domain.enums import ClaimType, LeaveStatus
from app.domain.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
    VersionConflictError,
)
from app.models import LeaveRequest
from app.repositories.claim_repository import ClaimRepository
from app.repositories.leave_repository import LeaveRepository
from app.repositories.simple import AuditRepository, ClaimantRepository
from app.schemas.leave import LeaveCreate, LeaveUpdate

log = logging.getLogger(__name__)

LEAVE_TRANSITIONS: dict[LeaveStatus, set[LeaveStatus]] = {
    LeaveStatus.REQUESTED: {LeaveStatus.APPROVED, LeaveStatus.DENIED, LeaveStatus.CANCELLED},
    LeaveStatus.APPROVED: {LeaveStatus.CANCELLED},
    LeaveStatus.DENIED: set(),
    LeaveStatus.CANCELLED: set(),
}


class LeaveService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.leaves = LeaveRepository(session)
        self.claimants = ClaimantRepository(session)
        self.claims = ClaimRepository(session)
        self.audit = AuditRepository(session)

    def create(self, data: LeaveCreate, user: CurrentUser) -> LeaveRequest:
        if self.claimants.get(data.claimant_id) is None:
            raise NotFoundError(f"Claimant {data.claimant_id} not found")
        if data.linked_claim_id is not None:
            self._check_linked_claim(data.linked_claim_id, data.claimant_id)
        if self.leaves.overlapping(data.claimant_id, data.start_date, data.end_date):
            raise ConflictError("Leave overlaps an existing active leave for this employee")
        leave = self.leaves.add(
            LeaveRequest(
                **data.model_dump(), status=LeaveStatus.REQUESTED.value, created_by=user.username
            )
        )
        self.audit.record("LEAVE", leave.leave_id, "CREATE", user.username, data.leave_type)
        self.session.commit()
        log.info("leave_created", extra={"event": "leave_created", "leave_id": leave.leave_id})
        return leave

    def get(self, leave_id: int) -> LeaveRequest:
        leave = self.leaves.get(leave_id)
        if leave is None:
            raise NotFoundError(f"Leave {leave_id} not found")
        return leave

    def for_claimant(self, claimant_id: int) -> list[LeaveRequest]:
        if self.claimants.get(claimant_id) is None:
            raise NotFoundError(f"Claimant {claimant_id} not found")
        return self.leaves.for_claimant(claimant_id)

    def update(self, leave_id: int, data: LeaveUpdate, user: CurrentUser) -> LeaveRequest:
        leave = self.get(leave_id)
        if leave.version != data.expected_version:
            raise VersionConflictError("Leave was changed by someone else. Reload and try again.")
        changes = data.model_dump(exclude_unset=True, exclude={"expected_version"})

        if "status" in changes and changes["status"] is not None:
            current, target = LeaveStatus(leave.status), LeaveStatus(changes["status"])
            if target != current and target not in LEAVE_TRANSITIONS[current]:
                raise ConflictError(f"Cannot move leave from {current} to {target}")
            leave.status = target.value
        if "end_date" in changes:
            end = changes["end_date"]
            if end is not None and end < leave.start_date:
                raise ValidationError("end_date must be on or after start_date")
            if self.leaves.overlapping(leave.claimant_id, leave.start_date, end, leave.leave_id):
                raise ConflictError("New end date overlaps another active leave")
            leave.end_date = end
        if changes.get("linked_claim_id") is not None:
            self._check_linked_claim(changes["linked_claim_id"], leave.claimant_id)
            leave.linked_claim_id = changes["linked_claim_id"]

        self.audit.record("LEAVE", leave_id, "UPDATE", user.username, ",".join(sorted(changes)))
        self.session.commit()
        return leave

    def _check_linked_claim(self, claim_id: int, claimant_id: int) -> None:
        claim = self.claims.get(claim_id)
        if claim is None:
            raise NotFoundError(f"Claim {claim_id} not found")
        if claim.claimant_id != claimant_id:
            raise ValidationError("Linked claim belongs to a different employee")
        if claim.claim_type != ClaimType.STD:
            raise ValidationError("Only STD claims can be linked to a leave")
