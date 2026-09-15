#!/usr/bin/env python3
"""Check one-test-file preference and protect generated tests from staging."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def check_count(files: list[str]) -> dict[str, object]:
    unique = sorted(set(str(Path(value).resolve()) for value in files))
    return {"allowed": len(unique) <= 1, "test_files": unique, "count": len(unique), "reason": None if len(unique) <= 1 else "more than one test file; split only when scenarios are unrelated"}


def staged(root: Path) -> list[str]:
    completed = subprocess.run(["git", "diff", "--cached", "--name-only"], cwd=root, capture_output=True, text=True, encoding="utf-8", check=False)
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "git staged-file check failed")
    return [line.strip() for line in completed.stdout.splitlines() if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    count = sub.add_parser("count")
    count.add_argument("--file", action="append", required=True)
    protect = sub.add_parser("check-staged")
    protect.add_argument("--root", required=True)
    protect.add_argument("--file", action="append", required=True)
    args = parser.parse_args()
    try:
        if args.command == "count":
            result = check_count(args.file)
        else:
            expected = {Path(value).resolve() for value in args.file}
            staged_files = staged(Path(args.root).resolve())
            hits = [value for value in staged_files if (Path(args.root).resolve() / value).resolve() in expected]
            result = {"allowed": not hits, "generated_tests": [str(value) for value in expected], "staged_hits": hits, "reason": None if not hits else "generated test is staged; remove it unless explicitly requested"}
    except (OSError, RuntimeError) as error:
        print(json.dumps({"allowed": False, "error": str(error)}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(2) from error
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["allowed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
