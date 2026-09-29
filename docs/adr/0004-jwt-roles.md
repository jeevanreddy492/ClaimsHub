# ADR 0004: JWT bearer tokens with three roles

- Status: Accepted
- Date: 2026-09-29

## Decision
Users log in with a username and password (bcrypt hashes in `APP_USER`) and get a 60-minute HS256 JWT. Roles: ADJUSTER (file and review), SUPERVISOR (also approve/deny), VIEWER (read-only). Role checks run in API dependencies and again in services for status moves.

## Consequences
Simple and stateless. There is no refresh token and no single sign-on yet (see backlog TD-5, CH-108).
