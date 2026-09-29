# ClaimsHub

A claims management platform for **Short-Term Disability (STD)**, **Life insurance** and **employee leave**, built the way a real company team would build it.

**Stack:** Python 3.12, FastAPI, SQLAlchemy 2, Oracle (SQL + PL/SQL), React + TypeScript, Docker, GitHub Actions, Splunk.
**Hosting:** Oracle Cloud Always Free (about $0/month).
**Data:** 100% fake (Faker). No real people, SSNs or medical details.

```
Browser ──HTTPS──▶ Caddy ──▶ FastAPI (routers → services → repositories) ──SQL + PL/SQL──▶ Oracle Autonomous DB
                                   │                                                       (CLAIMS_PKG, scheduler jobs)
                                   └── JSON logs (correlation ID) ──▶ Splunk Free on your laptop
```

## What it does

| Area | Features |
| --- | --- |
| STD claims | Intake, review, approve/deny, weekly benefit calculation (PL/SQL), return-to-work, weekly payment batch |
| Life claims | Intake with beneficiaries (shares must total 100%), approval creates one payment per beneficiary (PL/SQL) |
| Employee leave | FMLA / medical / personal leave, open-ended leave, overlap check, link a leave to an STD claim |
| Claim rules | Status flow `RECEIVED → IN_REVIEW → APPROVED/DENIED → CLOSED` (DENIED → APPEALED → IN_REVIEW), row lock + version check in Oracle |
| Security | JWT login, roles: ADJUSTER, SUPERVISOR (approve/deny), VIEWER (read-only), audit log table |
| Operations | JSON logs with correlation IDs, `/health` and `/health/ready`, one error format, idempotency keys, Splunk saved searches, runbook |

## Run it on your Mac

You need **Docker Desktop**, **Python 3.12** and **Node 22** (`brew install python@3.12 node@22`).

```bash
make setup          # Python venv + UI packages
make db-up          # Oracle Free in Docker (first start: 1-2 minutes)
docker compose ps   # wait until oracle shows "healthy"
make db-setup       # tables, PL/SQL package, demo data
make api            # API on http://localhost:8000  (Swagger: /docs)
make ui             # UI on  http://localhost:5173
```

Log in with **adjuster1**, **supervisor1** or **viewer1**. The password for all of them is `Passw0rd!` (demo only).

Or run the whole stack in Docker: `docker compose up -d --build`, then open http://localhost:8080.

> Apple Silicon: `gvenzl/oracle-free` has an ARM image. If it ever fails to start, run `docker compose up -d oracle` again and check `docker compose logs oracle`.

## Checks (same as CI)

```bash
make check         # ruff, mypy, pytest (SQLite), eslint, tsc, vitest
make test-oracle   # integration tests against the local Oracle container
```

Unit and API tests run on SQLite, so they are fast. On SQLite, `app/repositories/local_rules.py` stands in for PL/SQL. The integration tests run the real `CLAIMS_PKG` on Oracle in CI.

## Project layout

```
backend/
  app/api/v1/        routers only (HTTP in, HTTP out)
  app/services/      business use cases, own the transaction
  app/repositories/  SQLAlchemy queries + PL/SQL calls
  app/domain/        status rules, benefit calculators, exceptions
  app/models/        ORM tables
  db/migrations/     Alembic
  db/plsql/          CLAIMS_PKG + scheduler jobs (deployed by scripts/deploy_plsql.py)
  tests/             unit, api, integration
frontend/            React + TypeScript (Vite), served by Caddy
deploy/              prod compose, release script, log pull script
splunk/              Splunk Free compose + app (inputs, saved searches)
docs/                ADRs, runbook, deploy guide, incidents, backlog
```

## How we work

- Every change is a GitHub issue, a branch (`feature/CH-12-...`), a pull request and green CI. See [CONTRIBUTING.md](CONTRIBUTING.md).
- Releases are tags (`v0.1.0`). A tag deploys to Oracle Cloud through `.github/workflows/deploy.yml`.
- Production problems follow [docs/runbook.md](docs/runbook.md). Each incident gets an RCA in [docs/incidents/](docs/incidents/).
- Upcoming work lives in [docs/backlog.md](docs/backlog.md).

## Docs

- [Deploy to Oracle Cloud Free](docs/deploy-oracle-cloud.md)
- [Splunk setup](docs/splunk.md)
- [Runbook](docs/runbook.md)
- [Architecture decisions](docs/adr/)
- [Backlog](docs/backlog.md)
