from fastapi.testclient import TestClient


def test_health(client: TestClient) -> None:
    assert client.get("/health").json()["status"] == "ok"
    ready = client.get("/health/ready")
    assert ready.status_code == 200 and ready.json()["database"] == "up"


def test_login_ok_and_me(client: TestClient, supervisor: dict[str, str]) -> None:
    me = client.get("/api/v1/auth/me", headers=supervisor).json()
    assert me == {"username": "supervisor1", "role": "SUPERVISOR", "full_name": "Supervisor1"}


def test_login_wrong_password(client: TestClient) -> None:
    r = client.post("/api/v1/auth/login", json={"username": "adjuster1", "password": "nope"})
    assert r.status_code == 401
    assert r.json()["code"] == "UNAUTHORIZED"


def test_no_token(client: TestClient) -> None:
    r = client.get("/api/v1/claims")
    assert r.status_code == 401


def test_correlation_id_is_echoed_in_header_and_error(
    client: TestClient, adjuster: dict[str, str]
) -> None:
    r = client.get("/api/v1/claims/999", headers={**adjuster, "X-Correlation-ID": "trace-42"})
    assert r.status_code == 404
    assert r.headers["X-Correlation-ID"] == "trace-42"
    assert r.json() == {
        "code": "NOT_FOUND",
        "message": "Claim 999 not found",
        "correlation_id": "trace-42",
    }


def test_validation_error_format(client: TestClient, adjuster: dict[str, str]) -> None:
    r = client.post("/api/v1/employers", headers=adjuster, json={"name": "X", "tax_id": "bad"})
    assert r.status_code == 422
    body = r.json()
    assert body["code"] == "VALIDATION_FAILED"
    assert {d["field"] for d in body["details"]} == {"name", "tax_id"}


def test_viewer_cannot_write(client: TestClient, viewer: dict[str, str]) -> None:
    r = client.post(
        "/api/v1/employers", headers=viewer, json={"name": "Viewer Corp", "tax_id": "12-3456789"}
    )
    assert r.status_code == 403


def test_duplicate_employer(
    client: TestClient, adjuster: dict[str, str], setup_data: dict[str, int]
) -> None:
    r = client.post(
        "/api/v1/employers", headers=adjuster, json={"name": "test corp", "tax_id": "12-3456789"}
    )
    assert r.status_code == 409


def test_policy_requires_product_fields(
    client: TestClient, adjuster: dict[str, str], setup_data: dict[str, int]
) -> None:
    r = client.post(
        "/api/v1/policies",
        headers=adjuster,
        json={
            "employer_id": setup_data["employer_id"],
            "product_type": "STD",
            "effective_date": "2024-01-01",
        },
    )
    assert r.status_code == 422


def test_claimant_search_and_update(
    client: TestClient, adjuster: dict[str, str], setup_data: dict[str, int]
) -> None:
    page = client.get("/api/v1/claimants?q=doe", headers=adjuster).json()
    assert page["total"] == 1 and page["items"][0]["last_name"] == "Doe"
    cid = setup_data["claimant_id"]
    r = client.patch(
        f"/api/v1/claimants/{cid}", headers=adjuster, json={"weekly_salary": "2100.00"}
    )
    assert r.status_code == 200 and r.json()["weekly_salary"] == "2100.00"


def test_duplicate_employee_number(
    client: TestClient, adjuster: dict[str, str], setup_data: dict[str, int]
) -> None:
    r = client.post(
        "/api/v1/claimants",
        headers=adjuster,
        json={
            "employer_id": setup_data["employer_id"],
            "employee_number": "E0000001",
            "first_name": "A",
            "last_name": "B",
            "date_of_birth": "1990-01-01",
            "hire_date": "2020-01-01",
            "weekly_salary": "900",
        },
    )
    assert r.status_code == 409
