#!/usr/bin/env python3
"""Reject SQL that can mutate data or schema; never executes SQL."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


MUTATING = re.compile(r"\b(INSERT|UPDATE|DELETE|ALTER|DROP|CREATE|TRUNCATE|REPLACE|MERGE|GRANT|REVOKE|CALL|SET|LOCK|UNLOCK|LOAD|DO)\b", re.I)
READ_START = re.compile(r"^(SELECT|WITH|SHOW|DESCRIBE|DESC|EXPLAIN)\b", re.I)
READ_FORBIDDEN = re.compile(r"\b(INTO\s+(OUTFILE|DUMPFILE)|FOR\s+UPDATE|LOCK\s+IN\s+SHARE\s+MODE)\b", re.I)


def strip_comments(sql: str) -> str:
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.S)
    sql = re.sub(r"--[^\n]*", " ", sql)
    return re.sub(r"#[^\n]*", " ", sql)


def split_statements(sql: str) -> list[str]:
    return [part.strip() for part in strip_comments(sql).split(";") if part.strip()]


def inspect(sql: str) -> dict[str, object]:
    violations: list[dict[str, object]] = []
    statements = split_statements(sql)
    for index, statement in enumerate(statements, start=1):
        normalized = re.sub(r"\s+", " ", statement).strip()
        if not READ_START.match(normalized) or MUTATING.search(normalized) or READ_FORBIDDEN.search(normalized):
            violations.append({"statement": index, "preview": normalized[:240], "reason": "only read-only query SQL is allowed"})
    return {"allowed": not violations, "statement_count": len(statements), "violations": violations, "executed": False}


def main() -> None:
    parser = argparse.ArgumentParser()
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--file")
    source.add_argument("--sql")
    args = parser.parse_args()
    try:
        sql = Path(args.file).read_text(encoding="utf-8") if args.file else args.sql
        result = inspect(sql)
    except OSError as error:
        print(json.dumps({"allowed": False, "error": str(error)}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(2) from error
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["allowed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
