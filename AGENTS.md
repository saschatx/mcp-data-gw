# Instructions for AI Coding Agents

These instructions apply to the entire `mcp-data-gw` repository. See [Agent Instructions](agents/AGENT_INSTRUCTIONS.md) for details.

## Context

- This coding challenge implements a production-ready Python MCP server for controlled access to a Titanic database.
- MCP uses HTTP transport; local operation uses Docker Compose. Production deployment is currently user-managed. AI agents must leave deployment configuration and execution to users unless explicitly asked to assist.
- The prescribed database has **no primary-key or foreign-key constraints**. Do not alter the schema or invent constraints.
- Development proceeds in explicitly approved phases. Read-only tools form the initial demonstrable minimum.

## Required practices

1. Read available requirements, architecture decisions, and phase documents before editing. Ask when they conflict or omit a necessary decision.
2. Work only within the approved scope. Do not add unrequested dependencies, migrations, tools, or deployment infrastructure.
3. Use **English for code, identifiers, comments, docstrings, tests, and AI-agent instruction files**. General project documentation in Markdown (`.md`) should be **in German**, reflecting the language of the coding challenge. The AI disclosure is an English-language exception. Communicate with the project owner in German or English, following the language of their prompt.
4. Keep changes focused and reviewable. Do not create empty directories or `.gitkeep` placeholders.
5. Apply appropriate type hints, boundary validation, safe error handling, structured logging, and least-privilege database access. Never log secrets.
6. Add relevant unit and integration tests. Use Ruff and pytest according to `pyproject.toml`; mypy is not required.
7. Run relevant checks or explicitly report which could not be run. Never claim unverified results.
8. Keep [AI_DISCLOSURE.md](AI_DISCLOSURE.md) updated for substantial AI contributions.

## Constraints

- Respect the database schema and its missing keys.
- Design for security, maintainability, testability, scalability, and recovery/failover, while leaving production deployment to users unless explicitly asked to assist.
- For project checks, installing existing locked dependencies with `uv sync --locked` or `uv run --locked ...` is authorized. Do not change dependency definitions or lock files, or install additional dependencies, without explicit authorization.
- Preserve existing files, changes, and Git history; review the impact before deleting or overwriting.

Read [Agent Instructions](agents/AGENT_INSTRUCTIONS.md) for the operational workflow and further conventions.
