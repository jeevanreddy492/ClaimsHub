from datetime import date, datetime

from pydantic import BaseModel, Field, model_validator

from app.domain.enums import LeaveStatus, LeaveType
from app.schemas.common import ORMModel


class LeaveCreate(BaseModel):
    claimant_id: int
    leave_type: LeaveType
    start_date: date
    end_date: date | None = Field(default=None, description="Empty = open-ended leave")
    linked_claim_id: int | None = None
    reason: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def check_dates(self) -> "LeaveCreate":
        if self.end_date is not None and self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class LeaveUpdate(BaseModel):
    expected_version: int = Field(ge=1)
    end_date: date | None = None
    status: LeaveStatus | None = None
    linked_claim_id: int | None = None


class LeaveOut(ORMModel):
    leave_id: int
    claimant_id: int
    leave_type: str
    start_date: date
    end_date: date | None
    status: str
    linked_claim_id: int | None
    reason: str | None
    created_by: str
    created_at: datetime
    version: int
