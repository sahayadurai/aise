/* RAG Benchmark — Frontend Logic */
(function () {
  "use strict";

  let currentSession = null;
  let selectedFiles = [];

  // ── DOM refs ────────────────────────────────────────────────────────────
  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => [...document.querySelectorAll(sel)];

  const sidebar       = $("#sidebar");
  const sidebarToggle = $("#sidebarToggle");
  const newSessionBtn = $("#newSessionBtn");
  const sessionList   = $("#sessionList");
  const fileList      = $("#fileList");
  const chatHistory   = $("#chatHistory");

  const dropZone   = $("#dropZone");
  const fileInput  = $("#fileInput");
  const uploadBtn  = $("#uploadBtn");
  const uploadStatus = $("#uploadStatus");

  const queryInput = $("#queryInput");
  const queryBtn   = $("#queryBtn");
  const resultsArea = $("#resultsArea");

  const modelSelect = $("#modelSelect");
  const modelSearch = $("#modelSearch");
  const modelDropdown = $("#modelDropdown");
  const selectedModelsDisplay = $("#selectedModels");

  // ── Searchable Multiselect Dropdown ─────────────────────────────────────
  function updateSelectedDisplay() {
    const selected = [...modelSelect.selectedOptions].map(opt => opt.value);
    selectedModelsDisplay.innerHTML = "";
    selected.forEach(val => {
      const option = [...modelSelect.options].find(o => o.value === val);
      if (option) {
        const tag = document.createElement("div");
        tag.className = "model-tag";
        tag.innerHTML = `${option.text} <button type="button" data-value="${val}">×</button>`;
        tag.querySelector("button").addEventListener("click", () => {
          modelSelect.value = null;
          [...modelSelect.options].forEach(o => {
            if (o.value === val) o.selected = false;
          });
          populateDropdown();
          updateSelectedDisplay();
        });
        selectedModelsDisplay.appendChild(tag);
      }
    });
  }

  function populateDropdown() {
    const options = [...modelSelect.options];
    const searchTerm = modelSearch.value.toLowerCase();
    const selected = [...modelSelect.selectedOptions].map(opt => opt.value);
    
    modelDropdown.innerHTML = "";
    options
      .filter(opt => opt.text.toLowerCase().includes(searchTerm) && opt.value)
      .forEach(opt => {
        const div = document.createElement("div");
        div.className = "dropdown-item";
        const isSelected = selected.includes(opt.value);
        if (isSelected) div.classList.add("selected");
        div.textContent = opt.text;
        div.addEventListener("click", () => {
          if (isSelected) {
            opt.selected = false;
            div.classList.remove("selected");
          } else {
            opt.selected = true;
            div.classList.add("selected");
          }
          updateSelectedDisplay();
        });
        modelDropdown.appendChild(div);
      });
  }

  modelSearch.addEventListener("focus", () => {
    populateDropdown();
    modelDropdown.classList.add("active");
  });

  modelSearch.addEventListener("input", populateDropdown);

  document.addEventListener("click", (e) => {
    if (!e.target.closest(".searchable-dropdown-wrapper")) {
      modelDropdown.classList.remove("active");
    }
  });

  // ── Slider & Input Sync ─────────────────────────────────────────────────
  const sliderPairs = [
    { slider: "#topKSlider", input: "#topK" },
    { slider: "#cosineThresholdSlider", input: "#cosineThreshold" },
    { slider: "#temperatureSlider", input: "#temperature" }
  ];

  sliderPairs.forEach(pair => {
    const slider = $(pair.slider);
    const input = $(pair.input);
    slider.addEventListener("input", () => { input.value = slider.value; });
    input.addEventListener("input", () => { slider.value = input.value; });
  });

  // ── Sidebar toggle ──────────────────────────────────────────────────────
  sidebarToggle.addEventListener("click", () => sidebar.classList.toggle("open"));

  // ── File selection ──────────────────────────────────────────────────────
  dropZone.addEventListener("dragover", (e) => {
    e.preventDefault(); dropZone.classList.add("dragover");
  });
  dropZone.addEventListener("dragleave", () => dropZone.classList.remove("dragover"));
  dropZone.addEventListener("drop", (e) => {
    e.preventDefault(); dropZone.classList.remove("dragover");
    selectedFiles = [...e.dataTransfer.files].filter(f => f.name.endsWith(".pdf"));
    updateFilePreview();
  });
  fileInput.addEventListener("change", () => {
    selectedFiles = [...fileInput.files];
    updateFilePreview();
  });

  function updateFilePreview() {
    if (selectedFiles.length) {
      dropZone.innerHTML = `<p>${selectedFiles.length} file(s) selected: ${selectedFiles.map(f=>f.name).join(", ")}</p>`;
      uploadBtn.disabled = false;
    }
  }

  // ── Upload ──────────────────────────────────────────────────────────────
  uploadBtn.addEventListener("click", async () => {
    if (!selectedFiles.length) return;
    uploadBtn.disabled = true;
    uploadStatus.className = "status";
    uploadStatus.innerHTML = '<span class="loading"></span> Uploading & indexing …';

    const fd = new FormData();
    selectedFiles.forEach(f => fd.append("files", f));
    fd.append("text_chunk_size", $("#textChunkSize").value);
    fd.append("text_chunk_overlap", $("#textOverlap").value);
    fd.append("image_chunk_size", $("#imageChunkSize").value);
    if (currentSession) fd.append("session_id", currentSession);

    try {
      const resp = await fetch("/api/upload", { method: "POST", body: fd });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.detail || "Upload failed");

      currentSession = data.session_id;
      uploadStatus.className = "status success";
      let summary = data.results.map(r =>
        `<b>${r.filename}</b>: ${r.total_chunks} chunks (${r.text_chunks} text, ` +
        `${r.table_chunks} table, ${r.image_chunks} image), ` +
        `${r.ground_truth_pairs} GT pairs, built in ${r.build_time_s}s`
      ).join("<br>");
      uploadStatus.innerHTML = summary;
      queryBtn.disabled = false;
      refreshSidebar();
    } catch (e) {
      uploadStatus.className = "status error";
      uploadStatus.textContent = e.message;
      uploadBtn.disabled = false;
    }
  });

  // ── Query ───────────────────────────────────────────────────────────────
  queryBtn.addEventListener("click", sendQuery);
  queryInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendQuery(); }
  });

  async function sendQuery() {
    const query = queryInput.value.trim();
    if (!query || !currentSession) return;

    const selectedModels = [...modelSelect.selectedOptions].map(opt => opt.value);
    if (!selectedModels.length) { alert("Select at least one model"); return; }

    queryBtn.disabled = true;
    resultsArea.innerHTML = '<div class="card"><span class="loading"></span> Querying models …</div>';

    const fd = new FormData();
    fd.append("query", query);
    fd.append("session_id", currentSession);
    fd.append("models", selectedModels.join(","));
    fd.append("top_k", $("#topK").value);
    fd.append("cosine_threshold", $("#cosineThreshold").value);
    fd.append("temperature", $("#temperature").value);
    fd.append("run_benchmark", $("#runBenchmark").checked ? "true" : "false");

    try {
      const resp = await fetch("/api/query", { method: "POST", body: fd });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.detail || "Query failed");
      renderResults(data.chat);
      refreshSidebar();
    } catch (e) {
      resultsArea.innerHTML = `<div class="card status error">${e.message}</div>`;
    }
    queryBtn.disabled = false;
  }

  function renderResults(chat) {
    let html = `<div class="card"><h2>Query: ${escHtml(chat.query)}</h2>`;
    html += `<p class="muted">${chat.timestamp} · Models: ${chat.models.join(", ")}</p></div>`;

    for (const r of chat.results) {
      html += `<div class="result-card">`;
      html += `<h3>${r.model}</h3>`;
      if (r.error) {
        html += `<p class="status error">${r.error}</p>`;
      } else {
        html += `<div class="answer-text">${escHtml(r.answer)}</div>`;
        html += `<p class="muted">Latency: ${r.latency_s}s</p>`;
        if (r.sources) {
          html += `<div>`;
          r.sources.forEach(s => {
            html += `<span class="source-tag">${s.source} p.${s.page} (${s.score.toFixed(3)})</span>`;
          });
          html += `</div>`;
        }
        if (r.benchmark) {
          html += renderBenchTable(r.benchmark);
        }
      }
      html += `</div>`;
    }
    resultsArea.innerHTML = html;
  }

  function renderBenchTable(b) {
    return `<table class="bench-table">
      <tr><th>Metric</th><th>Value</th></tr>
      <tr><td>BLEU</td><td>${b.bleu}</td></tr>
      <tr><td>ROUGE-L F1</td><td>${b.rouge_l?.f1 ?? "—"}</td></tr>
      <tr><td>Faithfulness</td><td>${b.faithfulness}</td></tr>
      <tr><td>Answer Relevancy</td><td>${b.answer_relevancy}</td></tr>
      <tr><td>Context Precision</td><td>${b.context_precision}</td></tr>
      <tr><td>Context Recall</td><td>${b.context_recall}</td></tr>
      <tr><td>MRR</td><td>${b.mrr}</td></tr>
      <tr><td>Hit Rate</td><td>${b.hit_rate}</td></tr>
    </table>`;
  }

  // ── Sidebar refresh ─────────────────────────────────────────────────────
  async function refreshSidebar() {
    try {
      const resp = await fetch("/api/sessions");
      const data = await resp.json();
      sessionList.innerHTML = "";
      data.sessions.forEach(s => {
        const li = document.createElement("li");
        li.textContent = `${s.id} (${s.files} files)`;
        if (s.id === currentSession) li.classList.add("active");
        li.addEventListener("click", () => loadSession(s.id));
        sessionList.appendChild(li);
      });
    } catch (_) {}

    if (currentSession) {
      try {
        const resp = await fetch(`/api/session/${currentSession}`);
        const sess = await resp.json();
        fileList.innerHTML = "";
        (sess.files || []).forEach(f => {
          const li = document.createElement("li"); li.textContent = f;
          fileList.appendChild(li);
        });
        chatHistory.innerHTML = "";
        (sess.chats || []).forEach(c => {
          const li = document.createElement("li");
          li.textContent = c.query.substring(0, 40) + (c.query.length > 40 ? "…" : "");
          li.addEventListener("click", () => renderResults(c));
          chatHistory.appendChild(li);
        });
      } catch (_) {}
    }
  }

  async function loadSession(sid) {
    currentSession = sid;
    queryBtn.disabled = false;
    refreshSidebar();
  }

  // ── New session ─────────────────────────────────────────────────────────
  newSessionBtn.addEventListener("click", () => {
    currentSession = null;
    selectedFiles = [];
    dropZone.innerHTML = '<p>Drop PDF files here or <label class="link" for="fileInput">browse</label></p>';
    fileInput.value = "";
    uploadBtn.disabled = true;
    queryBtn.disabled = true;
    resultsArea.innerHTML = "";
    uploadStatus.innerHTML = "";
    refreshSidebar();
  });

  function escHtml(s) {
    const d = document.createElement("div"); d.textContent = s; return d.innerHTML;
  }

  // ── Init ────────────────────────────────────────────────────────────────
  refreshSidebar();
})();
