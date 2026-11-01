# Phase 3 – Acceptance Criteria and Test Evidence

**Project:** `mcp-data-gw`  
**Status:** Phase 3 accepted; verification completed
**Date:** 2026-10-31

This checklist records the original Phase 3 scope. Executed checks and subsequent
findings are documented in the [implementation report](phase-3-implementation.md).
The current MVP, including the Compose configuration, is described in the
[README](../../README.md).

This document specifies the **verifiable acceptance** of the requirements from `phase-3.md`. The actual implementation is handled by a separate coding agent. The agent documents test results; checks that cannot be executed must be explicitly marked as pending.

## 1. Automated Checks

### Tool Registration and MCP Contracts

- [x] **AC-01 (P3-TBL-01, P3-COM-01):** `Client(mcp)` lists exactly `list_tables`, `describe_table`, `select_rows`, and `aggregate_rows`. No write tools and no generic SQL tool.
- [x] **AC-02 (P3-TBL-02):** `list_tables` returns only the eight approved table names in sorted order; other/internal tables are not exposed. Database access is mocked in a controlled manner.
- [x] **AC-03 (P3-DES-01–05):** `describe_table("Observation")` returns technical columns, actual declared constraints, **separately** identified logical relationships, and dynamic lookup values in the specified JSON fields. The provided reference database has no PK/FK constraints.
- [x] **AC-04 (P3-SEL-01–04):** `select_rows` respects projection, filtering, sorting, limits, and the `rows`/`returned_count` response fields. An empty result set returns `[]` and `0` without an error.
- [x] **AC-05 (P3-AGG-01–06):** `aggregate_rows` maps `count(*)`, `count(column)`, `sum`, `avg`, `min`, `max`, as well as grouping and sorting, to SQLAlchemy Core. Aliases and response fields are correct.
- [x] **AC-06 (P3-COM-03):** Successful MCP calls contain structured content with native JSON value types; `is_error` is not true. Invalid tool inputs are visibly reported as errors.

### Validation and Query Security

- [x] **AC-07 (P3-COM-02, P3-SEC-02):** Unknown tables, columns, internal tables, duplicates in column/group selections, and disallowed operators are rejected.
- [x] **AC-08 (P3-FLT-01–03):** AND/OR nesting, all ten specified comparison/NULL/text operators, and `in` are implemented correctly. Empty groups, `in: []`, missing/disallowed values, and incompatible types produce controlled errors.
- [x] **AC-09 (P3-FLT-04, P3-FLT-06, P3-ARC-03):** Values containing `'`, `%`, `_`, escape characters, and SQL-like payloads remain bound data. `contains` treats LIKE special characters literally. No user-supplied SQL is interpolated.
- [x] **AC-10 (P3-FLT-05, P3-COM-04):** Tree depths greater than 5, more than 30 conditions, more than 100 `in` values, `limit=0`, negative/invalid limits, and `limit>200` are rejected. The default limit is 50; even at the maximum of 200, the response remains bounded.
- [x] **AC-11 (P3-AGG-02–05):** Missing columns for non-`count` metrics, numerically incompatible `sum`/`avg` operations, duplicate/invalid aliases, and prohibited sort keys are rejected.
- [x] **AC-12 (P3-ARC-02, P3-SEC-01):** There are no ORM mappings, schema modifications, CREATE/INSERT/UPDATE/DELETE logic, or automatically generated SQLite files at startup.

### Semantic Layer, Errors, and Startup Configuration

- [x] **AC-13 (P3-SEM-01–04):** Domain-specific descriptions are present; a modified mocked lookup record appears updated on the next call. Static lookup IDs are not assumed. Unexpectedly large lookups are rejected in a controlled manner.
- [x] **AC-14 (P3-ERR-01–03):** Domain errors contain the specified codes and an MCP-compliant error indicator. Unexpected errors expose neither tracebacks nor SQL/file-path details to clients; they remain traceable on the server side.
- [x] **AC-15 (P3-RUN-01–04, P3-SEC-03):** The CLI entry point can be imported and started; the default configuration binds locally, uses Streamable HTTP at the documented path, and validates missing/invalid database settings. SDK host/origin protection remains enabled.
- [x] **AC-16 (P3-TST-01–04):** Unit tests and in-memory MCP tests are reproducible, run without an external service, and use mocks only at the necessary data-access boundary. No SQLite fixture database is used in automated tests.

For in-memory MCP tests, the pattern from the attached `test_server.py` may be adopted: `asyncio.run(...)`, `async with Client(mcp)`, `list_tools()`, `call_tool(...)`, `monkeypatch` at the service/repository boundary, and assertions on `structured_content` or `is_error`. Project-specific imports from the example (`mcp_ttrpg`) must **not** be adopted. Since `pytest-asyncio` is not specified as a dependency, `asyncio.run` is one possible simple solution.

## 2. Manual Smoke Test Against the Real Titanic Database

**No automated integration-test database.** The following test is performed after the build using an already prepared, unchanged SQLite database. It must not trigger a reset or data import into an existing file that may have been modified. If no real database is available, this acceptance check remains **pending** and must not be marked as passed.

- [x] **SM-01:** Start the service locally with a valid `MCP_DATA_GW_DATABASE_URL`, access `/mcp` using an MCP client, and list exactly four tools.
- [x] **SM-02:** `list_tables` returns the eight expected tables; `describe_table("Observation")` returns all 15 Observation columns, no declared PK/FK constraints, logical relationships, and actual lookup values.
- [x] **SM-03:** `select_rows(table="Observation", columns=["pclass","survived"], limit=5)` returns at most five records with correct columns/value types.
- [x] **SM-04:** `select_rows` with a nested `where` clause and sorting returns rows matching the filter condition; an impossible condition returns an empty list.
- [x] **SM-05:** `aggregate_rows` with `count(*)` returns a plausible total count; `avg(survived)` grouped by `pclass` returns rates in the range 0–1 and semantically appropriate groups.
- [x] **SM-06:** Invalid tables/columns and invalid filters produce controlled errors; no database file details are disclosed.
- [x] **SM-07:** Stop and restart the server and retrieve the same read-only data; the database file and schema remain unchanged.

The manual results should be recorded in the implementation report with the date, executed startup command, brief example parameters, and success/failure status. Do not include sensitive content or unnecessary data dumps in the evidence.

Nachweis: SM-01–SM-07 am 31. Oktober 2026 über reales lokales HTTP bestanden;
siehe [Implementierungsbericht](phase-3-implementation.md#smoke-test-mit-der-bereitgestellten-datenbank).

## 3. Prescribed Verification Commands

Installing already locked dependencies is explicitly approved for Phase 3; modifying the dependency definitions or lockfile is not.

```bash
uv sync --locked
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked pytest
uv run --locked pytest -m unit
uv run --locked pytest -m integration
```

Markers must be assigned according to the actual tests: `unit` for isolated logic, `integration` for interaction between MCP layers **in memory**, with mocking at the database boundary. These integration tests do not demonstrate actual SQL execution against SQLite; only the manual smoke test provides that evidence.

## 4. Definition of Done

Phase 3 is considered accepted only when:

1. All four tool contracts have been implemented and the relevant criteria **AC-01 through AC-16** have been met.
2. Ruff and pytest have completed successfully, and the commands actually executed and their results have been documented.
3. The manual smoke tests **SM-01 through SM-07** have been completed successfully, or their non-execution has been explicitly reported as an **outstanding acceptance blocker**.
4. The README and `AI_DISCLOSURE.md` have been updated, and the installation rule in `AGENTS.md` has been clarified for Phase 3.
5. No unauthorized dependencies, lockfile changes, schema modifications, write tools, Docker artifacts, or deployment artifacts have been added.
6. The coding agent has transparently communicated all deviations, risks, and unverified assumptions to the project owner.

**Important:** A successful automated test suite alone does not replace the manual SQLite verification.
