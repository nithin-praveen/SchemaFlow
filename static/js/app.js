/**
 * SchemaFlow Terminal Controller
 * Encapsulated in an IIFE to eliminate global namespace collisions.
 */
(function () {
  "use strict";

  // State
  let activeTabMode = "er";
  let erDiagramStyle = "chen";
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
  const workspaceContainerEl = document.querySelector(".workspace-container");
  const editorPanelEl = document.querySelector(".editor-panel");
  const erStyleToggleEl = document.getElementById("er-style-toggle");
  const styleToggleBtns = document.querySelectorAll(".style-toggle-btn");
  const uploadBtnEl = document.getElementById("btn-upload-sql");
  const sqlFileInputEl = document.getElementById("sql-file-input");
  const editorWrapperEl = document.getElementById("editor-wrapper");
  const editorDropzoneEl = document.getElementById("editor-dropzone");
  const dictateBtnEl = document.getElementById("btn-dictate-sql");
  const speakBtnEl = document.getElementById("btn-speak-narrative");

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
      if (workspaceContainerEl) workspaceContainerEl.classList.add("mode-query");
      if (editorPanelEl) editorPanelEl.classList.add("hidden");
      diagramPanelEl.classList.add("hidden");
      queryPanelEl.classList.remove("hidden");
      if (erStyleToggleEl) erStyleToggleEl.style.display = "none";
      outputTitleEl.textContent = "QUERY // CANONICAL PIPELINE EXECUTION";
      if (charCountEl) charCountEl.textContent = "Pipeline Active // 8 Canonical Tuples";
      setStatus("READY");
      if (window.SchemaFlowQueryVisualizer && window.SchemaFlowQueryVisualizer.init) {
        window.SchemaFlowQueryVisualizer.init();
      }
      return;
    }

    if (workspaceContainerEl) workspaceContainerEl.classList.remove("mode-query");
    if (editorPanelEl) editorPanelEl.classList.remove("hidden");
    diagramPanelEl.classList.remove("hidden");
    queryPanelEl.classList.add("hidden");

    const sqlCode = sqlInputEl.value.trim();
    if (!sqlCode) {
      outputPreEl.textContent = "-- Input SQL script is empty. Please enter CREATE TABLE statements. --";
      updateOutputStats("");
      return;
    }

    let endpoint = "/api/er";
    let titleText = erDiagramStyle === "chen"
      ? "OUTPUT // CHEN ER (RECTANGLES & DIAMONDS)"
      : "OUTPUT // RELATIONAL SCHEMA (TABLE BOXES)";

    if (activeTabMode === "er") {
      if (erStyleToggleEl) erStyleToggleEl.style.display = "inline-flex";
      if (speakBtnEl) speakBtnEl.style.display = "none";
    } else {
      if (erStyleToggleEl) erStyleToggleEl.style.display = "none";
      if (activeTabMode === "uml") {
        endpoint = "/api/uml";
        titleText = "OUTPUT // UML CLASS DIAGRAM";
        if (speakBtnEl) speakBtnEl.style.display = "none";
      } else if (activeTabMode === "describe") {
        endpoint = "/api/describe";
        titleText = "OUTPUT // SCREEN-READER NATURAL LANGUAGE";
        if (speakBtnEl) speakBtnEl.style.display = "inline-flex";
      }
    }
    outputTitleEl.textContent = titleText;

    if (isRequestPending) return;
    isRequestPending = true;
    setStatus("PROCESSING...");

    try {
      const response = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sql: sqlCode, style: erDiagramStyle }),
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

    // Stop active audio or dictation on tab switch
    stopSpeaking();
    stopListening();

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

  function handleFileUpload(file) {
    if (!file) return;

    // Check extension
    const isSqlExt = /\.(sql|ddl|txt)$/i.test(file.name);
    if (!isSqlExt && file.type && !file.type.startsWith("text/")) {
      setStatus("WARN: PLEASE SELECT A .SQL OR .TXT FILE", true);
    }

    setStatus(`READING ${file.name.toUpperCase()}...`);

    const reader = new FileReader();
    reader.onload = function (e) {
      const content = e.target.result;
      if (!content || !content.trim()) {
        setStatus(`WARN: ${file.name} IS EMPTY`, true);
        return;
      }

      sqlInputEl.value = content;
      if (sampleSelectEl) sampleSelectEl.value = "";
      const lineCount = content.split("\n").length;
      setStatus(`LOADED: ${file.name} (${lineCount} lines)`);

      // Automatically generate diagram for instant visual feedback
      executeCurrentTab();
    };

    reader.onerror = function () {
      setStatus(`ERROR READING ${file.name}`, true);
    };

    reader.readAsText(file, "UTF-8");
  }

  // ==========================================================================
  // Two-Way Voice Accessibility (Speech Synthesis & Speech Recognition)
  // ==========================================================================
  let isSpeaking = false;
  const synth = window.speechSynthesis;

  function stopSpeaking() {
    if (synth && isSpeaking) {
      synth.cancel();
      isSpeaking = false;
      updateSpeakButton(false);
    }
  }

  function speakNarrative() {
    if (!synth) {
      setStatus("SPEECH SYNTHESIS NOT SUPPORTED IN THIS BROWSER", true);
      return;
    }

    if (isSpeaking) {
      stopSpeaking();
      setStatus("AUDIO NARRATION PAUSED");
      return;
    }

    const text = outputPreEl ? outputPreEl.textContent : "";
    if (!text || text.startsWith("Loading") || text.startsWith("Connection error")) {
      setStatus("NO NARRATIVE TO READ ALOUD", true);
      return;
    }

    synth.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 0.95;
    utterance.pitch = 1.0;

    const voices = synth.getVoices();
    const preferredVoice = voices.find(function (v) {
      return (
        v.lang &&
        v.lang.startsWith("en") &&
        (v.name.includes("Natural") ||
          v.name.includes("Google") ||
          v.name.includes("David") ||
          v.name.includes("Zira"))
      );
    });
    if (preferredVoice) {
      utterance.voice = preferredVoice;
    }

    utterance.onstart = function () {
      isSpeaking = true;
      updateSpeakButton(true);
      setStatus("🔊 READING SCHEMA ALOUD...");
    };

    utterance.onend = function () {
      isSpeaking = false;
      updateSpeakButton(false);
      setStatus("AUDIO NARRATION COMPLETE");
    };

    utterance.onerror = function (e) {
      console.warn("Speech synthesis error:", e);
      isSpeaking = false;
      updateSpeakButton(false);
      setStatus("AUDIO PLAYBACK STOPPED", true);
    };

    synth.speak(utterance);
  }

  function updateSpeakButton(speaking) {
    if (!speakBtnEl) return;
    if (speaking) {
      speakBtnEl.textContent = "⏹ STOP AUDIO";
      speakBtnEl.classList.add("btn-speaking");
    } else {
      speakBtnEl.textContent = "🔊 READ ALOUD";
      speakBtnEl.classList.remove("btn-speaking");
    }
  }

  const SpeechRecognition =
    window.SpeechRecognition || window.webkitSpeechRecognition;
  let recognition = null;
  let isListening = false;
  let preDictationSql = "";

  function stopListening() {
    if (recognition && isListening) {
      try {
        recognition.stop();
      } catch (err) {}
    }
    isListening = false;
    updateDictateButton(false);
  }

  function initSpeechRecognition() {
    if (!SpeechRecognition) return null;
    const rec = new SpeechRecognition();
    rec.continuous = true;
    rec.interimResults = true;
    rec.lang = "en-US";

    rec.onstart = function () {
      isListening = true;
      updateDictateButton(true);
      setStatus("🎙️ LISTENING... SPEAK SQL COMMANDS");
      preDictationSql = sqlInputEl.value;
      if (preDictationSql && !preDictationSql.endsWith("\n")) {
        preDictationSql += "\n";
      }
    };

    rec.onresult = function (event) {
      let speechText = "";
      for (let i = event.resultIndex; i < event.results.length; ++i) {
        speechText += event.results[i][0].transcript;
      }

      // Automatically format spoken SQL syntax to standard DBMS casing
      let formatted = speechText
        .replace(/\bcreate table\b/gi, "CREATE TABLE")
        .replace(/\bprimary key\b/gi, "PRIMARY KEY")
        .replace(/\bforeign key\b/gi, "FOREIGN KEY")
        .replace(/\breferences\b/gi, "REFERENCES")
        .replace(/\bint\b|\binteger\b/gi, "INT")
        .replace(/\bvarchar\b/gi, "VARCHAR")
        .replace(/\bunique\b/gi, "UNIQUE")
        .replace(/\bnot null\b/gi, "NOT NULL")
        .replace(/\bnull\b/gi, "NULL")
        .replace(/\bselect\b/gi, "SELECT")
        .replace(/\bfrom\b/gi, "FROM")
        .replace(/\bwhere\b/gi, "WHERE")
        .replace(/\bsemicolon\b/gi, ";\n")
        .replace(/\bcomma\b/gi, ",")
        .replace(/\bopen bracket\b|\bopen parenthesis\b/gi, "(")
        .replace(/\bclose bracket\b|\bclose parenthesis\b/gi, ")");

      sqlInputEl.value = preDictationSql + formatted;
    };

    rec.onerror = function (event) {
      console.warn("Speech recognition error:", event.error);
      if (event.error !== "no-speech") {
        setStatus(`MIC ERROR: ${event.error.toUpperCase()}`, true);
      }
      stopListening();
    };

    rec.onend = function () {
      isListening = false;
      updateDictateButton(false);
      setStatus("DICTATION COMPLETE // READY");
    };

    return rec;
  }

  function toggleDictate() {
    if (!SpeechRecognition) {
      setStatus("SPEECH RECOGNITION NOT SUPPORTED (PLEASE USE CHROME OR EDGE)", true);
      return;
    }

    if (isListening) {
      stopListening();
      setStatus("DICTATION STOPPED");
      return;
    }

    if (!recognition) {
      recognition = initSpeechRecognition();
    }

    try {
      recognition.start();
    } catch (e) {
      recognition = initSpeechRecognition();
      if (recognition) recognition.start();
    }
  }

  function updateDictateButton(listening) {
    if (!dictateBtnEl) return;
    if (listening) {
      dictateBtnEl.textContent = "🔴 LISTENING...";
      dictateBtnEl.classList.add("btn-recording-pulse");
    } else {
      dictateBtnEl.textContent = "🎙️ DICTATE";
      dictateBtnEl.classList.remove("btn-recording-pulse");
    }
  }

  // Event Listeners
  tabElements.forEach(function (btn) {
    btn.addEventListener("click", handleTabClick);
  });

  if (styleToggleBtns) {
    styleToggleBtns.forEach(function (btn) {
      btn.addEventListener("click", function () {
        const targetStyle = btn.getAttribute("data-style");
        if (!targetStyle || targetStyle === erDiagramStyle) return;
        erDiagramStyle = targetStyle;
        styleToggleBtns.forEach(function (b) {
          b.classList.toggle("active", b === btn);
        });
        executeCurrentTab();
      });
    });
  }

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

  // File Upload & Drag-and-Drop
  if (uploadBtnEl && sqlFileInputEl) {
    uploadBtnEl.addEventListener("click", function () {
      sqlFileInputEl.click();
    });

    sqlFileInputEl.addEventListener("change", function (e) {
      const file = e.target.files && e.target.files[0];
      if (file) {
        handleFileUpload(file);
      }
      sqlFileInputEl.value = "";
    });
  }

  if (editorWrapperEl) {
    let dragCounter = 0;

    editorWrapperEl.addEventListener("dragenter", function (e) {
      e.preventDefault();
      e.stopPropagation();
      dragCounter++;
      if (editorDropzoneEl) editorDropzoneEl.classList.remove("hidden");
    });

    editorWrapperEl.addEventListener("dragover", function (e) {
      e.preventDefault();
      e.stopPropagation();
      if (e.dataTransfer) {
        e.dataTransfer.dropEffect = "copy";
      }
    });

    editorWrapperEl.addEventListener("dragleave", function (e) {
      e.preventDefault();
      e.stopPropagation();
      dragCounter--;
      if (dragCounter <= 0) {
        dragCounter = 0;
        if (editorDropzoneEl) editorDropzoneEl.classList.add("hidden");
      }
    });

    editorWrapperEl.addEventListener("drop", function (e) {
      e.preventDefault();
      e.stopPropagation();
      dragCounter = 0;
      if (editorDropzoneEl) editorDropzoneEl.classList.add("hidden");

      const dt = e.dataTransfer;
      if (dt && dt.files && dt.files.length > 0) {
        handleFileUpload(dt.files[0]);
      }
    });
  }

  // Voice Accessibility Event Listeners
  if (dictateBtnEl) {
    dictateBtnEl.addEventListener("click", toggleDictate);
  }

  if (speakBtnEl) {
    speakBtnEl.addEventListener("click", speakNarrative);
  }

  // Initialize
  loadSamplesList();
})();
