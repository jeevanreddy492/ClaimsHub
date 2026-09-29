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


def test_money_always_has_two_decimals() -> None:
    """Oracle returns Decimal('1200') for NUMBER(12,2); the API must still send '1200.00'."""
    from decimal import Decimal

    from app.schemas.claim import PaymentOut

    out = PaymentOut(
        payment_id=1,
        beneficiary_id=None,
        period_start=None,
        period_end=None,
        amount=Decimal("1200"),
        status="PENDING",
        created_at="2026-01-01T00:00:00",
    )
    assert out.model_dump(mode="json")["amount"] == "1200.00"
