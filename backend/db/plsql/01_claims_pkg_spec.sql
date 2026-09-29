-- CLAIMS_PKG: business rules that must never be skipped.
-- Deployed by scripts/deploy_plsql.py (run in CI and on every release).
-- Error numbers are mapped to HTTP errors in app/domain/exceptions.py:
--   -20001 invalid status move      -> 409
--   -20002 version conflict         -> 409
--   -20003 not found                -> 404
--   -20004 beneficiary/payout rule  -> 422
--   -20005 benefit calc not allowed -> 422
CREATE OR REPLACE PACKAGE claims_pkg AS

  c_invalid_transition CONSTANT PLS_INTEGER := -20001;
  c_version_conflict   CONSTANT PLS_INTEGER := -20002;
  c_not_found          CONSTANT PLS_INTEGER := -20003;
  c_payout_rule        CONSTANT PLS_INTEGER := -20004;
  c_benefit_rule       CONSTANT PLS_INTEGER := -20005;

  FUNCTION is_valid_transition(p_from IN VARCHAR2, p_to IN VARCHAR2) RETURN BOOLEAN;

  -- Locks the claim, checks version + rule, updates status, writes history and audit.
  -- Does NOT commit: the calling service owns the transaction.
  PROCEDURE change_claim_status(
    p_claim_id         IN NUMBER,
    p_to_status        IN VARCHAR2,
    p_reason           IN VARCHAR2,
    p_expected_version IN NUMBER,
    p_changed_by       IN VARCHAR2,
    p_correlation_id   IN VARCHAR2 DEFAULT NULL
  );

  -- weekly benefit = LEAST(weekly_salary * benefit_pct / 100, max_weekly_benefit)
  -- benefit start  = disability_start_date + elimination_days. Does NOT commit.
  PROCEDURE calculate_std_benefit(p_claim_id IN NUMBER, p_changed_by IN VARCHAR2);

  -- Checks shares = 100 and creates one payment per beneficiary. Does NOT commit.
  PROCEDURE approve_life_claim(p_claim_id IN NUMBER);

  -- Batch jobs (run by DBMS_SCHEDULER). These DO commit.
  PROCEDURE close_stale_claims(p_days_inactive IN NUMBER DEFAULT 180, p_closed OUT NUMBER);
  PROCEDURE generate_weekly_payments(p_as_of IN DATE DEFAULT TRUNC(SYSDATE), p_created OUT NUMBER);

END claims_pkg;
/
