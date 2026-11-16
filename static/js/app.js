/**
 * AutoQuiz Web Client Application — Gemini Clean Chat Edition
 * Features:
 *  1. Conversational Chat Interface (Normal Rectangles, Flat Design)
 *  2. Drag & Drop / File Attachment (PDF, PPTX, TXT, MD)
 *  3. Adaptive Remediation Loops until 100% Mastery (BR-2)
 *  4. Confidence Guard & Unverified Retry (BR-6)
 *  5. LaTeX Math & AST Code Block Preservation
 */

const state = {
  currentUser: {
    userId: "24CSB1A12",
    name: "Dasari Rahul",
    role: "student"
  },
  currentView: "chat",
  documents: [],
  topics: [],
  activeSession: null,
  currentQuestionIndex: 0,
  currentSelection: null,
  currentConfidence: null,
  submittedAnswers: [],
  pendingDuplicateFile: null
};

// --- Initialization ---
document.addEventListener("DOMContentLoaded", () => {
  setupNavigation();
  setupQuizKeyShortcuts();
  checkAuthAndLoad();
  loadRecentMaterials();
});

function setupQuizKeyShortcuts() {
  window.addEventListener("keydown", (e) => {
    const activeBox = document.getElementById("active-quiz-box");
    if (!activeBox) return;
    const activeEl = document.activeElement;
    if (activeEl && (activeEl.tagName === "INPUT" || activeEl.tagName === "TEXTAREA")) return;

    const key = e.key.toLowerCase();
    if (key === "a" || key === "1") {
      const btn = activeBox.querySelector("#q-opt-0");
      if (btn) btn.click();
    } else if (key === "b" || key === "2") {
      const btn = activeBox.querySelector("#q-opt-1");
      if (btn) btn.click();
    } else if (key === "c" || key === "3") {
      const btn = activeBox.querySelector("#q-opt-2");
      if (btn) btn.click();
    } else if (key === "d" || key === "4") {
      const btn = activeBox.querySelector("#q-opt-3");
      if (btn) btn.click();
    } else if (key === "h") {
      const btn = activeBox.querySelector(".btn-conf.high");
      if (btn) btn.click();
    } else if (key === "m") {
      const btn = activeBox.querySelector(".btn-conf.medium");
      if (btn) btn.click();
    } else if (key === "l") {
      const btn = activeBox.querySelector(".btn-conf.low");
      if (btn) btn.click();
    } else if (e.key === "Enter") {
      const submitBtn = activeBox.querySelector("#btn-next-q");
      if (submitBtn) submitBtn.click();
    }
  });
}

function setupNavigation() {
  document.querySelectorAll(".sidebar-link").forEach(link => {
    link.addEventListener("click", () => {
      const view = link.dataset.view;
      if (view) switchView(view);
    });
  });
}

function switchView(viewName) {
  state.currentView = viewName;
  document.querySelectorAll(".sidebar-link").forEach(l => {
    l.classList.toggle("active", l.dataset.view === viewName);
  });

  const views = ["chat", "dashboard", "admin", "manual"];
  views.forEach(v => {
    const el = document.getElementById(`view-${v}`);
    if (el) {
      if (v === "chat") {
        el.style.display = viewName === "chat" ? "flex" : "none";
      } else {
        el.style.display = viewName === v ? "block" : "none";
      }
    }
  });

  if (viewName === "dashboard") {
    loadDashboardAnalytics();
  } else if (viewName === "admin") {
    loadAdminTaxonomy();
  }
}

async function checkAuthAndLoad() {
  try {
    const res = await fetch("/api/auth/me");
    if (res.ok) {
      const data = await res.json();
      state.currentUser = { userId: data.user_id, name: data.name, role: data.role };
    }
  } catch (e) {
    console.warn("Using default student credentials:", e);
  }
  updateUserProfileDisplay();
}

function updateUserProfileDisplay() {
  const nameEl = document.getElementById("user-display-name");
  const idEl = document.getElementById("user-display-id");
  const avatarEl = document.getElementById("user-avatar-initial");
  const welcomeEl = document.getElementById("welcome-username");

  const firstName = state.currentUser.name.split(" ")[0] || "Student";
  if (nameEl) nameEl.textContent = state.currentUser.name;
  if (idEl) idEl.textContent = `${state.currentUser.userId} (${state.currentUser.role.toUpperCase()})`;
  if (avatarEl) avatarEl.textContent = state.currentUser.name.charAt(0).toUpperCase();
  if (welcomeEl) welcomeEl.textContent = firstName;

  // Toggle admin sidebar item based on role
  const adminLink = document.querySelector('[data-view="admin"]');
  if (adminLink) {
    adminLink.style.display = (state.currentUser.role === "admin" || state.currentUser.userId === "admin") ? "flex" : "none";
  }
}

function startNewChat() {
  state.activeSession = null;
  state.currentQuestionIndex = 0;
  state.submittedAnswers = [];
  state.currentSelection = null;
  state.currentConfidence = null;

  switchView("chat");
  const welcome = document.getElementById("gemini-welcome-block");
  if (welcome) welcome.style.display = "block";

  const conv = document.getElementById("chat-conversation");
  if (conv) conv.innerHTML = "";

  const titleEl = document.getElementById("chat-header-title");
  if (titleEl) titleEl.textContent = "AutoQuiz - Adaptive Practice";

  const statusEl = document.getElementById("chat-header-status");
  if (statusEl) statusEl.innerHTML = `<span class="status-chip">Ready</span>`;

  if (window.ThreeElements && window.ThreeElements.init) {
    setTimeout(() => window.ThreeElements.init(), 50);
  }
}

// --- Chat Message Appender ---
function appendMessage(role, htmlContent) {
  const conv = document.getElementById("chat-conversation");
  if (!conv) return null;

  // Hide welcome banner once conversation starts
  const welcome = document.getElementById("gemini-welcome-block");
  if (welcome) welcome.style.display = "none";

  const msgId = "msg_" + Math.random().toString(36).substring(2, 9);
  const isAi = role === "ai";
  const authorName = isAi ? "AutoQuiz Assistant" : (state.currentUser.name || "Student");

  const msgDiv = document.createElement("div");
  msgDiv.className = `chat-msg ${isAi ? 'assistant' : 'user'}`;
  msgDiv.id = msgId;
  msgDiv.innerHTML = `
    <div class="msg-header-row">
      <span class="msg-author">${escapeHtml(authorName)}</span>
      <span style="font-size:0.72rem; color:var(--text-dim);">${new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
    </div>
    <div class="msg-body">${htmlContent}</div>
  `;

  conv.appendChild(msgDiv);

  // Auto scroll chat to bottom
  const stream = document.getElementById("chat-stream");
  if (stream) {
    stream.scrollTop = stream.scrollHeight;
  }

  // Render LaTeX math
  if (window.renderMathInElement) {
    window.renderMathInElement(msgDiv, {
      delimiters: [
        {left: '$$', right: '$$', display: true},
        {left: '$', right: '$', display: false}
      ]
    });
  }

  return msgDiv;
}

// --- File Attachment & Sample Starters ---
function handleFileSelected(fileList) {
  if (!fileList || fileList.length === 0) return;
  const file = fileList[0];
  document.getElementById("file-input").value = "";
  uploadAndStartQuiz(file);
}

function handleChatInputKey(e) {
  if (e.key === "Enter") {
    handleSendClicked();
  }
}

function handleSendClicked() {
  const input = document.getElementById("chat-input");
  const text = (input.value || "").trim();
  if (!text) return;
  input.value = "";

  appendMessage("user", escapeHtml(text));

  // If user typed something when no session is active, guide them
  if (!state.activeSession) {
    appendMessage("ai", `
      Please attach your course notes using the 'Attach File' button or select one of the suggested sample topics above to generate your adaptive quiz loop.
    `);
  }
}

async function quickStartSample(sampleType) {
  const sampleNames = {
    ml: "Machine Learning Overfitting (PDF)",
    code: "Algorithms & LaTeX Math (Markdown)",
    biz: "Business & Financial Essentials (TXT)"
  };
  const title = sampleNames[sampleType] || sampleType;

  appendMessage("user", `Practice sample topic: <strong>${escapeHtml(title)}</strong>`);
  const loadingMsg = appendMessage("ai", `Grounding course material from <strong>${escapeHtml(title)}</strong> and generating initial question loop...`);

  try {
    const res = await fetch("/api/quiz/quick-start", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-User-ID": state.currentUser.userId
      },
      body: JSON.stringify({ sample: sampleType })
    });

    const textRes = await res.text();
    let data;
    try { data = JSON.parse(textRes); } catch (_) { throw new Error(textRes); }

    if (!res.ok) {
      loadingMsg.querySelector(".msg-content").innerHTML = `Error: ${data.error || "Failed to load sample"}`;
      return;
    }

    loadingMsg.remove();
    initQuizSession(data);
    loadRecentMaterials();
  } catch (err) {
    loadingMsg.querySelector(".msg-content").innerHTML = `Connection Error: ${escapeHtml(err.message)}`;
  }
}

async function uploadAndStartQuiz(file) {
  appendMessage("user", `Uploaded study material: <strong>${escapeHtml(file.name)}</strong>`);
  const loadingMsg = appendMessage("ai", `Parsing <strong>${escapeHtml(file.name)}</strong>, extracting AST code and LaTeX formulas, and preparing your quiz...`);

  const formData = new FormData();
  formData.append("file", file);
  formData.append("overwrite", "true");

  try {
    const res = await fetch("/api/quiz/quick-start", {
      method: "POST",
      headers: { "X-User-ID": state.currentUser.userId },
      body: formData
    });

    const textRes = await res.text();
    let data;
    try { data = JSON.parse(textRes); } catch (_) { throw new Error(textRes); }

    if (res.status === 200 && data.status === "duplicate_prompt") {
      loadingMsg.remove();
      state.pendingDuplicateFile = file;
      showDuplicateModal(data.message);
      return;
    }

    if (!res.ok) {
      loadingMsg.querySelector(".msg-content").innerHTML = `Ingestion Error: ${escapeHtml(data.error || "Upload failed.")}`;
      return;
    }

    loadingMsg.remove();
    initQuizSession(data);
    loadRecentMaterials();
  } catch (err) {
    loadingMsg.querySelector(".msg-content").innerHTML = `Ingestion Error: ${escapeHtml(err.message)}`;
  }
}

function initQuizSession(sessionData) {
  state.activeSession = sessionData;
  state.currentQuestionIndex = sessionData.current_index || 0;
  state.submittedAnswers = sessionData.saved_answers || [];
  state.currentSelection = null;
  state.currentConfidence = null;

  const headerTitle = document.getElementById("chat-header-title");
  if (headerTitle) {
    headerTitle.textContent = `Topic: ${sessionData.topic_name || "Course Notes"}`;
  }

  const headerStatus = document.getElementById("chat-header-status");
  if (headerStatus) {
    headerStatus.innerHTML = `<span class="status-chip remediation">Practice Loop In Progress</span>`;
  }

  renderCurrentQuestionInChat();
}

// --- Question Rendering in Chat Stream ---
function renderCurrentQuestionInChat() {
  const session = state.activeSession;
  if (!session || !session.questions || state.currentQuestionIndex >= session.questions.length) {
    submitFullLoop();
    return;
  }

  const q = session.questions[state.currentQuestionIndex];
  const qNum = state.currentQuestionIndex + 1;
  const total = session.questions.length;

  state.currentSelection = null;
  state.currentConfidence = null;

  const letters = ["A", "B", "C", "D"];

  const questionHtml = `
    <div class="quiz-box" id="active-quiz-box">
      <div class="quiz-header">
        <span style="font-size:0.82rem; font-weight:600; color:var(--google-blue);">QUESTION ${qNum} OF ${total}</span>
        <button class="btn-secondary" style="padding:0.2rem 0.5rem; font-size:0.75rem;" onclick="promptEarlyExit()">Exit Loop</button>
      </div>

      <div class="quiz-stem">${escapeHtml(q.question)}</div>

      <div class="quiz-options">
        ${q.options.map((opt, i) => `
          <button type="button" class="quiz-option-btn" id="q-opt-${i}" onclick="selectChatOption(${i}, '${escapeForJs(opt)}')">
            <span class="opt-letter">${letters[i] || (i + 1)}</span>
            <span style="flex:1;">${escapeHtml(opt)}</span>
          </button>
        `).join("")}
      </div>

      <!-- Mandatory Confidence Rating -->
      <div class="confidence-bar">
        <div class="confidence-label">Rate your confidence (Mandatory):</div>
        <div class="confidence-buttons">
          <button type="button" class="btn-conf high" onclick="selectChatConfidence('High', this)">High Confidence</button>
          <button type="button" class="btn-conf medium" onclick="selectChatConfidence('Medium', this)">Medium Confidence</button>
          <button type="button" class="btn-conf low" onclick="selectChatConfidence('Low', this)">Low Confidence</button>
        </div>
      </div>

      <div class="quiz-actions">
        <button type="button" class="btn-submit-quiz" id="btn-next-q" onclick="submitChatQuestionAnswer()">
          ${qNum === total ? "Finish & Evaluate Loop" : "Next Question →"}
        </button>
      </div>
    </div>
  `;

  appendMessage("ai", questionHtml);
}

function selectChatOption(idx, answerValue) {
  state.currentSelection = answerValue;
  const activeBox = document.getElementById("active-quiz-box");
  if (!activeBox) return;
  activeBox.querySelectorAll(".quiz-option-btn").forEach((btn, i) => {
    btn.classList.toggle("selected", i === idx);
  });
}

function selectChatConfidence(level, element) {
  state.currentConfidence = level;
  const activeBox = document.getElementById("active-quiz-box");
  if (!activeBox) return;
  activeBox.querySelectorAll(".btn-conf").forEach(b => b.classList.remove("selected"));
  element.classList.add("selected");
}

function submitChatQuestionAnswer() {
  if (!state.currentSelection) {
    alert("Please select an answer choice.");
    return;
  }
  if (!state.currentConfidence) {
    alert("Confidence tag required: Please select High, Medium, or Low confidence before proceeding.");
    return;
  }

  // Freeze the current active question box immediately
  const activeBox = document.getElementById("active-quiz-box");
  if (activeBox) {
    activeBox.id = ""; // remove id so next question box becomes active
    activeBox.querySelectorAll("button").forEach(b => b.disabled = true);
  }

  const selectedAnswer = state.currentSelection;
  const conf = state.currentConfidence;
  const qIdx = state.currentQuestionIndex;
  const session = state.activeSession;

  // Append user's choice message in the chat immediately (0ms perceived latency)
  appendMessage("user", `Selected: <strong>${escapeHtml(selectedAnswer)}</strong> [${conf} Confidence]`);

  // Asynchronous non-blocking background progress save (PERF: student does not wait for HTTP roundtrip)
  if (session && session.session_id) {
    fetch(`/api/quiz/session/${session.session_id}/progress`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-User-ID": state.currentUser.userId
      },
      body: JSON.stringify({
        question_index: qIdx,
        selected_answer: selectedAnswer,
        confidence: conf
      })
    }).catch(e => console.warn("Background progress sync:", e));
  }

  state.submittedAnswers.push({
    question_index: qIdx,
    selected_answer: selectedAnswer,
    confidence: conf
  });

  state.currentQuestionIndex++;
  renderCurrentQuestionInChat();
}

async function submitFullLoop() {
  const evalLoading = appendMessage("ai", "Evaluating your loop responses against source notes and computing mastery score...");

  const session = state.activeSession;
  try {
    const res = await fetch(`/api/quiz/session/${session.session_id}/submit`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-User-ID": state.currentUser.userId
      },
      body: JSON.stringify({ answers: state.submittedAnswers })
    });

    const result = await res.json();
    evalLoading.remove();

    if (!res.ok) {
      appendMessage("ai", `Evaluation Error: ${result.error}`);
      return;
    }

    const isMastered = result.is_mastered;
    const headerStatus = document.getElementById("chat-header-status");
    if (headerStatus) {
      headerStatus.innerHTML = isMastered
        ? `<span class="status-chip mastered">100% Mastered</span>`
        : `<span class="status-chip remediation">Remediation Required (${result.score}%)</span>`;
    }

    const trophyHtml = isMastered
      ? `<div style="display:flex; align-items:center; gap:1.25rem; margin:0.75rem 0;">
           <div id="mastery-3d-stage" style="width:100px; height:100px; flex-shrink:0;"></div>
           <div>
             <div style="font-weight:700; color:var(--success-green); font-size:1rem;">100% Mastery Verified</div>
             <div style="font-size:0.82rem; color:var(--text-muted); margin-top:0.2rem;">All concepts verified with sufficient confidence. Next sequential module is unlocked.</div>
           </div>
         </div>`
      : ``;

    const summaryHtml = `
      <div class="eval-box">
        <div class="eval-banner ${isMastered ? 'success' : 'warning'}">
          <div style="font-size:1.1rem; font-weight:700; margin-bottom:0.25rem;">
            ${isMastered ? '100% Mastery Achieved' : `Loop Score: ${result.score}% (Remediation Required)`}
          </div>
          <p style="font-size:0.88rem; line-height:1.5;">
            ${isMastered
              ? 'All concepts verified with High/Medium confidence. Next sequential module is now unlocked.'
              : 'Advancement requires a strict 100% score on the current loop iteration (BR-2). Review the feedback below and begin your next targeted question loop.'}
          </p>
        </div>

        ${trophyHtml}

        <div style="font-size:0.88rem; font-weight:700; margin-bottom:0.75rem;">Verified Concept Explanations:</div>
        <div style="display:flex; flex-direction:column; gap:0.6rem; margin-bottom:1.25rem;">
          ${result.evaluations.map((ev, i) => `
            <div style="background:#18191a; padding:0.75rem 0.95rem; border-radius:2px; border-left:3px solid ${ev.is_correct && !ev.is_unverified ? 'var(--success-green)' : (ev.is_unverified ? 'var(--warning-amber)' : 'var(--danger-red)')};">
              <div style="font-weight:600; font-size:0.88rem; margin-bottom:0.2rem;">Q${i+1}: ${escapeHtml(ev.question)}</div>
              <div style="font-size:0.82rem; color:var(--text-dim);">Your answer: <span style="color:var(--text-main); font-weight:500;">${escapeHtml(ev.selected)}</span> (${ev.confidence} Confidence)</div>
              <div style="font-size:0.82rem; color:var(--text-muted); margin-top:0.2rem; line-height:1.4;">${escapeHtml(ev.feedback)}</div>
            </div>
          `).join("")}
        </div>

        <div style="display:flex; justify-content:space-between; align-items:center;">
          <button class="btn-secondary" onclick="startNewChat()">Start Different Topic</button>
          ${isMastered
            ? `<button class="btn-submit-quiz" onclick="switchView('dashboard')">View Updated Analytics</button>`
            : `<button class="btn-submit-quiz" onclick="launchQuizSession('${result.topic_id}')">Begin New Remediation Loop</button>`
          }
        </div>
      </div>
    `;

    appendMessage("ai", summaryHtml);

    // Mount 3D Mastery Trophy if 100% mastery achieved
    if (isMastered && window.ThreeElements && window.ThreeElements.renderMasteryTrophy) {
      setTimeout(() => {
        window.ThreeElements.renderMasteryTrophy("mastery-3d-stage");
      }, 50);
    }
  } catch (err) {
    evalLoading.querySelector(".msg-content").innerHTML = `Evaluation Error: ${escapeHtml(err.message)}`;
  }
}

async function launchQuizSession(topicId) {
  appendMessage("ai", `Preparing newly framed questions for your remediation loop...`);

  try {
    const res = await fetch("/api/quiz/session/start", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-User-ID": state.currentUser.userId
      },
      body: JSON.stringify({ topic_id: topicId, num_questions: 3 })
    });

    const data = await res.json();
    if (!res.ok) {
      appendMessage("ai", `Cannot start session: ${data.error}`);
      return;
    }

    initQuizSession(data);
  } catch (e) {
    appendMessage("ai", `Session launch error: ${e.message}`);
  }
}

function promptEarlyExit() {
  const conf = confirm("Topic mastery is not yet complete. Current loop progress will be saved as 'In Progress'. Are you sure you want to exit?");
  if (conf) {
    if (state.activeSession) {
      fetch(`/api/quiz/session/${state.activeSession.session_id}/exit`, {
        method: "POST",
        headers: { "X-User-ID": state.currentUser.userId }
      });
    }
    startNewChat();
  }
}

// --- Recent Materials Sidebar List ---
async function loadRecentMaterials() {
  const list = document.getElementById("sidebar-recent-list");
  if (!list) return;

  try {
    const res = await fetch("/api/documents", {
      headers: { "X-User-ID": state.currentUser.userId }
    });
    const data = await res.json();
    const docs = data.documents || [];

    if (docs.length === 0) {
      list.innerHTML = `<li style="padding:0.4rem 0.75rem; font-size:0.78rem; color:var(--text-dim);">No materials uploaded yet</li>`;
      return;
    }

    list.innerHTML = docs.slice(0, 8).map(d => `
      <li class="sidebar-link" title="${escapeHtml(d.title)}" onclick="practiceRecentDoc('${d.doc_id}', '${escapeForJs(d.title)}')">
        <span style="overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${escapeHtml(d.title)}</span>
      </li>
    `).join("");
  } catch (e) {
    console.warn("Could not load recent docs:", e);
  }
}

async function practiceRecentDoc(docId, title) {
  switchView("chat");
  appendMessage("user", `Start practice on recent document: <strong>${escapeHtml(title)}</strong>`);
  const loading = appendMessage("ai", `Fetching curriculum modules for <strong>${escapeHtml(title)}</strong>...`);

  try {
    const res = await fetch("/api/quiz/topics", {
      headers: { "X-User-ID": state.currentUser.userId }
    });
    const data = await res.json();
    const docTopics = (data.topics || []).filter(t => t.doc_id === docId);

    loading.remove();
    if (docTopics.length === 0) {
      appendMessage("ai", `No topics found for this document.`);
      return;
    }

    // Launch first unlocked topic
    const targetTopic = docTopics.find(t => t.is_unlocked) || docTopics[0];
    launchQuizSession(targetTopic.topic_id);
  } catch (e) {
    loading.querySelector(".msg-content").innerHTML = `Error: ${e.message}`;
  }
}

// --- Analytics & Dashboard View ---
async function loadDashboardAnalytics() {
  const container = document.getElementById("analytics-view-container");
  if (!container) return;

  container.innerHTML = `<div style="color:var(--text-dim); padding:1rem;">Loading performance metrics...</div>`;

  try {
    const res = await fetch("/api/analytics/dashboard", {
      headers: { "X-User-ID": state.currentUser.userId }
    });
    const data = await res.json();

    if (!res.ok) {
      container.innerHTML = `<div class="eval-banner warning">${data.error}</div>`;
      return;
    }

    if (data.welcome_state) {
      container.innerHTML = `
        <div class="panel-card">
          <p style="font-weight:500;">${data.message}</p>
          <button class="btn-submit-quiz" style="margin-top:1rem;" onclick="startNewChat()">Start Your First Practice Session</button>
        </div>
      `;
      return;
    }

    container.innerHTML = `
      <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(200px, 1fr)); gap:1rem; margin-bottom:1.5rem;">
        <div class="panel-card">
          <div style="font-size:0.8rem; color:var(--text-dim);">OVERALL READINESS</div>
          <div style="font-size:2rem; font-weight:600; color:var(--google-blue); margin:0.25rem 0;">${data.readiness_percentage}%</div>
          <div style="font-size:0.8rem; color:var(--text-muted);">${data.mastered_topics} of ${data.total_topics} topics mastered</div>
        </div>
        <div class="panel-card">
          <div style="font-size:0.8rem; color:var(--text-dim);">FIRST-ATTEMPT SUCCESS (BR-4)</div>
          <div style="font-size:2rem; font-weight:600; color:var(--text-main); margin:0.25rem 0;">${data.first_try_mastery_percentage}%</div>
          <div style="font-size:0.8rem; color:var(--text-muted);">Looped Mastery: ${data.looped_mastery_percentage}%</div>
        </div>
        <div class="panel-card">
          <div style="font-size:0.8rem; color:var(--text-dim);">AUDIT LATENCY (PERF-3)</div>
          <div style="font-size:2rem; font-weight:600; color:var(--success-green); margin:0.25rem 0;">${data.render_time_ms} ms</div>
          <div style="font-size:0.8rem; color:var(--text-muted);">Sub-second target verified</div>
        </div>
      </div>

      <div class="panel-card">
        <h3 style="font-size:1rem; font-weight:500; margin-bottom:1rem;">Weakness Heatmap & Mastery Breakdown</h3>
        <div style="display:grid; grid-template-columns:repeat(auto-fill, minmax(200px, 1fr)); gap:0.75rem;">
          ${data.heatmap_tiles.map(tile => `
            <div style="background:#18191a; padding:1rem; border-radius:4px; border-top:3px solid ${tile.color_hex};">
              <div style="font-weight:500; font-size:0.92rem; margin-bottom:0.25rem;">${escapeHtml(tile.topic_name)}</div>
              <div style="font-size:0.78rem; color:${tile.color_hex}; font-weight:600; margin-bottom:0.4rem;">${tile.weakness_level}</div>
              <div style="font-size:0.78rem; color:var(--text-dim);">Avg Score: ${tile.average_score}%</div>
              <div style="font-size:0.78rem; color:var(--text-dim);">Failures: ${tile.failure_count} | Unverified: ${tile.unverified_guesses}</div>
            </div>
          `).join("")}
        </div>
      </div>
    `;
  } catch (err) {
    container.innerHTML = `<div style="color:var(--danger-red);">Failed to load analytics: ${err.message}</div>`;
  }
}

// --- Admin Portal View ---
async function loadAdminTaxonomy() {
  const container = document.getElementById("admin-taxonomy-container");
  if (!container) return;

  try {
    const res = await fetch("/api/admin/taxonomy", {
      headers: { "X-User-Role": state.currentUser.role, "X-User-ID": state.currentUser.userId }
    });
    const data = await res.json();
    if (!res.ok) {
      container.innerHTML = `<div style="color:var(--danger-red);">Access Denied: Admin authorization required.</div>`;
      return;
    }

    container.innerHTML = `
      <div style="display:flex; flex-direction:column; gap:0.5rem;">
        ${(data.taxonomy || []).map(t => `
          <div style="background:#18191a; padding:0.75rem 1rem; border-radius:4px; display:flex; justify-content:space-between; align-items:center;">
            <div>
              <strong>${escapeHtml(t.topic_name)}</strong>
              <div style="font-size:0.8rem; color:var(--text-dim);">${escapeHtml(t.description || "Core syllabus")}</div>
            </div>
            <button class="btn-secondary" style="padding:0.25rem 0.5rem; font-size:0.75rem;" onclick="adminDeleteTopic(${t.id})">Delete</button>
          </div>
        `).join("")}
      </div>
    `;
  } catch (err) {
    container.innerHTML = `<div style="color:var(--danger-red);">Failed to load taxonomy: ${err.message}</div>`;
  }
}

async function adminWipeVectors() {
  const docId = prompt("Enter Document ID to purge vectors from Chroma DB:");
  if (!docId) return;
  try {
    const res = await fetch(`/api/admin/vectors/wipe/${encodeURIComponent(docId)}`, {
      method: "DELETE",
      headers: { "X-User-Role": state.currentUser.role, "X-User-ID": state.currentUser.userId }
    });
    const d = await res.json();
    alert(d.message || d.error);
    loadRecentMaterials();
  } catch (e) { alert(e.message); }
}

async function adminResetStudent() {
  const targetUser = prompt("Enter Student ID to reset (e.g. 24CSB1A12):", state.currentUser.userId);
  if (!targetUser) return;
  try {
    const res = await fetch(`/api/admin/student/reset/${encodeURIComponent(targetUser)}`, {
      method: "POST",
      headers: { "X-User-Role": state.currentUser.role, "X-User-ID": state.currentUser.userId }
    });
    const d = await res.json();
    alert(d.message || d.error);
    loadDashboardAnalytics();
  } catch (e) { alert(e.message); }
}

async function adminDeleteTopic(topicId) {
  if (!confirm("Are you sure you want to delete this topic?")) return;
  try {
    await fetch(`/api/admin/taxonomy/${topicId}`, {
      method: "DELETE",
      headers: { "X-User-Role": state.currentUser.role, "X-User-ID": state.currentUser.userId }
    });
    loadAdminTaxonomy();
  } catch (e) { alert(e.message); }
}

// --- Duplicate Resolution Modal ---
function showDuplicateModal(message) {
  const modal = document.getElementById("duplicate-modal");
  document.getElementById("duplicate-modal-msg").innerText = message;
  modal.style.display = "flex";
}

function closeDuplicateModal() {
  document.getElementById("duplicate-modal").style.display = "none";
  state.pendingDuplicateFile = null;
}

function resolveDuplicate(choice) {
  const file = state.pendingDuplicateFile;
  closeDuplicateModal();
  if (!file) return;

  const overwrite = (choice === "overwrite");
  const createNewVersion = (choice === "version");

  const formData = new FormData();
  formData.append("file", file);
  if (overwrite) formData.append("overwrite", "true");
  if (createNewVersion) formData.append("create_new_version", "true");

  appendMessage("ai", `Processing '${file.name}' with choice: ${choice}...`);

  fetch("/api/quiz/quick-start", {
    method: "POST",
    headers: { "X-User-ID": state.currentUser.userId },
    body: formData
  })
  .then(res => res.json())
  .then(data => {
    if (data.error) {
      appendMessage("ai", `Error: ${data.error}`);
    } else {
      initQuizSession(data);
    }
  })
  .catch(err => {
    appendMessage("ai", `Ingestion Error: ${err.message}`);
  });
}

// --- User Account Switcher ---
function openAuthModal() {
  document.getElementById("auth-modal").style.display = "flex";
}

function closeAuthModal() {
  document.getElementById("auth-modal").style.display = "none";
}

async function switchUserAccount(username, password, role) {
  try {
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password })
    });
    const data = await res.json();
    if (res.ok) {
      state.currentUser = {
        userId: data.user.user_id,
        name: data.user.name,
        role: data.user.role
      };
      closeAuthModal();
      updateUserProfileDisplay();
      startNewChat();
      loadRecentMaterials();
    } else {
      alert(`Login failed: ${data.error}`);
    }
  } catch (e) {
    alert(`Login error: ${e.message}`);
  }
}

// --- Utilities ---
function escapeHtml(text) {
  if (!text) return "";
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function escapeForJs(text) {
  if (!text) return "";
  return String(text)
    .replace(/\\/g, "\\\\")
    .replace(/'/g, "\\'")
    .replace(/"/g, '\\"')
    .replace(/\n/g, "\\n");
}
