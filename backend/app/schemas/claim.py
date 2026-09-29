from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.domain.enums import ClaimStatus
from app.schemas.common import ORMModel


class StdClaimCreate(BaseModel):
    claimant_id: int
    policy_id: int
    disability_start_date: date
    condition_category: str = Field(
        min_length=2, max_length=40, examples=["MUSCULOSKELETAL", "MATERNITY", "SURGERY"]
    )
    received_date: date | None = None


class BeneficiaryIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    relationship: str = Field(min_length=2, max_length=30, examples=["SPOUSE", "CHILD"])
    share_pct: Decimal = Field(gt=0, le=100, decimal_places=2)


class LifeClaimCreate(BaseModel):
    claimant_id: int
    policy_id: int
    date_of_death: date
    cause_category: str = Field(min_length=2, max_length=40, examples=["NATURAL", "ACCIDENT"])
    beneficiaries: list[BeneficiaryIn] = Field(min_length=1, max_length=10)
    received_date: date | None = None

    @field_validator("beneficiaries")
    @classmethod
    def shares_add_to_100(cls, v: list[BeneficiaryIn]) -> list[BeneficiaryIn]:
        if sum(b.share_pct for b in v) != Decimal(100):
            raise ValueError("beneficiary share_pct values must add up to 100")
        return v


class StatusChangeRequest(BaseModel):
    to_status: ClaimStatus
    reason: str = Field(min_length=3, max_length=300)
    expected_version: int = Field(ge=1, description="The claim version you read (optimistic lock)")


class StdDetailOut(ORMModel):
    disability_start_date: date
    condition_category: str
    elimination_days: int
    weekly_benefit: Decimal | None
    benefit_start_date: date | None
    return_to_work_date: date | None


class LifeDetailOut(ORMModel):
    date_of_death: date
    cause_category: str
    payout_amount: Decimal


class BeneficiaryOut(ORMModel):
    beneficiary_id: int
    full_name: str
    relationship: str = Field(validation_alias="relationship_type")
    share_pct: Decimal


class HistoryOut(ORMModel):
    from_status: str | None
    to_status: str
    reason: str | None
    changed_by: str
    changed_at: datetime


class PaymentOut(ORMModel):
    payment_id: int
    beneficiary_id: int | None
    period_start: date | None
    period_end: date | None
    amount: Decimal
    status: str
    created_at: datetime


class ClaimSummaryOut(ORMModel):
    claim_id: int
    claim_number: str
    claim_type: str
    status: str
    claimant_id: int
    policy_id: int
    received_date: date
    assigned_to: str | None
    version: int
    updated_at: datetime


class ClaimDetailOut(ClaimSummaryOut):
    closed_date: date | None
    created_by: str
    created_at: datetime
    std_detail: StdDetailOut | None
    life_detail: LifeDetailOut | None
    beneficiaries: list[BeneficiaryOut]
    history: list[HistoryOut]
    payments: list[PaymentOut]


class BenefitCalculationOut(BaseModel):
    claim_id: int
    weekly_benefit: Decimal
    benefit_start_date: date


class ReturnToWorkRequest(BaseModel):
    return_to_work_date: date


class ClaimStats(BaseModel):
    by_status: dict[str, int]
    by_type: dict[str, int]
    total: int
