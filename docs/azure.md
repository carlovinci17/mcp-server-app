# Azure Architecture

## Hosting model

This server is **not** a standalone FastMCP process. It runs on Azure Functions'
native MCP tool trigger extension (`azure-functions>=1.24.0`,
`@app.mcp_tool()` / `@bp.mcp_tool()`). Azure Functions itself is the MCP host:
each Python function decorated with `@bp.mcp_tool()` becomes one MCP tool, with
its name, parameters, and types inferred from the function signature, and its
description taken from the docstring. See
[Microsoft's MCP tool trigger docs](https://learn.microsoft.com/en-us/azure/azure-functions/functions-bindings-mcp-tool-trigger).

Tools are grouped into `func.Blueprint()` instances per domain
(`src/tools/documents.py`, `employees.py`, etc.) and registered onto the single
`func.FunctionApp()` in `function_app.py` via `app.register_functions(bp)`.

Each `@bp.mcp_tool()`-decorated function is a thin wrapper: the decorator
replaces the function object in the module namespace with a `FunctionBuilder`,
so the actual logic lives in a private `_impl`-style function underneath and is
unit tested directly — the decorated wrapper itself is only exercised by
integration tests against a running `func start` host.

## Data layer

| Concern | Service | Auth |
|---|---|---|
| Employee/customer/document metadata | Azure SQL Database (serverless, auto-pause) | `DefaultAzureCredential` token passed via pyodbc `attrs_before` (SQL_COPT_SS_ACCESS_TOKEN) |
| Document/policy/meeting-note content | Azure Blob Storage | `DefaultAzureCredential` |
| Full-text/vector search | Azure AI Search, Free (F0) tier, vector search only | `DefaultAzureCredential` |
| Embeddings for indexing/querying | Azure OpenAI (Foundry), `text-embedding-3-small`, Standard SKU | `DefaultAzureCredential` bearer token (`get_bearer_token_provider`) |
| Secrets (Phase 3) | Azure Key Vault | `DefaultAzureCredential` |
| Config (Phase 3) | Azure App Configuration | `DefaultAzureCredential` |
| Telemetry (Phase 3) | Application Insights | connection string |

No connection strings or account keys are used anywhere in application code —
every client is constructed with `DefaultAzureCredential` (`src/azure/identity.py`),
which resolves to the developer's `az login` session locally and to the Function
App's managed identity once deployed.

### Why Azure SQL Database instead of SQLite

The original scope favored local SQLite for zero-setup local dev. Given the goal
of maximizing genuine Azure service usage for this portfolio project, Azure SQL
Database's free offer (100,000 vCore-seconds + 32GB storage/month, auto-pausing
outside that) covers this workload at $0/month, so SQLite was dropped in favor of
using the real Azure SQL Database service even in local dev.

### Why AI Search Free tier + vector search only (not Semantic Ranker)

Semantic Ranker requires the Basic tier or higher (~$75/month fixed cost),
independent of actual query volume. Vector search is available on every tier,
including Free, at no extra charge. `semantic_search` is implemented via
embeddings + vector query on the Free tier rather than Microsoft's Semantic
Ranker feature, to keep the whole project's Azure spend at effectively $0/month.

### Owner does not imply data-plane access

Being subscription Owner grants full control-plane access (create/configure any
resource) but **not** data-plane access to Storage, Key Vault, Search, or
Cognitive Services/Azure OpenAI — those require explicit role assignments even
for the account that created the resource:

| Resource | Role needed |
|---|---|
| Blob Storage | `Storage Blob Data Contributor` |
| Azure AI Search | `Search Index Data Contributor` (read/write documents) + `Search Service Contributor` (create/manage indexes) |
| Azure OpenAI (embeddings, `mcp-app-demo-openai`) | `Cognitive Services OpenAI User` |
| Azure AI Foundry project (chat agent, `mcp-app-demo-foundry` / `mcp-server-agent`) | `Foundry User`, scoped to the project |
| Azure SQL Database | Not an RBAC role — the Microsoft Entra admin set on the logical server (or a contained database user granted via T-SQL) |

This was discovered empirically while building this project: `az storage
container list --auth-mode login` succeeded even without the role (CLI-level
listing), but the actual Python SDK `upload_blob()` call failed with
`AuthorizationPermissionMismatch` until `Storage Blob Data Contributor` was
assigned. Don't assume a working `az` read command means the data plane is
actually accessible from application code.

### Azure AI Search Free tier write throttling

Free tier throttles rapid single-document write calls. Indexing all 165 seed
documents one `merge_or_upload_documents` call at a time immediately hit
`HttpResponseError: You are sending too many requests`. `SearchService.index_documents`
batches uploads (10 documents/call), sleeps between batches, and retries with
backoff on `HttpResponseError` — see `src/services/search_service.py`.

### Azure SQL Database serverless: the first request after auto-pause needs an application-level retry

Serverless auto-pause is what keeps this project at $0/month, but it has a
sharp edge: when the database has paused from idleness, the **first**
connection attempt after that fails outright (`pyodbc.OperationalError:
Login timeout expired`) rather than blocking until the resume completes.
Increasing the ODBC `Connection Timeout` or adding `ConnectRetryCount`/
`ConnectRetryInterval` to the connection string does **not** fix this — those
were tried first and empirically confirmed not to help (same error, failing
in ~21s, nowhere near the configured timeout). The actual behavior is: the
first attempt fails fast as the trigger that starts the resume, and the
*caller* has to retry the connection attempt itself after a short delay.

`src/database/sql.py`'s `get_session()` forces an eager connection
(`session.connection()`) wrapped in a retry loop (`_ensure_connected`, 5
attempts, 8s apart) before yielding control to the caller. Confirmed working
against a real auto-paused database: the resumed request succeeded in ~53s
(a few retry cycles) instead of failing immediately. This latency is paid
only by the first request after ~60 minutes of total idleness — every
request after that is fast again.

## Local development without every Azure service

`src/core/settings.py` exposes `*_enabled` properties (`sql_enabled`,
`blob_enabled`, `search_enabled`, `embeddings_enabled`, `key_vault_enabled`,
`app_config_enabled`, `telemetry_enabled`) that are `False` whenever the corresponding endpoint env var
is unset. `server_health` reports `"not_configured"` for any dependency not
wired up, rather than failing at import time — so `func start` and `uv run pytest`
both work without every Azure resource provisioned.

## Deployment

Deployed to `mcp-app-demo-func` (Flex Consumption plan, Linux, Python 3.13),
via `func azure functionapp publish` — not Container Apps/ACR, no Docker image
in this architecture. The Function App has a system-assigned managed identity
with the same RBAC roles granted to the developer's own identity (Storage,
Search x2, Cognitive Services OpenAI User), plus a SQL Database user created
via `CREATE USER ... FROM EXTERNAL PROVIDER`, so `DefaultAzureCredential`
resolves to the managed identity in production instead of `az login`.

The MCP webhook endpoint (`/runtime/webhooks/mcp`) requires the
`mcp_extension` system key as a `?code=` query parameter or `x-functions-key`
header when called remotely — this is a platform-level requirement from the
Functions host's webhook routing model (`extensions.mcp.system.webhookAuthorizationLevel`
in host.json, defaulting to `"System"`), not something configured in this
repo's Python code. It can be set to `"Anonymous"` to remove the requirement,
but that trades away the one thing currently preventing anonymous internet
traffic from running up real Azure OpenAI usage costs — not done here.

`.github/workflows/ci.yml` runs `pytest`/`ruff`/`black` on every push/PR to
`main`, but there is no CD for the Function App itself; deploys are manual
via `func azure functionapp publish` for now.

A custom domain (`vortex-mcp.carlovinci.com.au`, via Crazy Domains DNS) is
bound to the Static Web App, with the free App Service Managed Certificate.

### The frontend and backend deploy through two entirely separate paths

This is the single most important thing to know before touching deployment,
and the thing that caused real confusion once in practice: **pushing to
`main` does not deploy the MCP server / chat backend.**

- `web/` (the Vera chat console) is deployed automatically by
  `.github/workflows/azure-static-web-apps-black-dune-027faae00.yml` on every
  push to `main`. That workflow's `api_location` is intentionally empty — it
  uploads `web/` only, as static content to the Azure Static Web App
  (`mcp-app-demo-swa`).
- The actual MCP server / Function App (`mcp-app-demo-func`, Flex
  Consumption plan) is a **separate Azure resource** with no CI/CD wired to
  it at all. Changes to `src/`, `function_app.py`, etc. only reach
  production when someone runs `func azure functionapp publish
  mcp-app-demo-func` by hand.
- The two are connected via a Static Web Apps **linked backend**
  (`az staticwebapp backends link`, requires the Standard plan — the Free
  tier only supports SWA's own bundled "Managed Functions," which is what
  the reverted `80493a8` / `92b1244` commits attempted before this project
  was moved to Standard). Any request to `vortex-mcp.carlovinci.com.au/api/*`
  is proxied by the SWA edge straight to `mcp-app-demo-func`.

Practical consequence: if you fix a bug in `src/tools/health.py` (for
example) and only `git push`, the live site will keep serving the old
backend behavior indefinitely — the fix needs its own explicit
`func azure functionapp publish mcp-app-demo-func` before it's live.
