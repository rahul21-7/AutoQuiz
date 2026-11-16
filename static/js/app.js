/**
 * AutoQuiz Web Client Application
 * Implements SRS & Vision Document workflows: Ingestion, Adaptive Remediation,
 * Confidence Guard, Spaced Repetition Verification, and Analytics Heatmap.
 */

const state = {
  currentUser: {
    userId: "24CSB1A12",
    name: "Dasari Rahul",
    role: "student"
  },
  activeTab: "dashboard",
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
  setupUploadDropzone();
  checkAuthAndLoad();
});

function setupNavigation() {
  document.querySelectorAll(".nav-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const target = btn.dataset.target;
      switchTab(target);
    });
  });
}

function switchTab(tabId) {
  state.activeTab = tabId;
  document.querySelectorAll(".nav-btn").forEach(b => b.classList.toggle("active", b.dataset.target === tabId));
  document.querySelectorAll(".tab-pane").forEach(p => p.classList.toggle("active", p.id === `tab-${tabId}`));

  if (tabId === "dashboard" || tabId === "analytics") {
    loadDashboardAnalytics();
  } else if (tabId === "practice") {
    loadTopicsForPractice();
  } else if (tabId === "admin") {
    loadAdminTaxonomy();
  } else if (tabId === "ingest") {
    loadDocumentList();
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
    console.warn("Using default student session:", e);
  }
  updateUserBadge();
  switchTab("dashboard");
}

function updateUserBadge() {
  const badge = document.getElementById("user-profile-display");
  if (badge) {
    badge.innerHTML = `
      <span class="user-tag">👤 ${state.currentUser.userId} (${state.currentUser.role.toUpperCase()})</span>
      <button class="btn-secondary" style="padding:0.3rem 0.6rem; font-size:0.8rem;" onclick="openAuthModal()">Switch User</button>
    `;
  }
  // Show or hide admin tab
  const adminBtn = document.querySelector('[data-target="admin"]');
  if (adminBtn) {
    adminBtn.style.display = (state.currentUser.role === "admin" || state.currentUser.userId === "admin") ? "block" : "none";
  }
}

// --- Document Ingestion (REQ_01 to REQ_05, TC-07 to TC-16) ---
function setupUploadDropzone() {
  const dropzone = document.getElementById("upload-dropzone");
  const fileInput = document.getElementById("file-input");

  if (!dropzone || !fileInput) return;

  dropzone.addEventListener("click", () => fileInput.click());
  dropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropzone.classList.add("dragover");
  });
  dropzone.addEventListener("dragleave", () => dropzone.classList.remove("dragover"));
  dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropzone.classList.remove("dragover");
    if (e.dataTransfer.files.length > 0) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  });

  fileInput.addEventListener("change", () => {
    if (fileInput.files.length > 0) {
      handleFileUpload(fileInput.files[0]);
    }
  });
}

async function handleFileUpload(file, overwrite = false, createNewVersion = false) {
  const statusBanner = document.getElementById("upload-status");
  statusBanner.innerHTML = `<div class="alert-banner warning">⏳ Vectorizing and parsing '${file.name}' via local AST engine...</div>`;

  const formData = new FormData();
  formData.append("file", file);
  if (overwrite) formData.append("overwrite", "true");
  if (createNewVersion) formData.append("create_new_version", "true");

  try {
    const res = await fetch("/api/documents/upload", {
      method: "POST",
      headers: { "X-User-ID": state.currentUser.userId },
      body: formData
    });

    const data = await res.json();

    if (res.status === 200 && data.status === "duplicate_prompt") {
      // Show duplicate resolution prompt (REQ_05, TC-13 to TC-16)
      state.pendingDuplicateFile = file;
      showDuplicateModal(data.message);
      statusBanner.innerHTML = "";
      return;
    }

    if (!res.ok) {
      statusBanner.innerHTML = `<div class="alert-banner danger">❌ Ingestion Error: ${data.error || "Upload failed."}</div>`;
      return;
    }

    statusBanner.innerHTML = `
      <div class="alert-banner success">
        <div>
          <strong>✅ Document Vectorized Successfully!</strong>
          <p>Title: <em>${data.title}</em> | Chunks: ${data.chunk_count} | Processing Time: ${data.processing_time_seconds}s</p>
          <p>Discovered Sub-Topics: ${data.topics.join(", ")}</p>
        </div>
      </div>
    `;
    loadDocumentList();
  } catch (err) {
    statusBanner.innerHTML = `<div class="alert-banner danger">❌ Network or Engine Error: ${err.message}</div>`;
  }
}

function showDuplicateModal(message) {
  const modal = document.getElementById("duplicate-modal");
  document.getElementById("duplicate-modal-msg").innerText = message;
  modal.style.display = "flex";
}

function closeDuplicateModal() {
  document.getElementById("duplicate-modal").style.display = "none";
  state.pendingDuplicateFile = null;
}

function resolveDuplicate(action) {
  const file = state.pendingDuplicateFile;
  closeDuplicateModal();
  if (action === "overwrite") {
    handleFileUpload(file, true, false);
  } else if (action === "version") {
    handleFileUpload(file, false, true);
  }
}

async function loadDocumentList() {
  const container = document.getElementById("documents-container");
  if (!container) return;

  try {
    const res = await fetch("/api/documents", {
      headers: { "X-User-ID": state.currentUser.userId }
    });
    const data = await res.json();
    state.documents = data.documents || [];

    if (state.documents.length === 0) {
      container.innerHTML = `<p class="metric-caption">No uploaded documents yet. Upload a PDF, Markdown, or TXT file above.</p>`;
      return;
    }

    container.innerHTML = state.documents.map(doc => `
      <div class="topic-row">
        <div>
          <strong>${doc.title}</strong> <span class="status-badge unmastered">${doc.file_type}</span>
          <div class="metric-caption">Chunks: ${doc.chunk_count} | Version: ${doc.version}</div>
        </div>
        <div>
          <button class="btn-secondary" onclick="viewDocumentTopics('${doc.doc_id}')">Practice Topics</button>
        </div>
      </div>
    `).join("");
  } catch (e) {
    container.innerHTML = `<p class="metric-caption text-danger">Failed to load documents.</p>`;
  }
}

// --- Adaptive Practice Loop (UC-2, REQ_10, REQ_11, REQ_12, BR-2, BR-6) ---
async function loadTopicsForPractice() {
  const container = document.getElementById("practice-topics-container");
  if (!container) return;

  try {
    const res = await fetch("/api/quiz/topics", {
      headers: { "X-User-ID": state.currentUser.userId }
    });
    const data = await res.json();
    state.topics = data.topics || [];

    if (state.topics.length === 0) {
      container.innerHTML = `
        <div class="alert-banner warning">
          No topics available. Please upload a course document (PDF/MD/TXT) in the Document Ingestion tab.
        </div>
      `;
      return;
    }

    container.innerHTML = state.topics.map(t => {
      const isLocked = !t.is_unlocked;
      const statusClass = t.mastery_status.toLowerCase().replace(" ", "-");
      return `
        <div class="topic-row ${isLocked ? 'locked' : ''}">
          <div class="topic-meta">
            <div>
              <strong>${t.name}</strong>
              <div class="metric-caption">Attempts: ${t.attempt_count} | Sequential Node #${t.order_index + 1}</div>
            </div>
          </div>
          <div style="display:flex; align-items:center; gap:0.75rem;">
            <span class="status-badge ${statusClass}">${t.mastery_status}</span>
            ${isLocked ?
              `<button class="btn-secondary" disabled title="Locked: Complete previous module with 100% mastery first">🔒 Locked</button>` :
              `<button class="btn-primary" onclick="launchQuizSession('${t.topic_id}')">Start Practice Loop</button>`
            }
          </div>
        </div>
      `;
    }).join("");
  } catch (err) {
    container.innerHTML = `<p class="metric-caption text-danger">Error loading topics: ${err.message}</p>`;
  }
}

function viewDocumentTopics(docId) {
  switchTab("practice");
}

async function launchQuizSession(topicId) {
  const arena = document.getElementById("practice-arena");
  const listArea = document.getElementById("practice-list-area");

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
      alert(`Cannot start session: ${data.error}`);
      return;
    }

    state.activeSession = data;
    state.currentQuestionIndex = data.current_index || 0;
    state.submittedAnswers = data.saved_answers || [];
    state.currentSelection = null;
    state.currentConfidence = null;

    listArea.style.display = "none";
    arena.style.display = "block";
    renderCurrentQuestion();
  } catch (e) {
    alert(`Session launch failed: ${e.message}`);
  }
}

function renderCurrentQuestion() {
  const session = state.activeSession;
  if (!session || !session.questions || state.currentQuestionIndex >= session.questions.length) {
    // Completed all questions in the loop, prompt submission
    renderLoopSubmissionSummary();
    return;
  }

  const q = session.questions[state.currentQuestionIndex];
  const qNum = state.currentQuestionIndex + 1;
  const total = session.questions.length;

  state.currentSelection = null;
  state.currentConfidence = null;

  const container = document.getElementById("active-question-container");
  container.innerHTML = `
    <div class="question-card">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem;">
        <span class="status-badge in-progress">Question ${qNum} of ${total}</span>
        <button class="btn-secondary" style="font-size:0.8rem; padding:0.3rem 0.6rem;" onclick="promptEarlyExit()">Exit Session</button>
      </div>
      
      <div class="question-stem" id="q-stem-text">${escapeHtml(q.question)}</div>

      <div class="options-grid">
        ${q.options.map((opt, i) => `
          <label class="option-label" id="opt-label-${i}" onclick="selectAnswerOption(${i}, '${escapeForJs(opt)}')">
            <input type="radio" name="practice_option" value="${escapeHtml(opt)}">
            <span>${escapeHtml(opt)}</span>
          </label>
        `).join("")}
      </div>

      <!-- 1-Click Confidence Tagging Selector (REQ_10, TC-49, TC-50) -->
      <div class="confidence-selector-container">
        <div class="confidence-title">
          <span>🎯 Select Your Confidence Rating (Mandatory):</span>
        </div>
        <div class="confidence-radios">
          <div class="confidence-pill high" onclick="selectConfidenceRating('High', this)">High Confidence</div>
          <div class="confidence-pill medium" onclick="selectConfidenceRating('Medium', this)">Medium Confidence</div>
          <div class="confidence-pill low" onclick="selectConfidenceRating('Low', this)">Low Confidence</div>
        </div>
      </div>

      <div style="display:flex; justify-content:flex-end;">
        <button class="btn-primary" id="btn-submit-q" onclick="submitCurrentQuestionAnswer()">
          ${qNum === total ? "Finish & Evaluate Loop" : "Next Question →"}
        </button>
      </div>
    </div>
  `;

  // Render LaTeX math via KaTeX if available
  if (window.renderMathInElement) {
    window.renderMathInElement(container, {
      delimiters: [
        {left: '$$', right: '$$', display: true},
        {left: '$', right: '$', display: false}
      ]
    });
  }
}

function selectAnswerOption(idx, answerValue) {
  state.currentSelection = answerValue;
  document.querySelectorAll(".option-label").forEach((el, i) => {
    el.classList.toggle("selected", i === idx);
  });
}

function selectConfidenceRating(level, element) {
  state.currentConfidence = level;
  document.querySelectorAll(".confidence-pill").forEach(el => el.classList.remove("selected"));
  element.classList.add("selected");
}

async function submitCurrentQuestionAnswer() {
  if (!state.currentSelection) {
    alert("Please select an answer choice.");
    return;
  }
  if (!state.currentConfidence) {
    // REQ_10, TC-49: submission blocked if confidence missing
    alert("⚠️ Unselected Confidence Tag: You must choose High, Medium, or Low confidence before proceeding.");
    return;
  }

  // Save progress via API (TC-47)
  const session = state.activeSession;
  try {
    await fetch(`/api/quiz/session/${session.session_id}/progress`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-User-ID": state.currentUser.userId
      },
      body: JSON.stringify({
        question_index: state.currentQuestionIndex,
        selected_answer: state.currentSelection,
        confidence: state.currentConfidence
      })
    });
  } catch (e) {
    console.error("Progress save failed:", e);
  }

  state.submittedAnswers.push({
    question_index: state.currentQuestionIndex,
    selected_answer: state.currentSelection,
    confidence: state.currentConfidence
  });

  state.currentQuestionIndex++;
  renderCurrentQuestion();
}

async function renderLoopSubmissionSummary() {
  const container = document.getElementById("active-question-container");
  container.innerHTML = `<div class="alert-banner warning">⏳ Evaluating responses and grounding against source notes...</div>`;

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
    if (!res.ok) {
      container.innerHTML = `<div class="alert-banner danger">❌ Evaluation Error: ${result.error}</div>`;
      return;
    }

    const isMastered = result.is_mastered;

    container.innerHTML = `
      <div class="question-card">
        <div style="text-align:center; margin-bottom:1.5rem;">
          <h2 style="font-size:1.75rem; color:${isMastered ? 'var(--success-green)' : 'var(--warning-amber)'}; margin-bottom:0.5rem;">
            ${isMastered ? '🎉 100% Mastery Achieved!' : '⚠️ Remediation Required (Mastery Below 100%)'}
          </h2>
          <div class="metric-big">${result.score}%</div>
          <p class="metric-caption">
            ${isMastered ?
              'All concepts verified with High/Medium confidence. Next sequential module is now unlocked!' :
              'Advancement requires a strict 100% score on the current loop iteration (BR-2). Review the verified feedback below and begin a newly framed question loop.'}
          </p>
        </div>

        <h3 style="margin-bottom:1rem; border-bottom:1px solid var(--border-color); padding-bottom:0.5rem;">Verified Answer Analysis & Grounding:</h3>
        <div style="display:flex; flex-direction:column; gap:1rem; margin-bottom:2rem;">
          ${result.evaluations.map((ev, i) => `
            <div style="background:var(--bg-secondary); padding:1rem; border-radius:var(--radius-md); border-left:4px solid ${ev.is_correct && !ev.is_unverified ? 'var(--success-green)' : (ev.is_unverified ? 'var(--warning-amber)' : 'var(--danger-red)')};">
              <div><strong>Q${i+1}: ${escapeHtml(ev.question)}</strong></div>
              <div style="margin:0.25rem 0; font-size:0.9rem;">Your Answer: <em>${escapeHtml(ev.selected)}</em> (${ev.confidence} Confidence)</div>
              <div style="color:var(--text-muted); font-size:0.85rem;">${escapeHtml(ev.feedback)}</div>
            </div>
          `).join("")}
        </div>

        <div style="display:flex; justify-content:space-between;">
          <button class="btn-secondary" onclick="closePracticeSession()">Back to Topics</button>
          ${isMastered ?
            `<button class="btn-primary" onclick="switchTab('analytics')">View Updated Analytics</button>` :
            `<button class="btn-primary" onclick="launchQuizSession('${result.topic_id}')">🔄 Begin New Remediation Loop</button>`
          }
        </div>
      </div>
    `;

    if (window.renderMathInElement) {
      window.renderMathInElement(container, {
        delimiters: [{left: '$$', right: '$$', display: true}, {left: '$', right: '$', display: false}]
      });
    }
  } catch (err) {
    container.innerHTML = `<div class="alert-banner danger">❌ Evaluation Error: ${err.message}</div>`;
  }
}

function promptEarlyExit() {
  const conf = confirm("Warning: Current topic mastery is incomplete and progress on this loop will be saved as 'In Progress'. Are you sure you want to exit?");
  if (conf) {
    if (state.activeSession) {
      fetch(`/api/quiz/session/${state.activeSession.session_id}/exit`, {
        method: "POST",
        headers: { "X-User-ID": state.currentUser.userId }
      });
    }
    closePracticeSession();
  }
}

function closePracticeSession() {
  state.activeSession = null;
  document.getElementById("practice-arena").style.display = "none";
  document.getElementById("practice-list-area").style.display = "block";
  loadTopicsForPractice();
}

// --- Spaced Repetition Micro-Verification (UC-5, TC-59 to TC-61) ---
async function startDecayMicroVerification(topicId) {
  try {
    const res = await fetch("/api/quiz/micro-verification/start", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-User-ID": state.currentUser.userId },
      body: JSON.stringify({ topic_id: topicId })
    });
    const data = await res.json();
    if (!res.ok) {
      alert(data.error);
      return;
    }

    // Modal or Practice runner for 2 questions
    switchTab("practice");
    state.activeSession = {
      session_id: `micro_${topicId}`,
      topic_id: topicId,
      questions: data.questions,
      is_micro: true
    };
    state.currentQuestionIndex = 0;
    state.submittedAnswers = [];
    document.getElementById("practice-list-area").style.display = "none";
    document.getElementById("practice-arena").style.display = "block";
    renderCurrentQuestion();
  } catch (e) {
    alert("Micro verification error: " + e.message);
  }
}

// --- Analytics & Heatmap Dashboard (UC-3, REQ_16, REQ_17, BR-4, TC-63 to TC-67) ---
async function loadDashboardAnalytics() {
  const container = document.getElementById("analytics-view-container");
  if (!container) return;

  try {
    const res = await fetch("/api/analytics/dashboard", {
      headers: { "X-User-ID": state.currentUser.userId }
    });
    const data = await res.json();

    if (!res.ok) {
      container.innerHTML = `<div class="alert-banner danger">${data.error}</div>`;
      return;
    }

    // 1. Welcome State for 0 attempts (Exception 3.0.E.1 / TC-66)
    if (data.welcome_state) {
      container.innerHTML = `
        <div class="alert-banner warning">
          <div>
            <strong>👋 ${data.message}</strong>
            <p style="margin-top:0.5rem;"><button class="btn-primary" onclick="switchTab('ingest')">Upload Study Materials</button></p>
          </div>
        </div>
      `;
      return;
    }

    // 2. Decaying Review Alerts (TC-68)
    let decayAlertHtml = "";
    if (data.decay_alerts && data.decay_alerts.length > 0) {
      decayAlertHtml = `
        <div class="alert-banner danger" style="margin-bottom:1.5rem;">
          <div>
            <strong>🔔 Spaced Repetition Retention Due!</strong>
            <p>Ebbinghaus memory curve indicates review required for: <strong>${data.decay_alerts.map(a => a.name).join(", ")}</strong></p>
          </div>
          <button class="btn-danger" onclick="startDecayMicroVerification('${data.decay_alerts[0].topic_id}')">Take 2-Q Verification</button>
        </div>
      `;
    }

    // 3. Render Dashboard with First-Try vs Looped Distinction (BR-4, REQ_17, TC-64)
    container.innerHTML = `
      ${decayAlertHtml}
      <div class="card-grid">
        <div class="ui-card">
          <div class="ui-card-title">Overall Exam Readiness</div>
          <div class="metric-big">${data.readiness_percentage}%</div>
          <div class="metric-caption">${data.mastered_topics} of ${data.total_topics} topics reached 100% mastery</div>
        </div>
        <div class="ui-card">
          <div class="ui-card-title">First-Attempt Success (BR-4)</div>
          <div class="metric-big" style="color:var(--accent-indigo);">${data.first_attempt_metrics.success_rate_percent}%</div>
          <div class="metric-caption">Passed on first attempt: ${data.first_attempt_metrics.passed} / ${data.first_attempt_metrics.total}</div>
        </div>
        <div class="ui-card">
          <div class="ui-card-title">Remediated / Looped Mastery (BR-4)</div>
          <div class="metric-big" style="color:var(--accent-purple);">${data.looped_mastery_metrics.success_rate_percent}%</div>
          <div class="metric-caption">Mastered after remediation loops: ${data.looped_mastery_metrics.passed} / ${data.looped_mastery_metrics.total}</div>
        </div>
      </div>

      <!-- Weakness Heatmap (UC-3, REQ_16, TC-63, TC-67) -->
      <div class="ui-card" style="margin-bottom:2rem;">
        <div class="ui-card-header">
          <div class="ui-card-title">🔥 Concept Weakness Heatmap</div>
          <span class="metric-caption">Color coded by failure rate and unverified lucky guesses</span>
        </div>
        <div class="heatmap-grid">
          ${data.heatmap_data.map(tile => `
            <div class="heatmap-tile" style="border-top-color: ${tile.color_hex};">
              <div class="heatmap-tile-name">${tile.topic_name}</div>
              <div style="margin: 0.5rem 0;">
                <span class="status-badge" style="background-color:rgba(255,255,255,0.08); color:${tile.color_hex};">
                  ${tile.weakness_level}
                </span>
              </div>
              <div class="heatmap-tile-stat">Avg Score: ${tile.average_score}%</div>
              <div class="heatmap-tile-stat">Failures: ${tile.failure_count} | Unverified: ${tile.unverified_guesses}</div>
            </div>
          `).join("")}
        </div>
      </div>

      <!-- Attempt History (TC-65) -->
      <div class="ui-card">
        <div class="ui-card-header">
          <div class="ui-card-title">📜 Attempt History & Score Trends</div>
          <span class="metric-caption">Rendered in ${data.render_time_ms} ms (PERF-3)</span>
        </div>
        <div style="overflow-x:auto;">
          <table style="width:100%; border-collapse:collapse; text-align:left; font-size:0.9rem;">
            <thead>
              <tr style="border-bottom:1px solid var(--border-color); color:var(--text-muted);">
                <th style="padding:0.6rem;">Topic</th>
                <th style="padding:0.6rem;">Score</th>
                <th style="padding:0.6rem;">Confidence</th>
                <th style="padding:0.6rem;">Attempt Type</th>
              </tr>
            </thead>
            <tbody>
              ${data.retry_history.map(att => `
                <tr style="border-bottom:1px solid rgba(255,255,255,0.05);">
                  <td style="padding:0.6rem;">${att.topic_name}</td>
                  <td style="padding:0.6rem; font-weight:700; color:${att.score >= 100 ? 'var(--success-green)' : 'var(--warning-amber)'}">${att.score}%</td>
                  <td style="padding:0.6rem;">${att.confidence}</td>
                  <td style="padding:0.6rem;">${att.is_first_attempt ? '<span class="status-badge in-progress">First-Try</span>' : '<span class="status-badge unmastered">Looped</span>'}</td>
                </tr>
              `).join("")}
            </tbody>
          </table>
        </div>
      </div>
    `;
  } catch (err) {
    container.innerHTML = `<p class="metric-caption text-danger">Failed to load analytics: ${err.message}</p>`;
  }
}

// --- Admin Portal (UC-10, UC-11, TC-74 to TC-77) ---
async function loadAdminTaxonomy() {
  const container = document.getElementById("admin-taxonomy-container");
  if (!container) return;

  try {
    const res = await fetch("/api/admin/taxonomy", {
      headers: { "X-User-Role": state.currentUser.role, "X-User-ID": state.currentUser.userId }
    });
    const data = await res.json();
    if (!res.ok) {
      container.innerHTML = `<div class="alert-banner danger">Access Denied: Admin authorization required.</div>`;
      return;
    }

    container.innerHTML = `
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem;">
        <h3>Syllabus Taxonomy Topics</h3>
        <button class="btn-primary" onclick="promptAddTaxonomy()">+ Add Topic</button>
      </div>
      <div class="topic-list-group">
        ${data.taxonomy.map(item => `
          <div class="topic-row">
            <div>
              <strong>${item.topic_name}</strong>
              <div class="metric-caption">${item.description || "No description"}</div>
            </div>
            <div style="display:flex; gap:0.5rem;">
              <button class="btn-secondary" onclick="promptEditTaxonomy(${item.id}, '${escapeForJs(item.topic_name)}')">Edit</button>
              <button class="btn-danger" onclick="deleteTaxonomy(${item.id})">Delete</button>
            </div>
          </div>
        `).join("")}
      </div>
    `;
  } catch (e) {
    container.innerHTML = `<p class="metric-caption text-danger">Admin error: ${e.message}</p>`;
  }
}

async function promptAddTaxonomy() {
  const name = prompt("Enter syllabus topic name:");
  if (!name) return;
  const desc = prompt("Enter topic description (optional):") || "";
  await fetch("/api/admin/taxonomy", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-User-Role": state.currentUser.role, "X-User-ID": state.currentUser.userId },
    body: JSON.stringify({ topic_name: name, description: desc })
  });
  loadAdminTaxonomy();
}

async function promptEditTaxonomy(id, currentName) {
  const name = prompt("Update topic name:", currentName);
  if (!name) return;
  await fetch(`/api/admin/taxonomy/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", "X-User-Role": state.currentUser.role, "X-User-ID": state.currentUser.userId },
    body: JSON.stringify({ topic_name: name })
  });
  loadAdminTaxonomy();
}

async function deleteTaxonomy(id) {
  if (!confirm("Are you sure you want to delete this taxonomy node?")) return;
  await fetch(`/api/admin/taxonomy/${id}`, {
    method: "DELETE",
    headers: { "X-User-Role": state.currentUser.role, "X-User-ID": state.currentUser.userId }
  });
  loadAdminTaxonomy();
}

async function adminWipeVectors() {
  const docId = prompt("Enter Document ID to wipe vector collection (UC-11):");
  if (!docId) return;
  const targetUser = prompt("Enter Student User ID:", state.currentUser.userId) || state.currentUser.userId;

  const res = await fetch("/api/admin/wipe-vectors", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-User-Role": state.currentUser.role, "X-User-ID": state.currentUser.userId },
    body: JSON.stringify({ user_id: targetUser, doc_id: docId })
  });
  const data = await res.json();
  if (res.ok) {
    alert(`Success: Wiped ${data.vectors_wiped} vectors for document '${docId}'.`);
  } else {
    alert(`Error: ${data.error}`);
  }
}

async function adminResetStudent() {
  const studentId = prompt("Enter Student User ID to reset performance history (UC-11):", "24CSB1A12");
  if (!studentId) return;

  const res = await fetch("/api/admin/reset-student", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-User-Role": state.currentUser.role, "X-User-ID": state.currentUser.userId },
    body: JSON.stringify({ student_user_id: studentId })
  });
  const data = await res.json();
  if (res.ok) {
    alert(data.message);
    if (state.currentUser.userId === studentId) {
      loadDashboardAnalytics();
    }
  } else {
    alert(`Error: ${data.error}`);
  }
}

// --- User Switcher Modal (Student A, Student B, Admin) ---
function openAuthModal() {
  const modal = document.getElementById("auth-modal");
  modal.style.display = "flex";
}

function closeAuthModal() {
  document.getElementById("auth-modal").style.display = "none";
}

async function switchUserAccount(userId, password, role) {
  const res = await fetch("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId, password: password })
  });
  const data = await res.json();
  if (res.ok) {
    state.currentUser = { userId: data.user.user_id, name: data.user.name, role: data.user.role };
    closeAuthModal();
    updateUserBadge();
    switchTab("dashboard");
  } else {
    alert(`Login failed: ${data.error}`);
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

function escapeForJs(str) {
  if (!str) return "";
  return String(str).replace(/\\/g, "\\\\").replace(/'/g, "\\'");
}

