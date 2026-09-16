# Clarifying Questions

Use this before writing the technical方案 when the requirement may be under-specified.

## Principle

Ask only questions that can change the implementation direction. Do not ask the user to do Codex's analysis work.

Good questions isolate business boundaries, authority, lifecycle, state source, data ownership, and historical handling. Bad questions ask for generic implementation instructions.

## Question Budget

- Ask 0 questions when code and existing docs give a safe answer.
- Ask 1 question when one business boundary controls the whole solution.
- Ask 2-3 questions only when separate answers affect separate implementation paths.
- Never ask more than 3 questions in one response.
- If there are many doubts, collapse them into the one decision that controls the most downstream changes.

## Blocking vs Non-Blocking

Blocking question:

- The answer changes database/API/page/permission/workflow design.
- A wrong assumption causes meaningful rework or user-visible data errors.
- Existing code cannot reveal the correct business rule.

Non-blocking uncertainty:

- The answer affects only copy text or minor UI wording.
- The current code has an obvious existing pattern.
- A recommended default can be documented in the technical方案.
- The issue can be verified during implementation without changing the plan.

For non-blocking uncertainty, write a recommended assumption instead of stopping.

## High-Value Question Types

Prefer these:

- Authority: "命中条件后是完全禁止，还是允许特定角色强制继续？我建议完全禁止，因为这是数据一致性限制。"
- State source: "生效状态以服务端状态枚举、业务时间还是客户端展示值为准？我建议使用现有服务端权威字段。"
- Lifecycle: "主记录终止后，关联流程只处理进行中记录，还是也回改已完成历史？我建议只处理进行中记录并保留历史痕迹。"
- Scope: "这次只处理新流程，还是需要补偿历史数据？我建议只处理新发生数据，历史补偿另开任务。"
- Ownership: "归属结果以当次保存快照为准，还是每次按当前组织关系实时计算？我建议保存当次结果，避免历史漂移。"
- User-visible result: "拦截时需要前端隐藏按钮，还是保留按钮并展示后端错误？我建议后端兜底，前端只做体验优化。"

Avoid these:

- "这个需求具体怎么做？"
- "是否需要改前端？"
- "是否需要加字段？"
- "还有其他要求吗？"
- "请提供完整流程。"

## Response Shape

When asking:

```text
我有 2 个会影响实现边界的问题：

1. <问题>
   我建议：<推荐答案和理由>。

2. <问题>
   我建议：<推荐答案和理由>。
```

When not asking:

```text
我会按以下默认假设生成技术方案：

- <假设一>，因为 <依据>。
- <假设二>，因为 <依据>。
```

## Document Integration

In the technical方案:

- Put blocking unresolved items under `需要确认` or in the relevant section.
- Put non-blocking assumptions in `## 1. 需求范围`.
- Do not hide assumptions in final chat only; the Markdown document must carry them.
