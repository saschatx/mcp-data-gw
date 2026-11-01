# Phase 3 — Coding Agent Handover

**Project:** `mcp-data-gw`
**Status:** Approved for implementation
**Date:** 2026-10-31

This is the original implementation brief. The current MVP and Compose
configuration are described in the [README](../../README.md); verification results
are recorded in the [implementation report](phase-3-implementation.md).

## Mission

Implement **Phase 3 only**: a minimal, running, read-only Python MCP server for the existing Titanic SQLite database. The implementation will be performed by a separate coding agent. Your deliverable is functioning, tested code, not another implementation proposal.

The German requirements are the normative source of truth:

1. `docs/structure/phase-3.md` — scope, architecture, exact tool contracts, validation and runtime rules.
2. `docs/requirements/phase-3-acceptance.md` — acceptance criteria, commands and manual smoke tests.

Before editing, read `AGENTS.md`, `agents/AGENT_INSTRUCTIONS.md` (if present), the Phase 1 and Phase 2 documentation, the existing `pyproject.toml`, `README.md`, `AI_DISCLOSURE.md`, and the database-generation script if present. If paths differ in the real repository, locate the actual files without fabricating replacements. Follow newer, explicit Phase 3 decisions where older phase documents disagree.

## Mandatory scope

- Exactly four MCP tools: `list_tables`, `describe_table`, `select_rows`, `aggregate_rows`.
- Official Python MCP SDK 2.x, SQLAlchemy **Core**, Pydantic 2; use the existing `src/mcp_data_gw/` package and `mcp-data-gw` entry point.
- A clear boundary between MCP handlers, validation, query construction, semantic metadata and database connections.
- Validated table/column allowlists, recursive filters, safe literal text searches, bounded SELECT/aggregate queries and structured outputs.
- `describe_table` must separate actual database metadata from logical relationships and dynamically retrieve lookup values.
- A working local Streamable HTTP endpoint, preferably stateless with JSON responses. Default binding: `127.0.0.1`; database URL must be configured explicitly.
- Unit tests and in-memory MCP contract tests with targeted mocks, plus a **manual** smoke test against an already prepared Titanic database.
- Minimal README and AI disclosure updates. Keep the database schema unchanged.

## Explicit non-goals

- No write tools, SQL execution tool, joins, pagination, `offset` or `has_more`.
- No Dockerfile, Docker Compose, Secure MCP Tunnel setup or public network exposure. Production deployment is currently user-managed; leave its configuration and execution to users unless explicitly asked to assist.
- Preserve local bind defaults and SDK transport protections; do not imply that an unauthenticated public endpoint is safe.
- No temporary SQLite test databases, automated real-DB integration fixtures, broad test-mocking of pure logic, or unnecessary testing frameworks.
- No new libraries, changed dependency constraints, regenerated lockfile or schema changes without approval.
- No speculative framework or folder structure; create only files and directories that contain working content.

## Working permissions and escalation rules

The project owner has **explicitly authorized installing existing locked dependencies** and executing checks for Phase 3. You may run:

```bash
uv sync --locked
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked pytest
```

Other relevant read-only diagnostics are permitted. Do **not** change `pyproject.toml` or `uv.lock`, add a dependency, run `uv lock`, regenerate/reset an existing database, or deploy services without explicit approval. If the lock is inconsistent, report the issue and ask rather than silently updating it.

Update the blanket sentence in `AGENTS.md` that currently forbids *all* dependency installations, so it explicitly permits installing **already locked dependencies for Phase 3 checks** while retaining the prohibition on modifying dependencies and lockfiles without approval. Also correct the repository-name typo (`mc-data-gw` → `mcp-data-gw`) if still present; preserve all other user-owned instructions. The original `AGENTS.md` points to `agents/AGENT_INSTRUCTIONS.md`, while older Phase 2 notes may refer to `agents/conventions.md`; follow the actual repository files.

You may independently decide internal module names, private helpers, small implementation details and test decomposition. **Stop and request approval before** changing any published tool signature or output shape, adding/removing features, broadening network exposure, altering the data model or schema, adding dependencies, or materially changing the test approach. Ask only when the choice is consequential; otherwise make and document a reasonable decision.

## Recommended implementation sequence

1. Inspect the repository, reconcile existing files and record a short plan. Preserve all user changes.
2. Implement configuration and a local MCP server factory/entry point without automatic database creation.
3. Implement the explicit schema allowlist, SQLAlchemy Core expressions, shared validation/filter models and safe error translation.
4. Implement `list_tables` and `describe_table`, including technical reflection, semantic descriptions, logical relationships and live lookup values.
5. Implement `select_rows` with projection, recursive filters, sorting and hard limits.
6. Implement `aggregate_rows` with validated metric functions, grouping, aliases and hard limits.
7. Add unit tests for deterministic logic and `Client(mcp)` in-memory tests with mocked database boundary. Use the attached `test_server.py` only as a pattern: its `mcp_ttrpg` imports and domain data belong to another project.
8. Run locked Ruff/pytest checks. Manually exercise the four tools against the existing SQLite database without resetting it; if unavailable, report the manual smoke test as pending.
9. Update the documentation, `AGENTS.md` rule and `AI_DISCLOSURE.md`; provide a concise evidence-based handoff report.

## Test and output expectations

All automated tests must run without an actual database. Use mocks only where external database behavior must be simulated. SQLAlchemy expression construction and parameter safety can be checked without a database connection. In-memory MCP tests should assert tool discovery, valid structured results, invalid-input errors and sanitized unexpected failures.

The official SDK supports in-process `Client(mcp)` calls; it is appropriate to use `asyncio.run` inside normal pytest tests when no async pytest plugin is installed. Add test markers from `pyproject.toml` appropriately. Refer to the complete acceptance checklist rather than treating this summary as exhaustive.

In the final report, provide:

- Changed/added files and a brief explanation.
- Results of every executed command (do not assert success for unrun checks).
- Status of AC-01–AC-16 and SM-01–SM-07, especially the real-database smoke test.
- Known limitations, unresolved risks and any design decisions made without escalation.
- Confirmation that no schema, lockfile or dependency-definition changes occurred, or a precise disclosure if a change was approved.

**Language convention:** Code, identifiers, comments, docstrings, test names and agent instructions in English. General project documentation in German. Project-owner communication may follow the owner's German or English prompt.
