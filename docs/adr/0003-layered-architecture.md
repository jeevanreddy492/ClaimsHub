# ADR 0003: Layered architecture with dependency injection

- Status: Accepted
- Date: 2026-09-29

## Decision
`api` (routers) → `services` (use cases, own the transaction) → `repositories` (SQL, PL/SQL) → `models`. Business rules with no I/O live in `domain`. Services are built with FastAPI `Depends`, so tests and future jobs can swap parts.

## Consequences
Routers never touch the database. Each layer can be tested on its own. A bit more code than putting everything in routers.
