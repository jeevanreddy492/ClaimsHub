from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field, model_validator

from app.schemas.common import ORMModel


class ClaimantCreate(BaseModel):
    employer_id: int
    employee_number: str = Field(min_length=1, max_length=30)
    first_name: str = Field(min_length=1, max_length=60)
    last_name: str = Field(min_length=1, max_length=60)
    date_of_birth: date
    hire_date: date
    weekly_salary: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    email: EmailStr | None = None

    @model_validator(mode="after")
    def check_dates(self) -> "ClaimantCreate":
        if self.hire_date <= self.date_of_birth:
            raise ValueError("hire_date must be after date_of_birth")
        if self.hire_date > date.today():
            raise ValueError("hire_date cannot be in the future")
        return self


class ClaimantUpdate(BaseModel):
    weekly_salary: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    email: EmailStr | None = None


class ClaimantOut(ORMModel):
    claimant_id: int
    employer_id: int
    employee_number: str
    first_name: str
    last_name: str
    date_of_birth: date
    hire_date: date
    weekly_salary: Decimal
    email: str | None
    created_at: datetime
