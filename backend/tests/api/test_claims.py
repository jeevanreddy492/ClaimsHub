from datetime import date, timedelta

from fastapi.testclient import TestClient

from tests.conftest import std_payload

H = dict[str, str]


def _file_std(client: TestClient, headers: H, data: dict[str, int], **extra: object) -> dict:
    r = client.post("/api/v1/claims/std", headers=headers, json={**std_payload(data), **extra})
    assert r.status_code == 201, r.text
    return r.json()


def _move(client: TestClient, headers: H, claim: dict, to: str) -> dict:
    r = client.post(
        f"/api/v1/claims/{claim['claim_id']}/status",
        headers=headers,
        json={"to_status": to, "reason": f"move to {to}", "expected_version": claim["version"]},
    )
    assert r.status_code == 200, r.text
    return r.json()


class TestStdIntake:
    def test_file_std_claim(self, client: TestClient, adjuster: H, setup_data: dict) -> None:
        claim = _file_std(client, adjuster, setup_data)
        assert claim["claim_number"].startswith(f"STD-{date.today().year}-")
        assert claim["status"] == "RECEIVED"
        assert claim["std_detail"]["condition_category"] == "SURGERY"
        assert claim["std_detail"]["elimination_days"] == 7
        assert claim["history"][0]["to_status"] == "RECEIVED"

    def test_duplicate_disability_date_rejected(
        self, client: TestClient, adjuster: H, setup_data: dict
    ) -> None:
        _file_std(client, adjuster, setup_data)
        r = client.post("/api/v1/claims/std", headers=adjuster, json=std_payload(setup_data))
        assert r.status_code == 409

    def test_wrong_policy_type(self, client: TestClient, adjuster: H, setup_data: dict) -> None:
        body = {**std_payload(setup_data), "policy_id": setup_data["life_policy_id"]}
        r = client.post("/api/v1/claims/std", headers=adjuster, json=body)
        assert r.status_code == 422
        assert "not a STD policy" in r.json()["message"]

    def test_far_future_start_rejected(
        self, client: TestClient, adjuster: H, setup_data: dict
    ) -> None:
        start = str(date.today() + timedelta(days=45))
        r = client.post("/api/v1/claims/std", headers=adjuster, json=std_payload(setup_data, start))
        assert r.status_code == 422

    def test_idempotency_key_replays_same_claim(
        self, client: TestClient, adjuster: H, setup_data: dict
    ) -> None:
        hdr = {**adjuster, "Idempotency-Key": "abc-123"}
        first = client.post("/api/v1/claims/std", headers=hdr, json=std_payload(setup_data))
        again = client.post("/api/v1/claims/std", headers=hdr, json=std_payload(setup_data))
        assert first.status_code == 201 and again.status_code == 200
        assert first.json()["claim_id"] == again.json()["claim_id"]
        other = client.post(
            "/api/v1/claims/std", headers=hdr, json=std_payload(setup_data, "2025-01-01")
        )
        assert other.status_code == 409


class TestStatusFlow:
    def test_full_approval_flow(
        self, client: TestClient, adjuster: H, supervisor: H, setup_data: dict
    ) -> None:
        claim = _file_std(client, adjuster, setup_data)
        claim = _move(client, adjuster, claim, "IN_REVIEW")
        assert claim["version"] == 2
        claim = _move(client, supervisor, claim, "APPROVED")
        claim = _move(client, supervisor, claim, "CLOSED")
        assert claim["closed_date"] == str(date.today())
        assert [h["to_status"] for h in claim["history"]] == [
            "RECEIVED",
            "IN_REVIEW",
            "APPROVED",
            "CLOSED",
        ]

    def test_adjuster_cannot_approve(
        self, client: TestClient, adjuster: H, setup_data: dict
    ) -> None:
        claim = _move(client, adjuster, _file_std(client, adjuster, setup_data), "IN_REVIEW")
        r = client.post(
            f"/api/v1/claims/{claim['claim_id']}/status",
            headers=adjuster,
            json={"to_status": "APPROVED", "reason": "looks fine", "expected_version": 2},
        )
        assert r.status_code == 403

    def test_invalid_transition(
        self, client: TestClient, supervisor: H, adjuster: H, setup_data: dict
    ) -> None:
        claim = _file_std(client, adjuster, setup_data)
        r = client.post(
            f"/api/v1/claims/{claim['claim_id']}/status",
            headers=supervisor,
            json={"to_status": "APPROVED", "reason": "skip", "expected_version": 1},
        )
        assert r.status_code == 409
        assert r.json()["code"] == "INVALID_STATUS_TRANSITION"

    def test_stale_version_rejected(
        self, client: TestClient, adjuster: H, setup_data: dict
    ) -> None:
        claim = _file_std(client, adjuster, setup_data)
        _move(client, adjuster, claim, "IN_REVIEW")
        r = client.post(
            f"/api/v1/claims/{claim['claim_id']}/status",
            headers=adjuster,
            json={"to_status": "IN_REVIEW", "reason": "again", "expected_version": 1},
        )
        assert r.status_code == 409
        assert r.json()["code"] == "VERSION_CONFLICT"


class TestBenefit:
    def test_calculate_std_benefit(self, client: TestClient, adjuster: H, setup_data: dict) -> None:
        claim = _file_std(client, adjuster, setup_data, disability_start_date="2026-03-02")
        r = client.post(f"/api/v1/claims/{claim['claim_id']}/calculate-benefit", headers=adjuster)
        assert r.status_code == 200, r.text
        detail = r.json()["std_detail"]
        assert detail["weekly_benefit"] == "1200.00"  # 2000 x 60%
        assert detail["benefit_start_date"] == "2026-03-09"

    def test_return_to_work(self, client: TestClient, adjuster: H, setup_data: dict) -> None:
        claim = _file_std(client, adjuster, setup_data, disability_start_date="2026-03-02")
        url = f"/api/v1/claims/{claim['claim_id']}/return-to-work"
        assert (
            client.put(
                url, headers=adjuster, json={"return_to_work_date": "2026-02-01"}
            ).status_code
            == 422
        )
        r = client.put(url, headers=adjuster, json={"return_to_work_date": "2026-04-20"})
        assert r.json()["std_detail"]["return_to_work_date"] == "2026-04-20"


class TestLife:
    def _life(self, data: dict, shares: list[str]) -> dict:
        return {
            "claimant_id": data["claimant_id"],
            "policy_id": data["life_policy_id"],
            "date_of_death": str(date.today() - timedelta(days=5)),
            "cause_category": "natural",
            "beneficiaries": [
                {"full_name": f"Person {i}", "relationship": "child", "share_pct": s}
                for i, s in enumerate(shares)
            ],
        }

    def test_shares_must_add_to_100(
        self, client: TestClient, adjuster: H, setup_data: dict
    ) -> None:
        r = client.post(
            "/api/v1/claims/life", headers=adjuster, json=self._life(setup_data, ["50", "40"])
        )
        assert r.status_code == 422

    def test_approval_creates_exact_payments(
        self, client: TestClient, adjuster: H, supervisor: H, setup_data: dict
    ) -> None:
        r = client.post(
            "/api/v1/claims/life",
            headers=adjuster,
            json=self._life(setup_data, ["33.33", "33.33", "33.34"]),
        )
        assert r.status_code == 201, r.text
        claim = r.json()
        assert claim["life_detail"]["payout_amount"] == "100000.00"
        claim = _move(client, adjuster, claim, "IN_REVIEW")
        claim = _move(client, supervisor, claim, "APPROVED")
        payments = client.get(
            f"/api/v1/claims/{claim['claim_id']}/payments", headers=adjuster
        ).json()
        assert len(payments) == 3
        assert sum(float(p["amount"]) for p in payments) == 100000.00

    def test_second_life_claim_blocked(
        self, client: TestClient, adjuster: H, setup_data: dict
    ) -> None:
        body = self._life(setup_data, ["100"])
        assert client.post("/api/v1/claims/life", headers=adjuster, json=body).status_code == 201
        assert client.post("/api/v1/claims/life", headers=adjuster, json=body).status_code == 409


class TestSearch:
    def test_search_filters_and_paging(
        self, client: TestClient, adjuster: H, setup_data: dict
    ) -> None:
        for start in ("2026-01-05", "2026-02-02", "2026-03-02"):
            _file_std(client, adjuster, setup_data, disability_start_date=start)
        page = client.get("/api/v1/claims?limit=2&status=RECEIVED", headers=adjuster).json()
        assert page["total"] == 3 and len(page["items"]) == 2
        assert client.get("/api/v1/claims?status=APPROVED", headers=adjuster).json()["total"] == 0
        stats = client.get("/api/v1/claims/stats", headers=adjuster).json()
        assert stats == {"by_status": {"RECEIVED": 3}, "by_type": {"STD": 3}, "total": 3}

    def test_bad_filter_value(self, client: TestClient, adjuster: H) -> None:
        assert client.get("/api/v1/claims?status=NOPE", headers=adjuster).status_code == 422
