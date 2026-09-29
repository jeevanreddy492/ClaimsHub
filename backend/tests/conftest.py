"""Test setup.

Unit and API tests run on in-memory SQLite (fast, no Docker needed).
Integration tests (tests/integration, marker `integration`) run on real Oracle in CI.
"""

import os
from collections.abc import Iterator
from datetime import date

os.environ.setdefault("CLAIMSHUB_DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("CLAIMSHUB_JWT_SECRET", "test-secret-please-change-0123456789")
os.environ.setdefault("CLAIMSHUB_ENVIRONMENT", "test")

import pytest
from fastapi.testclient import TestClient

from app.core.db import Base, SessionLocal, engine
from app.core.security import hash_password
from app.main import app
from app.models import AppUser

PASSWORD = "Passw0rd!"
USERS = {"adjuster1": "ADJUSTER", "supervisor1": "SUPERVISOR", "viewer1": "VIEWER"}


@pytest.fixture(autouse=True)
def fresh_db() -> Iterator[None]:
    if engine.dialect.name != "sqlite":  # integration tests manage their own data
        yield
        return
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    hashed = hash_password(PASSWORD)
    with SessionLocal() as s:
        for username, role in USERS.items():
            s.add(
                AppUser(
                    username=username, full_name=username.title(), role=role, password_hash=hashed
                )
            )
        s.commit()
    yield


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


def _token(client: TestClient, username: str) -> dict[str, str]:
    r = client.post("/api/v1/auth/login", json={"username": username, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def adjuster(client: TestClient) -> dict[str, str]:
    return _token(client, "adjuster1")


@pytest.fixture
def supervisor(client: TestClient) -> dict[str, str]:
    return _token(client, "supervisor1")


@pytest.fixture
def viewer(client: TestClient) -> dict[str, str]:
    return _token(client, "viewer1")


@pytest.fixture
def setup_data(client: TestClient, adjuster: dict[str, str]) -> dict[str, int]:
    """One employer with an STD and a LIFE policy, and one employee."""
    emp = client.post(
        "/api/v1/employers", json={"name": "Test Corp", "tax_id": "12-3456789"}, headers=adjuster
    )
    assert emp.status_code == 201, emp.text
    employer_id = emp.json()["employer_id"]
    std = client.post(
        "/api/v1/policies",
        headers=adjuster,
        json={
            "employer_id": employer_id,
            "product_type": "STD",
            "effective_date": "2020-01-01",
            "benefit_pct": "60",
            "max_weekly_benefit": "1500",
            "elimination_days": 7,
            "max_benefit_weeks": 26,
        },
    )
    assert std.status_code == 201, std.text
    life = client.post(
        "/api/v1/policies",
        headers=adjuster,
        json={
            "employer_id": employer_id,
            "product_type": "LIFE",
            "effective_date": "2020-01-01",
            "face_amount": "100000",
        },
    )
    assert life.status_code == 201, life.text
    person = client.post(
        "/api/v1/claimants",
        headers=adjuster,
        json={
            "employer_id": employer_id,
            "employee_number": "E0000001",
            "first_name": "Jane",
            "last_name": "Doe",
            "date_of_birth": "1985-04-12",
            "hire_date": "2015-06-01",
            "weekly_salary": "2000.00",
            "email": "jane.doe@example.com",
        },
    )
    assert person.status_code == 201, person.text
    return {
        "employer_id": employer_id,
        "std_policy_id": std.json()["policy_id"],
        "life_policy_id": life.json()["policy_id"],
        "claimant_id": person.json()["claimant_id"],
    }


def std_payload(data: dict[str, int], start: str | None = None) -> dict[str, object]:
    return {
        "claimant_id": data["claimant_id"],
        "policy_id": data["std_policy_id"],
        "disability_start_date": start or str(date.today().replace(day=1)),
        "condition_category": "surgery",
    }
