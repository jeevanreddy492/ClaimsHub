#!/usr/bin/env bash
# Release on the VM: pull a tag, migrate the DB, deploy PL/SQL, restart, smoke test.
# Usage: ./deploy/release.sh v0.1.0
set -euo pipefail
TAG="${1:?usage: release.sh <tag>}"
cd "$(dirname "$0")/.."
COMPOSE="docker compose -f deploy/docker-compose.prod.yml --env-file .env"

git fetch --tags --quiet
git checkout --quiet "$TAG"
echo "==> building $TAG"
$COMPOSE build
echo "==> database migrations"
$COMPOSE run --rm api alembic upgrade head
echo "==> PL/SQL package"
$COMPOSE run --rm api python -m scripts.deploy_plsql
echo "==> restart"
$COMPOSE up -d
sleep 8
echo "==> smoke test"
curl -fsS http://localhost/health/ready && echo && echo "Release $TAG OK"
