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

function appendMessage(role, text) {
  const el = document.createElement("div");
  el.className = `message message-${role}`;
  el.textContent = text;
  els.messages.appendChild(el);
  els.messages.scrollTop = els.messages.scrollHeight;
  return el;
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
  const loadingEl = appendMessage("agent", "Thinking…");
  loadingEl.classList.add("loading");

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
      loadingEl.textContent = errorBody.error || "Something went wrong. Please try again.";
      loadingEl.classList.remove("loading");
      return;
    }

    const data = await response.json();
    state.previousResponseId = data.response_id;
    loadingEl.textContent = data.reply;
    loadingEl.classList.remove("loading");
  } catch (error) {
    loadingEl.textContent = "Couldn't reach Vera. Please try again.";
    loadingEl.classList.remove("loading");
  }
}

els.sendButton.addEventListener("click", sendMessage);
els.composerInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    sendMessage();
  }
});
