"""Deploy the PL/SQL files in db/plsql to Oracle, in file-name order.

Usage:  python -m scripts.deploy_plsql [--skip-jobs]

Fails (exit code 1) if CLAIMS_PKG does not compile, so CI and releases stop early.
"""

import argparse
import re
import sys
from pathlib import Path

from sqlalchemy import text

from app.core.db import engine

PLSQL_DIR = Path(__file__).resolve().parent.parent / "db" / "plsql"


def split_blocks(sql: str) -> list[str]:
    """Split a file on lines that hold only '/' (the SQL*Plus block terminator)."""
    blocks = re.split(r"^\s*/\s*$", sql, flags=re.MULTILINE)
    return [_strip_leading_comments(b) for b in blocks if b.strip() and not _only_comments(b)]


def _strip_leading_comments(block: str) -> str:
    lines = block.strip().splitlines()
    while lines and (not lines[0].strip() or lines[0].strip().startswith("--")):
        lines.pop(0)
    return "\n".join(lines).strip()


def _only_comments(block: str) -> bool:
    return all(not line.strip() or line.strip().startswith("--") for line in block.splitlines())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-jobs", action="store_true", help="skip DBMS_SCHEDULER jobs")
    args = parser.parse_args()

    if engine.dialect.name != "oracle":
        print("deploy_plsql: not an Oracle database, nothing to do")
        return 0

    files = sorted(PLSQL_DIR.glob("*.sql"))
    with engine.begin() as conn:
        for path in files:
            if args.skip_jobs and "scheduler" in path.name:
                print(f"skip  {path.name}")
                continue
            for block in split_blocks(path.read_text()):
                conn.exec_driver_sql(block)
            print(f"ok    {path.name}")

        errors = conn.execute(
            text(
                "SELECT name, type, line, position, text FROM user_errors "
                "WHERE name = 'CLAIMS_PKG' ORDER BY type, sequence"
            )
        ).all()
    if errors:
        print("CLAIMS_PKG has compile errors:")
        for e in errors:
            print(f"  {e.type} line {e.line}:{e.position}  {e.text.strip()}")
        return 1
    print("CLAIMS_PKG compiled with no errors")
    return 0


if __name__ == "__main__":
    sys.exit(main())
