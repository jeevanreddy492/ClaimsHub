from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from app.domain.enums import ProductType
from app.schemas.common import Money, ORMModel


class EmployerCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    tax_id: str = Field(pattern=r"^\d{2}-\d{7}$", examples=["12-3456789"])


class EmployerOut(ORMModel):
    employer_id: int
    name: str
    created_at: datetime


class PolicyCreate(BaseModel):
    employer_id: int
    product_type: ProductType
    effective_date: date
    benefit_pct: Decimal | None = Field(default=None, gt=0, le=100)
    max_weekly_benefit: Decimal | None = Field(default=None, gt=0)
    elimination_days: int | None = Field(default=None, ge=0, le=180)
    max_benefit_weeks: int | None = Field(default=None, ge=1, le=52)
    face_amount: Decimal | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def check_product_fields(self) -> "PolicyCreate":
        if self.product_type == ProductType.STD:
            missing = [
                f
                for f in ("benefit_pct", "max_weekly_benefit", "elimination_days")
                if getattr(self, f) is None
            ]
            if missing:
                raise ValueError(f"STD policy needs: {', '.join(missing)}")
        if self.product_type == ProductType.LIFE and self.face_amount is None:
            raise ValueError("LIFE policy needs face_amount")
        return self


class PolicyOut(ORMModel):
    policy_id: int
    policy_number: str
    employer_id: int
    product_type: str
    benefit_pct: Money | None
    max_weekly_benefit: Money | None
    elimination_days: int | None
    max_benefit_weeks: int | None
    face_amount: Money | None
    effective_date: date
