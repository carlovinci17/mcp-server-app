# Setup

## Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/)
- [Azure Functions Core Tools v4](https://learn.microsoft.com/en-us/azure/azure-functions/functions-run-local)
- [ODBC Driver 18 for SQL Server](https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server) (required by `pyodbc` for Azure SQL Database access)
- Azure CLI, logged in (`az login`) with an active subscription

## Install dependencies

```bash
uv sync
```

This creates `.venv` and installs everything from `pyproject.toml`. `requirements.txt`
is a separately-exported, flattened copy used by the Azure Functions deploy path
(Oryx/zip deploy reads `requirements.txt`, not `pyproject.toml`). Regenerate it after
changing dependencies:

```bash
uv export --no-hashes --no-dev -o requirements.txt
```

## Provision Azure resources (one-time)

These commands are illustrative — run them yourself against your own subscription
and resource group; nothing in this repo provisions cloud resources automatically.

```bash
RG=enterprise-knowledge-mcp-rg
LOCATION=eastus

az group create -n $RG -l $LOCATION

# Azure SQL Database (serverless, free-offer eligible: 100k vCore-seconds + 32GB/month)
az sql server create -n <unique-sql-server-name> -g $RG -l $LOCATION \
  --enable-ad-only-auth --external-admin-principal-type User \
  --external-admin-name <your-email> --external-admin-sid <your-aad-object-id>
az sql db create -g $RG -s <unique-sql-server-name> -n enterprise-knowledge-db \
  --edition GeneralPurpose --family Gen5 --capacity 1 --compute-model Serverless \
  --auto-pause-delay 60

# Blob Storage containers (reuse the storage account already referenced by
# AzureWebJobsStorage in local.settings.json, or create a dedicated one)
az storage container create --account-name <storage-account> --name documents --auth-mode login
az storage container create --account-name <storage-account> --name policies --auth-mode login
az storage container create --account-name <storage-account> --name meeting-notes --auth-mode login
az storage container create --account-name <storage-account> --name project-docs --auth-mode login

# Azure AI Search (Free tier - one per subscription)
az search service create -g $RG -n <unique-search-name> --sku free

# Azure OpenAI / AI Foundry, with a text-embedding-3-small deployment
az cognitiveservices account create -g $RG -n <unique-openai-name> \
  --kind AIServices --sku S0 --custom-domain <unique-openai-name>
az cognitiveservices account deployment create -g $RG -n <unique-openai-name> \
  --deployment-name text-embedding-3-small --model-name text-embedding-3-small \
  --model-version 1 --model-format OpenAI --sku-name Standard --sku-capacity 120
```

Being subscription Owner does **not** grant data-plane access to any of these
services — grant your own identity (and later, the Function App's managed
identity) the following, or every SDK call will fail with an authorization
error even though `az` control-plane commands succeed:

| Resource | Role |
|---|---|
| Storage account | `Storage Blob Data Contributor` |
| AI Search service | `Search Index Data Contributor` + `Search Service Contributor` |
| Azure OpenAI/Foundry resource | `Cognitive Services OpenAI User` |
| SQL Database | Not RBAC — set yourself as the server's Microsoft Entra admin at creation (`--external-admin-*` flags above) |

The app authenticates via `DefaultAzureCredential` everywhere, never a
connection string or API key.

## Configure local environment

Copy `.env.example` to `.env` and fill in the values from the resources above:

```bash
cp .env.example .env
```

`.env` is used by scripts/tests run directly with `uv run`. When running via
`func start`, the same keys go in `local.settings.json`'s `"Values"` block instead
(the Functions host does not read `.env`).

## Seed sample data

```bash
uv run python scripts/create_sample_data.py     # generates data/seed/ locally, no Azure calls
uv run python scripts/import_documents.py       # loads employees/customers/document metadata into SQL
uv run python scripts/seed_blob_storage.py      # uploads document content into Blob Storage
uv run python scripts/create_search_index.py    # creates the Azure AI Search index (idempotent)
uv run python scripts/index_documents.py        # embeds + uploads document content into the search index
```

## Run locally

```bash
func start
```

The MCP endpoint is `http://localhost:7071/runtime/webhooks/mcp` (already configured
in `.vscode/mcp.json` for use from VS Code / Claude Desktop).

## Run tests

```bash
uv run pytest
uv run ruff check .
uv run black --check .
```

Unit tests run against an in-memory SQLite database and a fake blob client — no
Azure resources are required to run `uv run pytest`.
