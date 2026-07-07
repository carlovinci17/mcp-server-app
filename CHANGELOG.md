# Changelog

All notable changes to this project are documented here. Format loosely
follows [Keep a Changelog](https://keepachangelog.com/); this project doesn't
use version tags, so entries are grouped by date instead.

## 2026-07-07

- Fixed `/api/health` blocking on SQL/Blob connectivity checks - it now
  kicks off those checks on background threads and returns immediately,
  avoiding Static Web Apps' ~45s hard backend timeout during Azure SQL
  Serverless cold-start resumes.

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
