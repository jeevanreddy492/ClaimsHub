-- Nightly and weekly batch jobs. Needs the CREATE JOB privilege.
-- Safe to run again: an existing job (ORA-27477) is left as it is.
BEGIN
  DBMS_SCHEDULER.CREATE_JOB(
    job_name        => 'CLAIMSHUB_CLOSE_STALE_CLAIMS',
    job_type        => 'PLSQL_BLOCK',
    job_action      => 'DECLARE n NUMBER; BEGIN claims_pkg.close_stale_claims(180, n); END;',
    start_date      => SYSTIMESTAMP,
    repeat_interval => 'FREQ=DAILY; BYHOUR=2; BYMINUTE=0',
    enabled         => TRUE,
    comments        => 'Close denied/paid claims with no activity for 180 days');
EXCEPTION
  WHEN OTHERS THEN
    IF SQLCODE <> -27477 THEN RAISE; END IF;
END;
/

BEGIN
  DBMS_SCHEDULER.CREATE_JOB(
    job_name        => 'CLAIMSHUB_WEEKLY_PAYMENTS',
    job_type        => 'PLSQL_BLOCK',
    job_action      => 'DECLARE n NUMBER; BEGIN claims_pkg.generate_weekly_payments(TRUNC(SYSDATE), n); END;',
    start_date      => SYSTIMESTAMP,
    repeat_interval => 'FREQ=DAILY; BYHOUR=3; BYMINUTE=0',
    enabled         => TRUE,
    comments        => 'Create STD payments for every finished benefit week');
EXCEPTION
  WHEN OTHERS THEN
    IF SQLCODE <> -27477 THEN RAISE; END IF;
END;
/
