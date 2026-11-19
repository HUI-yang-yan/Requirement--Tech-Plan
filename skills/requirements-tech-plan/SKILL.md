---
name: requirements-tech-plan
description: Use when the user explicitly invokes this skill for a technical plan, requirement analysis, code-location review, or implementation workflow in an existing software project.
---

# Requirements Tech Plan

## Invocation

This skill is explicit-only. Use it when the user invokes `$requirements-governor:requirements-tech-plan` or explicitly asks for this technical-plan workflow. Ordinary requests remain governed by the project instructions and the user's current request.

## Core Rule

When this skill is explicitly invoked, first create a real Markdown technical plan in the configured external output directory. Do not modify source code, tests, configuration, or database state until the document exists and the user gives a separate approval after reading it.

This skill is a workflow and quality gate, not a fixed answer template. Keep the plan project-specific, concise, and traceable to code.

Discover actual languages, module roots, entry points and persistence from source and build configuration. Do not assume Java layers, a database, HTTP APIs, or a frontend exist. Keep document sections but explain inapplicable sections instead of inventing components. Use the existing architecture's names for the real call chain.

## Workflow

1. Confirm the active project root and read `AGENTS.md`; read `docs/codex-qa.md` when it exists.
2. Clarify the requirement: run `scripts/clarify_requirement.py` or apply `references/clarifying-questions.md` before deep planning.
3. Ask at most 1-3 blocking questions only when the answer can change the implementation direction; otherwise record recommended assumptions and continue.
4. Run `scripts/collect_evidence.py` once to recall cross-layer candidates quickly. By default it searches the full project root; after discovering the repository, pass repeated `--search-root <module>` values when the affected modules are known. Treat its output as candidates, not conclusions.
5. Read current source around the candidates and confirm the live call chain and exact line numbers. If `requires_deep_search` is true, an expected project-specific component is absent, or the chain breaks, fall back to targeted full-repository `rg` searches.
6. Generate document and branch names. Prefer `scripts/suggest_names.py` when title naming is not obvious. If project-specific Chinese terms produce a generic slug, supply an accurate `--slug <english-short-name>` rather than accepting `requirement`.
7. Prepare substantive Markdown content from `assets/technical-plan-template.md`, then run `scripts/generate_plan.py` to write it outside the project root.
8. Run `scripts/validate_plan.py <plan-file> --project-root <project-root>` and repair the document until it passes, then stop and ask whether to implement.

Use the collector from the skill directory:

```powershell
python scripts/collect_evidence.py --root <project-root> --requirement "<original requirement>"
```

For a large monorepo, scope it without hard-coded project names:

```powershell
python scripts/collect_evidence.py --root <project-root> --search-root <module-a> --search-root <module-b> --requirement "<original requirement>"
```

Do not cite a cached location without opening the current file around that location. Avoid reading large source files in full: locate with evidence or `rg -n`, then read only the smallest useful surrounding range.

The evidence cache is only a search accelerator. It does not learn project semantics, prove a call chain, or authorize skipping current-source reads. A cache hit must still be verified against the live files.

Generated artifacts must stay outside the project root. Use `generate_plan.py` for technical plans and keep SQL files beside the external document output. Before any SQL-related action, run `sql_guard.py`; only read-only query SQL is allowed and the script never executes SQL. Before configuring database access, run `db_mapping_guard.py`; if any interface has no database mapping, ask the user for the mapping and do not change code until it is supplied. When backend/service tests apply, prefer one test file per requirement; use `test_file_guard.py count` when more than one file is proposed, and use `check-staged` to keep generated tests out of Git staging.

Available scripts:

- `clarify_requirement.py`: identify high-impact clarification candidates.
- `collect_evidence.py`: cache-safe cross-layer code candidate search.
- `suggest_names.py`: dated document and branch naming.
- `requirement_session.py`: optionally persist phase state, run the same plan validator before approval, and report whether a project-file write is allowed when explicitly called; it does not intercept writes or authenticate who supplied approval text.
- `generate_plan.py`: write prepared Markdown outside the project root.
- `validate_plan.py`: validate sections, tables, logic, console trace, path/line references, and output location.
- `sql_guard.py`: allow only read-only query SQL; never execute SQL.
- `db_mapping_guard.py`: require explicit endpoint-to-database mappings.
- `test_file_guard.py`: enforce the one-test-file preference and detect staged generated tests.

## References

Load only the reference needed for the current step:

- `assets/technical-plan-template.md`: required output skeleton. Copy its structure, then replace every placeholder.
- `references/document-format.md`: content rules for current logic, affected data stores, modification logic, code locations, user-visible behavior, compatibility, and tests.
- `references/clarifying-questions.md`: how to ask only high-impact product/business questions and avoid noisy questioning.
- `references/quality-gate.md`: phase rules, source-change prohibition, exact `path:line` requirements, implementation-stage test rules, failure modes to avoid.
- `references/project-map.md`: discover actual project layout and extend candidate searches.

## Skill Conflict Rule

When explicitly invoked, use this skill for Phase 1, subject to higher-priority instructions and the user's current requirements.

The technical plan itself is the design artifact; do not introduce a second generic design-document workflow unless requested or required by applicable instructions.

Use brainstorming-style judgment only inside this skill's clarification step: ask at most 1-3 high-impact questions, then continue to the technical-plan workflow.

Keep implementation testing in Phase 2. Follow explicit user and project testing requirements; distinguish tests not required by default from tests forbidden by the user.

## Phase Boundary

Phase 1 is document-only. Allowed work: search, read, analyze, and write the technical方案 Markdown to an external output directory. Do not create generated documents or SQL files inside the project root.

Phase 2 begins only after a separate follow-up approval after the document exists, such as `可以修改`, `开始修改`, `按文档修改`, `开始实现`, `动代码`, or `帮我改`.

Original requirement wording such as "修改/实现/处理/修复/直接改" is not Phase 2 approval.

## Minimal Change Rule

All Phase 2 changes must exist only to complete the current approved requirement.

Do not add unrelated behavior, broad refactors, speculative compatibility layers, new abstractions, or extra complex logic. Prefer the smallest code path that satisfies the requirement and preserves existing behavior.

Do not omit bugs introduced by the requirement change: cover direct side effects, boundary states, and regressions that naturally follow from the current requirement.

## Implementation Preference

When Phase 2 is approved, use the smallest code change that completes the requirement. Prefer existing fields, APIs, services, and patterns. Add a small helper/private method when it makes the change easier to reason about or prevents duplicated condition logic.

After backend/service changes, do not compile that backend for verification. Generate unit tests that cover its real business chain, but do not run them unless the user explicitly asks. Prefer one test file per requirement unless scenarios are unrelated. Each generated backend/service test must print a clear full-flow trace to the console: input/precondition, entry method, important collaborations, data or status changes, exception/boundary result, and final assertion result. Do not stage or commit generated tests unless the user explicitly asks. Do not require frontend validation/build/lint unless the user explicitly asks. For projects without a backend/service, follow the applicable project instructions and document why backend testing is not applicable.

## Final Response After Phase 1

Reply briefly:

```markdown
【需求分析模式：最小改动技术文档】
已生成技术方案：[文件名](绝对路径)

需要确认：...

是否按该技术方案开始修改代码？
```

Do not paste the full document unless the user asks.
