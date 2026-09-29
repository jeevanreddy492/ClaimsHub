## What changed
<!-- One or two sentences. Link the issue: Closes #123 -->

## Why

## How I tested it
- [ ] `make check`
- [ ] Oracle integration tests (CI or `make test-oracle`)
- [ ] Tried it in the UI / Swagger

## Risk and rollback
<!-- What could break? How do we roll back (previous tag, migration downgrade)? -->

## Checklist
- [ ] New migration if the schema changed
- [ ] Rules kept in step: `claim_rules.py` / `CLAIMS_PKG` / `rules.ts`
- [ ] CHANGELOG updated
- [ ] No secrets or real personal data
