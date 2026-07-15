# Changelog

All notable changes to this project are documented here. Format loosely
follows [Keep a Changelog](https://keepachangelog.com/); this project doesn't
use version tags, so entries are grouped by date instead.

## 2026-07-15 (app copy accuracy pass)

- The sidebar model label (`web/index.html`) no longer hardcodes a model
  name; `ChatJobStatus` now carries the real `model` field from the
  completed Foundry response (`response.model` in
  `src/services/chat_service.py`), and the frontend renders whatever comes
  back instead of a static guess.
- Fixed `vera-how-it-works.html`'s Infrastructure panel: Blob Storage uses
  4 containers (`documents`, `policies`, `meeting-notes`, `project-docs`),
  not one `documents` container as previously stated.
- Fixed the "Reply" step's polling interval claim (`vera-how-it-works.js`):
  the browser polls `/api/chat/status` every ~2s, not ~1.5s.
- Reworded the "8 blueprints ... exposing 23 MCP tools" claim to make clear
  only 7 of the 8 registered blueprints contribute MCP tools; `chat`
  registers two plain HTTP routes and no tools of its own.
- Softened "the one and only LLM call for the whole turn" to "one API
  call" in both the Infrastructure panel and the "Async kickoff" step -
  this repo's code can see one API call per turn, not how many model
  invocations the agent runs internally to get there.

## 2026-07-09 (code audit)

- Tool inputs that fail to parse into a known enum (invalid `doc_type` on
  `search_documents`/`list_documents`/`keyword_search`/`semantic_search`,
  invalid `status` on `list_customers`) now return the same
  `{"error": ...}` JSON contract as every other error path, instead of
  raising an unhandled `ValueError`.
- `find_related_documents` no longer misreports a document as "not found"
  when one of its *related* IDs is a stale/dangling reference; related
  documents are now fetched in a single batched query (was one query per
  related ID) and missing ones are silently omitted from the result.
- `list_documents` and `list_customers` cap `limit` at 100 server-side,
  instead of accepting an unbounded value from the caller.
- `server_health` no longer echoes raw SQL/Blob exception text (which can
  include internal hostnames/driver diagnostics) back to the caller; the
  full exception is now logged server-side and the tool response returns a
  generic `"error: unable to connect"`.
- Added a Content-Security-Policy and baseline security headers
  (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`) to
  `web/staticwebapp.config.json`; extracted `vera-how-it-works.html`'s
  inline `<script>` into `web/vera-how-it-works.js` so `script-src 'self'`
  can be enforced with no `unsafe-inline`.
- Added `ruff`'s bandit-derived security rules (`S`) and simplification
  rules (`SIM`) to the lint config.

## 2026-07-07 to 2026-07-09

- CONNECTED SOURCES dots now double as a color legend (one hue per
  category: employees/customers/documents/policies/meetings) instead of
  uniform green; each "try asking" chip gets a matching dot, or a mini
  Vera avatar for the one question that calls no tool at all. Clicking a
  chip now sends the message immediately instead of just filling the
  composer.
- Rewrote the example-question set against the actual seed data in
  `data/seed/`, and grouped the empty-state chip row and full sidebar list
  into one continuous color-ordered sequence.
- Sidebar footer shows the real underlying model, queried directly from the
  live Foundry agent rather than assumed.
- Added a "How it works" page (`vera-how-it-works.html`, served at the
  extensionless `/vera-how-it-works` route) tracing the real request
  lifecycle - async background run, agentic tool selection, and all three
  retrieval strategies (exact SQL lookup, SQL substring search, vector/
  hybrid RAG) - using real endpoint/function names and index details, with
  a Reset control and a pinned footer.
- Hardcoded the MCP Server Tools popup list in `app.js` instead of fetching
  `/api/tools`, since the catalog is static.
- Fixed `/api/health` blocking on SQL/Blob connectivity checks - it now
  kicks off those checks on background threads and returns immediately,
  avoiding Static Web Apps' ~45s hard backend timeout during Azure SQL
  Serverless cold-start resumes.
- Repo audit cleanup: added SECURITY.md, CONTRIBUTING.md, CODE_OF_CONDUCT.md,
  CHANGELOG.md, issue/PR templates, and a CI workflow (pytest/ruff/black on
  push/PR to main); documented the two-part deployment story in
  `docs/azure.md`; untracked the superseded `design_handoff_mcp_agent_console/`
  reference material; removed the unused `src/utils/` scaffold.

## 2026-07-03

- Added a "New chat" button, auto-scroll fix, and additional sidebar-only
  suggestion chips.
- Added an "MCP Server Tools" popup (backed by a new `/api/tools` endpoint)
  listing every registered tool by category, plus a "More info" link on
  reply tool pills.
- Surfaced which tools Vera used per reply as pills, with sidebar polish.
- Reworked `/api/chat` to run in background mode (`background=True` +
  polling via `/api/chat/status`) to avoid Static Web Apps' 45-second
  synchronous request timeout on longer agent runs.
- Redesigned the startup screen as a centered overlay; added a "thought for
  X seconds" timer per reply.
- Documented running the full chat frontend locally via the SWA CLI
  (`func start` + `swa start`).

## 2026-07-02

- Initial commit: Enterprise Knowledge Hub MCP server (23 MCP tools across
  documents, policies, meetings, employees, customers, search, and health)
  plus the Vera chat console frontend.
- Added the Azure Static Web Apps CI/CD workflow (deploys `web/` only - the
  Function App backend deploys separately, see [docs/azure.md](docs/azure.md)).
- Briefly reworked the chat proxy as a separate Functions app for SWA
  Free-tier compatibility, then reverted both that change and the workflow
  change that pointed at it the same day.
- Fixed the chat proxy to omit `previous_response_id` instead of passing
  `null` on the first message of a conversation.
- Added a once-off startup health check to warm the backend on page load;
  various mobile-layout and UI fixes (favicon, demo note, composer
  positioning, sidebar suggestion placement).
