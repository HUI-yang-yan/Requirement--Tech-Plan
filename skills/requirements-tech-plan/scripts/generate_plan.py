#!/usr/bin/env python3
"""Generate a dated technical-plan file outside the project root."""

from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import re
import sys
from pathlib import Path


def load_name_helper():
    path = Path(__file__).with_name("suggest_names.py")
    spec = importlib.util.spec_from_file_location("suggest_names", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load suggest_names.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def default_output_dir(root: Path) -> Path:
    configured = __import__("os").environ.get("REQUIREMENTS_GOVERNOR_OUTPUT_DIR")
    if configured:
        return Path(configured).resolve()
    return root.parent / f"{root.name}-codex-docs"


def ensure_outside_root(output: Path, root: Path) -> None:
    try:
        output.relative_to(root)
    except ValueError:
        return
    raise ValueError(f"generated documents must be outside project root: {output}")


def replace_known_placeholders(content: str, title: str, branch: str) -> str:
    content = content.replace("<准确需求名>", title)
    content = content.replace("<feature/yyyyMMdd-english-short-name 或 fix/yyyyMMdd-english-short-name>", branch)
    content = re.sub(r"<准确需求名>技术方案", f"{title}技术方案", content)
    return content


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--requirement", required=True)
    parser.add_argument("--content-file", required=True, help="UTF-8 Markdown content prepared by the agent.")
    parser.add_argument("--output-dir")
    parser.add_argument("--date")
    parser.add_argument("--kind", choices=["feature", "fix"])
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.is_dir():
        raise SystemExit(f"project root does not exist: {root}")
    content_file = Path(args.content_file).resolve()
    if not content_file.is_file():
        raise SystemExit(f"content file does not exist: {content_file}")
    day = args.date or dt.date.today().isoformat()
    helper = load_name_helper()
    names = helper.suggest(args.requirement, day, args.kind, "")
    title = helper.clean_title(args.requirement)
    branch = names["branch"]
    output_dir = Path(args.output_dir).resolve() if args.output_dir else default_output_dir(root)
    ensure_outside_root(output_dir, root)
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / Path(names["doc_file"]).name
    if output.exists() and not args.force:
        raise SystemExit(f"plan already exists: {output}; use --force to replace it")
    content = replace_known_placeholders(content_file.read_text(encoding="utf-8"), title, branch)
    output.write_text(content, encoding="utf-8")
    print(json.dumps({"file": str(output), "title": title, "branch": branch, "outside_project_root": True}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
