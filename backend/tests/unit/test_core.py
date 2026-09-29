import json
import logging

import pytest

from app.core.logging import JsonFormatter, correlation_id_var
from app.core.security import (
    CurrentUser,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.domain.enums import Role
from app.domain.exceptions import AuthError


def test_json_log_masks_personal_fields() -> None:
    correlation_id_var.set("abc123")
    record = logging.makeLogRecord(
        {"msg": "hello", "levelname": "INFO", "name": "t", "last_name": "Doe", "claim_id": 7}
    )
    line = json.loads(JsonFormatter().format(record))
    assert line["correlation_id"] == "abc123"
    assert line["last_name"] == "***"
    assert line["claim_id"] == 7


def test_password_hash_roundtrip() -> None:
    hashed = hash_password("s3cret!")
    assert verify_password("s3cret!", hashed)
    assert not verify_password("wrong", hashed)
    assert not verify_password("x", "not-a-bcrypt-hash")


def test_token_roundtrip() -> None:
    token, expires = create_access_token(CurrentUser("u1", Role.ADJUSTER, "U One"))
    user = decode_access_token(token)
    assert user.username == "u1" and user.role == Role.ADJUSTER
    assert expires > 0


def test_bad_token_rejected() -> None:
    with pytest.raises(AuthError):
        decode_access_token("not.a.token")
