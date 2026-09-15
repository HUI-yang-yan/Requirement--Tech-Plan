# Technical Plan Document Format

Use this reference with `assets/technical-plan-template.md`. Keep the module-oriented style of an engineering design document: explain how the current business works, which data it uses, how each affected module changes, and where the code changes land.

## File And Opening Rules

- Save to the configured external output directory, outside the active project root: `<output-dir>/<yyyy-mm-dd>-<accurate-requirement-name>技术方案.md`.
- Use the current date and a specific Chinese requirement name.
- Start with `【需求分析模式：最小改动技术文档】`.
- Include a suggested branch: `feature/yyyyMMdd-english-short-name` or `fix/yyyyMMdd-english-short-name`.
- Use the exact ten numbered sections from the template. Do not leave placeholders or empty headings.

## 1. 需求目标与范围

State the business problem, observable goal, included behavior, excluded behavior, default assumptions, unresolved blocking questions with recommended answers, and minimum-change boundary. Do not merely repeat the original request.

## 2. 现有业务逻辑

Explain the current behavior before proposing changes:

- user/page or scheduled-task entry
- frontend request when present
- Controller -> Biz -> Service -> Mapper/domain call chain
- data read/write and current status transitions
- existing error or missing behavior that creates the requirement

Use numbered steps or a compact text flow. Cite current source as `path:line`. If a chain crosses projects, separate it by project.

## 3. 涉及项目与模块

Use a table with `项目`, `模块/职责`, `是否修改`, `修改原因`. Include every project inspected, including projects that need no change when that conclusion matters.

Do not invent a project merely to make the table look complete.

## 4. 涉及表、字段与数据关系

Use a table with:

- table name and business purpose
- current relevant fields
- relation key to other tables
- read/write/update effect
- whether schema or historical data changes are required

List tables that are queried even when no schema change is required. Distinguish clearly among `只查询`, `更新数据`, `新增字段`, and `无表结构变化`.

For each field, identify its PO/DTO/VO source where possible. Do not paste large serialized JSON; list only relevant keys. If no database table is involved, explicitly state why.

Do not propose new tables or fields unless current storage cannot satisfy the requirement and the need is proved from code.

## 5. 详细修改逻辑

Organize this section by business module, similar to `人群SOP管理`, `成员同步`, or `标签查询`, rather than by a generic frontend/backend split.

Each module must include:

1. `当前逻辑`: what it does now and the current condition/status/data source.
2. `修改后逻辑`: exact new decision, query, write, status transition, and visible outcome.
3. `修改步骤`: ordered implementation steps from entry to final data/result.
4. `异常与边界`: empty data, duplicate processing, completed/history status, permission, failure behavior, or transaction boundary that directly follows from the requirement.
5. `最小改动说明`: why no unrelated branch, broad refactor, extra compatibility layer, or complex abstraction is needed.

Use short pseudocode when a condition or state transition would otherwise be ambiguous. Do not include unrelated optimization ideas.

## 6. 接口与后端代码修改点

For every backend modification, include:

- API path and HTTP method when applicable
- request/response fields
- Controller/Biz/Service/Mapper/domain class and method
- exact insertion or replacement logic
- table and status values involved
- exact `path:line` for every planned source change

If adding a private helper, state its file, insertion line, name, inputs, outputs, and single responsibility. Explain which layers do not need changes and why.

## 7. 前端修改点

For every frontend modification, include exact `path:line`, page/component, button/form/dialog/table/filter, API function, request/response field, and interaction behavior.

If no frontend change is needed, keep the section and explain how the current UI receives the backend result.

## 8. 修改前后页面与交互

Use `修改前` and `修改后`. A compact text mockup is preferred for visible changes. When there is no visual change, describe the before/after user-visible behavior, message, and operation result.

Do not invent UI changes that are not required by the business logic.

## 9. 历史数据、兼容性与影响范围

State explicitly:

- whether historical data cleaning is required
- whether old records keep their existing behavior
- whether old API callers remain compatible
- whether scheduled jobs, callbacks, permissions, transactions, or other downstream paths are affected
- rollback or failure impact only when the current requirement creates one

Write `无需历史数据处理` with code/data justification when no cleanup is needed.

## 10. 测试单元与回归点

Separate backend unit tests and frontend regression checks.

For each backend test, include input/precondition -> entry method -> important biz/service collaboration -> data/status change -> exception/boundary -> expected assertion. Name the test class/file to create or update.

Generated backend tests must print an obvious full-flow trace to the console. The trace should identify:

- test scenario and input
- entry method
- each important business step or dependency call
- before/after status or data
- exception or boundary result
- final assertion result

Do not require backend compilation or test execution by default. Generate the test code only unless the user explicitly requests execution. Do not stage or commit generated tests unless explicitly requested.

Frontend checks must describe user operations and expected results. Do not require frontend build/lint unless explicitly requested.

## Traceability Rules

- Every planned modification must use `path:line`.
- Re-open cached candidates and verify current source before citing them.
- If a line cannot be confirmed after reading, write `需进一步确认：<file> 中 <method/location> 的准确行号`.
- Connect each source change to one modification step and one test point.
- Keep the plan detailed enough to implement, but exclude unrelated logic and speculative expansion.
