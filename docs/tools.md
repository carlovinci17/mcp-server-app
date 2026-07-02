# MCP Tool Catalog

All tools are registered via `@bp.mcp_tool()` in `src/tools/*.py` and wired into
the host in `function_app.py`. Tool descriptions below match each function's
docstring, which is what the MCP host actually surfaces to the calling LLM.

## Documents (`src/tools/documents.py`)

| Tool | Description |
|---|---|
| `search_documents(query, doc_type=None)` | Search documents, policies, meeting notes, and project docs by title, department, or tags. |
| `list_documents(doc_type=None, department=None)` | List documents, optionally filtered by document type or department. |
| `get_document(document_id)` | Retrieve a document's full content and metadata by ID. |
| `get_document_metadata(document_id)` | Retrieve metadata without fetching full content. |
| `find_related_documents(document_id)` | Find documents related to the given document ID. |
| `summarize_document(document_id)` | Retrieve full content for the calling assistant to summarize (no server-side LLM call). |

## Policies (`src/tools/policies.py`)

| Tool | Description |
|---|---|
| `search_policies(query)` | Search company policies by title or department. |
| `list_policies(department=None)` | List company policies, optionally filtered by department. |
| `get_policy(policy_id)` | Retrieve a policy's full content and metadata by ID. |

## Meetings (`src/tools/meetings.py`)

| Tool | Description |
|---|---|
| `search_meetings(query)` | Search meeting notes by title or department. |
| `list_meetings(department=None)` | List meeting notes, optionally filtered by department. |
| `summarize_meeting(meeting_id)` | Retrieve full content for the calling assistant to summarize. |

## Employees (`src/tools/employees.py`)

| Tool | Description |
|---|---|
| `find_employee(query)` | Find employees by name, email, department, or title. |
| `list_departments()` | List all departments and their employee counts. |
| `get_department_contacts(department)` | List all employees in a given department. |

## Customers (`src/tools/customers.py`)

| Tool | Description |
|---|---|
| `search_customers(query)` | Search customers by name, industry, or region. |
| `get_customer(customer_id)` | Retrieve a customer's details by ID. |
| `list_customers(status=None)` | List customers, optionally filtered by status (prospect/active/churned). |

## Health (`src/tools/health.py`)

| Tool | Description |
|---|---|
| `server_health()` | Report health and connectivity status for each configured Azure dependency. |
| `list_capabilities()` | List all MCP tool categories and the tools available in each. |

## Search (`src/tools/search.py`)

| Tool | Description |
|---|---|
| `keyword_search(query, doc_type=None)` | Full-text keyword search across all indexed content. Best for exact terms, names, or IDs. |
| `semantic_search(query, doc_type=None)` | Vector similarity search across all indexed content. Best for conceptual or natural-language questions where exact wording may not match the source text. |
| `global_search(query)` | Hybrid keyword + vector search across all indexed content, no type filtering. Default choice when unsure which of the above fits better. |

Backed by `src/services/search_service.py` against Azure AI Search (Free tier,
vector search only — no Semantic Ranker, see [docs/azure.md](azure.md)).
Embeddings for both indexing and querying come from an Azure OpenAI
`text-embedding-3-small` deployment via `src/azure/embeddings.py`.

## Not yet implemented (Phase 2 remainder)

Key Vault and App Configuration integration — both resources are provisioned
but no application code reads from them yet.
