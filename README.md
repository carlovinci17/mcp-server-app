# Enterprise Knowledge Hub MCP Server

A Model Context Protocol (MCP) server for **Vortex Digital** (fictional company),
built on Azure Functions' native MCP tool trigger extension. It exposes enterprise
knowledge — documents, policies, meeting notes, employees, and customers — as MCP
tools an LLM client (e.g. Claude Desktop) can call directly.

## Architecture

- **Azure Functions (Python v2 model)** hosts the MCP server itself, via the
  `@app.mcp_tool()` / `@bp.mcp_tool()` decorators (`azure-functions>=1.24.0`).
  There is no separate FastMCP process — Functions *is* the MCP host.
- **Azure SQL Database** stores employee, customer, and document metadata.
- **Azure Blob Storage** stores document/policy/meeting-note content.
- **Azure AI Search** (Free tier, vector search only) provides full-text and
  semantic search across content, using **Azure OpenAI** (`text-embedding-3-small`)
  for embeddings.
- **Azure Key Vault** / **Azure App Configuration** (Phase 3) hold secrets and
  centralized non-secret config.
- **Application Insights** (Phase 3) provides telemetry.

Authentication to every Azure resource uses `DefaultAzureCredential` — no
connection-string secrets in code. See [docs/azure.md](docs/azure.md) for details.

## Status

Phase 1 and 2 complete: Functions scaffold + SQL Database + Blob Storage +
Azure AI Search + Azure OpenAI embeddings, with all 23 tools (documents,
policies, meetings, employees, customers, health, search) verified end-to-end
against real Azure resources, plus unit tests against an in-memory SQLite
database and fake blob/search clients. Key Vault, App Configuration, and
Application Insights integration are provisioned but not yet wired into
application code (Phase 3) — see [docs/setup.md](docs/setup.md).

## Quick start

```bash
uv sync
cp .env.example .env   # fill in AZURE_SQL_SERVER / AZURE_STORAGE_ACCOUNT_URL once provisioned
uv run pytest
func start
```

See [docs/setup.md](docs/setup.md) for provisioning the underlying Azure resources
and [docs/tools.md](docs/tools.md) for the full MCP tool catalog.

## Repository layout

```
config/       non-secret defaults (settings.yaml, logging.yaml)
data/seed/    generated fictional Vortex Digital sample data
scripts/      sample data generation, index creation, and Azure seeding scripts
src/core/     settings, logging, dependency wiring
src/azure/    Azure SDK client wrappers (identity, blob, search, embeddings)
src/database/ SQLAlchemy models + Azure SQL Database session management
src/models/   Pydantic domain models
src/services/ business logic, independent of the Functions host
src/tools/    MCP tool definitions (thin Functions blueprint wrappers over services)
tests/        unit tests (mocked/in-memory) and integration tests
function_app.py   Functions app entry point; registers all tool blueprints

web/          Vera chat console frontend (static HTML/CSS/JS, no build step)
api/          separate, self-contained Functions app proxying chat messages
              to an Azure AI Foundry agent - deployed together with web/ by
              Static Web Apps' Managed Functions, independent of the main
              MCP server app above (see docs/azure.md for why)
```

## License

See [LICENSE](LICENSE).
