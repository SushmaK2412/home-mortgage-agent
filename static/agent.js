const thread = document.getElementById("thread");
const banner = document.getElementById("agentBanner");
const bannerText = document.getElementById("agentBannerText");
const composer = document.getElementById("composer");
const msg = document.getElementById("msg");
const sendBtn = document.getElementById("sendBtn");

let history = [
  {
    role: "assistant",
    content:
      "Hi — I’m here to help you understand the homebuying and mortgage process in plain language. " +
      "What would you like to explore first?",
  },
];

function render() {
  thread.innerHTML = "";
  for (const m of history) {
    const div = document.createElement("div");
    div.className = "bubble " + (m.role === "user" ? "bubble-user" : "bubble-asst");
    div.textContent = m.content;
    thread.appendChild(div);
  }
  thread.scrollTop = thread.scrollHeight;
}

async function checkStatus() {
  const res = await fetch("/api/assistant/status");
  if (!res.ok) return;
  const d = await res.json();
  if (!d.assistant_enabled) {
    banner.hidden = false;
    bannerText.textContent =
      "Assistant is not configured. Add OPENAI_API_KEY to your .env file and restart the server. " +
      "Rates and charts on the home page still work without it.";
    sendBtn.disabled = true;
    msg.disabled = true;
  }
}

function setLoading(on) {
  sendBtn.disabled = on;
  msg.disabled = on;
  sendBtn.classList.toggle("is-loading", on);
}

composer.addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = msg.value.trim();
  if (!text) return;
  msg.value = "";
  history.push({ role: "user", content: text });
  render();
  setLoading(true);
  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages: history }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      if (history.length) history.pop();
      render();
      const err = document.createElement("div");
      err.className = "bubble bubble-err";
      let msgErr = "Something went wrong. Try again.";
      const d = data.detail;
      if (typeof d === "string") msgErr = d;
      else if (Array.isArray(d)) msgErr = d.map((x) => x.msg || JSON.stringify(x)).join(" ");
      err.textContent = msgErr;
      thread.appendChild(err);
      return;
    }
    history.push({ role: "assistant", content: data.reply });
    render();
  } catch {
    if (history.length) history.pop();
    render();
    const err = document.createElement("div");
    err.className = "bubble bubble-err";
    err.textContent = "Network error. Check your connection and try again.";
    thread.appendChild(err);
  } finally {
    setLoading(false);
  }
});

render();
checkStatus();
