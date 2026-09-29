# ADR 0005: JSON logs with correlation IDs, searched in Splunk Free

- Status: Accepted
- Date: 2026-09-29

## Decision
Every log line is JSON with `correlation_id` and `user`. The ID comes from the `X-Correlation-ID` header (the UI sends one) or is created by the API, is returned in every response and appears in every error body. Personal fields are masked in the formatter. Splunk Free runs on a laptop, and a script pulls logs from the VM.

## Consequences
One ID traces a request from the UI to the Oracle error. Splunk Free has no alerts and no logins, which is fine for one developer. A hosted log tool can replace the pull script later without code changes.
