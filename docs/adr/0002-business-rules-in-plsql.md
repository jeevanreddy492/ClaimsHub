# ADR 0002: Critical claim rules run in a PL/SQL package

- Status: Accepted
- Date: 2026-09-29

## Context
Status changes, benefit amounts and payouts must be correct even if another app, a batch job or a DBA touches the data. They must also be safe when two adjusters act at the same time.

## Decision
`CLAIMS_PKG` owns status changes (row lock `FOR UPDATE WAIT 5`, version check, history, audit), STD benefit calculation, Life payouts and batch jobs. The same status table lives in `app/domain/claim_rules.py`, so the API can return fast, clear errors before calling the database. Simple CRUD stays in SQLAlchemy.

## Consequences
- Rules run in one transaction, close to the data.
- Rules exist in two places (Python + PL/SQL). Both must change together; integration tests run the real package in CI.
- PL/SQL is deployed from versioned files by `scripts/deploy_plsql.py`, never typed by hand in production.
