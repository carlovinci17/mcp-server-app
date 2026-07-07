# Integration tests

Placeholder - not yet populated. Unlike `tests/unit/` (in-memory SQLite,
fake blob/search clients, no Azure required), true integration tests here
would need real provisioned Azure resources (SQL, Blob, Search, OpenAI,
Foundry) and are not run in CI (`.github/workflows/ci.yml` only runs
`tests/unit/`).

All 23 MCP tools have been manually verified end-to-end against real Azure
resources during development (see [README.md](../../README.md) Status
section) - this directory is where automated versions of those checks would
live if added later.
