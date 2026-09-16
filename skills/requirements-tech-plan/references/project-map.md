# Project Discovery Map

Use this reference to discover the real structure of the active repository. Directory names below are examples, not required conventions.

## Discover The Repository

1. Read repository instructions such as `AGENTS.md` and the smallest relevant project documentation.
2. Inspect root manifests and build files, for example `package.json`, `pom.xml`, `build.gradle`, `pyproject.toml`, `requirements.txt`, `go.mod`, `Cargo.toml`, `.sln`, and `.csproj`.
3. List top-level modules and identify executable applications, shared libraries, workers, migrations, tests, and generated/vendor directories.
4. Locate the user-facing or machine-facing entry point from routes, commands, consumers, schedulers, callbacks, or exported APIs.
5. Trace only the affected path through the architecture actually used by the project.

Do not assume a frontend/backend split, a particular framework, a database, HTTP, or conventional layer names.

## Common Layout Hints

These are discovery hints only:

- UI/client: `src/pages`, `src/views`, `src/components`, `app`, `client`, `frontend`.
- Request/command entry: `routes`, `controllers`, `handlers`, `commands`, `cli`, `consumers`, `jobs`.
- Core behavior: `services`, `usecases`, `domain`, `core`, `biz`.
- Persistence/integration: `repositories`, `dao`, `mappers`, `models`, `entities`, `adapters`, `clients`.
- Tests: `test`, `tests`, `spec`, `__tests__`, or language-specific test filenames.

Names may overlap. Confirm each candidate from imports, calls, routes, dependency injection, configuration, and tests before assigning a role in the plan.

## Search Strategy

Start with `scripts/collect_evidence.py` to obtain candidates across the entire supplied root. Its path classification and keyword aliases are heuristics, not a parser or call graph.

Then open current source around candidates and extend the chain with targeted `rg -n` searches. Search for concrete identifiers in this order when available:

1. route, command, event, UI label, or error text
2. method/function/component/type name
3. request/response field or status constant
4. table, collection, topic, cache key, or external endpoint
5. direct callers, callees, imports, and tests

Broaden the search when:

- `requires_deep_search` is `true`;
- the expected entry or downstream effect is absent;
- a UI/API/command cannot be matched to its implementation;
- a status, field, or persisted value has no confirmed source;
- a cached path, line, or file hash no longer matches;
- the project uses a suffix or generated source format not covered by the collector.

## Exact Locations

Use commands that preserve line numbers, for example:

```powershell
rg -n "routeName|methodName|fieldName" <project-root> -S
```

Every planned edit needs a current `path:line` insertion or replacement point. Re-open files after cached evidence is returned. If a new helper is proposed, cite the nearest current method or class boundary and describe where the helper will be inserted.

## Minimum-Change Bias

- Put enforcement in the layer that owns the invariant; UI-only restrictions are insufficient for server-owned rules.
- Reuse existing fields, statuses, APIs, stores, and local patterns when they satisfy the requirement.
- Avoid adding layers that the project does not already use.
- Add a small helper only when it makes a directly required condition clearer or removes meaningful duplication.
- Treat no-database, no-frontend, and no-backend conclusions as valid when source evidence supports them.
