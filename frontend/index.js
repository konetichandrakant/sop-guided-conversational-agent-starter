// SOP claims agent test UI.
// Talks to the FastAPI backend (POST /chat) and mirrors the workflow phases
// from workflow.txt: VERIFY_ID -> RESOLVE_INTENT -> PROCESS_CASE -> POST_PROCESS.

const API_URL = "http://localhost:8000/chat";
const PHASES = ["VERIFY_ID", "RESOLVE_INTENT", "PROCESS_CASE", "POST_PROCESS"];

// New session per page load, so the agent's memory matches what's on screen.
const sessionId = crypto.randomUUID();
let currentPhase = "VERIFY_ID";

const chatEl = document.getElementById("chat");
const formEl = document.getElementById("composer");
const inputEl = document.getElementById("prompt-input");
const sendBtnEl = document.getElementById("send-btn");
const suggestionEl = document.getElementById("suggestion");
const suggestionBtnEl = document.getElementById("suggestion-btn");
const phasePillEl = document.getElementById("phase-pill");
const stepperEl = document.getElementById("stepper");

function renderMessage(role, text) {
  const el = document.createElement("div");
  el.className = `msg ${role}`;
  el.textContent = text;
  chatEl.appendChild(el);
  chatEl.scrollTop = chatEl.scrollHeight;
}

function renderTyping() {
  const el = document.createElement("div");
  el.className = "typing";
  el.innerHTML = "<span></span><span></span><span></span>";
  chatEl.appendChild(el);
  chatEl.scrollTop = chatEl.scrollHeight;
  return el;
}

function setPhase(phase) {
  if (!PHASES.includes(phase)) return;
  currentPhase = phase;
  phasePillEl.textContent = phase;
  const idx = PHASES.indexOf(phase);
  stepperEl.querySelectorAll(".step").forEach((step, i) => {
    step.classList.toggle("active", i === idx);
    step.classList.toggle("done", i < idx);
  });
}

async function sendPrompt(prompt) {
  renderMessage("user", prompt);
  suggestionEl.classList.add("hidden");

  const typingEl = renderTyping();
  inputEl.value = "";
  sendBtnEl.disabled = true;
  inputEl.disabled = true;

  try {
    const res = await fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, prompt }),
    });
    if (!res.ok) throw new Error(`Server responded ${res.status}`);
    const data = await res.json();

    typingEl.remove();
    renderMessage("agent", data.response);
    setPhase(data.phase);
  } catch (err) {
    typingEl.remove();
    renderMessage(
      "error",
      `Could not reach the agent (${err.message}). Is the backend running on ${API_URL}?`
    );
  } finally {
    sendBtnEl.disabled = false;
    inputEl.disabled = false;
    inputEl.focus();
  }
}

formEl.addEventListener("submit", (event) => {
  event.preventDefault();
  const prompt = inputEl.value.trim();
  if (prompt) sendPrompt(prompt);
});

suggestionBtnEl.addEventListener("click", () => {
  sendPrompt(
    "I'm the policyholder. My name is Margaret Chen, policy POL-9921. " +
      "I'm calling about my denied healthcare claim from January. DOB is 1985-03-15, SSN last four is 4472."
  );
});

// Opening message: the agent greets and starts VERIFY_ID, without a server round trip.
setPhase("VERIFY_ID");
renderMessage(
  "agent",
  "Hi, thanks for calling Greenline Insurance support. Before we get started, " +
    "I need to verify your identity. Could you tell me your full name, plus two more " +
    "details like your date of birth, phone, email, policy number or the last 4 digits of your ID?"
);
inputEl.focus();
