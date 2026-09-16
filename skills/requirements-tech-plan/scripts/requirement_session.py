#!/usr/bin/env python3
"""Persist and guard the lifecycle of one requirement session."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
import uuid
from pathlib import Path


STATES = (
    "ANALYZING",
    "PLAN_CREATED",
    "WAITING_APPROVAL",
    "APPROVED",
    "IMPLEMENTING",
    "TEST_GENERATED",
    "COMPLETED",
)
APPROVAL_WORDS = ("可以修改", "开始修改", "按文档修改", "开始实现", "动代码", "帮我改")


def sessions_root() -> Path:
    configured = os.environ.get("REQUIREMENTS_GOVERNOR_SESSION_DIR")
    if configured:
        return Path(configured)
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "Codex" / "requirements-governor" / "sessions"
    return Path.home() / ".codex" / "requirements-governor" / "sessions"


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def state_path(session_id: str, root: Path) -> Path:
    root_key = hashlib.sha256(str(root.resolve()).lower().encode("utf-8")).hexdigest()[:16]
    return sessions_root() / root_key / f"{session_id}.json"


def read_state(session_id: str, root: Path) -> tuple[dict[str, object], Path]:
    path = state_path(session_id, root)
    if not path.is_file():
        raise ValueError(f"session not found: {session_id}")
    return json.loads(path.read_text(encoding="utf-8")), path


def write_state(state: dict[str, object], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = now()
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def is_source_path(value: str) -> bool:
    # All in-project files need approval, including root configuration and tests.
    return bool(value.strip())


def cmd_start(args: argparse.Namespace) -> dict[str, object]:
    root = Path(args.root).resolve()
    if not root.is_dir():
        raise ValueError(f"project root does not exist: {root}")
    session_id = args.session_id or f"{dt.date.today():%Y%m%d}-{uuid.uuid4().hex[:8]}"
    state = {
        "session_id": session_id,
        "project_root": str(root),
        "requirement": args.requirement.strip(),
        "status": "ANALYZING",
        "plan_file": None,
        "plan_sha256": None,
        "approved": False,
        "approval_text": None,
        "generated_tests": [],
        "created_at": now(),
        "updated_at": now(),
    }
    if not state["requirement"]:
        raise ValueError("requirement must not be empty")
    path = state_path(session_id, root)
    if path.exists() and not args.force:
        raise ValueError(f"session already exists: {session_id}; use --force to replace it")
    write_state(state, path)
    state["state_file"] = str(path)
    return state


def cmd_plan_created(args: argparse.Namespace) -> dict[str, object]:
    root = Path(args.root).resolve()
    state, path = read_state(args.session_id, root)
    if state["status"] not in {"ANALYZING", "PLAN_CREATED"}:
        raise ValueError(f"plan cannot be recorded from state {state['status']}")
    plan = Path(args.plan_file).resolve()
    if not plan.is_file():
        raise ValueError(f"plan file does not exist: {plan}")
    state["status"] = "PLAN_CREATED"
    state["plan_file"] = str(plan)
    state["plan_sha256"] = sha256(plan)
    write_state(state, path)
    state["state_file"] = str(path)
    return state


def cmd_validate_plan(args: argparse.Namespace) -> dict[str, object]:
    root = Path(args.root).resolve()
    state, path = read_state(args.session_id, root)
    if state["status"] != "PLAN_CREATED":
        raise ValueError(f"plan validation cannot start from state {state['status']}")
    plan = Path(str(state["plan_file"]))
    if not plan.is_file():
        raise ValueError(f"recorded plan file does not exist: {plan}")
    if sha256(plan) != state["plan_sha256"]:
        raise ValueError("recorded plan changed after it was created")
    state["status"] = "WAITING_APPROVAL"
    state["plan_validated"] = True
    write_state(state, path)
    state["state_file"] = str(path)
    return state


def cmd_approve(args: argparse.Namespace) -> dict[str, object]:
    root = Path(args.root).resolve()
    state, path = read_state(args.session_id, root)
    if state["status"] != "WAITING_APPROVAL":
        raise ValueError(f"approval cannot start from state {state['status']}")
    text = args.text.strip()
    if not any(word in text for word in APPROVAL_WORDS):
        raise ValueError("approval text does not contain an explicit implementation approval")
    state["status"] = "APPROVED"
    state["approved"] = True
    state["approval_text"] = text
    state["approved_at"] = now()
    write_state(state, path)
    state["state_file"] = str(path)
    return state


def cmd_check_write(args: argparse.Namespace) -> dict[str, object]:
    root = Path(args.root).resolve()
    state, path = read_state(args.session_id, root)
    candidate = Path(args.file)
    if not candidate.is_absolute():
        candidate = root / candidate
    relative = candidate.resolve().relative_to(root).as_posix()
    source = is_source_path(relative)
    allowed = not source or state["status"] in {"APPROVED", "IMPLEMENTING", "TEST_GENERATED", "COMPLETED"}
    next_status = "IMPLEMENTING" if allowed and source and state["status"] == "APPROVED" else state["status"]
    result = {
        "allowed": allowed,
        "file": relative,
        "status": next_status,
        "reason": "approved" if allowed else "source write requires explicit approval after validated plan",
    }
    if allowed and source and state["status"] == "APPROVED":
        state["status"] = "IMPLEMENTING"
        write_state(state, path)
    if not allowed:
        raise PermissionError(json.dumps(result, ensure_ascii=False))
    return result


def cmd_register_test(args: argparse.Namespace) -> dict[str, object]:
    root = Path(args.root).resolve()
    state, path = read_state(args.session_id, root)
    if state["status"] not in {"IMPLEMENTING", "TEST_GENERATED"}:
        raise ValueError(f"test registration cannot start from state {state['status']}")
    test_file = Path(args.file).resolve()
    tests = list(state.get("generated_tests", []))
    if str(test_file) not in tests:
        tests.append(str(test_file))
    state["generated_tests"] = tests
    state["status"] = "TEST_GENERATED"
    write_state(state, path)
    return {
        "session_id": args.session_id,
        "status": state["status"],
        "generated_tests": tests,
        "warning": "more than one test file registered" if len(tests) > 1 else None,
    }


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    start = sub.add_parser("start")
    start.add_argument("--root", required=True)
    start.add_argument("--requirement", required=True)
    start.add_argument("--session-id")
    start.add_argument("--force", action="store_true")

    for name in ("plan-created", "validate-plan", "approve", "check-write", "register-test", "status"):
        command = sub.add_parser(name)
        command.add_argument("--root", required=True)
        command.add_argument("--session-id", required=True)
        if name == "plan-created":
            command.add_argument("--plan-file", required=True)
        elif name == "approve":
            command.add_argument("--text", required=True)
        elif name == "check-write":
            command.add_argument("--file", required=True)
        elif name == "register-test":
            command.add_argument("--file", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    handlers = {
        "start": cmd_start,
        "plan-created": cmd_plan_created,
        "validate-plan": cmd_validate_plan,
        "approve": cmd_approve,
        "check-write": cmd_check_write,
        "register-test": cmd_register_test,
        "status": lambda value: read_state(value.session_id, Path(value.root).resolve())[0],
    }
    try:
        result = handlers[args.command](args)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (OSError, ValueError, PermissionError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(2) from error


if __name__ == "__main__":
    main()
