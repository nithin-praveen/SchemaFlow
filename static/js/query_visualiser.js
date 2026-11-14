/**
 * SchemaFlow Enhanced Query Pipeline Execution Visualizer Controller
 * Features:
 * - Interactive visual roadmap/flowtrack with arrows
 * - Query clause trace highlighter
 * - Written order vs Physical execution order contrast
 * - Dual plain-English insights (What is happening + Under the hood secret)
 * - Physical Group-By Buckets and Stamped Partitions
 * - Filtered employee cards with pass/drop calculation chips
 * - View mode toggle between Interactive Graphics and Raw ASCII Table
 */
(function () {
  "use strict";

  // State
  let presets = [];
  let canonicalDataset = [];
  let currentSimulation = null;
  let currentStepIndex = 0;
  let autoPlayTimer = null;
  let isInitialized = false;
  let currentViewMode = "graphic"; // "graphic" or "ascii"

  // DOM Elements
  const presetSelectEl = document.getElementById("query-preset-select");
  const sqlInputEl = document.getElementById("query-sql-input");
  const runBtnEl = document.getElementById("btn-run-query");
  const statusBadgeEl = document.getElementById("query-status-badge");
  const datasetPanelEl = document.getElementById("query-dataset-panel");
  const datasetPreEl = document.getElementById("query-dataset-pre");
  const toggleDatasetBtnEl = document.getElementById("btn-toggle-dataset");
  const closeDatasetBtnEl = document.getElementById("btn-close-dataset");

  const stepperContainerEl = document.getElementById("query-stepper-container");
  const activeClauseBadgeEl = document.getElementById("query-active-clause-badge");
  const highlightedSqlEl = document.getElementById("query-highlighted-sql");
  const flowTrackEl = document.getElementById("query-flow-track");

  const stageCardEl = document.getElementById("query-stage-card");
  const stepNumberBadgeEl = document.getElementById("query-step-number-badge");
  const stepTitleEl = document.getElementById("query-step-title");
  const stepMetricsEl = document.getElementById("query-step-metrics");
  const writtenVsPhysEl = document.getElementById("query-written-vs-phys");
  const stepWhatTextEl = document.getElementById("query-step-what-text");
  const stepHoodTextEl = document.getElementById("query-step-hood-text");

  const visualCanvasEl = document.getElementById("query-visual-canvas");
  const asciiCanvasWrapperEl = document.getElementById("query-ascii-canvas-wrapper");
  const stepTableEl = document.getElementById("query-step-table");

  const prevBtnEl = document.getElementById("btn-step-prev");
  const nextBtnEl = document.getElementById("btn-step-next");
  const playBtnEl = document.getElementById("btn-step-play");
  const viewGraphicBtnEl = document.getElementById("btn-view-graphic");
  const viewAsciiBtnEl = document.getElementById("btn-view-ascii");

  function setQueryStatus(text, isError = false) {
    if (statusBadgeEl) {
      statusBadgeEl.textContent = text;
      statusBadgeEl.style.color = isError ? "var(--accent-red)" : "var(--accent-cyan)";
    }
  }

  function renderAsciiTable(rows, columns) {
    if (!rows || rows.length === 0) return "(0 rows returned)";
    const cols = columns || Object.keys(rows[0]);

    const strRows = rows.map((r) => {
      const rowObj = {};
      cols.forEach((c) => {
        rowObj[c] = r[c] !== undefined && r[c] !== null ? String(r[c]) : "";
      });
      return rowObj;
    });

    const colWidths = {};
    cols.forEach((c) => {
      let maxLen = c.length;
      strRows.forEach((r) => {
        if (r[c].length > maxLen) maxLen = r[c].length;
      });
      colWidths[c] = maxLen + 2;
    });

    const top = "┌" + cols.map((c) => "─".repeat(colWidths[c])).join("┬") + "┐";
    const header = "│" + cols.map((c) => ` ${c} `.padEnd(colWidths[c])).join("│") + "│";
    const sep = "├" + cols.map((c) => "─".repeat(colWidths[c])).join("┼") + "┤";
    const bot = "└" + cols.map((c) => "─".repeat(colWidths[c])).join("┴") + "┘";

    const dataLines = strRows.map((r) => {
      return "│" + cols.map((c) => ` ${r[c]} `.padEnd(colWidths[c])).join("│") + "│";
    });

    return [top, header, sep, ...dataLines, bot].join("\n");
  }

  async function loadPresetsAndDataset() {
    try {
      const response = await fetch("/api/query-pipeline/presets");
      if (!response.ok) return;
      const data = await response.json();
      presets = data.presets || [];
      canonicalDataset = data.dataset || [];

      if (datasetPreEl && canonicalDataset.length > 0) {
        datasetPreEl.textContent = renderAsciiTable(canonicalDataset);
      }

      if (presetSelectEl) {
        presetSelectEl.innerHTML = '<option value="">-- Choose SQL Query Preset --</option>';
        presets.forEach((p, idx) => {
          const opt = document.createElement("option");
          opt.value = p.id;
          opt.textContent = `[${idx + 1}] ${p.title}`;
          presetSelectEl.appendChild(opt);
        });

        if (presets.length > 0) {
          presetSelectEl.value = presets[0].id;
          if (sqlInputEl) sqlInputEl.value = presets[0].sql;
          await runSimulation();
        }
      }
    } catch (err) {
      console.warn("Could not load query presets:", err);
    }
  }

  async function runSimulation() {
    stopAutoPlay();
    const sql = sqlInputEl ? sqlInputEl.value.trim() : "";
    if (!sql) {
      setQueryStatus("EMPTY QUERY", true);
      return;
    }

    setQueryStatus("SIMULATING...");
    try {
      const response = await fetch("/api/query-pipeline/simulate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sql: sql }),
      });

      const data = await response.json();
      if (!response.ok) {
        setQueryStatus("SYNTAX ERROR", true);
        if (stageCardEl) stageCardEl.classList.remove("hidden");
        if (stepperContainerEl) stepperContainerEl.classList.add("hidden");
        if (stepTitleEl) stepTitleEl.textContent = "Pipeline Execution Failed";
        if (stepWhatTextEl) stepWhatTextEl.textContent = data.error || "Execution failed.";
        if (stepHoodTextEl) stepHoodTextEl.textContent = "Check SQL syntax for invalid operators, unmatched quotes, or unknown identifiers.";
        if (visualCanvasEl) visualCanvasEl.innerHTML = `<div class="insight-card" style="border-color:var(--accent-red); color:var(--accent-red); padding:16px;">Error: ${data.error}</div>`;
        return;
      }

      currentSimulation = data;
      setQueryStatus("READY");
      buildFlowTrack();
      goToStep(0);
    } catch (err) {
      setQueryStatus("NETWORK ERROR", true);
      console.error(err);
    }
  }

  function parseQueryClauses(sql) {
    const clauses = [];
    const keywords = ["SELECT", "FROM", "WHERE", "GROUP BY", "HAVING", "ORDER BY", "LIMIT"];
    const regex = new RegExp(`\\b(${keywords.join("|")})\\b`, "gi");
    let match;
    const indices = [];

    while ((match = regex.exec(sql)) !== null) {
      indices.push({ keyword: match[1].toUpperCase(), index: match.index });
    }

    for (let i = 0; i < indices.length; i++) {
      const start = indices[i].index;
      const end = i + 1 < indices.length ? indices[i + 1].index : sql.length;
      const snippet = sql.substring(start, end).trim();
      clauses.push({
        keyword: indices[i].keyword,
        text: snippet,
      });
    }

    return clauses;
  }

  function updateQueryClauseHighlighter(currentClause) {
    if (!highlightedSqlEl || !currentSimulation) return;
    const sql = currentSimulation.query || (sqlInputEl ? sqlInputEl.value : "");
    const clauses = parseQueryClauses(sql);

    highlightedSqlEl.innerHTML = "";
    clauses.forEach((c) => {
      const chip = document.createElement("span");
      chip.className = "sql-clause-chip";
      const matchesActive = c.keyword.toUpperCase() === currentClause.toUpperCase();
      if (matchesActive) {
        chip.classList.add("active-clause");
      }
      chip.textContent = c.text;
      highlightedSqlEl.appendChild(chip);
    });
  }

  function buildFlowTrack() {
    if (!currentSimulation || !flowTrackEl) return;
    flowTrackEl.innerHTML = "";

    currentSimulation.steps.forEach((step, idx) => {
      // Flow Node Card
      const node = document.createElement("button");
      node.type = "button";
      node.className = "flow-node";
      node.setAttribute("role", "tab");
      node.setAttribute("aria-selected", idx === 0 ? "true" : "false");
      node.setAttribute("data-step-index", String(idx));

      let icon = "⚙️";
      if (step.clause === "FROM") icon = "📂";
      else if (step.clause === "WHERE") icon = "🔍";
      else if (step.clause === "GROUP BY") icon = "📦";
      else if (step.clause === "HAVING") icon = "🎯";
      else if (step.clause === "SELECT") icon = "📋";
      else if (step.clause === "ORDER BY") icon = "🔀";
      else if (step.clause === "LIMIT") icon = "✂️";

      node.innerHTML = `
        <div class="flow-node-title">
          <span>${icon}</span>
          <span>${step.clause}</span>
        </div>
        <div class="flow-node-status" id="flow-status-${idx}">Step ${idx + 1}</div>
      `;

      node.addEventListener("click", () => {
        stopAutoPlay();
        goToStep(idx);
      });

      flowTrackEl.appendChild(node);

      // Flow Arrow (if not last step)
      if (idx < currentSimulation.steps.length - 1) {
        const arrow = document.createElement("span");
        arrow.className = "flow-arrow";
        arrow.id = `flow-arrow-${idx}`;
        arrow.textContent = "➔";
        flowTrackEl.appendChild(arrow);
      }
    });

    if (stepperContainerEl) stepperContainerEl.classList.remove("hidden");
    if (stageCardEl) stageCardEl.classList.remove("hidden");
  }

  function goToStep(index) {
    if (!currentSimulation || !currentSimulation.steps || currentSimulation.steps.length === 0) return;
    if (index < 0 || index >= currentSimulation.steps.length) return;

    currentStepIndex = index;
    const step = currentSimulation.steps[index];
    const totalSteps = currentSimulation.steps.length;

    // 1. Update Clause Pill & Highlighter
    if (activeClauseBadgeEl) {
      activeClauseBadgeEl.textContent = `ACTIVE: ${step.clause} (STEP ${index + 1}/${totalSteps})`;
    }
    updateQueryClauseHighlighter(step.clause);

    // 2. Update Flow Track Nodes & Arrows
    const nodes = flowTrackEl.querySelectorAll(".flow-node");
    nodes.forEach((node, idx) => {
      const isActive = idx === index;
      const isPassed = idx < index;
      node.classList.toggle("active", isActive);
      node.classList.toggle("passed", isPassed);
      node.setAttribute("aria-selected", isActive ? "true" : "false");

      const statusEl = document.getElementById(`flow-status-${idx}`);
      if (statusEl) {
        if (isActive) statusEl.textContent = "RUNNING ⚡";
        else if (isPassed) statusEl.textContent = "DONE ✔";
        else statusEl.textContent = `Step ${idx + 1}`;
      }

      const arrowEl = document.getElementById(`flow-arrow-${idx}`);
      if (arrowEl) {
        arrowEl.classList.toggle("passed", isPassed || isActive);
      }
    });

    // 3. Update Stage Titles & Metrics
    if (stepNumberBadgeEl) {
      stepNumberBadgeEl.textContent = `STEP ${index + 1} OF ${totalSteps} // ${step.clause}`;
    }
    if (stepTitleEl) {
      stepTitleEl.textContent = step.title;
    }
    if (stepMetricsEl) {
      const pruned = step.input_count - step.output_count;
      const prunedMsg = pruned > 0 ? ` (${pruned} discarded)` : "";
      stepMetricsEl.textContent = `Input: ${step.input_count} ──► Output: ${step.output_count}${prunedMsg}`;
    }

    // 4. Update Reality Check Banner & Plain-English Insights
    if (writtenVsPhysEl) {
      writtenVsPhysEl.textContent = step.written_vs_physical || "Physical execution order.";
    }
    if (stepWhatTextEl) {
      stepWhatTextEl.textContent = step.what_is_happening || step.explanation || "";
    }
    if (stepHoodTextEl) {
      stepHoodTextEl.textContent = step.under_the_hood || step.rule || "";
    }

    // 5. Render Interactive Visual Canvas & ASCII Table
    renderVisualCanvas(step);
    if (stepTableEl) {
      stepTableEl.textContent = step.ascii_table || "(0 rows)";
    }

    // 6. Update Navigation Prev/Next
    if (prevBtnEl) prevBtnEl.disabled = index === 0;
    if (nextBtnEl) nextBtnEl.disabled = index === totalSteps - 1;
  }

  function renderVisualCanvas(step) {
    if (!visualCanvasEl) return;
    visualCanvasEl.innerHTML = "";

    // -------------------------------------------------------------
    // Case A: GROUP BY & HAVING (Physical Department Buckets)
    // -------------------------------------------------------------
    if (step.visual_type === "buckets" || step.visual_type === "filter_buckets") {
      const buckets = step.buckets || [];
      const bucketsGrid = document.createElement("div");
      bucketsGrid.className = "buckets-grid";

      buckets.forEach((b) => {
        const bucketCard = document.createElement("div");
        bucketCard.className = "visual-bucket";

        let stampHtml = "";
        if (step.visual_type === "filter_buckets") {
          const isApproved = b.passed === true;
          bucketCard.classList.add(isApproved ? "bucket-passed" : "bucket-dropped");
          const badgeClass = isApproved ? "approved" : "rejected";
          const badgeIcon = isApproved ? "✔ BUCKET APPROVED" : "✖ BUCKET DROPPED";
          stampHtml = `
            <div class="bucket-stamp-bar">
              <span class="eval-calc">${b.condition_check || ""}</span>
              <span class="bucket-stamp-badge ${badgeClass}">${badgeIcon}</span>
            </div>
          `;
        } else {
          bucketCard.classList.add("bucket-active");
        }

        const membersHtml = (b.members || [])
          .map(
            (m) => `
          <div class="bucket-member-chip">
            <span class="member-name">👤 ${m.emp_name} <small style="color:var(--text-muted)">(${m.job || ""})</small></span>
            <span class="member-sal">$${Number(m.salary).toLocaleString()}</span>
          </div>
        `
          )
          .join("");

        bucketCard.innerHTML = `
          <div class="bucket-header">
            <div class="bucket-title-wrap">
              <span class="bucket-icon">🏢</span>
              <span class="bucket-title">${b.group_name.toUpperCase()}</span>
            </div>
            <span class="bucket-count-badge">${b.count} ${b.count === 1 ? "TUPLE" : "TUPLES"}</span>
          </div>
          <div class="bucket-members-list">
            ${membersHtml || '<div style="color:var(--text-muted); font-size:0.75rem;">(No members)</div>'}
          </div>
          ${stampHtml}
        `;

        bucketsGrid.appendChild(bucketCard);
      });

      visualCanvasEl.appendChild(bucketsGrid);
      return;
    }

    // -------------------------------------------------------------
    // Case B: WHERE Filter & FROM (Individual Tuple Cards)
    // -------------------------------------------------------------
    if (step.visual_type === "filter" || step.visual_type === "stream") {
      const cardsGrid = document.createElement("div");
      cardsGrid.className = "visual-cards-grid";

      (step.rows || []).forEach((r) => {
        const card = document.createElement("div");
        card.className = "tuple-card";

        let evalHtml = "";
        if (step.visual_type === "filter") {
          const passed = r._passed !== false;
          card.classList.add(passed ? "passed" : "dropped");
          const badgeText = passed ? "✔ SURVIVED" : "✖ DROPPED";
          const badgeClass = passed ? "pass" : "fail";
          evalHtml = `
            <div class="tuple-eval-bar">
              <span class="eval-calc">salary = $${Number(r.salary).toLocaleString()}</span>
              <span class="eval-badge ${badgeClass}">${badgeText}</span>
            </div>
          `;
        }

        card.innerHTML = `
          <div class="tuple-card-header">
            <div class="tuple-name-wrap">
              <span>👤</span>
              <span class="tuple-name">${r.emp_name}</span>
            </div>
            <span class="tuple-job-badge">${r.job || "STAFF"}</span>
          </div>
          <div class="tuple-dept-sal">
            <span>🏢 ${r.dept || "GENERAL"}</span>
            <span style="font-family:var(--font-mono); color:var(--accent-cyan);">$${Number(r.salary).toLocaleString()}</span>
          </div>
          ${evalHtml}
        `;

        cardsGrid.appendChild(card);
      });

      visualCanvasEl.appendChild(cardsGrid);
      return;
    }

    // -------------------------------------------------------------
    // Case C: SELECT, ORDER BY, LIMIT (Materialized Result Cards)
    // -------------------------------------------------------------
    const matGrid = document.createElement("div");
    matGrid.className = "materialized-grid";

    (step.rows || []).forEach((r, idx) => {
      const rowCard = document.createElement("div");
      rowCard.className = "materialized-row-card";

      // Pick title column
      const titleCol = step.columns.find((c) => c.toLowerCase().includes("name") || c.toLowerCase().includes("dept")) || step.columns[0];
      const titleVal = r[titleCol];

      // Other metrics
      const metricsHtml = step.columns
        .filter((c) => c !== titleCol && !c.startsWith("_"))
        .map(
          (c) => `
        <div class="metric-item">
          <span class="metric-label">${c}</span>
          <span class="metric-value">${r[c] !== undefined ? r[c] : ""}</span>
        </div>
      `
        )
        .join("");

      rowCard.innerHTML = `
        <div class="row-rank-wrap">
          <span class="rank-badge">#${idx + 1}</span>
          <span class="row-key-title">${titleVal}</span>
        </div>
        <div class="row-metrics-list">
          ${metricsHtml}
        </div>
      `;

      matGrid.appendChild(rowCard);
    });

    visualCanvasEl.appendChild(matGrid);
  }

  function setViewMode(mode) {
    currentViewMode = mode;
    const isGraphic = mode === "graphic";
    if (viewGraphicBtnEl) viewGraphicBtnEl.classList.toggle("active", isGraphic);
    if (viewAsciiBtnEl) viewAsciiBtnEl.classList.toggle("active", !isGraphic);

    if (visualCanvasEl) visualCanvasEl.classList.toggle("hidden", !isGraphic);
    if (asciiCanvasWrapperEl) asciiCanvasWrapperEl.classList.toggle("hidden", isGraphic);
  }

  function toggleAutoPlay() {
    if (autoPlayTimer) {
      stopAutoPlay();
    } else {
      startAutoPlay();
    }
  }

  function startAutoPlay() {
    if (!currentSimulation || currentSimulation.steps.length === 0) return;
    if (currentStepIndex >= currentSimulation.steps.length - 1) {
      currentStepIndex = 0;
      goToStep(0);
    }
    if (playBtnEl) playBtnEl.textContent = "⏸ PAUSE";

    autoPlayTimer = setInterval(() => {
      if (currentStepIndex < currentSimulation.steps.length - 1) {
        goToStep(currentStepIndex + 1);
      } else {
        stopAutoPlay();
      }
    }, 2500);
  }

  function stopAutoPlay() {
    if (autoPlayTimer) {
      clearInterval(autoPlayTimer);
      autoPlayTimer = null;
    }
    if (playBtnEl) playBtnEl.textContent = "▶ AUTO-PLAY";
  }

  function init() {
    if (isInitialized) return;
    isInitialized = true;

    if (runBtnEl) {
      runBtnEl.addEventListener("click", () => {
        runSimulation();
      });
    }

    if (presetSelectEl) {
      presetSelectEl.addEventListener("change", (e) => {
        const selectedId = e.target.value;
        const found = presets.find((p) => p.id === selectedId);
        if (found && sqlInputEl) {
          sqlInputEl.value = found.sql;
          runSimulation();
        }
      });
    }

    if (prevBtnEl) {
      prevBtnEl.addEventListener("click", () => {
        stopAutoPlay();
        goToStep(currentStepIndex - 1);
      });
    }

    if (nextBtnEl) {
      nextBtnEl.addEventListener("click", () => {
        stopAutoPlay();
        goToStep(currentStepIndex + 1);
      });
    }

    if (playBtnEl) {
      playBtnEl.addEventListener("click", () => {
        toggleAutoPlay();
      });
    }

    if (viewGraphicBtnEl) {
      viewGraphicBtnEl.addEventListener("click", () => {
        setViewMode("graphic");
      });
    }

    if (viewAsciiBtnEl) {
      viewAsciiBtnEl.addEventListener("click", () => {
        setViewMode("ascii");
      });
    }

    if (toggleDatasetBtnEl && datasetPanelEl) {
      toggleDatasetBtnEl.addEventListener("click", () => {
        datasetPanelEl.classList.toggle("hidden");
      });
    }

    if (closeDatasetBtnEl && datasetPanelEl) {
      closeDatasetBtnEl.addEventListener("click", () => {
        datasetPanelEl.classList.add("hidden");
      });
    }

    loadPresetsAndDataset();
  }

  window.SchemaFlowQueryVisualizer = {
    init: init,
  };
})();
