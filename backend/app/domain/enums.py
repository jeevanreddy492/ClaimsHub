from enum import StrEnum


class ClaimType(StrEnum):
    STD = "STD"
    LIFE = "LIFE"


class ProductType(StrEnum):
    STD = "STD"
    LIFE = "LIFE"


class ClaimStatus(StrEnum):
    RECEIVED = "RECEIVED"
    IN_REVIEW = "IN_REVIEW"
    APPROVED = "APPROVED"
    DENIED = "DENIED"
    APPEALED = "APPEALED"
    CLOSED = "CLOSED"


class LeaveType(StrEnum):
    FMLA = "FMLA"
    MEDICAL = "MEDICAL"
    PERSONAL = "PERSONAL"


class LeaveStatus(StrEnum):
    REQUESTED = "REQUESTED"
    APPROVED = "APPROVED"
    DENIED = "DENIED"
    CANCELLED = "CANCELLED"


class PaymentStatus(StrEnum):
    PENDING = "PENDING"
    ISSUED = "ISSUED"
    CANCELLED = "CANCELLED"


class Role(StrEnum):
    ADJUSTER = "ADJUSTER"
    SUPERVISOR = "SUPERVISOR"
    VIEWER = "VIEWER"
