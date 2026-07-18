const C = {
  blue: "#4176e9",
  amber: "#b45309",
  green: "#0f9d6b",
  violet: "#8b5cf6",
  red: "#dc2626",
  grey: "#565c72",
  teal: "#14b8a6",
  deep: "#0d9488",
};

const VERA_MINI = (s) => `<svg width="${s}" height="${s}" viewBox="0 0 48 48" style="color:#14b8a6" fill="none">
  <rect x="8" y="8" width="32" height="33" rx="12" fill="currentColor"/>
  <rect x="12.5" y="19" width="23" height="17.5" rx="7.5" fill="#081026"/>
  <rect x="18" y="23.5" width="4.2" height="8.6" rx="2.1" fill="#5eead4"/>
  <rect x="25.8" y="23.5" width="4.2" height="8.6" rx="2.1" fill="#5eead4"/>
</svg>`;

// Verified against the real backend code (src/tools/chat.py,
// src/services/chat_service.py, function_app.py) - see docs/azure.md and
// this repo's own audit history for how each fact was confirmed.
const STEPS = [
  {
    t: "Prompt sent",
    llm: false,
    plain: "Your message is posted to the backend, validated, and handed to the agent service — anonymous, no login required.",
    tech: 'POST /api/chat  { message, previous_response_id }\n→ { response_id, status: "queued" }\nsrc/tools/chat.py',
  },
  {
    t: "Async kickoff",
    llm: false,
    plain: "The agent run starts in the background and returns instantly. This is the one API call for the whole turn — built to dodge Static Web Apps' hard 45s request timeout.",
    tech: "client.responses.create(background=True, store=True)\nsrc/services/chat_service.py",
  },
  {
    t: "Tool choice",
    llm: true,
    plain: "The agent itself decides whether a tool is needed and which of the 23 to call — not fixed app logic. Same run, now polled mid-flight.",
    tech: "responses.retrieve(id)  ·  23 MCP tools available\ndocuments 6 · policies 3 · meetings 3 · employees 3\ncustomers 3 · search 3 · health 2",
  },
  {
    t: "Retrieval",
    llm: false,
    plain: "The chosen tool fetches data via one of three paths — exact SQL lookup, fuzzy SQL substring, or vector/hybrid search (see the strategies above).",
    tech: "src/services/*_service.py\n→ Azure SQL / Blob Storage / AI Search",
  },
  {
    t: "Synthesis",
    llm: true,
    plain: "The agent writes a plain-language answer from whatever the tool returned. Still the same single run, polled once it reaches its terminal status.",
    tech: 'responses.retrieve(id) → status "completed"\nreply = response.output_text',
  },
  {
    t: "Reply",
    llm: false,
    plain: "The browser — polling every ~2s — receives the finished reply, de-dupes the tool calls into pills, and renders the markdown safely.",
    tech: "GET /api/chat/status\n→ marked.parse() → DOMPurify.sanitize()",
  },
];

const RETR = [
  { c: C.blue, h: "Exact lookup", p: "Direct query by id or a simple filter. Deterministic, no matching logic at all.", code: "SELECT … WHERE col = :val" },
  { c: C.amber, h: "SQL substring", p: "Fuzzy but literal match on title & department columns only — no embeddings.", code: "WHERE title ILIKE '%term%'" },
  { c: C.green, h: "Vector / hybrid", p: "Embeds the query, then BM25 + HNSW vector search fused in a single call.", code: "text-embedding-3-small → Azure AI Search" },
];

const INFRA = [
  { c: C.blue, h: "Azure SQL Database", p: "EmployeeRecord, CustomerRecord & DocumentMetadataRecord. AAD-token auth via DefaultAzureCredential — no password in the connection string.", src: "src/database/sql.py" },
  { c: C.blue, h: "Azure Blob Storage", p: "4 containers (documents, policies, meeting-notes, project-docs). SQL stores pointers; the document text is fetched here.", src: "src/azure/blob_client.py" },
  { c: C.green, h: "Azure AI Search", p: "Fields: title · content · content_vector (HNSW, 1536-dim, cosine). Embeddings from text-embedding-3-small.", src: "src/services/search_service.py" },
  { c: C.teal, h: "Azure AI Foundry Agent", p: "Reached via the OpenAI-compatible Responses API (background + store). The model name comes from response.model, never hardcoded.", src: "src/azure/foundry_agent.py" },
  { c: C.teal, h: "Azure Functions Remote MCP", p: "Each tool is an @bp.mcp_tool(). 8 blueprints register one FunctionApp; 7 expose 23 tools, chat adds 2 HTTP routes.", src: "function_app.py" },
];

const TOOLS = [
  { c: C.blue, l: "Documents", items: [["search_documents", "Search all doc types"], ["list_documents", "List by type / dept"], ["get_document", "Full content by id"], ["get_document_metadata", "Metadata only"], ["find_related_documents", "Related by id"], ["summarize_document", "Content to summarize"]] },
  { c: C.amber, l: "Policies", items: [["search_policies", "By title / dept"], ["list_policies", "List by dept"], ["get_policy", "Full content + metadata"]] },
  { c: C.green, l: "Meetings", items: [["search_meetings", "By title / dept"], ["list_meetings", "List by dept"], ["summarize_meeting", "Content to summarize"]] },
  { c: C.violet, l: "Employees", items: [["find_employee", "By name / email / dept"], ["list_departments", "Depts + counts"], ["get_department_contacts", "People in a dept"]] },
  { c: C.red, l: "Customers", items: [["search_customers", "By name / industry"], ["get_customer", "Details by id"], ["list_customers", "List by status"]] },
  { c: C.teal, l: "Search", items: [["keyword_search", "BM25 full-text"], ["semantic_search", "Vector similarity"], ["global_search", "Hybrid fusion"]] },
  { c: C.grey, l: "Health", items: [["server_health", "Deps connectivity"], ["list_capabilities", "All tool categories"]] },
];

// Render retrieval-strategy cards
document.getElementById("branches").innerHTML = RETR.map(
  (r) => `<div class="branch glass" style="border-left-color:${r.c}"><h4 style="color:${r.c}">${r.h}</h4><p>${r.p}</p><code>${r.code}</code></div>`
).join("");

// Render pipeline nodes
let selectedStep = 1;
document.getElementById("pipe").innerHTML = STEPS.map(
  (s, i) =>
    `<button class="node" data-i="${i}" type="button">` +
    `<div class="dot ${s.llm ? "llm" : ""}">${i + 1}</div>` +
    `<div class="nl">${s.t}${s.llm ? '<span class="llm-tag">LLM</span>' : ""}</div>` +
    `</button>`
).join("");

function renderStepDetail(i) {
  const s = STEPS[i];
  document.getElementById("pipe-detail").innerHTML =
    `<div class="detail-top"><div class="detail-badge ${s.llm ? "llm" : ""}">${i + 1}</div>` +
    `<span class="detail-title">${s.t}</span>` +
    `${s.llm ? `<span class="llm-chip">${VERA_MINI(12)} LLM thinking</span>` : ""}</div>` +
    `<div class="detail-plain">${s.plain}</div><div class="detail-tech">${s.tech}</div>`;
  document.querySelectorAll(".node").forEach((n, ni) => n.classList.toggle("sel", ni === i));
}

document.getElementById("pipe").addEventListener("click", (event) => {
  const node = event.target.closest(".node");
  if (!node) return;
  selectedStep = +node.dataset.i;
  renderStepDetail(selectedStep);
});

renderStepDetail(selectedStep);

// Render infrastructure cards
document.getElementById("infra").innerHTML = INFRA.map(
  (x) => `<div class="icard glass" style="border-left-color:${x.c}"><h4>${x.h}</h4><p>${x.p}</p><span class="src">${x.src}</span></div>`
).join("");

// Render the 23-tool catalog, grouped by category
document.getElementById("tools").innerHTML = TOOLS.map(
  (g) =>
    `<div class="tgroup" style="border-left-color:${g.c}"><div class="gt" style="color:${g.c}">${g.l} (${g.items.length})</div>` +
    `<div class="tgrid">${g.items.map(([n, d]) => `<div><div class="tname">${n}</div><div class="tdesc">${d}</div></div>`).join("")}</div></div>`
).join("");

// Tab switching
document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    const target = tab.dataset.tab;
    document.querySelectorAll(".tab").forEach((b) => {
      const active = b === tab;
      b.classList.toggle("active", active);
      b.setAttribute("aria-selected", String(active));
    });
    document.querySelectorAll(".hiw-panel").forEach((p) => p.classList.toggle("active", p.id === `panel-${target}`));
  });
});
