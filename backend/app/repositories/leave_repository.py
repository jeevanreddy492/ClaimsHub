from datetime import date

from sqlalchemy import or_, select

from app.models import LeaveRequest
from app.repositories.base import Repository

_FAR_FUTURE = date(9999, 12, 31)


class LeaveRepository(Repository[LeaveRequest]):
    model = LeaveRequest

    def for_claimant(self, claimant_id: int) -> list[LeaveRequest]:
        return list(
            self.session.scalars(
                select(LeaveRequest)
                .where(LeaveRequest.claimant_id == claimant_id)
                .order_by(LeaveRequest.start_date.desc())
            )
        )

    def overlapping(
        self, claimant_id: int, start: date, end: date | None, exclude_id: int | None = None
    ) -> list[LeaveRequest]:
        """Active leaves that overlap [start, end]. An empty end date means open-ended."""
        end = end or _FAR_FUTURE
        stmt = select(LeaveRequest).where(
            LeaveRequest.claimant_id == claimant_id,
            LeaveRequest.status.in_(["REQUESTED", "APPROVED"]),
            LeaveRequest.start_date <= end,
            or_(LeaveRequest.end_date.is_(None), LeaveRequest.end_date >= start),
        )
        if exclude_id is not None:
            stmt = stmt.where(LeaveRequest.leave_id != exclude_id)
        return list(self.session.scalars(stmt))
