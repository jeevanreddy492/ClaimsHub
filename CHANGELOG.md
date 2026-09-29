# Changelog

All notable changes to this project. Format: [Keep a Changelog](https://keepachangelog.com), versions: [SemVer](https://semver.org).

## [Unreleased]

### Fixed
- CH-1: `CLAIMS_PKG` body did not compile on Oracle (PLS-00382 at `utc_now`). `SYS_EXTRACT_UTC(SYSTIMESTAMP)` now runs only inside SQL statements, and the helper function is gone.

### Changed
- CI actions moved to Node 24 versions (checkout v5, setup-python v6, setup-node v5).

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
