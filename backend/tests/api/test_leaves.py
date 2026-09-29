import httpx
from fastapi.testclient import TestClient

from tests.conftest import std_payload

H = dict[str, str]


def _leave(
    client: TestClient, h: H, data: dict, start: str, end: str | None = None, **extra: object
) -> httpx.Response:
    return client.post(
        "/api/v1/leaves",
        headers=h,
        json={
            "claimant_id": data["claimant_id"],
            "leave_type": "FMLA",
            "start_date": start,
            "end_date": end,
            **extra,
        },
    )


def test_create_and_list(client: TestClient, adjuster: H, setup_data: dict) -> None:
    r = _leave(client, adjuster, setup_data, "2026-05-01", "2026-05-31")
    assert r.status_code == 201, r.text
    leaves = client.get(
        f"/api/v1/claimants/{setup_data['claimant_id']}/leaves", headers=adjuster
    ).json()
    assert len(leaves) == 1 and leaves[0]["status"] == "REQUESTED"


def test_overlap_rejected_including_open_ended(
    client: TestClient, adjuster: H, setup_data: dict
) -> None:
    assert _leave(client, adjuster, setup_data, "2026-05-01").status_code == 201
    r = _leave(client, adjuster, setup_data, "2026-09-01", "2026-09-10")
    assert r.status_code == 409


def test_end_before_start(client: TestClient, adjuster: H, setup_data: dict) -> None:
    r = _leave(client, adjuster, setup_data, "2026-05-10", "2026-05-01")
    assert r.status_code == 422


def test_link_to_std_claim(client: TestClient, adjuster: H, setup_data: dict) -> None:
    claim = client.post("/api/v1/claims/std", headers=adjuster, json=std_payload(setup_data)).json()
    r = _leave(
        client, adjuster, setup_data, "2026-06-01", "2026-06-30", linked_claim_id=claim["claim_id"]
    )
    assert r.status_code == 201 and r.json()["linked_claim_id"] == claim["claim_id"]


def test_status_transitions_and_version(client: TestClient, adjuster: H, setup_data: dict) -> None:
    leave = _leave(client, adjuster, setup_data, "2026-07-01", "2026-07-15").json()
    url = f"/api/v1/leaves/{leave['leave_id']}"
    ok = client.patch(url, headers=adjuster, json={"expected_version": 1, "status": "APPROVED"})
    assert ok.status_code == 200 and ok.json()["version"] == 2
    stale = client.patch(url, headers=adjuster, json={"expected_version": 1, "status": "CANCELLED"})
    assert stale.status_code == 409
    bad = client.patch(url, headers=adjuster, json={"expected_version": 2, "status": "REQUESTED"})
    assert bad.status_code == 409
    closed = client.patch(
        url, headers=adjuster, json={"expected_version": 2, "end_date": "2026-07-10"}
    )
    assert closed.status_code == 200 and closed.json()["end_date"] == "2026-07-10"
