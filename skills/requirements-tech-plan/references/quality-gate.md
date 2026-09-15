# Requirements Quality Gate

Use this before responding after Phase 1 or finishing Phase 2.

## Skill Priority

When `requirements-tech-plan` is explicitly invoked for Shirley CRM, it owns Phase 1. Do not run the generic `superpowers:brainstorming` design-doc workflow before the Shirley technical方案. The required design artifact is an external-output `<yyyy-mm-dd>-<准确需求名>技术方案.md`.

If `superpowers:test-driven-development` or another generic testing workflow conflicts with this Shirley workflow, prefer `requirements-tech-plan`. The conflict resolution is narrow: generate valuable backend test code in Phase 2, but do not require a red/green test execution loop unless the user explicitly asks for it.

## Phase 1 Red Lines

Phase 1 may only:

- search files
- read code
- inspect routes, APIs, controller methods, biz/service/domain/api classes, mapper logic, frontend components, existing docs
- create or update the requirement technical方案 Markdown in an external output directory outside the project root

Phase 1 must not:

- edit source implementation files
- edit or create tests
- format code
- commit changes
- change database data or schema
- start implementation
- say "我开始改文件" about source code
- treat the original requirement as implementation approval

If source code was changed by mistake during Phase 1, stop immediately and report it.

## Phase 2 Entry

Only enter Phase 2 after the Markdown technical方案 exists and the user separately approves implementation.

Accepted examples:

- 可以修改
- 开始修改
- 按文档修改
- 开始实现
- 动代码
- 帮我改

## Phase 1 Document Checklist

Before final response, verify:

- A `.md` file was created or updated outside the project root in the configured document output directory.
- The filename contains date and accurate requirement name.
- The document starts with `【需求分析模式：最小改动技术文档】`.
- The document includes `## 建议 Git 分支名称`.
- The branch name uses `feature/yyyyMMdd-...` or `fix/yyyyMMdd-...`.
- High-impact ambiguity was checked before writing the plan.
- Blocking questions are limited to 1-3 and include recommended answers.
- Non-blocking ambiguity is recorded as assumptions in `需求范围`.
- The document uses all ten required numbered sections from `assets/technical-plan-template.md`.
- `需求范围` says what is in scope and out of scope.
- `现有业务逻辑` explains the live entry, call chain, data read/write, status transition, and current problem.
- `涉及项目与模块` identifies which inspected projects/modules change and why.
- `涉及表、字段与数据关系` lists queried or modified tables, fields, relation keys, data impact, schema impact, and historical-data handling, or explicitly proves that no table is involved.
- `详细修改逻辑` is organized by business module and includes current logic, changed logic, ordered steps, direct boundaries, and minimum-change justification.
- `接口与后端代码修改点` includes concrete files/classes/methods and exact line numbers for every planned change.
- `前端修改点` includes concrete files/components/API calls and exact line numbers for every planned change, or explains why none are needed.
- Every planned modification uses `path:line`; class names or method names alone are insufficient.
- Every cached candidate cited in the document was re-opened and verified against current source.
- Sparse evidence, missing layers, or a broken call chain triggered a broader `rg` search before completing the document.
- `修改前后页面与交互` includes before and after behavior.
- `历史数据、兼容性与影响范围` explicitly covers cleanup, old records, old callers, and affected downstream paths.
- `测试单元与回归点` includes backend and frontend/regression checks as applicable.
- The backend test plan names a test file/class and requires an obvious console trace for input, entry, important calls, before/after data or status, exception/boundary result, and final assertion result.
- No template placeholder such as `<...>` remains in the generated document.
- No source implementation files were changed in Phase 1.
- No SQL other than read-only query SQL was executed; normally SQL is only inspected or generated as a file.
- Database configuration changes were not made until every affected interface had an explicit database mapping.
- Generated artifacts, including SQL files, were kept outside the project root.
- The requirement uses one generated backend test file unless the test scenarios are unrelated.
- No unrelated logic or extra complex implementation is proposed.

If any checklist item fails, continue read-only investigation or revise the Markdown document before responding.

## Minimal Change Guard

Every planned or implemented change must be necessary for the current requirement.

- Do not add unrelated logic, speculative features, broad refactors, or extra compatibility branches.
- Do not introduce complex abstractions when a direct local change completes the requirement.
- Do not modify behavior outside the current requirement's affected chain unless needed to prevent a bug caused by this requirement.
- Do cover bugs and regressions naturally introduced by the requirement, including boundary states and downstream status/data changes.

## Flexible Planning Rules

- Do not force a frontend section to propose changes when the backend alone completes the requirement.
- Do not propose new tables or fields unless existing fields cannot satisfy the requirement.
- Do not only hide/disable frontend controls when backend validation is needed.
- Keep long serialized fields short: name the keys, source object, and usage; avoid oversized dumps.
- It is acceptable to propose a small helper/private method when repeated status checks, ownership checks, or cancellation logic would otherwise be scattered.
- Prefer "minimum sufficient behavior" over broad refactors.

## Phase 2 Testing Rule

After source code changes:

- Do not require frontend validation/build/lint unless the user explicitly asks.
- Do not compile the backend for verification.
- Generate backend unit tests.
- Do not create tests merely to pass mocks.
- Backend tests must cover the business chain: entry parameters -> core biz/service collaboration -> status/data change -> key exception or boundary behavior.
- Prefer controller/biz/service collaboration tests when practical.
- If full Spring/database startup is unavailable, assemble the business chain with focused mocks and clear assertions.
- Do not run backend tests unless the user explicitly asks; generate the test code only.
- Make each generated test print a clear full-flow trace to the console: scenario/input -> entry -> important biz/service calls -> before/after data or status -> exception/boundary -> assertion result.
- Do not claim tests passed unless they were actually run and the output was checked.
- Do not stage generated or modified test files with `git add`, and do not include them in commits, unless the user explicitly asks to stage or commit tests.

## Common Failure Modes

Avoid these:

- Chat-only方案 with no `.md` file.
- Template headings without project-specific file paths and fields.
- "Line numbers later" when files can be read now.
- Implementation before the user approves the generated document.
- Overlong pasted `reqContent`/JSON fields that bury the actual plan.
- Frontend-only restrictions for backend-enforced business rules.
- Listing files without explaining current logic and changed logic.
- Omitting involved tables because no schema change is planned.
