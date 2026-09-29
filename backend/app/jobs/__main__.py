"""Run a batch job by hand (the same code DBMS_SCHEDULER runs every night).

Usage:
  python -m app.jobs close-stale-claims [--days 180]
  python -m app.jobs weekly-payments
"""

import argparse
import logging

from app.core.config import get_settings
from app.core.db import engine
from app.core.logging import setup_logging

log = logging.getLogger("claimshub.jobs")


def main() -> None:
    setup_logging(get_settings().log_level)
    parser = argparse.ArgumentParser()
    parser.add_argument("job", choices=["close-stale-claims", "weekly-payments"])
    parser.add_argument("--days", type=int, default=180)
    args = parser.parse_args()
    if engine.dialect.name != "oracle":
        raise SystemExit(
            "Batch jobs run in Oracle (CLAIMS_PKG). Point CLAIMSHUB_DATABASE_URL at Oracle."
        )

    with engine.connect() as conn:
        raw = conn.connection.dbapi_connection
        assert raw is not None
        cur = raw.cursor()
        out = cur.var(int)
        if args.job == "close-stale-claims":
            cur.callproc("claims_pkg.close_stale_claims", [args.days, out])
        else:
            cur.execute(
                "BEGIN claims_pkg.generate_weekly_payments(TRUNC(SYSDATE), :n); END;", {"n": out}
            )
        count = out.getvalue()
    log.info("batch_job_done", extra={"event": "batch_job_done", "job": args.job, "rows": count})
    print(f"{args.job}: {count} rows")


if __name__ == "__main__":
    main()
