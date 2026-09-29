"""Shared repository helpers."""

import re
from typing import Generic, TypeVar

from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from app.core.db import Base, is_oracle
from app.domain.exceptions import ORACLE_ERROR_MAP, ConflictError, DomainError

ModelT = TypeVar("ModelT", bound=Base)

_ORA_CODE = re.compile(r"ORA-(\d{5})")


def oracle_error_code(exc: DBAPIError) -> int | None:
    """Return the ORA- error number (for example 20001) from a driver error."""
    orig = exc.orig
    code = getattr(getattr(orig, "args", [None])[0], "code", None)
    if isinstance(code, int):
        return code
    match = _ORA_CODE.search(str(orig))
    return int(match.group(1)) if match else None


def translate_db_error(exc: DBAPIError) -> DomainError | None:
    """Turn known database errors into clean business errors.

    Returns None for unknown errors so they surface as 500s and get logged.
    """
    code = oracle_error_code(exc)
    if code and code in ORACLE_ERROR_MAP:
        # Keep only our message text, not the PL/SQL stack.
        text = str(exc.orig).split("\n")[0]
        message = re.sub(r"^ORA-\d{5}:\s*", "", text)
        return ORACLE_ERROR_MAP[code](message)
    if isinstance(exc, IntegrityError) or code == 1:  # ORA-00001 unique constraint
        return ConflictError("Record conflicts with existing data (duplicate or bad reference)")
    return None


class Repository(Generic[ModelT]):
    model: type[ModelT]

    def __init__(self, session: Session) -> None:
        self.session = session

    @property
    def is_oracle(self) -> bool:
        return is_oracle(self.session)

    def get(self, pk: int) -> ModelT | None:
        return self.session.get(self.model, pk)

    def add(self, obj: ModelT) -> ModelT:
        self.session.add(obj)
        self.session.flush()
        return obj
