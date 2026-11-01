# Agent Instructions — mcp-data-gw

This document elaborates on [repository-wide instructions](../AGENTS.md). It provides context for AI coding assistants but does not authorize autonomous scope expansion.

## Objective and development phases

Build a Python MCP server for controlled access to the prescribed Titanic database. Its code and architecture should be **production-ready**. Production deployment is currently user-managed; AI agents must leave its configuration and execution to users unless explicitly asked to assist. Local runtime uses Docker Compose and HTTP transport. A possible secure MCP tunnel for a ChatGPT demonstration is not part of the detailed implementation scope.

1. Define requirements, tools, and architecture.
2. Set up the repository and development tooling.
3. Implement read-only MCP tools as the minimum demonstrable product.

Read existing phase documents and requirements before making changes. Do not assume that undocumented technical choices were already agreed upon.

## Technical guidelines

- **Database:** Preserve the existing schema without primary or foreign keys. Use only documented column relationships for joins. SQLAlchemy is acceptable, but never invent primary keys to support ORM identity.
- **Validation:** Use Pydantic for suitable input/output boundaries. Validate inputs and return controlled, understandable MCP errors.
- **Security:** Prevent SQL injection, enforce least-privilege access, bound queries and response sizes, and load secrets from configuration rather than source code.
- **Reliability:** Consider timeouts, resource cleanup, structured logs, clear error categories, observability, scalability, and recovery/failover. Do not imply that production infrastructure exists.
- **Dependencies:** Use `pyproject.toml` as the authoritative configuration. Locking and auditing do not imply permission to install packages. Avoid unnecessary database drivers.
- **Testing:** Use Ruff and pytest. Cover isolated logic and validation with unit tests, and database/MCP boundaries with integration tests. Mypy is optional, not mandatory.

## Task workflow

1. Identify the requirement, current phase, and affected components; clarify material gaps.
2. Plan the smallest coherent change.
3. Implement without modifying unrelated work.
4. Add and run appropriate tests and static checks.
5. Update relevant documentation and, where appropriate, [AI Disclosure](../AI_DISCLOSURE.md).
6. Report what changed, checks actually executed, and unresolved limitations. Communicate in German or English, following the project owner's prompt.

## Language and structure

- **English:** Code, comments, docstrings, identifiers, test names, AI-agent instructions (`AGENTS.md` and this file), and `AI_DISCLOSURE.md`.
- **German:** General project documentation in Markdown (`.md`), including technical documentation, phase descriptions, requirements, and architecture decisions, because the coding challenge is in German.
- **German or English:** Communication with the project owner; follow the language of the current prompt.
- Create directories only when needed for actual content; no `.gitkeep` files.
- Store helper and data-generation scripts in `scripts/`.
- Do not change the provided Titanic schema or data through unauthorized improvements.
- Respect existing changes and Git history; avoid destructive operations without authorization.

## AI provenance

Use concise, constructive attribution. Label code as AI-assisted when AI contributed to its implementation or revision; a summary by artifact or area in AI_DISCLOSURE.md is sufficient. Individual fixes do not need separate disclosure entries. Review and test code consistently regardless of authorship, and keep provenance separate from verification claims. Describe findings and next steps without assigning blame to people or AI tools.
