const state = {
  previousResponseId: null,
  hasStartedConversation: false,
  initializing: true,
  pendingSends: [],
};

const els = {
  menuTrigger: document.getElementById("menu-trigger"),
  drawer: document.getElementById("side-drawer"),
  drawerBackdrop: document.getElementById("drawer-backdrop"),
  drawerClose: document.getElementById("drawer-close"),
  welcomeBackdrop: document.getElementById("welcome-backdrop"),
  welcomeClose: document.getElementById("welcome-close"),
  welcomeEnter: document.getElementById("welcome-enter"),
  coldStartSpinner: document.getElementById("cold-start-spinner"),
  tryAskingSection: document.getElementById("try-asking-section"),
  chipRow: document.getElementById("chip-row"),
  moreQuestions: document.getElementById("more-questions"),
  composerBar: document.getElementById("composer-bar"),
  composerInput: document.getElementById("composer-input"),
  sendButton: document.getElementById("send-button"),
  newChatButton: document.getElementById("new-chat-button"),
  emptyState: document.getElementById("empty-state"),
  messages: document.getElementById("messages"),
  mainScroll: document.getElementById("main-scroll"),
  main: document.querySelector(".main"),
  statusPill: document.getElementById("status-pill"),
  statusText: document.getElementById("status-text"),
  sourcesList: document.getElementById("sources-list"),
  sidebarChipList: document.getElementById("sidebar-chip-list"),
  toolsTrigger: document.getElementById("mcp-tools-trigger"),
  toolsModalBackdrop: document.getElementById("tools-modal-backdrop"),
  toolsModalClose: document.getElementById("tools-modal-close"),
  toolsModalBody: document.getElementById("tools-modal-body"),
};

// Clicking a "try asking" chip both fills the composer and sends it
// immediately - matching what a visitor would get by typing the same text
// and hitting enter, just faster.
function applyChipQuestion(text) {
  els.composerInput.value = text;
  els.composerInput.focus();
  sendMessage();
}

els.chipRow.addEventListener("click", (event) => {
  const chip = event.target.closest(".chip");
  if (!chip) return;
  applyChipQuestion(chip.dataset.q);
});

// Static mini Vera avatar markup, shown in place of a category dot for
// questions that call no tool at all.
const VERA_CHIP_ICON = `<svg class="chip-vera-icon" viewBox="0 0 48 48" aria-hidden="true">
  <rect x="8" y="8" width="32" height="33" rx="12" fill="var(--accent)"></rect>
  <rect x="12.5" y="19" width="23" height="17.5" rx="7.5" fill="#081026"></rect>
  <rect x="18" y="23.5" width="4.2" height="8.6" rx="2.1" fill="#5eead4"></rect>
  <rect x="25.8" y="23.5" width="4.2" height="8.6" rx="2.1" fill="#5eead4"></rect>
</svg>`;

// Every example question available - the single source of truth for both
// the landing chip row (a handful shown at a time, reshuffled by "More
// questions") and the drawer's fuller "try asking" list (shows all of
// them, grouped by category). `cat` matches one of the CONNECTED SOURCES
// categories (see the cat-* classes in styles.css); omit `cat` for the one
// question that calls no tool at all (shown with the mini Vera icon).
const ALL_EXAMPLE_QUESTIONS = [
  { text: "Who are you and what can you help with?", icon: "vera" },
  { text: "Who manages the Design team?", cat: "employees" },
  { text: "What departments does Vortex Digital have?", cat: "employees" },
  { text: "Who's on the IT team?", cat: "employees" },
  { text: "Show churned customers in fintech", cat: "customers" },
  { text: "Tell me about Cedar Holdings", cat: "customers" },
  { text: "Which customers are up for renewal this quarter?", cat: "customers" },
  { text: "List our clients and their industries", cat: "customers" },
  { text: "What's in the IT Team Charter, and what other documents relate to it?", cat: "documents" },
  { text: "Tell me about Vortex Digital's mission and values", cat: "documents" },
  { text: "Summarize the latest project brief", cat: "documents" },
  { text: "What documents do we have on file for the Engineering team?", cat: "documents" },
  { text: "Show the remote-work policy", cat: "policies" },
  { text: "Can I work from home a few days a week?", cat: "policies" },
  { text: "What policies does Vortex Digital have on file?", cat: "policies" },
  { text: "What should I do if I lose my work laptop or badge?", cat: "policies" },
  { text: "Summarize the latest incident postmortem", cat: "meetings" },
  { text: "Find the latest all-hands notes", cat: "meetings" },
  { text: "What meeting notes have been logged for the Product team?", cat: "meetings" },
];

const CATEGORY_ORDER = ["employees", "customers", "documents", "policies", "meetings"];
const LANDING_CHIP_COUNT = 6;

function makeChip(className, { text, cat, icon }) {
  const chip = document.createElement("button");
  chip.className = className;
  chip.type = "button";
  chip.dataset.q = text;
  if (icon === "vera") {
    chip.insertAdjacentHTML("beforeend", VERA_CHIP_ICON);
  } else if (cat) {
    const dot = document.createElement("span");
    dot.className = `chip-dot cat-${cat}`;
    chip.appendChild(dot);
  }
  chip.appendChild(document.createTextNode(text));
  return chip;
}

function renderChipRow(questions) {
  els.chipRow.innerHTML = "";
  questions.forEach((q) => els.chipRow.appendChild(makeChip("chip glass", q)));
}

function shuffled(items) {
  const copy = [...items];
  for (let i = copy.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [copy[i], copy[j]] = [copy[j], copy[i]];
  }
  return copy;
}

// First load: "who are you" is always shown first, plus one representative
// question from every category, so the full breadth of what Vera can do is
// visible immediately without needing to click "More questions" first.
function initialChips() {
  const vera = ALL_EXAMPLE_QUESTIONS.find((q) => q.icon === "vera");
  const firstPerCategory = CATEGORY_ORDER.map((cat) => ALL_EXAMPLE_QUESTIONS.find((q) => q.cat === cat));
  return [vera, ...firstPerCategory];
}

renderChipRow(initialChips());

// "More questions" reshuffles the landing row from the full pool, always
// excluding whatever's currently shown so it reads as a genuinely fresh
// set - once clicked, "who are you" is just part of the pool like any
// other question and may or may not reappear.
els.moreQuestions.addEventListener("click", () => {
  const currentTexts = [...els.chipRow.querySelectorAll(".chip")].map((c) => c.dataset.q);
  const pool = shuffled(ALL_EXAMPLE_QUESTIONS.filter((q) => !currentTexts.includes(q.text)));
  renderChipRow(pool.slice(0, LANDING_CHIP_COUNT));
});

// The drawer's "try asking" list shows every example question, grouped by
// category (matching the CONNECTED SOURCES order above) - independent of
// whatever's currently shown in the landing row. The no-category "who are
// you" entry sorts first.
[...ALL_EXAMPLE_QUESTIONS]
  .sort((a, b) => (a.cat ? CATEGORY_ORDER.indexOf(a.cat) : -1) - (b.cat ? CATEGORY_ORDER.indexOf(b.cat) : -1))
  .forEach((q) => els.sidebarChipList.appendChild(makeChip("sidebar-chip", q)));

els.sidebarChipList.addEventListener("click", (event) => {
  const chip = event.target.closest(".sidebar-chip");
  if (!chip) return;
  applyChipQuestion(chip.dataset.q);
});

// ---------------------------------------------------------------------
// Side drawer: overlay menu (was the always-visible sidebar). Opens via
// the header hamburger, closes via its own close button, backdrop click,
// or Escape - same pattern as the MCP tools modal below, plus a focus trap
// and restoring focus to the trigger on close.
// ---------------------------------------------------------------------
let drawerLastFocused = null;

function getFocusable(container) {
  return [...container.querySelectorAll('a[href], button:not([disabled]), input, [tabindex]:not([tabindex="-1"])')].filter(
    (el) => el.offsetParent !== null
  );
}

function trapFocus(container, event) {
  if (event.key !== "Tab") return;
  const focusable = getFocusable(container);
  if (focusable.length === 0) return;
  const first = focusable[0];
  const last = focusable[focusable.length - 1];
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault();
    first.focus();
  }
}

function openDrawer() {
  drawerLastFocused = document.activeElement;
  els.drawerBackdrop.hidden = false;
  requestAnimationFrame(() => {
    els.drawerBackdrop.classList.add("open");
    els.drawer.classList.add("open");
  });
  els.menuTrigger.setAttribute("aria-expanded", "true");
  els.drawerClose.focus();
}

function closeDrawer() {
  els.drawerBackdrop.classList.remove("open");
  els.drawer.classList.remove("open");
  els.menuTrigger.setAttribute("aria-expanded", "false");
  setTimeout(() => {
    els.drawerBackdrop.hidden = true;
  }, 280);
  (drawerLastFocused || els.menuTrigger).focus();
}

function isDrawerOpen() {
  return els.drawer.classList.contains("open");
}

els.menuTrigger.addEventListener("click", () => {
  if (isDrawerOpen()) closeDrawer();
  else openDrawer();
});
els.drawerClose.addEventListener("click", closeDrawer);
els.drawerBackdrop.addEventListener("click", closeDrawer);
els.drawer.addEventListener("keydown", (event) => {
  if (event.key === "Escape") closeDrawer();
  else trapFocus(els.drawer, event);
});

// ---------------------------------------------------------------------
// Welcome popup: shown on every page load (product decision - not gated
// on localStorage), independent of the cold-start warming below. Dismiss
// via the enter button, close button, backdrop click, or Escape.
// ---------------------------------------------------------------------
function closeWelcome() {
  els.welcomeBackdrop.hidden = true;
  els.composerInput.focus();
}

els.welcomeEnter.addEventListener("click", closeWelcome);
els.welcomeClose.addEventListener("click", closeWelcome);
els.welcomeBackdrop.addEventListener("click", (event) => {
  if (event.target === els.welcomeBackdrop) closeWelcome();
});
els.welcomeBackdrop.addEventListener("keydown", (event) => {
  if (event.key === "Escape") closeWelcome();
  else trapFocus(els.welcomeBackdrop, event);
});
els.welcomeClose.focus();

// ---------------------------------------------------------------------
// Composer reparenting: the same input/button pair is used for both the
// centered landing prompt box and the pinned-bottom active-conversation
// composer - moved between the two positions (not duplicated) so there's
// still exactly one #composer-input for all the send/focus logic below.
// ---------------------------------------------------------------------
function pinComposerToBottom() {
  els.composerBar.classList.remove("landing");
  els.composerBar.classList.add("pinned");
  els.main.appendChild(els.composerBar);
}

function moveComposerToLanding() {
  els.composerBar.classList.remove("pinned");
  els.composerBar.classList.add("landing");
  els.emptyState.insertBefore(els.composerBar, els.coldStartSpinner);
}

// Once-off startup check: fired the instant the page loads (not gated on
// the welcome popup being dismissed) so the SQL/Blob cold-start window - up
// to ~40s if the database had auto-paused - happens up front, with an
// honest "waking up" indicator, instead of silently eating the visitor's
// first real question.
function beginInitialization() {
  fetch("/api/health")
    .catch(() => {
      // A failed/timed-out health check still means the attempt woke the
      // backend up - don't block the visitor over it.
    })
    .finally(markReady);
}

function markReady() {
  state.initializing = false;
  els.coldStartSpinner.hidden = true;
  els.composerBar.hidden = false;
  els.tryAskingSection.hidden = false;

  els.statusPill.classList.remove("pending");
  els.statusText.textContent = "Live";

  els.sourcesList.querySelectorAll(".source-dot.pending").forEach((dot) => {
    dot.classList.remove("pending");
  });
  els.sourcesList.querySelectorAll(".source-live.pending").forEach((label) => {
    label.classList.remove("pending");
    label.textContent = "live";
  });

  if (state.pendingSends.length > 0) {
    const queued = state.pendingSends;
    state.pendingSends = [];
    dispatchQueued(queued);
  }
}

async function dispatchQueued(queued) {
  for (const { text, loadingEl } of queued) {
    await dispatchToBackend(text, loadingEl);
  }
}

// Vera's replies come back as markdown. Convert to HTML and sanitize before
// inserting - agent output is model-generated text, not trusted input, so
// DOMPurify strips anything (e.g. injected <script>/event handlers) that
// shouldn't end up running in the page.
function renderMarkdown(text) {
  const html = marked.parse(text, { breaks: true });
  return DOMPurify.sanitize(html);
}

function appendMessage(role, text) {
  const el = document.createElement("div");
  el.className = `message message-${role}`;
  if (role === "agent") {
    el.innerHTML = renderMarkdown(text);
  } else {
    el.textContent = text;
  }
  els.messages.appendChild(el);
  els.mainScroll.scrollTop = els.mainScroll.scrollHeight;
  return el;
}

function formatThoughtDuration(seconds) {
  return `${seconds} second${seconds === 1 ? "" : "s"}`;
}

function appendLoadingMessage() {
  const el = document.createElement("div");
  el.className = "message message-agent loading";
  el.innerHTML =
    '<span class="thinking">' +
    '<span class="thinking-label">Vera is thinking</span>' +
    '<span class="thinking-dots"><span></span><span></span><span></span></span>' +
    '<span class="thinking-timer">0s</span>' +
    "</span>";

  el._startedAt = Date.now();
  const timerEl = el.querySelector(".thinking-timer");
  el._timerInterval = setInterval(() => {
    const elapsed = Math.floor((Date.now() - el._startedAt) / 1000);
    timerEl.textContent = `${elapsed}s`;
  }, 1000);

  els.messages.appendChild(el);
  els.mainScroll.scrollTop = els.mainScroll.scrollHeight;
  return el;
}

function stopThinkingTimer(el) {
  clearInterval(el._timerInterval);
  return Math.max(1, Math.round((Date.now() - el._startedAt) / 1000));
}

function renderToolPills(toolCalls) {
  if (!toolCalls || toolCalls.length === 0) return "";
  const pills = toolCalls.map((name) => `<span class="tool-pill">${name}</span>`).join("");
  const moreInfo = `<button class="tools-more-info" type="button">More info</button>`;
  return `<div class="tool-pills">${pills}${moreInfo}</div>`;
}

function formatToolCallSummary(toolCalls) {
  if (!toolCalls || toolCalls.length === 0) return "";
  return ` · ${toolCalls.length} tool${toolCalls.length === 1 ? "" : "s"} called`;
}

function resolveLoadingMessage(el, text, toolCalls) {
  const elapsedSeconds = stopThinkingTimer(el);
  el.classList.remove("loading");
  el.innerHTML =
    `<div class="thought-timer">Thought for ${formatThoughtDuration(elapsedSeconds)}` +
    `${formatToolCallSummary(toolCalls)}</div>` +
    renderToolPills(toolCalls) +
    renderMarkdown(text);
}

function resolveLoadingMessageAsError(el, text) {
  stopThinkingTimer(el);
  el.classList.remove("loading");
  el.textContent = text;
}

// Azure Static Web Apps enforces a hard 45-second timeout on any single call
// to the linked backend, not configurable at any plan tier - and a question
// that chains several tool calls can easily run past a minute (confirmed: a
// real request took 54s). Rather than race that clock, the backend starts
// the agent run in the background and returns immediately; we poll a status
// endpoint every couple of seconds (matching OpenAI's own recommended
// interval for background Responses API polling) until it's done. No single
// request in this flow ever approaches the timeout, however long the agent
// actually takes.
const POLL_INTERVAL_MS = 2000;
const MAX_POLL_MS = 5 * 60 * 1000;
const MAX_CONSECUTIVE_POLL_ERRORS = 3;

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function dispatchToBackend(text, loadingEl) {
  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: text,
        previous_response_id: state.previousResponseId,
      }),
    });

    if (!response.ok) {
      const errorBody = await response.json().catch(() => ({}));
      resolveLoadingMessageAsError(
        loadingEl,
        errorBody.error || "Something went wrong. Please try again."
      );
      return;
    }

    const job = await response.json();
    await pollUntilDone(job, loadingEl);
  } catch (error) {
    resolveLoadingMessageAsError(loadingEl, "Couldn't reach Vera. Please try again.");
  }
  els.mainScroll.scrollTop = els.mainScroll.scrollHeight;
}

async function pollUntilDone(initialJob, loadingEl) {
  let job = initialJob;
  const startedAt = Date.now();
  let consecutiveErrors = 0;

  while (job.status === "queued" || job.status === "in_progress") {
    if (Date.now() - startedAt > MAX_POLL_MS) {
      resolveLoadingMessageAsError(loadingEl, "This is taking longer than expected. Please try again.");
      return;
    }

    await sleep(POLL_INTERVAL_MS);

    try {
      const response = await fetch(`/api/chat/status?id=${encodeURIComponent(job.response_id)}`);
      if (!response.ok) {
        const errorBody = await response.json().catch(() => ({}));
        resolveLoadingMessageAsError(
          loadingEl,
          errorBody.error || "Something went wrong. Please try again."
        );
        return;
      }
      job = await response.json();
      consecutiveErrors = 0;
    } catch (error) {
      // A transient network blip during polling shouldn't kill the whole
      // exchange - only give up after a few consecutive failures.
      consecutiveErrors += 1;
      if (consecutiveErrors >= MAX_CONSECUTIVE_POLL_ERRORS) {
        resolveLoadingMessageAsError(loadingEl, "Couldn't reach Vera. Please try again.");
        return;
      }
    }
  }

  if (job.status === "completed") {
    state.previousResponseId = job.response_id;
    resolveLoadingMessage(loadingEl, job.reply, job.tool_calls);
  } else {
    resolveLoadingMessageAsError(loadingEl, job.error || "Something went wrong. Please try again.");
  }
}

function sendMessage() {
  const text = els.composerInput.value.trim();
  if (!text) return;

  if (!state.hasStartedConversation) {
    state.hasStartedConversation = true;
    els.emptyState.hidden = true;
    els.messages.hidden = false;
    pinComposerToBottom();
  }

  els.composerInput.value = "";
  appendMessage("user", text);
  const loadingEl = appendLoadingMessage();

  if (state.initializing) {
    // Still warming up: show the message right away, but hold off calling
    // the backend until the startup check settles.
    state.pendingSends.push({ text, loadingEl });
    return;
  }

  dispatchToBackend(text, loadingEl);
}

function startNewChat() {
  state.previousResponseId = null;
  state.hasStartedConversation = false;
  state.pendingSends = [];

  els.messages.innerHTML = "";
  els.messages.hidden = true;
  els.emptyState.hidden = false;
  moveComposerToLanding();

  els.composerInput.value = "";
  els.composerInput.focus();
}

const TOOL_CATEGORY_LABELS = {
  documents: "Documents",
  policies: "Policies",
  meetings: "Meetings",
  employees: "Employees",
  customers: "Customers",
  search: "Search",
  health: "Health",
};

// Mirrors src/tools/health.py's _CAPABILITIES / _TOOL_DESCRIPTIONS. Hardcoded
// here instead of fetched from /api/tools: this list is static, so there's
// no need to round-trip the backend just to render a popup.
const TOOL_GROUPS = [
  {
    category: "documents",
    tools: [
      { name: "search_documents", description: "Search documents, policies, meeting notes, and project docs." },
      { name: "list_documents", description: "List documents, optionally filtered by type or department." },
      { name: "get_document", description: "Retrieve a document's full content and metadata by ID." },
      { name: "get_document_metadata", description: "Retrieve a document's metadata without its full content." },
      { name: "find_related_documents", description: "Find documents related to a given document ID." },
      { name: "summarize_document", description: "Retrieve a document's content for summarization." },
    ],
  },
  {
    category: "policies",
    tools: [
      { name: "search_policies", description: "Search company policies by title or department." },
      { name: "list_policies", description: "List company policies, optionally filtered by department." },
      { name: "get_policy", description: "Retrieve a company policy's full content and metadata." },
    ],
  },
  {
    category: "meetings",
    tools: [
      { name: "search_meetings", description: "Search meeting notes by title or department." },
      { name: "list_meetings", description: "List meeting notes, optionally filtered by department." },
      { name: "summarize_meeting", description: "Retrieve a meeting note's content for summarization." },
    ],
  },
  {
    category: "employees",
    tools: [
      { name: "find_employee", description: "Find employees by name, email, department, or title." },
      { name: "list_departments", description: "List all departments and their employee counts." },
      { name: "get_department_contacts", description: "List all employees in a given department." },
    ],
  },
  {
    category: "customers",
    tools: [
      { name: "search_customers", description: "Search customers by name, industry, or region." },
      { name: "get_customer", description: "Retrieve a customer's details by ID." },
      { name: "list_customers", description: "List customers, optionally filtered by status." },
    ],
  },
  {
    category: "search",
    tools: [
      { name: "keyword_search", description: "Full-text keyword search across all indexed content." },
      { name: "semantic_search", description: "Vector similarity search for conceptual or natural-language queries." },
      { name: "global_search", description: "Hybrid keyword + vector search across all indexed content." },
    ],
  },
  {
    category: "health",
    tools: [
      { name: "server_health", description: "Report server health and Azure dependency connectivity." },
      { name: "list_capabilities", description: "List all MCP tool categories and their tools." },
    ],
  },
];

function renderToolGroups(groups) {
  els.toolsModalBody.innerHTML = groups
    .map((group) => {
      const label = TOOL_CATEGORY_LABELS[group.category] || group.category;
      const items = group.tools
        .map(
          (tool) =>
            `<div class="tool-item">` +
            `<div class="tool-name">${tool.name}</div>` +
            `<div class="tool-desc">${tool.description}</div>` +
            `</div>`
        )
        .join("");
      return `<div class="tool-group"><div class="tool-group-title">${label}</div>${items}</div>`;
    })
    .join("");
}

function openToolsModal() {
  els.toolsModalBackdrop.hidden = false;
  renderToolGroups(TOOL_GROUPS);
}

function closeToolsModal() {
  els.toolsModalBackdrop.hidden = true;
}

els.toolsTrigger.addEventListener("click", openToolsModal);
els.toolsModalClose.addEventListener("click", closeToolsModal);
// Event delegation, not a direct listener: "More info" links are inserted
// into reply bubbles dynamically (one per reply that used tools), so a
// single listener on the messages container catches all of them, present
// and future, without needing to re-bind on every new message.
els.messages.addEventListener("click", (event) => {
  if (event.target.closest(".tools-more-info")) openToolsModal();
});
els.toolsModalBackdrop.addEventListener("click", (event) => {
  if (event.target === els.toolsModalBackdrop) closeToolsModal();
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !els.toolsModalBackdrop.hidden) closeToolsModal();
});

els.sendButton.addEventListener("click", sendMessage);
els.newChatButton.addEventListener("click", startNewChat);
els.composerInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    sendMessage();
  }
});

beginInitialization();
