# Changelog

All notable changes to this project. Format: [Keep a Changelog](https://keepachangelog.com), versions: [SemVer](https://semver.org).

## [0.1.0] - 2026-09-29

### Added
- Claims API (FastAPI) for Short-Term Disability, Life insurance and employee leave.
- CLAIMS_PKG PL/SQL package: status changes with row lock and version check, STD benefit, Life payouts, nightly and weekly batch jobs.
- JWT login with ADJUSTER, SUPERVISOR and VIEWER roles; audit log.
- JSON logs with correlation IDs, health and readiness checks, one error format, idempotency keys.
- React + TypeScript UI: dashboard, claims, intake forms, employees and leave, setup.
- Docker images, local Oracle Free compose, Oracle Cloud prod compose, release script.
- CI: lint, types, tests (SQLite + Oracle), security scans, Docker builds. Tag-based deploy.
- Splunk Free app with saved searches; runbook, ADRs, RCA template, backlog.
