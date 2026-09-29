import logging

from sqlalchemy.orm import Session

from app.core.security import CurrentUser, create_access_token, verify_password
from app.domain.enums import Role
from app.domain.exceptions import AuthError
from app.repositories.simple import UserRepository
from app.schemas.auth import TokenResponse

log = logging.getLogger(__name__)


class AuthService:
    def __init__(self, session: Session) -> None:
        self.users = UserRepository(session)

    def login(self, username: str, password: str) -> TokenResponse:
        user = self.users.by_username(username)
        if user is None or not user.active or not verify_password(password, user.password_hash):
            log.warning("login_failed", extra={"event": "login_failed", "username": username})
            raise AuthError("Wrong username or password")
        current = CurrentUser(user.username, Role(user.role), user.full_name)
        token, expires_in = create_access_token(current)
        log.info("login_ok", extra={"event": "login_ok", "username": username})
        return TokenResponse(
            access_token=token,
            expires_in=expires_in,
            username=user.username,
            role=user.role,
            full_name=user.full_name,
        )
