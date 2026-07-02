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
  startupBanner: document.getElementById("startup-banner"),
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
  els.startupBanner.hidden = true;

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

function appendLoadingMessage() {
  const el = document.createElement("div");
  el.className = "message message-agent loading";
  el.innerHTML =
    '<span class="thinking">' +
    '<span class="thinking-label">Vera is thinking</span>' +
    '<span class="thinking-dots"><span></span><span></span><span></span></span>' +
    "</span>";
  els.messages.appendChild(el);
  els.messages.scrollTop = els.messages.scrollHeight;
  return el;
}

function resolveLoadingMessage(el, text) {
  el.classList.remove("loading");
  el.innerHTML = renderMarkdown(text);
}

function resolveLoadingMessageAsError(el, text) {
  el.classList.remove("loading");
  el.textContent = text;
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

    const data = await response.json();
    state.previousResponseId = data.response_id;
    resolveLoadingMessage(loadingEl, data.reply);
  } catch (error) {
    resolveLoadingMessageAsError(loadingEl, "Couldn't reach Vera. Please try again.");
  }
  els.messages.scrollTop = els.messages.scrollHeight;
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
