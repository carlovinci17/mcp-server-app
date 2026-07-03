const state = {
  previousResponseId: null,
  hasStartedConversation: false,
  initializing: true,
  pendingSends: [],
};

const els = {
  headerDate: document.getElementById("header-date"),
  chipRow: document.getElementById("chip-row"),
  composerInput: document.getElementById("composer-input"),
  sendButton: document.getElementById("send-button"),
  emptyState: document.getElementById("empty-state"),
  messages: document.getElementById("messages"),
  startupOverlay: document.getElementById("startup-overlay"),
  statusPill: document.getElementById("status-pill"),
  statusText: document.getElementById("status-text"),
  sourcesList: document.getElementById("sources-list"),
  sidebarTryAsking: document.getElementById("sidebar-try-asking"),
  sidebarTryDivider: document.getElementById("sidebar-try-divider"),
  sidebarChipList: document.getElementById("sidebar-chip-list"),
};

function formatHeaderDate() {
  const d = new Date();
  const weekday = d.toLocaleDateString("en-US", { weekday: "short" });
  const month = d.toLocaleDateString("en-US", { month: "short" });
  return `${weekday}, ${month} ${d.getDate()}`;
}
els.headerDate.textContent = formatHeaderDate();

function applyChipQuestion(text) {
  els.composerInput.value = text;
  els.composerInput.focus();
}

els.chipRow.addEventListener("click", (event) => {
  const chip = event.target.closest(".chip");
  if (!chip) return;
  applyChipQuestion(chip.dataset.q);
});

// The sidebar's "try asking" list mirrors the empty-state chips exactly -
// clone from the chip row (single source of truth) instead of duplicating
// the question text in the HTML, so the two stay in sync automatically.
els.chipRow.querySelectorAll(".chip").forEach((chip) => {
  const sidebarChip = document.createElement("button");
  sidebarChip.className = "sidebar-chip";
  sidebarChip.dataset.q = chip.dataset.q;
  sidebarChip.textContent = chip.textContent;
  els.sidebarChipList.appendChild(sidebarChip);
});

els.sidebarChipList.addEventListener("click", (event) => {
  const chip = event.target.closest(".sidebar-chip");
  if (!chip) return;
  applyChipQuestion(chip.dataset.q);
});

// Once-off startup check: fired the instant the page loads (not on first
// message) so the SQL/Blob cold-start window - up to ~40s if the database
// had auto-paused - happens up front, with an honest "starting up" message,
// instead of silently eating the visitor's first real question.
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
  els.startupOverlay.hidden = true;

  els.statusPill.classList.remove("pending");
  els.statusText.textContent = "All systems operational";

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
  els.messages.scrollTop = els.messages.scrollHeight;
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
  els.messages.scrollTop = els.messages.scrollHeight;
  return el;
}

function stopThinkingTimer(el) {
  clearInterval(el._timerInterval);
  return Math.max(1, Math.round((Date.now() - el._startedAt) / 1000));
}

function renderToolPills(toolCalls) {
  if (!toolCalls || toolCalls.length === 0) return "";
  const pills = toolCalls.map((name) => `<span class="tool-pill">${name}</span>`).join("");
  return `<div class="tool-pills">${pills}</div>`;
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
  els.messages.scrollTop = els.messages.scrollHeight;
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
    els.sidebarTryDivider.hidden = false;
    els.sidebarTryAsking.hidden = false;
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

els.sendButton.addEventListener("click", sendMessage);
els.composerInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    sendMessage();
  }
});

beginInitialization();
