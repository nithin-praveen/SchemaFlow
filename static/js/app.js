/**
 * SchemaFlow Terminal Controller
 * Encapsulated in an IIFE to eliminate global namespace collisions.
 */
(function () {
  "use strict";

  // State
  let activeTabMode = "er";
  let isRequestPending = false;

  // DOM Elements
  const tabElements = document.querySelectorAll(".tab-btn");
  const sampleSelectEl = document.getElementById("sample-select");
  const sqlInputEl = document.getElementById("sql-input");
  const generateBtnEl = document.getElementById("btn-generate");
  const copyBtnEl = document.getElementById("btn-copy");
  const downloadBtnEl = document.getElementById("btn-download");
  const outputPreEl = document.getElementById("output-pre");
  const outputTitleEl = document.getElementById("output-mode-title");
  const charCountEl = document.getElementById("char-count");
  const statusIndicatorEl = document.getElementById("system-status");
  const diagramPanelEl = document.getElementById("panel-diagram");
  const queryPanelEl = document.getElementById("panel-query");

  function setStatus(text, isError = false) {
    if (statusIndicatorEl) {
      statusIndicatorEl.textContent = text;
      statusIndicatorEl.style.color = isError ? "var(--accent-red)" : "var(--accent-cyan)";
    }
  }

  function updateOutputStats(content) {
    if (!charCountEl) return;
    const lines = content ? content.split("\n").length : 0;
    const chars = content ? content.length : 0;
    charCountEl.textContent = `${lines} lines // ${chars} chars`;
  }

  async function loadSamplesList() {
    try {
      const response = await fetch("/api/samples");
      if (!response.ok) return;
      const sampleNames = await response.json();
      sampleSelectEl.innerHTML = '<option value="">-- Choose Public Service Schema --</option>';
      sampleNames.forEach(function (sName) {
        const opt = document.createElement("option");
        opt.value = sName;
        // Format display name nicely: hospital -> Hospital System
        const formatted = sName.replace(/_/g, " ").replace(/\b\w/g, function (c) {
          return c.toUpperCase();
        });
        opt.textContent = formatted;
        sampleSelectEl.appendChild(opt);
      });

      // Default select the first sample (e.g. school or hospital)
      if (sampleNames.length > 0) {
        const defaultSample = sampleNames.includes("school") ? "school" : sampleNames[0];
        sampleSelectEl.value = defaultSample;
        await loadSampleContent(defaultSample);
      }
    } catch (err) {
      console.warn("Could not load samples list:", err);
    }
  }

  async function loadSampleContent(sampleName) {
    if (!sampleName) return;
    setStatus("LOADING SAMPLE...");
    try {
      const response = await fetch(`/api/samples/${encodeURIComponent(sampleName)}`);
      if (!response.ok) throw new Error("Sample file not found");
      const data = await response.json();
      sqlInputEl.value = data.sql || "";
      setStatus("READY");
      await executeCurrentTab();
    } catch (err) {
      setStatus("ERROR", true);
      outputPreEl.textContent = `Error loading sample schema: ${err.message}`;
    }
  }

  async function executeCurrentTab() {
    if (activeTabMode === "query") {
      diagramPanelEl.classList.add("hidden");
      queryPanelEl.classList.remove("hidden");
      outputTitleEl.textContent = "QUERY // CANONICAL PIPELINE EXECUTION";
      setStatus("READY");
      return;
    }

    diagramPanelEl.classList.remove("hidden");
    queryPanelEl.classList.add("hidden");

    const sqlCode = sqlInputEl.value.trim();
    if (!sqlCode) {
      outputPreEl.textContent = "-- Input SQL script is empty. Please enter CREATE TABLE statements. --";
      updateOutputStats("");
      return;
    }

    let endpoint = "/api/er";
    let titleText = "OUTPUT // ER DIAGRAM";
    if (activeTabMode === "uml") {
      endpoint = "/api/uml";
      titleText = "OUTPUT // UML CLASS DIAGRAM";
    } else if (activeTabMode === "describe") {
      endpoint = "/api/describe";
      titleText = "OUTPUT // SCREEN-READER NATURAL LANGUAGE";
    }
    outputTitleEl.textContent = titleText;

    if (isRequestPending) return;
    isRequestPending = true;
    setStatus("PROCESSING...");

    try {
      const response = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sql: sqlCode }),
      });

      const data = await response.json();
      if (!response.ok) {
        setStatus("SYNTAX ERROR", true);
        outputPreEl.textContent = data.error || "Parsing failed.";
      } else {
        setStatus("READY");
        outputPreEl.textContent = data.result || "(No output generated)";
      }
      updateOutputStats(outputPreEl.textContent);
    } catch (networkErr) {
      setStatus("NETWORK ERROR", true);
      outputPreEl.textContent = `Connection error: ${networkErr.message}`;
    } finally {
      isRequestPending = false;
    }
  }

  function handleTabClick(evt) {
    const clickedBtn = evt.currentTarget;
    const targetMode = clickedBtn.getAttribute("data-target");
    if (!targetMode) return;

    activeTabMode = targetMode;
    tabElements.forEach(function (btn) {
      const isActive = btn === clickedBtn;
      btn.classList.toggle("active", isActive);
      btn.setAttribute("aria-selected", isActive ? "true" : "false");
    });

    executeCurrentTab();
  }

  async function handleCopy() {
    const textToCopy = outputPreEl.textContent;
    if (!textToCopy) return;

    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(textToCopy);
      } else {
        const tempTextArea = document.createElement("textarea");
        tempTextArea.value = textToCopy;
        document.body.appendChild(tempTextArea);
        tempTextArea.select();
        document.execCommand("copy");
        document.body.removeChild(tempTextArea);
      }

      const origText = copyBtnEl.textContent;
      copyBtnEl.textContent = "✔ COPIED!";
      setTimeout(function () {
        copyBtnEl.textContent = origText;
      }, 1500);
    } catch (err) {
      console.error("Clipboard copy failed:", err);
    }
  }

  function handleDownload() {
    const textContent = outputPreEl.textContent;
    if (!textContent) return;

    const blob = new Blob([textContent], { type: "text/plain;charset=utf-8" });
    const downloadUrl = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = downloadUrl;
    anchor.download = `schemaflow_${activeTabMode}_output.txt`;
    document.body.appendChild(anchor);
    anchor.click();
    document.body.removeChild(anchor);
    URL.revokeObjectURL(downloadUrl);
  }

  // Event Listeners
  tabElements.forEach(function (btn) {
    btn.addEventListener("click", handleTabClick);
  });

  if (sampleSelectEl) {
    sampleSelectEl.addEventListener("change", function (e) {
      loadSampleContent(e.target.value);
    });
  }

  if (generateBtnEl) {
    generateBtnEl.addEventListener("click", function () {
      executeCurrentTab();
    });
  }

  if (copyBtnEl) {
    copyBtnEl.addEventListener("click", handleCopy);
  }

  if (downloadBtnEl) {
    downloadBtnEl.addEventListener("click", handleDownload);
  }

  // Initialize
  loadSamplesList();
})();
