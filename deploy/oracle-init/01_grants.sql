-- Runs once when the local Oracle container is first created.
-- The app user needs CREATE JOB for the DBMS_SCHEDULER batch jobs.
ALTER SESSION SET CONTAINER = FREEPDB1;
GRANT CREATE JOB TO claimshub;
