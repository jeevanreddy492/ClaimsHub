# Backlog

Copy each item into a GitHub issue (use the templates) and put it on the project board. IDs are the ticket numbers used in branch names, for example `feature/CH-101-ltd-claims`.

## Features

| ID | Story | Notes |
| --- | --- | --- |
| CH-101 | As an adjuster, I can file a **Long-Term Disability** claim | New `LTD_CLAIM_DETAIL` table, 180-day wait, monthly benefit, offset for Social Security. Reuse the claim engine. |
| CH-102 | As a supervisor, I can **reassign** claims to another adjuster | New endpoint + audit row. Add an "assigned to me" filter. |
| CH-103 | As an adjuster, I get a **work queue** of claims waiting on me, oldest first | Needs an index on `(assigned_to, status, received_date)`. |
| CH-104 | As finance, I can **issue** pending payments and export them as CSV | Status PENDING → ISSUED, batch number, CSV download. |
| CH-105 | STD benefit **stops at max weeks** and the claim closes itself | Extend `generate_weekly_payments`, add history row. |
| CH-106 | **Document upload** (doctor's note) stored in OCI Object Storage | Free tier: 20 GB. Virus scan out of scope. |
| CH-107 | **Email notice** to the employee when a claim changes status | Use a queue table + job so a mail failure never blocks the status change. |
| CH-108 | Admin screen to **manage users and roles** | Replace demo users; force password change. |

## Performance

| ID | Problem | How to prove and fix |
| --- | --- | --- |
| PERF-1 | Claim search by status gets slow as data grows | Seed 50,000 claims (`python -m scripts.seed --claims 50000`), run `make load-test`, check p95 in Splunk. `EXPLAIN PLAN` shows a full table scan. Add index `CLAIM(status, received_date)` in an Alembic migration. Measure before/after. |
| PERF-2 | `GET /claims/{id}` runs several queries | Check the query count in logs (`CLAIMSHUB_DB_ECHO=true`), tune `selectinload`/`joinedload`. |
| PERF-3 | Dashboard stats count the whole table on every load | Cache for 60 s, or add a materialized view refreshed by a job. |
| PERF-4 | Connection pool sizing for 2 workers on the free VM | Load test, then tune `pool_size`/`max_overflow`; document the numbers. |

## Tech debt and platform

| ID | Item |
| --- | --- |
| TD-1 | Lock Python dependencies (`uv` or `pip-tools`) so builds are repeatable. |
| TD-2 | Upgrade Vitest to v4+ (npm audit reports a moderate, dev-only issue in v3). |
| TD-3 | Add Dependabot for pip, npm, Docker and Actions. |
| TD-4 | Rate-limit `/auth/login` (brute-force protection). |
| TD-5 | Move the JWT from sessionStorage to an httpOnly cookie. |
| TD-6 | Add an OpenTelemetry trace ID next to the correlation ID. |

## Practice incidents (break, detect, fix, write the RCA)

Do these on a branch or in your local stack. Never fake the RCA: really reproduce the problem, find it in Splunk and fix it.

| ID | Scenario | What you practice |
| --- | --- | --- |
| INC-1 | Load test with 50k claims before PERF-1 | Finding slow endpoints with Splunk p95 and EXPLAIN PLAN |
| INC-2 | Stop the local Oracle container while the API runs | 503 `DATABASE_UNAVAILABLE`, readiness check, `pool_pre_ping`, recovery |
| INC-3 | Run the weekly payment job twice in one day | Proving the job is idempotent (it is: it continues from the last `period_end`) |
| INC-4 | Change a status rule in Python only, not in PL/SQL | ORA-20001 in logs, why rules live in one place, adding a test that compares both |
| INC-5 | Deploy a release with a broken migration | Rollback by redeploying the previous tag + `alembic downgrade` |
