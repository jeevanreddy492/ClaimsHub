# Contributing

## Flow for every change
1. Pick or create a GitHub issue (Feature, Bug or Incident template). Move it to **In progress** on the board.
2. Branch from `main`: `feature/CH-101-ltd-claims`, `bugfix/CH-120-leave-overlap`, `hotfix/CH-130-...`.
3. Commit with Conventional Commits: `feat:`, `fix:`, `perf:`, `refactor:`, `test:`, `docs:`, `chore:`.
4. Run `make check` before you push.
5. Open a pull request with the template filled in. CI must be green; one review is required.
6. Squash-merge. Update `CHANGELOG.md` under "Unreleased".
7. Release: move "Unreleased" to a new version, tag `vX.Y.Z`, push the tag. The deploy workflow ships it.

## Definition of Done
- [ ] Code, tests and docs updated
- [ ] `make check` green, CI green (including Oracle integration)
- [ ] DB change = new Alembic migration (never edit an old one); PL/SQL change = edit `db/plsql/*.sql`
- [ ] If a status rule changes: `claim_rules.py`, `CLAIMS_PKG` and `frontend/src/api/rules.ts` all updated
- [ ] No secrets, no real personal data
- [ ] Deployed, and `/health/ready` is OK after release

## Branch protection (set in GitHub → Settings → Branches → `main`)
Require a pull request, one approval, status checks `Backend - lint, types, unit + API tests`, `Backend - Oracle integration tests`, `Frontend - lint, types, tests, build`; block force pushes.
