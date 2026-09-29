# Splunk setup (laptop)

The API writes one JSON line per event to stdout. Every line has `correlation_id`, `user`, `event` and, for requests, `route`, `status_code` and `duration_ms`. Names, birth dates, salary and passwords are masked (`app/core/logging.py`).

## Start Splunk Free

```bash
make splunk-up            # http://localhost:8001 (first start takes a few minutes on Apple Silicon)
```

The `claimshub_app` app is mounted into Splunk. It watches `~/claimshub-logs/*.log` as sourcetype `claimshub:json` and adds the saved searches below.

## Get logs in

- **Local API:** `make api 2>&1 | tee -a ~/claimshub-logs/local.log`
- **Oracle Cloud VM:** `export CLAIMSHUB_VM=ubuntu@<vm-ip>` then `./deploy/pull-logs.sh 60`. Add it to cron to run every 5 minutes (see the script header).

## Saved searches (Search & Reporting → Reports)

| Report | Use it for |
| --- | --- |
| Error rate by endpoint (24h) | First look during an incident |
| Slowest endpoints p95 (24h) | Performance tickets |
| Trace one request | Paste the `ref` / correlation ID a user sees in an error message |
| Oracle errors by code (7d) | ORA-00001, ORA-01403, ORA-20001 and so on |
| Business errors (24h) | Spikes in 409/422 after a release |
| Failed logins (24h) | Security checks |
| Claims filed per hour (7d) | Traffic by claim type |

Handy searches:

```
sourcetype=claimshub:json correlation_id="<id>" | sort _time
sourcetype=claimshub:json event=http_request status_code>=500 | stats count by route
sourcetype=claimshub:json event=http_request | timechart span=5m perc95(duration_ms) by route
```
