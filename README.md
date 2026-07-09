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

## Frontend

`web/` is Vera, a small vanilla-JS chat console that talks to an Azure AI
Foundry agent (wired to this same MCP server) via three HTTP endpoints
alongside the MCP tools: `/api/chat`, `/api/chat/status`, and `/api/health`
(`src/tools/chat.py`, `src/tools/health.py`). It's deployed separately from
the Function App backend — see "Deployment" in [docs/azure.md](docs/azure.md)
for how the two pieces fit together in production.

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

## Local testing

Pick the option that matches what you're changing:

- **Frontend only** (layout/UI changes under `web/`): serve the folder with any
  static file server, e.g. VS Code's Live Server extension. Fast, no setup —
  but `/api/*` calls (the chat) won't work with no backend behind them, and
  pretty routes like `/vera-how-it-works` won't resolve since that rewrite is
  defined in `web/staticwebapp.config.json`, which a plain static server
  doesn't read. Use the literal filename (`vera-how-it-works.html`) instead.
- **Backend unit tests**: `uv run pytest` — runs against an in-memory SQLite
  database and fake blob/search clients, no Azure resources or credentials
  required.
- **Full end-to-end** (real chat, real Foundry agent, real MCP tools, real
  Azure data, with `/api/*` routed exactly like production): run `func start`
  and the Static Web Apps CLI together against `web/`. See
  [docs/setup.md](docs/setup.md) for the exact commands and prerequisites.
  This is also the only local setup where pretty routes like
  `/vera-how-it-works` resolve, since the SWA CLI reads
  `staticwebapp.config.json` the same way Azure does in production.
- **MCP tools only** (no frontend needed): once `func start` is running,
  connect directly to `http://localhost:7071/runtime/webhooks/mcp` — already
  configured as `mcp-demo-local-server` in `.vscode/mcp.json`, no auth
  required locally. Use this from VS Code or Claude Desktop to call tools
  one at a time without going through the chat UI.

### Before you start

- **Confirm your Azure session is live**: `az account show`. Every Azure
  client (SQL, Blob, Search, OpenAI/Foundry) authenticates via
  `DefaultAzureCredential`, which resolves to your `az login` session
  locally — if it's expired, `func start` will boot fine but every tool
  call will fail with an auth error.
- **`/api/health` won't tell you if dependencies are actually reachable** —
  it's a fire-and-forget wake-up ping (see `src/tools/health.py`) that
  always returns `{"status":"warming"}` immediately, by design. To check
  real SQL/Blob/Search connectivity locally, call the underlying check
  directly instead:
  ```bash
  python3 -c "from src.tools.health import _server_health; print(_server_health())"
  ```
- **Port 7071 already in use?** It's usually a stale `func start` left
  running from a *different* Functions project after its terminal closed
  uncleanly (it spawns a language-worker subprocess that can outlive the
  host and get orphaned). Find and confirm it before killing anything:
  ```bash
  lsof -nP -iTCP:7071 -sTCP:LISTEN          # get the PID
  lsof -p <PID> | grep cwd                  # confirm which project it's from
  kill -9 <PID>                             # if it's stale/orphaned
  ```
  To avoid this: stop the dev server via VS Code's **"Tasks: Terminate
  Task"** (or the trash-can icon on its terminal tab) rather than just
  closing the terminal tab or window.

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
tests/        unit tests (mocked/in-memory) and integration tests (placeholder, see tests/integration/README.md)
web/          Vera, the chat console frontend (static HTML/CSS/JS, no build step)
function_app.py   Functions app entry point; registers all tool blueprints
```

## License

See [LICENSE](LICENSE).
