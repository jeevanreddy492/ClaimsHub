# ADR 0001: Host on Oracle Cloud Always Free

- Status: Accepted
- Date: 2026-09-29

## Context
The system must use Oracle (SQL and PL/SQL) and cost as close to $0 as possible. Amazon RDS for Oracle includes the license in the hourly price, so even the smallest size costs tens of dollars a month. EC2 with Oracle Free in Docker costs about $20–40 a month once the free credits run out.

## Decision
Use an Oracle Cloud Always Free **Autonomous Database** (managed Oracle) and an Always Free **Ampere A1 VM** for the API and UI in Docker. Local development uses Oracle Database Free in Docker.

## Consequences
- About $0 a month, and real Oracle features (PL/SQL, DBMS_SCHEDULER).
- Free-tier limits can change (the ARM VM was halved in June 2026). The app is small, so we keep headroom.
- Idle free resources can be stopped or reclaimed; we keep a health-check cron.
- CloudWatch is not used; logs go to Splunk (ADR 0005).
