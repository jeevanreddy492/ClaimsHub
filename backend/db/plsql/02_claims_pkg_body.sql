CREATE OR REPLACE PACKAGE BODY claims_pkg AS

  -- ---------------------------------------------------------------- helpers
  -- PL/SQL use only: a private package function cannot be called inside SQL
  -- (PLS-00231), so SQL statements use SYS_EXTRACT_UTC(SYSTIMESTAMP) directly.
  FUNCTION utc_now RETURN TIMESTAMP IS
  BEGIN
    RETURN CAST(SYS_EXTRACT_UTC(SYSTIMESTAMP) AS TIMESTAMP);
  END utc_now;

  PROCEDURE write_audit(
    p_entity         IN VARCHAR2,
    p_entity_id      IN NUMBER,
    p_action         IN VARCHAR2,
    p_details        IN VARCHAR2,
    p_changed_by     IN VARCHAR2,
    p_correlation_id IN VARCHAR2 DEFAULT NULL
  ) IS
  BEGIN
    INSERT INTO audit_log (entity, entity_id, action, details, changed_by, changed_at, correlation_id)
    VALUES (p_entity, p_entity_id, p_action, SUBSTR(p_details, 1, 1000), p_changed_by, SYS_EXTRACT_UTC(SYSTIMESTAMP),
            p_correlation_id);
  END write_audit;

  -- Same table as app/domain/claim_rules.py ALLOWED_TRANSITIONS. Keep them in step.
  FUNCTION is_valid_transition(p_from IN VARCHAR2, p_to IN VARCHAR2) RETURN BOOLEAN IS
  BEGIN
    RETURN (p_from = 'RECEIVED'  AND p_to = 'IN_REVIEW')
        OR (p_from = 'IN_REVIEW' AND p_to IN ('APPROVED', 'DENIED'))
        OR (p_from = 'APPROVED'  AND p_to = 'CLOSED')
        OR (p_from = 'DENIED'    AND p_to IN ('APPEALED', 'CLOSED'))
        OR (p_from = 'APPEALED'  AND p_to = 'IN_REVIEW');
  END is_valid_transition;

  -- ---------------------------------------------------------------- status change
  PROCEDURE change_claim_status(
    p_claim_id         IN NUMBER,
    p_to_status        IN VARCHAR2,
    p_reason           IN VARCHAR2,
    p_expected_version IN NUMBER,
    p_changed_by       IN VARCHAR2,
    p_correlation_id   IN VARCHAR2 DEFAULT NULL
  ) IS
    v_status  claim.status%TYPE;
    v_version claim.version%TYPE;
    v_type    claim.claim_type%TYPE;
    e_row_locked EXCEPTION;
    PRAGMA EXCEPTION_INIT(e_row_locked, -30006);  -- WAIT 5 ran out
  BEGIN
    BEGIN
      -- Row lock: two adjusters cannot change the same claim at the same time.
      SELECT status, version, claim_type
        INTO v_status, v_version, v_type
        FROM claim
       WHERE claim_id = p_claim_id
         FOR UPDATE WAIT 5;
    EXCEPTION
      WHEN NO_DATA_FOUND THEN
        RAISE_APPLICATION_ERROR(c_not_found, 'Claim ' || p_claim_id || ' not found');
      WHEN e_row_locked THEN
        RAISE_APPLICATION_ERROR(c_version_conflict,
          'Claim ' || p_claim_id || ' is being changed by someone else. Try again.');
    END;

    IF p_expected_version IS NULL OR v_version <> p_expected_version THEN
      RAISE_APPLICATION_ERROR(c_version_conflict,
        'Claim ' || p_claim_id || ' was changed by someone else (version ' || v_version || ')');
    END IF;

    IF NOT NVL(is_valid_transition(v_status, p_to_status), FALSE) THEN
      RAISE_APPLICATION_ERROR(c_invalid_transition,
        'Cannot move claim from ' || v_status || ' to ' || p_to_status);
    END IF;

    IF v_type = 'LIFE' AND p_to_status = 'APPROVED' THEN
      approve_life_claim(p_claim_id);
    END IF;

    UPDATE claim
       SET status      = p_to_status,
           version     = version + 1,
           updated_at  = SYS_EXTRACT_UTC(SYSTIMESTAMP),
           closed_date = CASE WHEN p_to_status = 'CLOSED' THEN TRUNC(SYSDATE) ELSE closed_date END
     WHERE claim_id = p_claim_id;

    INSERT INTO claim_status_history (claim_id, from_status, to_status, reason, changed_by, changed_at)
    VALUES (p_claim_id, v_status, p_to_status, SUBSTR(p_reason, 1, 300), p_changed_by, SYS_EXTRACT_UTC(SYSTIMESTAMP));

    write_audit('CLAIM', p_claim_id, 'STATUS_CHANGE',
                v_status || ' -> ' || p_to_status || ': ' || p_reason,
                p_changed_by, p_correlation_id);
  END change_claim_status;

  -- ---------------------------------------------------------------- STD benefit
  PROCEDURE calculate_std_benefit(p_claim_id IN NUMBER, p_changed_by IN VARCHAR2) IS
    v_type   claim.claim_type%TYPE;
    v_start  std_claim_detail.disability_start_date%TYPE;
    v_elim   std_claim_detail.elimination_days%TYPE;
    v_salary claimant.weekly_salary%TYPE;
    v_pct    policy.benefit_pct%TYPE;
    v_max    policy.max_weekly_benefit%TYPE;
    v_weekly NUMBER(12, 2);
  BEGIN
    BEGIN
      SELECT c.claim_type, s.disability_start_date, s.elimination_days,
             cl.weekly_salary, p.benefit_pct, p.max_weekly_benefit
        INTO v_type, v_start, v_elim, v_salary, v_pct, v_max
        FROM claim c
        JOIN std_claim_detail s ON s.claim_id = c.claim_id
        JOIN claimant cl        ON cl.claimant_id = c.claimant_id
        JOIN policy p           ON p.policy_id = c.policy_id
       WHERE c.claim_id = p_claim_id;
    EXCEPTION
      WHEN NO_DATA_FOUND THEN
        RAISE_APPLICATION_ERROR(c_benefit_rule,
          'Claim ' || p_claim_id || ' is not an STD claim with details');
    END;

    IF v_pct IS NULL OR v_max IS NULL THEN
      RAISE_APPLICATION_ERROR(c_benefit_rule, 'Policy is missing STD benefit terms');
    END IF;

    v_weekly := ROUND(LEAST(v_salary * v_pct / 100, v_max), 2);

    UPDATE std_claim_detail
       SET weekly_benefit     = v_weekly,
           benefit_start_date = v_start + NVL(v_elim, 0)
     WHERE claim_id = p_claim_id;

    write_audit('CLAIM', p_claim_id, 'BENEFIT_CALCULATED', 'weekly_benefit=' || v_weekly,
                p_changed_by);
  END calculate_std_benefit;

  -- ---------------------------------------------------------------- Life payout
  PROCEDURE approve_life_claim(p_claim_id IN NUMBER) IS
    v_total      NUMBER;
    v_count      PLS_INTEGER;
    v_existing   PLS_INTEGER;
    v_payout     life_claim_detail.payout_amount%TYPE;
    v_amount     NUMBER(14, 2);
    v_paid       NUMBER(14, 2) := 0;
    v_first_id   payment.payment_id%TYPE;
    v_payment_id payment.payment_id%TYPE;
  BEGIN
    SELECT NVL(SUM(share_pct), 0), COUNT(*)
      INTO v_total, v_count
      FROM beneficiary
     WHERE claim_id = p_claim_id;

    IF v_count = 0 OR v_total <> 100 THEN
      RAISE_APPLICATION_ERROR(c_payout_rule,
        'Beneficiary shares must add up to 100 before approval (now ' || v_total || ')');
    END IF;

    SELECT COUNT(*) INTO v_existing FROM payment WHERE claim_id = p_claim_id;
    IF v_existing > 0 THEN
      RAISE_APPLICATION_ERROR(c_payout_rule, 'Payments already exist for this claim');
    END IF;

    BEGIN
      SELECT payout_amount INTO v_payout FROM life_claim_detail WHERE claim_id = p_claim_id;
    EXCEPTION
      WHEN NO_DATA_FOUND THEN
        RAISE_APPLICATION_ERROR(c_not_found, 'Life details missing for claim ' || p_claim_id);
    END;

    FOR b IN (SELECT beneficiary_id, share_pct
                FROM beneficiary
               WHERE claim_id = p_claim_id
               ORDER BY beneficiary_id) LOOP
      v_amount := ROUND(v_payout * b.share_pct / 100, 2);
      INSERT INTO payment (claim_id, beneficiary_id, amount, status, created_at)
      VALUES (p_claim_id, b.beneficiary_id, v_amount, 'PENDING', SYS_EXTRACT_UTC(SYSTIMESTAMP))
      RETURNING payment_id INTO v_payment_id;
      IF v_first_id IS NULL THEN
        v_first_id := v_payment_id;
      END IF;
      v_paid := v_paid + v_amount;
    END LOOP;

    -- Any rounding cent goes to the first beneficiary so the total is exact.
    IF v_paid <> v_payout THEN
      UPDATE payment SET amount = amount + (v_payout - v_paid) WHERE payment_id = v_first_id;
    END IF;
  END approve_life_claim;

  -- ---------------------------------------------------------------- batch: close stale
  PROCEDURE close_stale_claims(p_days_inactive IN NUMBER DEFAULT 180, p_closed OUT NUMBER) IS
    TYPE t_ids      IS TABLE OF claim.claim_id%TYPE;
    TYPE t_statuses IS TABLE OF claim.status%TYPE;
    v_ids      t_ids;
    v_statuses t_statuses;
    v_cutoff   TIMESTAMP := utc_now - NUMTODSINTERVAL(p_days_inactive, 'DAY');
  BEGIN
    SELECT c.claim_id, c.status
      BULK COLLECT INTO v_ids, v_statuses
      FROM claim c
     WHERE (c.status = 'DENIED' AND c.updated_at < v_cutoff)
        OR (c.status = 'APPROVED' AND c.claim_type = 'LIFE' AND c.updated_at < v_cutoff)
        OR (c.status = 'APPROVED' AND c.claim_type = 'STD'
            AND EXISTS (SELECT 1
                          FROM std_claim_detail s
                         WHERE s.claim_id = c.claim_id
                           AND s.return_to_work_date < TRUNC(SYSDATE) - p_days_inactive))
       FOR UPDATE SKIP LOCKED;

    FORALL i IN 1 .. v_ids.COUNT
      UPDATE claim
         SET status = 'CLOSED', closed_date = TRUNC(SYSDATE), version = version + 1,
             updated_at = SYS_EXTRACT_UTC(SYSTIMESTAMP)
       WHERE claim_id = v_ids(i);

    FORALL i IN 1 .. v_ids.COUNT
      INSERT INTO claim_status_history (claim_id, from_status, to_status, reason, changed_by, changed_at)
      VALUES (v_ids(i), v_statuses(i), 'CLOSED',
              'Auto-closed: no activity for ' || p_days_inactive || ' days', 'BATCH', SYS_EXTRACT_UTC(SYSTIMESTAMP));

    p_closed := v_ids.COUNT;
    write_audit('BATCH', 0, 'CLOSE_STALE_CLAIMS', 'closed=' || p_closed, 'BATCH');
    COMMIT;
  END close_stale_claims;

  -- ---------------------------------------------------------------- batch: weekly payments
  PROCEDURE generate_weekly_payments(p_as_of IN DATE DEFAULT TRUNC(SYSDATE), p_created OUT NUMBER) IS
    v_last_end     DATE;
    v_period_start DATE;
    v_period_end   DATE;
    v_benefit_end  DATE;
    v_amount       NUMBER(14, 2);
  BEGIN
    p_created := 0;
    FOR c IN (SELECT cl.claim_id, s.weekly_benefit, s.benefit_start_date, s.return_to_work_date,
                     p.max_benefit_weeks
                FROM claim cl
                JOIN std_claim_detail s ON s.claim_id = cl.claim_id
                JOIN policy p           ON p.policy_id = cl.policy_id
               WHERE cl.claim_type = 'STD'
                 AND cl.status = 'APPROVED'
                 AND s.weekly_benefit IS NOT NULL
                 AND s.benefit_start_date <= p_as_of) LOOP

      SELECT MAX(period_end) INTO v_last_end
        FROM payment
       WHERE claim_id = c.claim_id AND status <> 'CANCELLED';

      -- Benefits stop at return to work or after the policy's max weeks.
      v_benefit_end := c.benefit_start_date + NVL(c.max_benefit_weeks, 26) * 7 - 1;
      IF c.return_to_work_date IS NOT NULL THEN
        v_benefit_end := LEAST(v_benefit_end, c.return_to_work_date - 1);
      END IF;

      v_period_start := NVL(v_last_end + 1, c.benefit_start_date);
      LOOP
        EXIT WHEN v_period_start > v_benefit_end;
        v_period_end := LEAST(v_period_start + 6, v_benefit_end);
        EXIT WHEN v_period_end > p_as_of;  -- only pay periods that are over
        v_amount := ROUND(c.weekly_benefit * (v_period_end - v_period_start + 1) / 7, 2);
        INSERT INTO payment (claim_id, period_start, period_end, amount, status, created_at)
        VALUES (c.claim_id, v_period_start, v_period_end, v_amount, 'PENDING', SYS_EXTRACT_UTC(SYSTIMESTAMP));
        p_created := p_created + 1;
        v_period_start := v_period_end + 1;
      END LOOP;
    END LOOP;

    write_audit('BATCH', 0, 'WEEKLY_PAYMENTS', 'created=' || p_created, 'BATCH');
    COMMIT;
  END generate_weekly_payments;

END claims_pkg;
/
