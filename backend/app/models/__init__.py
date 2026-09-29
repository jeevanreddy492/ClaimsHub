"""SQLAlchemy ORM models. Table names are lower case in Python and become
UPPER CASE in Oracle (unquoted identifiers)."""

from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    Numeric,
    Sequence,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects import oracle
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


def utcnow() -> datetime:
    """Naive UTC timestamp (Oracle TIMESTAMP has no time zone)."""
    return datetime.now(UTC).replace(tzinfo=None)


# Oracle DATE drops fractions of a second; use TIMESTAMP there.
TS = DateTime().with_variant(oracle.TIMESTAMP(), "oracle")

# Used for readable claim numbers like STD-2026-000123.
claim_number_seq = Sequence("claim_number_seq", start=1, increment=1)


def _in(column: str, values: list[str]) -> str:
    joined = ", ".join(f"'{v}'" for v in values)
    return f"{column} IN ({joined})"


class AppUser(Base):
    __tablename__ = "app_user"
    __table_args__ = (
        CheckConstraint(_in("role", ["ADJUSTER", "SUPERVISOR", "VIEWER"]), name="role"),
    )

    user_id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True)
    password_hash: Mapped[str] = mapped_column(String(100))
    full_name: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(20))
    active: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(TS, default=utcnow)


class Employer(Base):
    __tablename__ = "employer"

    employer_id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    name: Mapped[str] = mapped_column(String(150), unique=True)
    tax_id: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(TS, default=utcnow)

    policies: Mapped[list["Policy"]] = relationship(back_populates="employer")


class Policy(Base):
    __tablename__ = "policy"
    __table_args__ = (
        CheckConstraint(_in("product_type", ["STD", "LIFE"]), name="product_type"),
        CheckConstraint(
            "benefit_pct IS NULL OR (benefit_pct > 0 AND benefit_pct <= 100)", name="benefit_pct"
        ),
    )

    policy_id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    policy_number: Mapped[str] = mapped_column(String(30), unique=True)
    employer_id: Mapped[int] = mapped_column(ForeignKey("employer.employer_id"))
    product_type: Mapped[str] = mapped_column(String(10))
    # STD fields
    benefit_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    max_weekly_benefit: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    elimination_days: Mapped[int | None] = mapped_column(Integer)
    max_benefit_weeks: Mapped[int | None] = mapped_column(Integer)
    # LIFE fields
    face_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    effective_date: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(TS, default=utcnow)

    employer: Mapped[Employer] = relationship(back_populates="policies")


class Claimant(Base):
    __tablename__ = "claimant"
    __table_args__ = (
        UniqueConstraint("employer_id", "employee_number"),
        CheckConstraint("weekly_salary > 0", name="salary"),
    )

    claimant_id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    employer_id: Mapped[int] = mapped_column(ForeignKey("employer.employer_id"))
    employee_number: Mapped[str] = mapped_column(String(30))
    first_name: Mapped[str] = mapped_column(String(60))
    last_name: Mapped[str] = mapped_column(String(60))
    date_of_birth: Mapped[date] = mapped_column(Date)
    hire_date: Mapped[date] = mapped_column(Date)
    weekly_salary: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    email: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(TS, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(TS, default=utcnow, onupdate=utcnow)

    employer: Mapped[Employer] = relationship()


class Claim(Base):
    __tablename__ = "claim"
    __table_args__ = (
        CheckConstraint(_in("claim_type", ["STD", "LIFE"]), name="claim_type"),
        CheckConstraint(
            _in("status", ["RECEIVED", "IN_REVIEW", "APPROVED", "DENIED", "APPEALED", "CLOSED"]),
            name="status",
        ),
        Index("ix_claim_claimant_id", "claimant_id"),
        # NOTE: no index on (status, received_date) yet. See docs/backlog.md PERF-1.
    )

    claim_id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    claim_number: Mapped[str] = mapped_column(String(30), unique=True)
    claimant_id: Mapped[int] = mapped_column(ForeignKey("claimant.claimant_id"))
    policy_id: Mapped[int] = mapped_column(ForeignKey("policy.policy_id"))
    claim_type: Mapped[str] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(20), default="RECEIVED")
    received_date: Mapped[date] = mapped_column(Date)
    closed_date: Mapped[date | None] = mapped_column(Date)
    assigned_to: Mapped[str | None] = mapped_column(String(50))
    created_by: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(TS, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(TS, default=utcnow, onupdate=utcnow)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    __mapper_args__ = {"version_id_col": version}  # noqa: RUF012

    claimant: Mapped[Claimant] = relationship()
    policy: Mapped[Policy] = relationship()
    std_detail: Mapped["StdClaimDetail | None"] = relationship(
        back_populates="claim", uselist=False, cascade="all, delete-orphan"
    )
    life_detail: Mapped["LifeClaimDetail | None"] = relationship(
        back_populates="claim", uselist=False, cascade="all, delete-orphan"
    )
    beneficiaries: Mapped[list["Beneficiary"]] = relationship(
        back_populates="claim", cascade="all, delete-orphan", order_by="Beneficiary.beneficiary_id"
    )
    history: Mapped[list["ClaimStatusHistory"]] = relationship(
        order_by="ClaimStatusHistory.history_id", viewonly=True
    )
    payments: Mapped[list["Payment"]] = relationship(order_by="Payment.payment_id", viewonly=True)


class StdClaimDetail(Base):
    __tablename__ = "std_claim_detail"

    claim_id: Mapped[int] = mapped_column(ForeignKey("claim.claim_id"), primary_key=True)
    disability_start_date: Mapped[date] = mapped_column(Date)
    condition_category: Mapped[str] = mapped_column(String(40))
    elimination_days: Mapped[int] = mapped_column(Integer)
    weekly_benefit: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    benefit_start_date: Mapped[date | None] = mapped_column(Date)
    return_to_work_date: Mapped[date | None] = mapped_column(Date)

    claim: Mapped[Claim] = relationship(back_populates="std_detail")


class LifeClaimDetail(Base):
    __tablename__ = "life_claim_detail"

    claim_id: Mapped[int] = mapped_column(ForeignKey("claim.claim_id"), primary_key=True)
    date_of_death: Mapped[date] = mapped_column(Date)
    cause_category: Mapped[str] = mapped_column(String(40))
    payout_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))

    claim: Mapped[Claim] = relationship(back_populates="life_detail")


class Beneficiary(Base):
    __tablename__ = "beneficiary"
    __table_args__ = (CheckConstraint("share_pct > 0 AND share_pct <= 100", name="share_pct"),)

    beneficiary_id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    claim_id: Mapped[int] = mapped_column(ForeignKey("claim.claim_id"), index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    relationship_type: Mapped[str] = mapped_column("relationship", String(30))
    share_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2))

    claim: Mapped[Claim] = relationship(back_populates="beneficiaries")


class LeaveRequest(Base):
    __tablename__ = "leave_request"
    __table_args__ = (
        CheckConstraint(_in("leave_type", ["FMLA", "MEDICAL", "PERSONAL"]), name="leave_type"),
        CheckConstraint(
            _in("status", ["REQUESTED", "APPROVED", "DENIED", "CANCELLED"]), name="status"
        ),
        CheckConstraint("end_date IS NULL OR end_date >= start_date", name="dates"),
        Index("ix_leave_request_claimant_id", "claimant_id"),
    )

    leave_id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    claimant_id: Mapped[int] = mapped_column(ForeignKey("claimant.claimant_id"))
    leave_type: Mapped[str] = mapped_column(String(20))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)  # open-ended leave allowed
    status: Mapped[str] = mapped_column(String(20), default="REQUESTED")
    linked_claim_id: Mapped[int | None] = mapped_column(ForeignKey("claim.claim_id"))
    reason: Mapped[str | None] = mapped_column(String(200))
    created_by: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(TS, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(TS, default=utcnow, onupdate=utcnow)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    __mapper_args__ = {"version_id_col": version}  # noqa: RUF012


class Payment(Base):
    __tablename__ = "payment"
    __table_args__ = (
        CheckConstraint(_in("status", ["PENDING", "ISSUED", "CANCELLED"]), name="status"),
        CheckConstraint("amount > 0", name="amount"),
        Index("ix_payment_claim_id", "claim_id"),
    )

    payment_id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    claim_id: Mapped[int] = mapped_column(ForeignKey("claim.claim_id"))
    beneficiary_id: Mapped[int | None] = mapped_column(ForeignKey("beneficiary.beneficiary_id"))
    period_start: Mapped[date | None] = mapped_column(Date)
    period_end: Mapped[date | None] = mapped_column(Date)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    created_at: Mapped[datetime] = mapped_column(TS, default=utcnow)


class ClaimStatusHistory(Base):
    __tablename__ = "claim_status_history"
    __table_args__ = (Index("ix_claim_status_history_claim_id", "claim_id"),)

    history_id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    claim_id: Mapped[int] = mapped_column(ForeignKey("claim.claim_id"))
    from_status: Mapped[str | None] = mapped_column(String(20))
    to_status: Mapped[str] = mapped_column(String(20))
    reason: Mapped[str | None] = mapped_column(String(300))
    changed_by: Mapped[str] = mapped_column(String(50))
    changed_at: Mapped[datetime] = mapped_column(TS, default=utcnow)


class AuditLog(Base):
    __tablename__ = "audit_log"
    __table_args__ = (Index("ix_audit_log_entity", "entity", "entity_id"),)

    audit_id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    entity: Mapped[str] = mapped_column(String(40))
    entity_id: Mapped[int] = mapped_column(Integer)
    action: Mapped[str] = mapped_column(String(40))
    details: Mapped[str | None] = mapped_column(String(1000))
    changed_by: Mapped[str] = mapped_column(String(50))
    changed_at: Mapped[datetime] = mapped_column(TS, default=utcnow)
    correlation_id: Mapped[str | None] = mapped_column(String(64))


class IdempotencyKey(Base):
    __tablename__ = "idempotency_key"

    idem_key: Mapped[str] = mapped_column(String(100), primary_key=True)
    request_hash: Mapped[str] = mapped_column(String(64))
    claim_id: Mapped[int] = mapped_column(ForeignKey("claim.claim_id"))
    created_at: Mapped[datetime] = mapped_column(TS, default=utcnow)
