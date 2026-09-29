"""End-to-end tests against real Oracle (CLAIMS_PKG in PL/SQL).

Run in CI (Oracle Free service container) or locally:
  docker compose up -d oracle
  export CLAIMSHUB_DATABASE_URL="oracle+oracledb://claimshub:claimshub@localhost:1521/?service_name=FREEPDB1"
  alembic upgrade head && python -m scripts.deploy_plsql --skip-jobs
  python -m scripts.seed --claims 0
  pytest -m integration
"""

import uuid
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.db import engine
from app.main import app

pytestmark = pytest.mark.integration

if engine.dialect.name != "oracle":
    pytest.skip(
        "integration tests need CLAIMSHUB_DATABASE_URL pointing at Oracle", allow_module_level=True
    )

client = TestClient(app, raise_server_exceptions=False)


def _login(user: str) -> dict[str, str]:
    r = client.post("/api/v1/auth/login", json={"username": user, "password": "Passw0rd!"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="module")
def ctx() -> dict:
    adj, sup = _login("adjuster1"), _login("supervisor1")
    tag = uuid.uuid4().hex[:6]
    emp = client.post(
        "/api/v1/employers", headers=adj, json={"name": f"IT Corp {tag}", "tax_id": "12-3456789"}
    ).json()
    std = client.post(
        "/api/v1/policies",
        headers=adj,
        json={
            "employer_id": emp["employer_id"],
            "product_type": "STD",
            "effective_date": "2020-01-01",
            "benefit_pct": "60",
            "max_weekly_benefit": "1500",
            "elimination_days": 7,
            "max_benefit_weeks": 26,
        },
    ).json()
    life = client.post(
        "/api/v1/policies",
        headers=adj,
        json={
            "employer_id": emp["employer_id"],
            "product_type": "LIFE",
            "effective_date": "2020-01-01",
            "face_amount": "100000",
        },
    ).json()
    person = client.post(
        "/api/v1/claimants",
        headers=adj,
        json={
            "employer_id": emp["employer_id"],
            "employee_number": f"IT{tag}",
            "first_name": "Ivy",
            "last_name": "Tester",
            "date_of_birth": "1988-02-02",
            "hire_date": "2016-01-04",
            "weekly_salary": "2000.00",
        },
    ).json()
    return {"adj": adj, "sup": sup, "std": std, "life": life, "person": person}


def _move(h: dict, claim: dict, to: str) -> dict:
    r = client.post(
        f"/api/v1/claims/{claim['claim_id']}/status",
        headers=h,
        json={"to_status": to, "reason": f"it {to}", "expected_version": claim["version"]},
    )
    assert r.status_code == 200, r.text
    return r.json()


def test_package_is_valid() -> None:
    with engine.connect() as conn:
        status = conn.execute(
            text(
                "SELECT status FROM user_objects WHERE object_name = 'CLAIMS_PKG' "
                "AND object_type = 'PACKAGE BODY'"
            )
        ).scalar()
    assert status == "VALID"


def test_std_flow_uses_plsql(ctx: dict) -> None:
    start = date.today() - timedelta(days=40)
    r = client.post(
        "/api/v1/claims/std",
        headers=ctx["adj"],
        json={
            "claimant_id": ctx["person"]["claimant_id"],
            "policy_id": ctx["std"]["policy_id"],
            "disability_start_date": str(start),
            "condition_category": "surgery",
        },
    )
    assert r.status_code == 201, r.text
    claim = r.json()
    calc = client.post(
        f"/api/v1/claims/{claim['claim_id']}/calculate-benefit", headers=ctx["adj"]
    ).json()
    assert calc["std_detail"]["weekly_benefit"] == "1200.00"

    claim = _move(ctx["adj"], claim, "IN_REVIEW")
    bad = client.post(
        f"/api/v1/claims/{claim['claim_id']}/status",
        headers=ctx["sup"],
        json={"to_status": "CLOSED", "reason": "skip", "expected_version": 2},
    )
    assert bad.status_code == 409
    claim = _move(ctx["sup"], claim, "APPROVED")
    assert claim["version"] == 3

    # Weekly payment batch: 40 days since start - 7 waiting days = 4 full weeks paid.
    with engine.begin() as conn:
        conn.execute(
            text("BEGIN claims_pkg.generate_weekly_payments(TRUNC(SYSDATE), :n); END;"), {"n": 0}
        )
    payments = client.get(f"/api/v1/claims/{claim['claim_id']}/payments", headers=ctx["adj"]).json()
    assert len(payments) == 4
    assert all(p["amount"] == "1200.00" for p in payments)


def test_life_approval_in_plsql(ctx: dict) -> None:
    r = client.post(
        "/api/v1/claims/life",
        headers=ctx["adj"],
        json={
            "claimant_id": ctx["person"]["claimant_id"],
            "policy_id": ctx["life"]["policy_id"],
            "date_of_death": str(date.today() - timedelta(days=3)),
            "cause_category": "natural",
            "beneficiaries": [
                {"full_name": "A One", "relationship": "child", "share_pct": "33.33"},
                {"full_name": "B Two", "relationship": "child", "share_pct": "33.33"},
                {"full_name": "C Three", "relationship": "spouse", "share_pct": "33.34"},
            ],
        },
    )
    assert r.status_code == 201, r.text
    claim = _move(ctx["adj"], r.json(), "IN_REVIEW")
    claim = _move(ctx["sup"], claim, "APPROVED")
    total = sum(float(p["amount"]) for p in claim["payments"])
    assert len(claim["payments"]) == 3 and total == 100000.00
