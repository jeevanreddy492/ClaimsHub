# Runbook

## Severity

| Level | Example | Response |
| --- | --- | --- |
| Sev 1 | Site down, or no claim can be filed | Right away |
| Sev 2 | One claim type broken, or wrong payment amounts | Same day |
| Sev 3 | Slow page, wrong value on one screen | Next sprint |
| Sev 4 | Cosmetic issue, log noise | Backlog |

## Incident steps

1. **Detect:** a failed `/health/ready`, an error spike in Splunk, or a user report with a `ref` (correlation ID).
2. **Triage:** open a GitHub issue from the **Incident** template and set the severity.
3. **Find:** in Splunk run "Trace one request" with the correlation ID. Look at `error_code`, `ora_code` and `exception`.
4. **Fix:** branch `hotfix/CH-<n>-...`, write a test that fails first, open a PR, get green CI, tag a patch release (`v0.1.1`).
5. **Learn:** copy `docs/incidents/TEMPLATE.md` and write a blameless RCA within 2 days.

## Common commands (on the VM)

```bash
cd ~/ClaimsHub
C="docker compose -f deploy/docker-compose.prod.yml --env-file .env"
$C ps                                   # what is running
$C logs --since 15m api | grep '"level": "ERROR"'
$C restart api                          # restart only the API
curl -s localhost/health/ready          # DB check (shows db_ms)
./deploy/release.sh v0.1.1              # deploy a tag
./deploy/release.sh v0.1.0              # roll back = deploy the previous tag
$C run --rm api alembic downgrade -1    # undo the last migration (only if the RCA says so)
$C run --rm api python -m app.jobs weekly-payments       # run a batch job by hand
```

## Known failure modes

| Symptom | Likely cause | Action |
| --- | --- | --- |
| `/health/ready` 503, `DATABASE_UNAVAILABLE` | Autonomous DB stopped (idle) or VM IP not allowed | Start the DB in the OCI console; check its allowed IPs |
| 409 `VERSION_CONFLICT` spikes | Two people editing the same claim | Expected; the user reloads |
| ORA-20001 in logs | Invalid status move reached PL/SQL | Check whether UI rules and `claim_rules.py` match `CLAIMS_PKG` |
| ORA-01403 | A query found no row where the code expected one | Find the caller by correlation ID; add a NO_DATA_FOUND handler |
| Slow `/api/v1/claims` | Missing index / big table scan | Get the plan with `EXPLAIN PLAN`, see backlog item PERF-1 |
| `QueuePool limit ... overflow` errors | Connection pool full | Check for slow queries first, then `CLAIMSHUB_DB_POOL_SIZE` |
| Payments missing for approved STD claims | Scheduler job failed or disabled | `SELECT * FROM user_scheduler_job_run_details ORDER BY log_date DESC` |
