"""Load test: adjusters searching and opening claims, some filing new ones.

  make load-test   then open http://localhost:8089 (try 50 users, spawn rate 5)
Watch p95 in Locust and in Splunk ("Slowest endpoints p95").
"""

import random

from locust import HttpUser, between, task

STATUSES = ["RECEIVED", "IN_REVIEW", "APPROVED", "DENIED", "CLOSED"]


class Adjuster(HttpUser):
    wait_time = between(0.5, 2)

    def on_start(self) -> None:
        r = self.client.post(
            "/api/v1/auth/login", json={"username": "adjuster1", "password": "Passw0rd!"}
        )
        self.client.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
        self.claim_ids: list[int] = []

    @task(5)
    def search_by_status(self) -> None:
        r = self.client.get(
            "/api/v1/claims",
            params={"status": random.choice(STATUSES), "limit": 20},
            name="/api/v1/claims?status",
        )
        if r.ok:
            self.claim_ids = [c["claim_id"] for c in r.json()["items"]] or self.claim_ids

    @task(3)
    def open_claim(self) -> None:
        if self.claim_ids:
            self.client.get(
                f"/api/v1/claims/{random.choice(self.claim_ids)}", name="/api/v1/claims/{id}"
            )

    @task(1)
    def dashboard(self) -> None:
        self.client.get("/api/v1/claims/stats")
