"""Claim status rules.

The same rules are enforced again inside CLAIMS_PKG.change_claim_status in Oracle
(defense in depth). The Python copy gives fast, clear errors before any DB call.
If you change a rule here, change db/plsql/claims_pkg_body.sql too.
"""

from app.domain.enums import ClaimStatus, Role

ALLOWED_TRANSITIONS: dict[ClaimStatus, set[ClaimStatus]] = {
    ClaimStatus.RECEIVED: {ClaimStatus.IN_REVIEW},
    ClaimStatus.IN_REVIEW: {ClaimStatus.APPROVED, ClaimStatus.DENIED},
    ClaimStatus.APPROVED: {ClaimStatus.CLOSED},
    ClaimStatus.DENIED: {ClaimStatus.APPEALED, ClaimStatus.CLOSED},
    ClaimStatus.APPEALED: {ClaimStatus.IN_REVIEW},
    ClaimStatus.CLOSED: set(),
}

# Moves only a supervisor may make.
SUPERVISOR_ONLY: set[ClaimStatus] = {ClaimStatus.APPROVED, ClaimStatus.DENIED}


def can_transition(current: ClaimStatus, target: ClaimStatus) -> bool:
    return target in ALLOWED_TRANSITIONS.get(current, set())


def role_can_set(role: Role, target: ClaimStatus) -> bool:
    if role == Role.VIEWER:
        return False
    if target in SUPERVISOR_ONLY:
        return role == Role.SUPERVISOR
    return True
