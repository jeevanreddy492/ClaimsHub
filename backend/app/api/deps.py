"""FastAPI dependencies: auth, roles and service wiring (dependency injection)."""

from collections.abc import Callable

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.logging import user_var
from app.core.security import CurrentUser, decode_access_token
from app.domain.enums import Role
from app.domain.exceptions import AuthError, ForbiddenError
from app.services.auth_service import AuthService
from app.services.claim_service import ClaimService
from app.services.claimant_service import ClaimantService
from app.services.leave_service import LeaveService
from app.services.policy_service import PolicyService

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> CurrentUser:
    # async on purpose: the contextvar set here is copied into the threadpool that runs
    # the (sync) endpoint, so every service log line carries the user.
    if creds is None:
        raise AuthError("Missing bearer token")
    user = decode_access_token(creds.credentials)
    user_var.set(user.username)
    request.state.username = user.username  # read by the access-log middleware
    return user


def require_roles(*roles: Role) -> Callable[[CurrentUser], CurrentUser]:
    def checker(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in roles:
            raise ForbiddenError(f"Role {user.role} cannot do this action")
        return user

    return checker


can_write = require_roles(Role.ADJUSTER, Role.SUPERVISOR)
supervisor_only = require_roles(Role.SUPERVISOR)


def auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(db)


def policy_service(db: Session = Depends(get_db)) -> PolicyService:
    return PolicyService(db)


def claimant_service(db: Session = Depends(get_db)) -> ClaimantService:
    return ClaimantService(db)


def claim_service(db: Session = Depends(get_db)) -> ClaimService:
    return ClaimService(db)


def leave_service(db: Session = Depends(get_db)) -> LeaveService:
    return LeaveService(db)
