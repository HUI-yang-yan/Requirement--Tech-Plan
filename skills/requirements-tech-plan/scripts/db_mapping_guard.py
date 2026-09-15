#!/usr/bin/env python3
"""Require explicit endpoint-to-database mapping before DB configuration changes."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def load(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def endpoints(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, dict):
        return [str(key) for key in value]
    raise ValueError("interfaces JSON must be an array or object")


def mapping(value: object) -> dict[str, str]:
    if not isinstance(value, dict):
        raise ValueError("mapping JSON must be an object")
    return {str(key): str(database) for key, database in value.items() if str(database).strip()}


def check(interface_value: object, mapping_value: object) -> dict[str, object]:
    interface_names = endpoints(interface_value)
    database_mapping = mapping(mapping_value)
    missing = [name for name in interface_names if name not in database_mapping]
    return {
        "allowed": not missing,
        "requires_user_confirmation": bool(missing),
        "interfaces": interface_names,
        "mapping": database_mapping,
        "missing_interfaces": missing,
        "reason": None if not missing else "ask the user which database each missing interface should access before changing code",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--interfaces-file", required=True)
    parser.add_argument("--mapping-file", required=True)
    args = parser.parse_args()
    try:
        result = check(load(Path(args.interfaces_file)), load(Path(args.mapping_file)))
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(json.dumps({"allowed": False, "error": str(error)}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(2) from error
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["allowed"]:
        raise SystemExit(3)


if __name__ == "__main__":
    main()
