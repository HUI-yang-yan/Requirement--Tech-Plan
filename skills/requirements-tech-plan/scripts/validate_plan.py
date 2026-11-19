#!/usr/bin/env python3
"""Validate the structure and traceability of a technical-plan Markdown file."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


SECTIONS = (
    "## 1. 需求目标与范围",
    "## 2. 现有业务逻辑",
    "## 3. 涉及项目与模块",
    "## 4. 涉及数据存储、字段与关系",
    "## 5. 详细修改逻辑",
    "## 6. 接口与核心代码修改点",
    "## 7. 页面、客户端与调用方修改点",
    "## 8. 修改前后页面与交互",
    "## 9. 历史数据、兼容性与影响范围",
    "## 10. 测试与回归点",
)
LOCATION_RE = re.compile(r"`(?P<path>(?:[A-Za-z]:[\\/])?[^`\n<>]+):(?P<line>[1-9][0-9]*)`")
PLAN_FILE_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}-.+技术方案\.md$")


def template_placeholders() -> set[str]:
    template = Path(__file__).resolve().parents[1] / "assets" / "technical-plan-template.md"
    return set(re.findall(r"<[^>\n]+>", template.read_text(encoding="utf-8")))


def check_location(match: re.Match[str], root: Path) -> str | None:
    raw_path = match.group("path").strip().strip("` ")
    line = int(match.group("line"))
    # Plans use portable forward-slash paths, even when generated on Windows.
    normalized_path = raw_path.replace("\\", "/")
    candidate = Path(normalized_path)
    if not candidate.is_absolute():
        candidate = root / candidate
    if not candidate.is_file():
        return f"location file does not exist: {raw_path}:{line}"
    count = len(candidate.read_text(encoding="utf-8", errors="replace").splitlines())
    if line > count:
        return f"location line exceeds file length: {raw_path}:{line} (lines={count})"
    return None


def validate(plan: Path, root: Path | None) -> dict[str, object]:
    text = plan.read_text(encoding="utf-8")
    errors: list[str] = []
    if not PLAN_FILE_RE.fullmatch(plan.name):
        errors.append("plan filename must be yyyy-mm-dd-<accurate-name>技术方案.md")
    if not text.startswith("【需求分析模式：最小改动技术文档】"):
        errors.append("missing required opening marker")
    missing = [section for section in SECTIONS if section not in text]
    errors.extend(f"missing section: {section}" for section in missing)
    present_positions = [text.find(section) for section in SECTIONS if section in text]
    if present_positions != sorted(present_positions):
        errors.append("numbered sections are out of order")
    duplicated = [section for section in SECTIONS if text.count(section) > 1]
    errors.extend(f"duplicate section: {section}" for section in duplicated)
    unresolved = sorted(placeholder for placeholder in template_placeholders() if placeholder in text)
    if unresolved:
        errors.append("unresolved template placeholders remain: " + ", ".join(unresolved))
    if not re.search(r"## 建议 Git 分支名称\s+\n\s*(?:feature|fix)/[0-9]{8}-[a-z0-9-]+", text):
        errors.append("missing valid suggested Git branch name")
    if "| 数据源/表/集合 |" not in text or "| 当前相关字段 |" not in text:
        errors.append("involved data-source/field table is missing")
    for required in ("当前逻辑", "修改后逻辑", "修改步骤", "异常与边界", "最小改动说明"):
        if required not in text:
            errors.append(f"missing modification-logic item: {required}")
    for required in ("修改前", "修改后"):
        if required not in text:
            errors.append(f"missing UI before/after item: {required}")
    for required in ("输入/前置条件", "操作链路", "预期结果", "控制台输出"):
        if required not in text:
            errors.append(f"missing test trace item: {required}")
    if root is not None:
        try:
            plan.relative_to(root)
            errors.append("generated plan must be outside project root")
        except ValueError:
            pass
        locations = list(LOCATION_RE.finditer(text))
        if not locations:
            errors.append("no path:line traceability locations found")
        for match in locations:
            location_error = check_location(match, root)
            if location_error:
                errors.append(location_error)
    return {"valid": not errors, "file": str(plan), "errors": errors, "sections": len(SECTIONS) - len(missing)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("plan_file")
    parser.add_argument("--project-root")
    args = parser.parse_args()
    try:
        result = validate(Path(args.plan_file).resolve(), Path(args.project_root).resolve() if args.project_root else None)
    except OSError as error:
        print(json.dumps({"valid": False, "errors": [str(error)]}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(2) from error
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["valid"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
