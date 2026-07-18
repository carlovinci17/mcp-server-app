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
//
// Steps 1, 2, 5 & 6 are identical no matter which tool gets called - only
// step 3 (tool choice) and step 4 (retrieval) actually differ per path,
// exactly mirroring the real code: chat.py/chat_service.py don't know or
// care which tool the agent picked, only the tool/service layer differs.
const RETRIEVAL_BY_KIND = {
  exact: {
    toolLine: "→ selects get_department_contacts",
    title: "Retrieval — exact lookup",
    plain: "A single, direct database query by ID or a simple filter. No text matching involved at all - the fastest, most deterministic path.",
    tech: 'get_department_contacts(department="Design")\nsrc/services/employee_service.py\nSQLAlchemy: SELECT * FROM employees\n  WHERE department = :department\nNo embeddings, no ranking',
  },
  substring: {
    toolLine: "→ selects search_documents",
    title: "Retrieval — SQL substring search",
    plain: "A fuzzy but literal text match against the title and department columns only. Finds partial matches, but has no concept of meaning or synonyms - and no embeddings are involved.",
    tech: 'search_documents(query="onboarding")\nsrc/services/document_service.py\nAzure SQL via SQLAlchemy:\nWHERE title ILIKE \'%onboarding%\'\n  OR department ILIKE \'%onboarding%\'',
  },
  vector: {
    toolLine: "→ selects global_search",
    title: "Retrieval — vector / hybrid RAG",
    plain: "The question is embedded into a vector, then Azure AI Search runs BM25 keyword search and HNSW vector search together in one query and fuses the two rankings automatically.",
    tech: 'global_search(query="remote work policy")\nsrc/services/search_service.py\nembed_text() → Azure OpenAI\n  text-embedding-3-small (1536-dim)\nAzure AI Search .search() called with\nboth search_text= (BM25) and\nvector_queries= (HNSW) → automatic\nhybrid fusion, single round trip',
  },
};

const PROMPT_BUTTONS = [
  { kind: "exact", q: "Who's the contact for the Design team?", label: "Exact lookup", c: C.blue },
  { kind: "substring", q: "Find documents about onboarding", label: "SQL substring search", c: C.amber },
  { kind: "vector", q: "What's our remote work policy?", label: "Vector / hybrid RAG", c: C.green },
];

function buildStepData(kind) {
  const retrieval = RETRIEVAL_BY_KIND[kind];
  return [
    {
      t: "Prompt sent",
      llm: false,
      plain: "Your message is posted to the backend, validated, and handed to the agent service — anonymous, no login required.",
      tech: 'POST /api/chat  { message, previous_response_id }\n→ { response_id, status: "queued" }\nsrc/tools/chat.py',
    },
    {
      t: "Async kickoff",
      llm: false,
      plain: "This is the one API call for the whole turn: the agent run starts in the background and returns instantly - built to dodge Static Web Apps' hard 45s request timeout. No icon yet because the backend can't see what the model decided until it polls.",
      tech: "client.responses.create(background=True, store=True)\nsrc/services/chat_service.py\n(single API call for this whole turn)",
    },
    {
      t: "Tool choice",
      llm: true,
      plain: "The agent itself decides whether a tool is needed and which of the 23 to call — not fixed app logic. Same run as step 2, now polled mid-flight; nothing new is sent to the model here.",
      tech: `responses.retrieve(id)  ·  23 MCP tools available\ndocuments 6 · policies 3 · meetings 3 · employees 3\ncustomers 3 · search 3 · health 2\n${retrieval.toolLine}`,
    },
    {
      t: retrieval.title,
      llm: false,
      plain: retrieval.plain,
      tech: retrieval.tech,
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
}

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

// Render the 3 "try a prompt" buttons
document.getElementById("prompt-buttons").innerHTML = PROMPT_BUTTONS.map(
  (p) =>
    `<button class="prompt-btn kind-${p.kind}" data-kind="${p.kind}" type="button">` +
    `<div class="prompt-btn-q">"${p.q}"</div>` +
    `<div class="prompt-btn-kind" style="color:${p.c}">${p.label}</div>` +
    `</button>`
).join("");

// --- Animated step-sequence state machine -------------------------------
// selected: which path (exact/substring/vector) is playing, or null.
// doneUpTo: highest step index (1-based) marked complete.
// activeStep: the step currently mid-animation (0 = none).
const state = {
  selected: null,
  doneUpTo: 0,
  activeStep: 0,
  timers: [],
};

const reducedMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

function stageState(n) {
  if (state.activeStep === n) return "active";
  if (state.doneUpTo >= n) return "done";
  return "pending";
}

function renderSteps() {
  const container = document.getElementById("step-cards");
  if (!state.selected) {
    container.innerHTML = "";
    return;
  }
  const stepData = buildStepData(state.selected);
  container.innerHTML = stepData
    .map((s, idx) => {
      const n = idx + 1;
      const st = stageState(n);
      return (
        `<div class="step-card ${st}">` +
        `<div class="step-card-grid">` +
        `<div>` +
        `<div class="step-top">` +
        `<div class="step-badge">${st === "done" ? "✓" : n}</div>` +
        `<span class="step-title">${s.t}</span>` +
        `${s.llm ? `<span class="llm-chip">${VERA_MINI(12)} LLM thinking</span>` : ""}` +
        `</div>` +
        `<div class="step-plain">${s.plain}</div>` +
        `</div>` +
        `<div class="step-tech">${s.tech}</div>` +
        `</div>` +
        `</div>`
      );
    })
    .join("");
}

// Steps 1,2,3 are quick; retrieval (4) and synthesis (5) take the longest -
// matching roughly how long each phase actually takes in a real run.
function durationFor(n) {
  if (reducedMotion) return 450;
  return [900, 1100, 1200, 2200, 1000, 1400][n - 1] || 900;
}

function advance(n) {
  const stepData = buildStepData(state.selected);
  if (n > stepData.length) {
    state.activeStep = 0;
    state.doneUpTo = stepData.length;
    renderSteps();
    return;
  }
  state.activeStep = n;
  renderSteps();
  const timer = setTimeout(() => {
    state.doneUpTo = n;
    state.activeStep = 0;
    renderSteps();
    advance(n + 1);
  }, durationFor(n));
  state.timers.push(timer);
}

function updatePromptButtonStyles() {
  document.querySelectorAll(".prompt-btn").forEach((btn) => {
    btn.classList.toggle("selected", btn.dataset.kind === state.selected);
  });
}

function startExample(kind) {
  state.timers.forEach(clearTimeout);
  state.timers = [];
  state.selected = kind;
  state.doneUpTo = 0;
  state.activeStep = 0;
  updatePromptButtonStyles();
  renderSteps();
  const timer = setTimeout(() => advance(1), 250);
  state.timers.push(timer);
}

function resetPrompt() {
  state.timers.forEach(clearTimeout);
  state.timers = [];
  state.selected = null;
  state.doneUpTo = 0;
  state.activeStep = 0;
  updatePromptButtonStyles();
  renderSteps();
}

document.getElementById("prompt-buttons").addEventListener("click", (event) => {
  const btn = event.target.closest(".prompt-btn");
  if (!btn) return;
  startExample(btn.dataset.kind);
});

document.getElementById("reset-prompt").addEventListener("click", resetPrompt);

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
