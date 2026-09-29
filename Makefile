# Common commands. Run `make help` to list them.
.DEFAULT_GOAL := help
PY := backend/.venv/bin

help:  ## Show this list
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  %-16s %s\n",$$1,$$2}'

setup:  ## Create the Python venv and install UI packages
	cd backend && python3 -m venv .venv && .venv/bin/pip install -U pip && .venv/bin/pip install -e ".[dev]"
	cd frontend && npm ci

db-up:  ## Start local Oracle Free (Docker)
	docker compose up -d oracle

db-setup:  ## Create tables, deploy PL/SQL, load demo data
	cd backend && .venv/bin/alembic upgrade head
	cd backend && .venv/bin/python -m scripts.deploy_plsql
	cd backend && .venv/bin/python -m scripts.seed --claims 200

api:  ## Run the API with auto-reload on :8000
	cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000

ui:  ## Run the UI dev server on :5173
	cd frontend && npm run dev

check:  ## Lint, type check and test everything (same as CI, minus Oracle)
	cd backend && .venv/bin/ruff check . && .venv/bin/ruff format --check . && .venv/bin/mypy app scripts && .venv/bin/pytest
	cd frontend && npm run lint && npm run typecheck && npm test

test-oracle:  ## Integration tests against local Oracle
	cd backend && .venv/bin/pytest -m integration -o addopts="" tests/integration -v

load-test:  ## Load test (needs the API running and seeded data)
	cd backend && .venv/bin/locust -f loadtest/locustfile.py --host http://localhost:8000

splunk-up:  ## Start Splunk Free on your laptop (:8001)
	mkdir -p $$HOME/claimshub-logs && docker compose -f splunk/docker-compose.splunk.yml up -d

.PHONY: help setup db-up db-setup api ui check test-oracle load-test splunk-up
