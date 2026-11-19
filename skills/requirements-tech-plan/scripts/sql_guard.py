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
    sql = strip_comments(sql)
    statements: list[str] = []
    current: list[str] = []
    quote: str | None = None
    index = 0
    while index < len(sql):
        char = sql[index]
        if quote:
            current.append(char)
            if char == quote:
                if index + 1 < len(sql) and sql[index + 1] == quote:
                    current.append(sql[index + 1])
                    index += 1
                else:
                    quote = None
        elif char in {"'", '"', "`"}:
            quote = char
            current.append(char)
        elif char == ";":
            statement = "".join(current).strip()
            if statement:
                statements.append(statement)
            current = []
        else:
            current.append(char)
        index += 1
    statement = "".join(current).strip()
    if statement:
        statements.append(statement)
    return statements


def mask_quoted_values(sql: str) -> str:
    return re.sub(r"'(?:''|[^'])*'|\"(?:\"\"|[^\"])*\"|`(?:``|[^`])*`", "''", sql)


def inspect(sql: str) -> dict[str, object]:
    violations: list[dict[str, object]] = []
    statements = split_statements(sql)
    if not statements:
        violations.append({"statement": 0, "preview": "", "reason": "SQL must contain at least one read-only query"})
    for index, statement in enumerate(statements, start=1):
        normalized = re.sub(r"\s+", " ", statement).strip()
        inspected = mask_quoted_values(normalized)
        if not READ_START.match(inspected) or MUTATING.search(inspected) or READ_FORBIDDEN.search(inspected):
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
