#!/usr/bin/env python3
"""Suggest a Shirley technical-plan file name and Git branch name."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import PurePosixPath


KEYWORDS = [
    ("退费", "refund"),
    ("退款", "refund"),
    ("申诉", "appeal"),
    ("审批", "approval"),
    ("作废", "cancel"),
    ("撤回", "cancel"),
    ("拒绝", "reject"),
    ("驳回", "reject"),
    ("归属人", "owner"),
    ("大课", "large-class"),
    ("APP", "app"),
    ("开课", "started"),
    ("学员", "student"),
    ("删除", "delete"),
    ("权限", "permission"),
    ("库存", "stock"),
    ("赠品", "gift"),
    ("班级", "class"),
    ("班主任", "teacher"),
    ("销售", "sales"),
    ("页面", "page"),
    ("列表", "list"),
    ("详情", "detail"),
    ("状态", "status"),
    ("同步", "sync"),
]

BUG_WORDS = ("bug", "fix", "修复", "缺陷", "问题", "报错", "异常", "不生效", "失败")


def clean_title(text: str) -> str:
    text = re.sub(r"\s+", "", text.strip())
    text = re.sub(r"[\\/:*?\"<>|#`]+", "", text)
    text = re.sub(r"技术方案$", "", text)
    return text[:40] or "需求"


def infer_kind(text: str, explicit: str | None) -> str:
    if explicit:
        return explicit
    lowered = text.lower()
    return "fix" if any(word in lowered for word in BUG_WORDS) else "feature"


def english_slug(text: str) -> str:
    lowered = text.lower()
    tokens: list[str] = []

    for cn, en in KEYWORDS:
        if cn.lower() in lowered and en not in tokens:
            tokens.append(en)

    ascii_words = re.findall(r"[a-zA-Z][a-zA-Z0-9]+", text)
    for word in ascii_words:
        word = word.lower()
        if word not in {"this", "that", "need", "requirement", "change"} and word not in tokens:
            tokens.append(word)

    if not tokens:
        tokens = ["requirement"]

    slug = "-".join(tokens)
    slug = re.sub(r"[^a-z0-9-]+", "-", slug)
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug[:48].strip("-") or "requirement"


def suggest(text: str, date: str | None, kind: str | None, docs_dir: str) -> dict[str, str]:
    day = dt.date.fromisoformat(date) if date else dt.date.today()
    title = clean_title(text)
    branch_kind = infer_kind(text, kind)
    slug = english_slug(text)
    doc_name = f"{day.isoformat()}-{title}技术方案.md"
    doc_file = str(PurePosixPath(docs_dir) / doc_name)
    branch = f"{branch_kind}/{day:%Y%m%d}-{slug}"
    return {"doc_file": doc_file, "branch": branch}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("text", nargs="*", help="Requirement title or summary.")
    parser.add_argument("--title", help="Requirement title or summary.")
    parser.add_argument("--date", help="Date in yyyy-mm-dd. Defaults to today.")
    parser.add_argument("--kind", choices=["feature", "fix"], help="Branch prefix override.")
    parser.add_argument("--docs-dir", default="docs", help="Docs directory prefix.")
    args = parser.parse_args()

    text = args.title or " ".join(args.text)
    print(json.dumps(suggest(text, args.date, args.kind, args.docs_dir), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
