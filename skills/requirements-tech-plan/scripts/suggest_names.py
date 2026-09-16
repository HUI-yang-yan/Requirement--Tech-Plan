#!/usr/bin/env python3
"""Suggest a technical-plan file name and Git branch name."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import PurePosixPath


KEYWORDS = [
    ("用户", "user"),
    ("账号", "account"),
    ("账户", "account"),
    ("登录", "login"),
    ("认证", "auth"),
    ("订单", "order"),
    ("支付", "payment"),
    ("优惠券", "coupon"),
    ("核销", "redeem"),
    ("通知", "notification"),
    ("消息", "message"),
    ("报表", "report"),
    ("命令行", "cli"),
    ("配置", "config"),
    ("导入", "import"),
    ("导出", "export"),
    ("新增", "create"),
    ("创建", "create"),
    ("更新", "update"),
    ("修改", "update"),
    ("退款", "refund"),
    ("申诉", "appeal"),
    ("审批", "approval"),
    ("作废", "cancel"),
    ("撤回", "cancel"),
    ("拒绝", "reject"),
    ("驳回", "reject"),
    ("归属人", "owner"),
    ("APP", "app"),
    ("删除", "delete"),
    ("权限", "permission"),
    ("库存", "stock"),
    ("页面", "page"),
    ("列表", "list"),
    ("详情", "detail"),
    ("状态", "status"),
    ("同步", "sync"),
    ("锁定", "lock"),
    ("冻结", "lock"),
]

BUG_WORDS = ("bug", "fix", "修复", "缺陷", "故障", "报错", "不生效", "无法", "崩溃")


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


def normalize_slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9-]+", "-", value.strip().lower())
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    if not slug:
        raise ValueError("slug must contain at least one ASCII letter or digit")
    return slug[:48].strip("-")


def suggest(
    text: str,
    date: str | None,
    kind: str | None,
    docs_dir: str,
    slug: str | None = None,
) -> dict[str, str]:
    day = dt.date.fromisoformat(date) if date else dt.date.today()
    title = clean_title(text)
    branch_kind = infer_kind(text, kind)
    branch_slug = normalize_slug(slug) if slug else english_slug(text)
    doc_name = f"{day.isoformat()}-{title}技术方案.md"
    doc_file = str(PurePosixPath(docs_dir) / doc_name)
    branch = f"{branch_kind}/{day:%Y%m%d}-{branch_slug}"
    return {"doc_file": doc_file, "branch": branch}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("text", nargs="*", help="Requirement title or summary.")
    parser.add_argument("--title", help="Requirement title or summary.")
    parser.add_argument("--date", help="Date in yyyy-mm-dd. Defaults to today.")
    parser.add_argument("--kind", choices=["feature", "fix"], help="Branch prefix override.")
    parser.add_argument("--slug", help="Manual English branch slug override for project-specific terms.")
    parser.add_argument("--docs-dir", default="docs", help="Docs directory prefix.")
    args = parser.parse_args()

    text = args.title or " ".join(args.text)
    try:
        result = suggest(text, args.date, args.kind, args.docs_dir, args.slug)
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
