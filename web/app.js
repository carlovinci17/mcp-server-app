const state = {
  previousResponseId: null,
  hasStartedConversation: false,
};

const els = {
  headerDate: document.getElementById("header-date"),
  chipRow: document.getElementById("chip-row"),
  composerInput: document.getElementById("composer-input"),
  sendButton: document.getElementById("send-button"),
  emptyState: document.getElementById("empty-state"),
  messages: document.getElementById("messages"),
};

function formatHeaderDate() {
  const d = new Date();
  const weekday = d.toLocaleDateString("en-US", { weekday: "short" });
  const month = d.toLocaleDateString("en-US", { month: "short" });
  return `${weekday}, ${month} ${d.getDate()}`;
}
els.headerDate.textContent = formatHeaderDate();

els.chipRow.addEventListener("click", (event) => {
  const chip = event.target.closest(".chip");
  if (!chip) return;
  els.composerInput.value = chip.dataset.q;
  els.composerInput.focus();
});

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

async function sendMessage() {
  const text = els.composerInput.value.trim();
  if (!text) return;

  if (!state.hasStartedConversation) {
    state.hasStartedConversation = true;
    els.emptyState.hidden = true;
    els.messages.hidden = false;
  }

  els.composerInput.value = "";
  appendMessage("user", text);
  const loadingEl = appendLoadingMessage();

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

els.sendButton.addEventListener("click", sendMessage);
els.composerInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    sendMessage();
  }
});
