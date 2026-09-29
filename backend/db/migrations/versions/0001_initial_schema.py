"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-09-29 12:33:10.677081
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import oracle

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _is_oracle() -> bool:
    return op.get_bind().dialect.name == "oracle"


def upgrade() -> None:
    if _is_oracle():
        op.execute(sa.schema.CreateSequence(sa.Sequence("claim_number_seq", start=1)))
    op.create_table(
        "app_user",
        sa.Column("user_id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("password_hash", sa.String(length=100), nullable=False),
        sa.Column("full_name", sa.String(length=100), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("active", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime().with_variant(oracle.TIMESTAMP(), "oracle"), nullable=False
        ),
        sa.CheckConstraint(
            "role IN ('ADJUSTER', 'SUPERVISOR', 'VIEWER')", name=op.f("ck_app_user_role")
        ),
        sa.PrimaryKeyConstraint("user_id", name=op.f("pk_app_user")),
        sa.UniqueConstraint("username", name=op.f("uq_app_user_username")),
    )
    op.create_table(
        "audit_log",
        sa.Column("audit_id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("entity", sa.String(length=40), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=40), nullable=False),
        sa.Column("details", sa.String(length=1000), nullable=True),
        sa.Column("changed_by", sa.String(length=50), nullable=False),
        sa.Column(
            "changed_at", sa.DateTime().with_variant(oracle.TIMESTAMP(), "oracle"), nullable=False
        ),
        sa.Column("correlation_id", sa.String(length=64), nullable=True),
        sa.PrimaryKeyConstraint("audit_id", name=op.f("pk_audit_log")),
    )
    op.create_index("ix_audit_log_entity", "audit_log", ["entity", "entity_id"], unique=False)
    op.create_table(
        "employer",
        sa.Column("employer_id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("tax_id", sa.String(length=20), nullable=False),
        sa.Column(
            "created_at", sa.DateTime().with_variant(oracle.TIMESTAMP(), "oracle"), nullable=False
        ),
        sa.PrimaryKeyConstraint("employer_id", name=op.f("pk_employer")),
        sa.UniqueConstraint("name", name=op.f("uq_employer_name")),
    )
    op.create_table(
        "claimant",
        sa.Column("claimant_id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("employer_id", sa.Integer(), nullable=False),
        sa.Column("employee_number", sa.String(length=30), nullable=False),
        sa.Column("first_name", sa.String(length=60), nullable=False),
        sa.Column("last_name", sa.String(length=60), nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=False),
        sa.Column("hire_date", sa.Date(), nullable=False),
        sa.Column("weekly_salary", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("email", sa.String(length=120), nullable=True),
        sa.Column(
            "created_at", sa.DateTime().with_variant(oracle.TIMESTAMP(), "oracle"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime().with_variant(oracle.TIMESTAMP(), "oracle"), nullable=False
        ),
        sa.CheckConstraint("weekly_salary > 0", name=op.f("ck_claimant_salary")),
        sa.ForeignKeyConstraint(
            ["employer_id"], ["employer.employer_id"], name=op.f("fk_claimant_employer_id")
        ),
        sa.PrimaryKeyConstraint("claimant_id", name=op.f("pk_claimant")),
        sa.UniqueConstraint("employer_id", "employee_number", name=op.f("uq_claimant_employer_id")),
    )
    op.create_table(
        "policy",
        sa.Column("policy_id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("policy_number", sa.String(length=30), nullable=False),
        sa.Column("employer_id", sa.Integer(), nullable=False),
        sa.Column("product_type", sa.String(length=10), nullable=False),
        sa.Column("benefit_pct", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("max_weekly_benefit", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("elimination_days", sa.Integer(), nullable=True),
        sa.Column("max_benefit_weeks", sa.Integer(), nullable=True),
        sa.Column("face_amount", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime().with_variant(oracle.TIMESTAMP(), "oracle"), nullable=False
        ),
        sa.CheckConstraint("product_type IN ('STD', 'LIFE')", name=op.f("ck_policy_product_type")),
        sa.CheckConstraint(
            "benefit_pct IS NULL OR (benefit_pct > 0 AND benefit_pct <= 100)",
            name=op.f("ck_policy_benefit_pct"),
        ),
        sa.ForeignKeyConstraint(
            ["employer_id"], ["employer.employer_id"], name=op.f("fk_policy_employer_id")
        ),
        sa.PrimaryKeyConstraint("policy_id", name=op.f("pk_policy")),
        sa.UniqueConstraint("policy_number", name=op.f("uq_policy_policy_number")),
    )
    op.create_table(
        "claim",
        sa.Column("claim_id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("claim_number", sa.String(length=30), nullable=False),
        sa.Column("claimant_id", sa.Integer(), nullable=False),
        sa.Column("policy_id", sa.Integer(), nullable=False),
        sa.Column("claim_type", sa.String(length=10), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("received_date", sa.Date(), nullable=False),
        sa.Column("closed_date", sa.Date(), nullable=True),
        sa.Column("assigned_to", sa.String(length=50), nullable=True),
        sa.Column("created_by", sa.String(length=50), nullable=False),
        sa.Column(
            "created_at", sa.DateTime().with_variant(oracle.TIMESTAMP(), "oracle"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime().with_variant(oracle.TIMESTAMP(), "oracle"), nullable=False
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.CheckConstraint("claim_type IN ('STD', 'LIFE')", name=op.f("ck_claim_claim_type")),
        sa.CheckConstraint(
            "status IN ('RECEIVED', 'IN_REVIEW', 'APPROVED', 'DENIED', 'APPEALED', 'CLOSED')",
            name=op.f("ck_claim_status"),
        ),
        sa.ForeignKeyConstraint(
            ["claimant_id"], ["claimant.claimant_id"], name=op.f("fk_claim_claimant_id")
        ),
        sa.ForeignKeyConstraint(
            ["policy_id"], ["policy.policy_id"], name=op.f("fk_claim_policy_id")
        ),
        sa.PrimaryKeyConstraint("claim_id", name=op.f("pk_claim")),
        sa.UniqueConstraint("claim_number", name=op.f("uq_claim_claim_number")),
    )
    op.create_index("ix_claim_claimant_id", "claim", ["claimant_id"], unique=False)
    op.create_table(
        "beneficiary",
        sa.Column("beneficiary_id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("claim_id", sa.Integer(), nullable=False),
        sa.Column("full_name", sa.String(length=120), nullable=False),
        sa.Column("relationship", sa.String(length=30), nullable=False),
        sa.Column("share_pct", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.CheckConstraint(
            "share_pct > 0 AND share_pct <= 100", name=op.f("ck_beneficiary_share_pct")
        ),
        sa.ForeignKeyConstraint(
            ["claim_id"], ["claim.claim_id"], name=op.f("fk_beneficiary_claim_id")
        ),
        sa.PrimaryKeyConstraint("beneficiary_id", name=op.f("pk_beneficiary")),
    )
    op.create_index(op.f("ix_beneficiary_claim_id"), "beneficiary", ["claim_id"], unique=False)
    op.create_table(
        "claim_status_history",
        sa.Column("history_id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("claim_id", sa.Integer(), nullable=False),
        sa.Column("from_status", sa.String(length=20), nullable=True),
        sa.Column("to_status", sa.String(length=20), nullable=False),
        sa.Column("reason", sa.String(length=300), nullable=True),
        sa.Column("changed_by", sa.String(length=50), nullable=False),
        sa.Column(
            "changed_at", sa.DateTime().with_variant(oracle.TIMESTAMP(), "oracle"), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["claim_id"], ["claim.claim_id"], name=op.f("fk_claim_status_history_claim_id")
        ),
        sa.PrimaryKeyConstraint("history_id", name=op.f("pk_claim_status_history")),
    )
    op.create_index(
        "ix_claim_status_history_claim_id", "claim_status_history", ["claim_id"], unique=False
    )
    op.create_table(
        "idempotency_key",
        sa.Column("idem_key", sa.String(length=100), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("claim_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime().with_variant(oracle.TIMESTAMP(), "oracle"), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["claim_id"], ["claim.claim_id"], name=op.f("fk_idempotency_key_claim_id")
        ),
        sa.PrimaryKeyConstraint("idem_key", name=op.f("pk_idempotency_key")),
    )
    op.create_table(
        "leave_request",
        sa.Column("leave_id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("claimant_id", sa.Integer(), nullable=False),
        sa.Column("leave_type", sa.String(length=20), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("linked_claim_id", sa.Integer(), nullable=True),
        sa.Column("reason", sa.String(length=200), nullable=True),
        sa.Column("created_by", sa.String(length=50), nullable=False),
        sa.Column(
            "created_at", sa.DateTime().with_variant(oracle.TIMESTAMP(), "oracle"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime().with_variant(oracle.TIMESTAMP(), "oracle"), nullable=False
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "leave_type IN ('FMLA', 'MEDICAL', 'PERSONAL')",
            name=op.f("ck_leave_request_leave_type"),
        ),
        sa.CheckConstraint(
            "status IN ('REQUESTED', 'APPROVED', 'DENIED', 'CANCELLED')",
            name=op.f("ck_leave_request_status"),
        ),
        sa.CheckConstraint(
            "end_date IS NULL OR end_date >= start_date", name=op.f("ck_leave_request_dates")
        ),
        sa.ForeignKeyConstraint(
            ["claimant_id"], ["claimant.claimant_id"], name=op.f("fk_leave_request_claimant_id")
        ),
        sa.ForeignKeyConstraint(
            ["linked_claim_id"], ["claim.claim_id"], name=op.f("fk_leave_request_linked_claim_id")
        ),
        sa.PrimaryKeyConstraint("leave_id", name=op.f("pk_leave_request")),
    )
    op.create_index("ix_leave_request_claimant_id", "leave_request", ["claimant_id"], unique=False)
    op.create_table(
        "life_claim_detail",
        sa.Column("claim_id", sa.Integer(), nullable=False),
        sa.Column("date_of_death", sa.Date(), nullable=False),
        sa.Column("cause_category", sa.String(length=40), nullable=False),
        sa.Column("payout_amount", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.ForeignKeyConstraint(
            ["claim_id"], ["claim.claim_id"], name=op.f("fk_life_claim_detail_claim_id")
        ),
        sa.PrimaryKeyConstraint("claim_id", name=op.f("pk_life_claim_detail")),
    )
    op.create_table(
        "std_claim_detail",
        sa.Column("claim_id", sa.Integer(), nullable=False),
        sa.Column("disability_start_date", sa.Date(), nullable=False),
        sa.Column("condition_category", sa.String(length=40), nullable=False),
        sa.Column("elimination_days", sa.Integer(), nullable=False),
        sa.Column("weekly_benefit", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("benefit_start_date", sa.Date(), nullable=True),
        sa.Column("return_to_work_date", sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(
            ["claim_id"], ["claim.claim_id"], name=op.f("fk_std_claim_detail_claim_id")
        ),
        sa.PrimaryKeyConstraint("claim_id", name=op.f("pk_std_claim_detail")),
    )
    op.create_table(
        "payment",
        sa.Column("payment_id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("claim_id", sa.Integer(), nullable=False),
        sa.Column("beneficiary_id", sa.Integer(), nullable=True),
        sa.Column("period_start", sa.Date(), nullable=True),
        sa.Column("period_end", sa.Date(), nullable=True),
        sa.Column("amount", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column(
            "created_at", sa.DateTime().with_variant(oracle.TIMESTAMP(), "oracle"), nullable=False
        ),
        sa.CheckConstraint(
            "status IN ('PENDING', 'ISSUED', 'CANCELLED')", name=op.f("ck_payment_status")
        ),
        sa.CheckConstraint("amount > 0", name=op.f("ck_payment_amount")),
        sa.ForeignKeyConstraint(
            ["beneficiary_id"],
            ["beneficiary.beneficiary_id"],
            name=op.f("fk_payment_beneficiary_id"),
        ),
        sa.ForeignKeyConstraint(["claim_id"], ["claim.claim_id"], name=op.f("fk_payment_claim_id")),
        sa.PrimaryKeyConstraint("payment_id", name=op.f("pk_payment")),
    )
    op.create_index("ix_payment_claim_id", "payment", ["claim_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_payment_claim_id", table_name="payment")
    op.drop_table("payment")
    op.drop_table("std_claim_detail")
    op.drop_table("life_claim_detail")
    op.drop_index("ix_leave_request_claimant_id", table_name="leave_request")
    op.drop_table("leave_request")
    op.drop_table("idempotency_key")
    op.drop_index("ix_claim_status_history_claim_id", table_name="claim_status_history")
    op.drop_table("claim_status_history")
    op.drop_index(op.f("ix_beneficiary_claim_id"), table_name="beneficiary")
    op.drop_table("beneficiary")
    op.drop_index("ix_claim_claimant_id", table_name="claim")
    op.drop_table("claim")
    op.drop_table("policy")
    op.drop_table("claimant")
    op.drop_table("employer")
    op.drop_index("ix_audit_log_entity", table_name="audit_log")
    op.drop_table("audit_log")
    op.drop_table("app_user")
    if _is_oracle():
        op.execute(sa.schema.DropSequence(sa.Sequence("claim_number_seq")))
