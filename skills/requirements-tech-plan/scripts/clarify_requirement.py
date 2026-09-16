#!/usr/bin/env python3
"""Suggest concise clarification questions for software requirements.

This script is intentionally heuristic. It helps the agent notice high-impact
ambiguity, then the agent should refine the final wording with project context.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Rule:
    name: str
    patterns: tuple[str, ...]
    resolved_patterns: tuple[str, ...]
    question: str
    recommendation: str
    assumption: str
    impact: str


RULES = [
    Rule(
        name="authority",
        patterns=("禁止", "不允许", "不能", "权限", "删除", "拦截"),
        resolved_patterns=("禁止", "不允许", "不能", "不可"),
        question="命中限制后是完全禁止，还是允许特定角色/主管强制继续？",
        recommendation="建议完全禁止或以后端业务规则为准；如果需要例外权限，应在需求中明确权限码和审计痕迹。",
        assumption="命中业务限制后不允许绕过，后端作为最终兜底。",
        impact="决定是后端硬校验、权限例外，还是仅前端体验限制。",
    ),
    Rule(
        name="state-source",
        patterns=("状态", "完成", "通过", "拒绝", "生效", "失效", "结束", "进行中"),
        resolved_patterns=("被拒绝时", "拒绝时", "通过时", "完成时"),
        question="这个状态以哪个字段/时间为准：业务发生时间、审批状态，还是页面展示状态？",
        recommendation="建议优先使用后端稳定字段或已有状态枚举，避免依赖前端展示文案。",
        assumption="状态口径优先沿用后端已有字段/枚举，并在技术方案中写明。",
        impact="决定查询条件、边界判断和历史数据表现。",
    ),
    Rule(
        name="lifecycle",
        patterns=("关联", "联动", "同步", "作废", "撤回", "取消", "恢复"),
        resolved_patterns=("仍在审批中", "审批中", "进行中", "未完成"),
        question="联动处理只影响进行中的记录，还是也处理已完成/历史记录？",
        recommendation="建议只处理仍在进行中的记录，已完成记录保留历史痕迹。",
        assumption="只联动处理进行中数据，已完成历史不回改。",
        impact="决定更新范围，避免误改历史审批或业务记录。",
    ),
    Rule(
        name="history",
        patterns=("历史", "补偿", "已有", "存量", "之前", "老数据"),
        resolved_patterns=(),
        question="这个需求需要处理历史存量数据，还是只对新发生流程生效？",
        recommendation="建议默认只处理新流程；历史补偿涉及数据脚本和核对，应单独确认。",
        assumption="仅处理新发生流程，不主动补偿历史数据。",
        impact="决定是否需要数据脚本、批处理、回滚方案。",
    ),
    Rule(
        name="ownership",
        patterns=("归属", "责任人", "负责人", "所有者", "人员", "归因", "owner", "assignee"),
        resolved_patterns=(),
        question="归属结果以当次保存的业务快照为准，还是每次按当前组织关系实时计算？",
        recommendation="建议保存当次业务选择结果，避免组织或人员变化导致历史漂移。",
        assumption="归属类结果保存当次选择或当次业务快照，不以后续实时关系覆盖历史。",
        impact="决定是否写入审批内容、业务表字段或仅展示计算结果。",
    ),
    Rule(
        name="ui-result",
        patterns=("页面", "按钮", "弹窗", "提示", "展示", "隐藏", "禁用", "样式"),
        resolved_patterns=(),
        question="前端是隐藏入口、禁用入口，还是保留入口并展示后端错误提示？",
        recommendation="建议后端硬校验，前端按体验隐藏或禁用；错误提示作为兜底。",
        assumption="前端只做体验优化，后端负责最终业务校验。",
        impact="决定前端改动范围和后端错误文案。",
    ),
]

GENERIC_BAD_PATTERNS = ("优化", "调整", "处理一下", "完善", "支持")


def contains_any(text: str, patterns: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(pattern.lower() in lowered for pattern in patterns)


def score_rule(text: str, rule: Rule) -> int:
    score = sum(1 for pattern in rule.patterns if pattern.lower() in text.lower())
    if rule.name in {"authority", "state-source", "lifecycle"}:
        score += 1 if score else 0
    return score


def clarify(text: str, max_questions: int) -> dict[str, object]:
    text = re.sub(r"\s+", " ", text.strip())
    scored = [(score_rule(text, rule), rule) for rule in RULES]
    matched = [item for item in scored if item[0] > 0]
    matched.sort(key=lambda item: (-item[0], item[1].name))

    blocking = []
    assumptions = []
    do_not_ask = [
        "不要问“这个需求具体怎么做”，应先根据代码和业务词分析。",
        "不要问“是否需要改前端/后端”，应由技术分析判断。",
        "不要问“还有其他要求吗”，应聚焦会改变实现方向的问题。",
    ]

    unresolved = []
    for _, rule in matched:
        if rule.resolved_patterns and contains_any(text, rule.resolved_patterns):
            assumptions.append({"topic": rule.name, "assumption": rule.assumption, "why": rule.impact})
        else:
            unresolved.append(rule)

    for rule in unresolved[:max_questions]:
        blocking.append(
            {
                "topic": rule.name,
                "question": rule.question,
                "recommended_answer": rule.recommendation,
                "why_it_matters": rule.impact,
            }
        )

    for rule in unresolved[max_questions:]:
        assumptions.append({"topic": rule.name, "assumption": rule.assumption, "why": rule.impact})

    if not matched:
        assumptions.append(
            {
                "topic": "minimum-change",
                "assumption": "按现有项目模式做最小改动，优先复用已有字段、接口和状态。",
                "why": "需求文本未暴露会改变实现方向的高风险歧义。",
            }
        )

    if contains_any(text, GENERIC_BAD_PATTERNS) and len(blocking) < max_questions:
        blocking.append(
            {
                "topic": "success-criteria",
                "question": "这个需求完成后，用户视角下最关键的可观察结果是什么？",
                "recommended_answer": "建议用一个具体操作结果描述成功标准，例如按钮不可点、审批自动作废、列表新增字段可见。",
                "why_it_matters": "泛化需求容易导致方案只改表象，成功标准能锁定最小闭环。",
            }
        )

    return {
        "blocking_questions": blocking[:max_questions],
        "recommended_assumptions": assumptions,
        "do_not_ask": do_not_ask,
        "question_budget": max_questions,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("text", nargs="*", help="Requirement text.")
    parser.add_argument("--max-questions", type=int, default=3)
    args = parser.parse_args()

    max_questions = max(0, min(args.max_questions, 3))
    print(json.dumps(clarify(" ".join(args.text), max_questions), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
