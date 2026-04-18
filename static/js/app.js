/* ============================================================
   Sport Science Quality Analyzer — Frontend Application
   ============================================================ */

(function () {
    "use strict";

    // --- DOM refs ---
    const dropZone = document.getElementById("dropZone");
    const fileInput = document.getElementById("fileInput");
    const browseBtn = document.getElementById("browseBtn");
    const fileList = document.getElementById("fileList");
    const analyzeBtn = document.getElementById("analyzeBtn");
    const clearBtn = document.getElementById("clearBtn");
    const progressBar = document.getElementById("progressBar");
    const progressFill = document.getElementById("progressFill");
    const progressText = document.getElementById("progressText");
    const resultsSection = document.getElementById("resultsSection");
    const resultTabs = document.getElementById("resultTabs");
    const tableView = document.getElementById("tableView");
    const detailsView = document.getElementById("detailsView");
    const statusDot = document.getElementById("statusDot");
    const statusText = document.getElementById("statusText");
    const toast = document.getElementById("toast");
    const toastMsg = document.getElementById("toastMsg");
    const toastClose = document.getElementById("toastClose");
    const apiKeyInput = document.getElementById("apiKeyInput");
    const apiKeySaveBtn = document.getElementById("apiKeySaveBtn");
    const apiKeyClearBtn = document.getElementById("apiKeyClearBtn");
    const apiKeyState = document.getElementById("apiKeyState");

    let selectedFiles = [];
    let analysisResults = [];

    // --- API Key management (localStorage) ---
    const API_KEY_STORAGE = "ssqa_gemini_api_key";
    let serverHasKey = false;

    function getStoredKey() {
        return localStorage.getItem(API_KEY_STORAGE) || "";
    }

    function renderKeyState() {
        const stored = getStoredKey();
        if (stored) {
            apiKeyState.textContent = "Personal key active";
            apiKeyState.className = "api-key-state state-personal";
        } else if (serverHasKey) {
            apiKeyState.textContent = "Using shared server key";
            apiKeyState.className = "api-key-state state-shared";
        } else {
            apiKeyState.textContent = "No key configured";
            apiKeyState.className = "api-key-state state-none";
        }
    }

    function updateStatusDot() {
        const hasAnyKey = serverHasKey || !!getStoredKey();
        if (hasAnyKey) {
            statusDot.classList.remove("offline");
            statusText.textContent = getStoredKey() ? "Your key" : "AI Ready";
        } else {
            statusDot.classList.add("offline");
            statusText.textContent = "No key";
        }
    }

    // Pre-fill from localStorage on boot
    const existing = getStoredKey();
    if (existing) apiKeyInput.value = existing;

    // Render initial key state immediately (before async health check) so the
    // user always sees a badge — avoids an empty-looking UI on boot
    renderKeyState();
    updateStatusDot();

    apiKeySaveBtn.addEventListener("click", (event) => {
        event.preventDefault();
        const v = (apiKeyInput.value || "").trim();
        if (!v) {
            showToast("Paste a Gemini API key before saving.");
            return;
        }
        try {
            localStorage.setItem(API_KEY_STORAGE, v);
        } catch (e) {
            showToast("Could not save to browser storage: " + e.message);
            return;
        }
        renderKeyState();
        updateStatusDot();
        showToast("Personal API key saved — analyses will now use your own quota.", "success");
    });

    apiKeyClearBtn.addEventListener("click", (event) => {
        event.preventDefault();
        localStorage.removeItem(API_KEY_STORAGE);
        apiKeyInput.value = "";
        renderKeyState();
        updateStatusDot();
        showToast("API key cleared. Falling back to the shared server key.", "success");
    });

    // --- Health check ---
    async function checkHealth() {
        try {
            const res = await fetch("/api/health");
            const data = await res.json();
            serverHasKey = !!data.api_key_configured;
        } catch {
            serverHasKey = false;
            statusDot.classList.add("offline");
            statusText.textContent = "Offline";
            renderKeyState();
            return;
        }
        updateStatusDot();
        renderKeyState();
    }
    checkHealth();

    // --- Toast ---
    // Errors stay visible until the user clicks the close button.
    // Success toasts auto-dismiss after 4s.
    toastClose.addEventListener("click", () => {
        toast.classList.remove("show");
        if (toast.__timer) { clearTimeout(toast.__timer); toast.__timer = null; }
    });

    function showToast(msg, type = "error", duration) {
        toastMsg.textContent = msg;
        toast.className = `toast toast-${type} show`;
        if (toast.__timer) { clearTimeout(toast.__timer); toast.__timer = null; }
        // Default: success auto-dismisses (4s), errors stay until closed.
        // Callers can override by passing an explicit duration in ms.
        let ms;
        if (typeof duration === "number") {
            ms = duration;
        } else {
            ms = type === "success" ? 4000 : 0;
        }
        if (ms > 0) {
            toast.__timer = setTimeout(() => toast.classList.remove("show"), ms);
        }
    }

    // --- File handling ---
    browseBtn.addEventListener("click", () => fileInput.click());
    dropZone.addEventListener("click", (e) => {
        if (e.target === dropZone || e.target.classList.contains("drop-zone-icon") || e.target.classList.contains("drop-zone-text")) {
            fileInput.click();
        }
    });

    dropZone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropZone.classList.add("dragover");
    });
    dropZone.addEventListener("dragleave", () => dropZone.classList.remove("dragover"));
    dropZone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropZone.classList.remove("dragover");
        addFiles(Array.from(e.dataTransfer.files));
    });

    fileInput.addEventListener("change", () => {
        addFiles(Array.from(fileInput.files));
        fileInput.value = "";
    });

    function addFiles(files) {
        const pdfs = files.filter(f => f.name.toLowerCase().endsWith(".pdf"));
        if (pdfs.length === 0) {
            showToast("Only PDF files are accepted.");
            return;
        }
        for (const f of pdfs) {
            if (selectedFiles.length >= 10) {
                showToast("Maximum 10 files per batch.");
                break;
            }
            if (!selectedFiles.some(sf => sf.name === f.name && sf.size === f.size)) {
                selectedFiles.push(f);
            }
        }
        renderFileList();
    }

    function removeFile(index) {
        selectedFiles.splice(index, 1);
        renderFileList();
    }

    function renderFileList() {
        fileList.innerHTML = selectedFiles.map((f, i) =>
            `<span class="file-tag">
                &#128196; ${escapeHtml(f.name)}
                <button onclick="window.__removeFile(${i})">&times;</button>
            </span>`
        ).join("");
        analyzeBtn.disabled = selectedFiles.length === 0;
        clearBtn.style.display = selectedFiles.length > 0 ? "" : "none";
    }
    window.__removeFile = removeFile;

    clearBtn.addEventListener("click", () => {
        selectedFiles = [];
        renderFileList();
    });

    // --- Analysis ---
    analyzeBtn.addEventListener("click", runAnalysis);

    async function runAnalysis() {
        if (selectedFiles.length === 0) return;

        const isBatch = selectedFiles.length > 1;
        const n = selectedFiles.length;

        analyzeBtn.disabled = true;
        progressBar.classList.add("active");
        progressFill.classList.remove("determinate");
        resultsSection.classList.remove("active");

        // Show elapsed time so the user knows the app isn't frozen
        const startedAt = Date.now();
        const baseMsg = `Analyzing ${n} paper${n > 1 ? "s" : ""}...`;
        const hintMsg = isBatch
            ? "Rate limits may cause batch delays up to ~2 minutes."
            : "Usually takes 10-30 seconds.";
        progressText.textContent = `${baseMsg} ${hintMsg} (0s)`;
        const tick = setInterval(() => {
            const s = Math.floor((Date.now() - startedAt) / 1000);
            progressText.textContent = `${baseMsg} ${hintMsg} (${s}s)`;
        }, 1000);

        // Abort the request after a hard client-side timeout so the UI never
        // feels "infinite". 100s for single, 180s for batch — matches the
        // server's worst-case retry budget (3 retries x 35s) with some slack.
        const controller = new AbortController();
        const timeoutMs = isBatch ? 180000 : 100000;
        const timer = setTimeout(() => controller.abort(), timeoutMs);

        const formData = new FormData();
        if (isBatch) {
            for (const f of selectedFiles) formData.append("files", f);
        } else {
            formData.append("file", selectedFiles[0]);
        }

        try {
            const endpoint = isBatch ? "/api/analyze/batch" : "/api/analyze";
            const headers = {};
            const personalKey = getStoredKey();
            if (personalKey) headers["X-Gemini-API-Key"] = personalKey;

            const res = await fetch(endpoint, {
                method: "POST",
                body: formData,
                headers,
                signal: controller.signal,
            });

            if (!res.ok) {
                const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
                const detail = err.detail || `HTTP ${res.status}`;
                // 429 (quota) and 401 (invalid key) are sticky errors —
                // the toast stays until the user dismisses it so they have
                // time to read the full explanation.
                showToast(detail);
                return;
            }

            const data = await res.json();
            analysisResults = isBatch ? data : [data];

            renderResults();
            resultsSection.classList.add("active");
            resultsSection.scrollIntoView({ behavior: "smooth" });
        } catch (err) {
            if (err.name === "AbortError") {
                showToast(
                    `Request timed out after ${timeoutMs / 1000}s. The Gemini API is likely rate-limited or unreachable. ` +
                    `Try again, switch to a personal API key above (uses your own quota), or verify your connection.`
                );
            } else {
                showToast(err.message || "Unknown error");
            }
        } finally {
            clearTimeout(timer);
            clearInterval(tick);
            progressBar.classList.remove("active");
            analyzeBtn.disabled = false;
        }
    }

    // --- Rendering ---
    function renderResults() {
        const isBatch = analysisResults.length > 1;

        if (isBatch) {
            resultTabs.style.display = "flex";
            renderBatchTable();
            renderDetailCards();
            switchTab("table");
        } else {
            resultTabs.style.display = "none";
            tableView.innerHTML = "";
            renderDetailCards();
        }
    }

    // Tab switching
    document.querySelectorAll(".tab").forEach(tab => {
        tab.addEventListener("click", () => switchTab(tab.dataset.tab));
    });

    function switchTab(name) {
        document.querySelectorAll(".tab").forEach(t => t.classList.toggle("active", t.dataset.tab === name));
        tableView.style.display = name === "table" ? "" : "none";
        detailsView.style.display = name === "details" ? "" : "none";
    }

    // --- Batch Table ---
    function renderBatchTable() {
        const rows = analysisResults.map((r, i) => {
            const s = r.scoring;
            const e = r.extracted;
            const scoreColor = getScoreColor(s.final_score, s.category);
            const coiFlag = s.coi_detected ? '<span style="color:var(--red);font-weight:600">COI</span>' : s.predatory_journal_detected ? '<span style="color:var(--red);font-weight:600">PRED</span>' : '<span style="color:var(--green)">OK</span>';
            const normColor = getNormColor(s.normalized_score);
            return `<tr>
                <td class="filename-cell" title="${escapeHtml(r.filename)}">${escapeHtml(r.filename)}</td>
                <td class="score-cell" style="color:${scoreColor}">${s.final_score.toFixed(1)}<span class="score-cap">/${s.design_cap}</span></td>
                <td class="norm-cell" style="color:${normColor}">${s.normalized_score.toFixed(0)}%</td>
                <td><span class="category-badge category-${s.category}">${s.category_label}</span></td>
                <td>${escapeHtml(e.study_design ? designLabel(e.study_design) : "—")}</td>
                <td>${e.sample_size != null ? e.sample_size : "—"}</td>
                <td>${coiFlag}</td>
                <td>${r.confidence.confidence_pct.toFixed(0)}%</td>
                <td><button class="expand-btn" onclick="window.__scrollToCard(${i})">Details</button></td>
            </tr>`;
        }).join("");

        tableView.innerHTML = `
        <div class="batch-table-wrapper">
            <table class="batch-table">
                <thead>
                    <tr>
                        <th>File</th>
                        <th>Score</th>
                        <th>Quality %</th>
                        <th>Category</th>
                        <th>Design</th>
                        <th>N</th>
                        <th>Flags</th>
                        <th>Confidence</th>
                        <th></th>
                    </tr>
                </thead>
                <tbody>${rows}</tbody>
            </table>
        </div>`;
    }

    window.__scrollToCard = function (i) {
        switchTab("details");
        const card = document.getElementById(`result-card-${i}`);
        if (card) card.scrollIntoView({ behavior: "smooth" });
    };

    // --- Detail Cards ---
    function renderDetailCards() {
        detailsView.innerHTML = analysisResults.map((r, i) => renderOneCard(r, i)).join("");
    }

    function renderOneCard(r, index) {
        const s = r.scoring;
        const e = r.extracted;
        const c = r.confidence;

        if (r.error) {
            return `
            <div class="result-card" id="result-card-${index}">
                <div class="result-header">
                    <div class="result-meta">
                        <div class="result-title">${escapeHtml(r.filename)}</div>
                        <span class="category-badge category-error">ERROR</span>
                        <p style="margin-top:12px;color:var(--red);font-size:13px">${escapeHtml(r.error)}</p>
                    </div>
                </div>
            </div>`;
        }

        const scoreColor = getScoreColor(s.final_score, s.category);
        const normColor = getNormColor(s.normalized_score);
        const circumference = 2 * Math.PI * 42;
        const offset = circumference - (s.normalized_score / 100) * circumference;

        // PEDro HTML
        let pedroHtml = "";
        if (e.pedro_criteria && e.study_design === "rct") {
            const pc = e.pedro_criteria;
            const cells = [
                { key: "C1", label: "Eligibility Specified", val: pc.c1_eligibility_specified, desc: true },
                { key: "C2", label: "Random Allocation", val: pc.c2_random_allocation },
                { key: "C3", label: "Concealed Allocation", val: pc.c3_concealed_allocation },
                { key: "C4", label: "Baseline Comparable", val: pc.c4_baseline_comparable },
                { key: "C5", label: "Blinding Subjects", val: pc.c5_blinding_subjects },
                { key: "C6", label: "Blinding Therapists", val: pc.c6_blinding_therapists },
                { key: "C7", label: "Blinding Assessors", val: pc.c7_blinding_assessors },
                { key: "C8", label: "Adequate Follow-up", val: pc.c8_adequate_followup },
                { key: "C9", label: "Intention to Treat", val: pc.c9_intention_to_treat },
                { key: "C10", label: "Between-Group Stats", val: pc.c10_between_group },
                { key: "C11", label: "Point & Variability", val: pc.c11_point_variability },
            ];
            const cellsHtml = cells.map(c => {
                let cls = "unknown";
                if (c.desc) cls = c.val === true ? "descriptive" : c.val === false ? "not-met" : "unknown";
                else cls = c.val === true ? "met" : c.val === false ? "not-met" : "unknown";
                return `<div class="pedro-item"><div class="pedro-cell ${cls}" title="${c.label}">${c.key}</div><div class="pedro-label">${c.label}</div></div>`;
            }).join("");

            pedroHtml = `
            <div class="detail-section" style="grid-column: 1/-1">
                <h4>PEDro Scale (C2-C11 scored)</h4>
                <div class="pedro-grid">${cellsHtml}</div>
                <div class="detail-row" style="margin-top:8px">
                    <span class="label">PEDro Score</span>
                    <span class="value">${s.pedro_score != null ? s.pedro_score + "/10" : "N/A"}</span>
                </div>
            </div>`;
        }

        // AMSTAR-2 HTML
        let amstarHtml = "";
        if (e.amstar2_criteria && (e.study_design === "meta_analysis" || e.study_design === "systematic_review")) {
            const ac = e.amstar2_criteria;
            const CRITICAL = new Set(["A2", "A4", "A7", "A9", "A11", "A13", "A15"]);
            const items = [
                { key: "A1",  label: "PICO",               val: ac.a1_pico },
                { key: "A2",  label: "Protocol Registered", val: ac.a2_protocol_registered },
                { key: "A3",  label: "Design Explained",    val: ac.a3_study_design_explained },
                { key: "A4",  label: "Comprehensive Search",val: ac.a4_comprehensive_search },
                { key: "A5",  label: "Duplicate Selection",  val: ac.a5_duplicate_selection },
                { key: "A6",  label: "Duplicate Extraction", val: ac.a6_duplicate_extraction },
                { key: "A7",  label: "Excluded Listed",      val: ac.a7_excluded_studies_listed },
                { key: "A8",  label: "Studies Described",    val: ac.a8_studies_described },
                { key: "A9",  label: "RoB Assessed",        val: ac.a9_risk_of_bias_assessed },
                { key: "A10", label: "Funding Reported",     val: ac.a10_funding_reported },
                { key: "A11", label: "Stats Methods",        val: ac.a11_statistical_methods },
                { key: "A12", label: "RoB Impact",           val: ac.a12_rob_impact_assessed },
                { key: "A13", label: "RoB Interpreted",      val: ac.a13_rob_in_interpretation },
                { key: "A14", label: "Heterogeneity",        val: ac.a14_heterogeneity_discussed },
                { key: "A15", label: "Publication Bias",     val: ac.a15_publication_bias },
                { key: "A16", label: "COI Disclosed",        val: ac.a16_coi_disclosed },
            ];
            const gridHtml = items.map(it => {
                const cls = it.val === true ? "met" : it.val === false ? "not-met" : "unknown";
                const crit = CRITICAL.has(it.key) ? " critical" : "";
                return `<div class="amstar-item"><div class="amstar-cell ${cls}${crit}" title="${it.label}${crit ? ' (CRITICAL)' : ''}">${it.key}</div><div class="amstar-label">${it.label}</div></div>`;
            }).join("");

            amstarHtml = `
            <div class="detail-section" style="grid-column: 1/-1">
                <h4>AMSTAR-2 Assessment (critical items marked with border)</h4>
                <div class="amstar-grid">${gridHtml}</div>
                <div class="detail-row" style="margin-top:8px">
                    <span class="label">Criteria Met</span>
                    <span class="value">${s.amstar2_met != null ? s.amstar2_met + "/16" : "N/A"}</span>
                </div>
            </div>`;
        }

        // NOS HTML
        let nosHtml = "";
        if (e.nos_criteria && (e.study_design === "prospective_cohort" || e.study_design === "cross_sectional")) {
            const nc = e.nos_criteria;
            const domains = [
                { name: "Selection", items: [
                    { key: "S1", label: "Representativeness",  val: nc.s1_representativeness },
                    { key: "S2", label: "Non-Exposed Selection", val: nc.s2_non_exposed_selection },
                    { key: "S3", label: "Exposure Ascertainment", val: nc.s3_exposure_ascertainment },
                    { key: "S4", label: "Outcome Not Present",  val: nc.s4_outcome_not_present },
                ]},
                { name: "Comparability", items: [
                    { key: "C1", label: "Primary Factor",    val: nc.c1_primary_factor },
                    { key: "C2", label: "Additional Factors", val: nc.c2_additional_factor },
                ]},
                { name: "Outcome", items: [
                    { key: "O1", label: "Assessment",    val: nc.o1_outcome_assessment },
                    { key: "O2", label: "Follow-up Length", val: nc.o2_followup_length },
                    { key: "O3", label: "Follow-up Adequacy", val: nc.o3_followup_adequacy },
                ]},
            ];
            const domainsHtml = domains.map(d => {
                const itemsHtml = d.items.map(it => {
                    const cls = it.val === true ? "met" : it.val === false ? "not-met" : "unknown";
                    return `<div class="nos-item"><div class="nos-cell ${cls}" title="${it.label}">${it.key}</div><div class="nos-label">${it.label}</div></div>`;
                }).join("");
                return `<div class="nos-domain"><div class="nos-domain-title">${d.name}</div><div class="nos-domain-items">${itemsHtml}</div></div>`;
            }).join("");

            nosHtml = `
            <div class="detail-section" style="grid-column: 1/-1">
                <h4>Newcastle-Ottawa Scale (9 stars)</h4>
                <div class="nos-grid">${domainsHtml}</div>
                <div class="detail-row" style="margin-top:8px">
                    <span class="label">Stars Awarded</span>
                    <span class="value">${s.nos_score != null ? s.nos_score + "/9" : "N/A"}</span>
                </div>
            </div>`;
        }

        // GRADE HTML
        let gradeHtml = "";
        if (e.grade_criteria && e.study_design === "consensus_statement") {
            const gc = e.grade_criteria;
            const items = [
                { key: "G1", label: "Systematic Search",       val: gc.g1_systematic_search },
                { key: "G2", label: "Evidence Graded",         val: gc.g2_evidence_graded },
                { key: "G3", label: "Consensus Method",        val: gc.g3_consensus_method },
                { key: "G4", label: "Panel Composition",       val: gc.g4_panel_composition },
                { key: "G5", label: "COI Management",          val: gc.g5_coi_management },
                { key: "G6", label: "Recommendation Strength", val: gc.g6_recommendation_strength },
                { key: "G7", label: "Evidence Gaps",           val: gc.g7_evidence_gaps },
                { key: "G8", label: "External Review",         val: gc.g8_external_review },
            ];
            const gridHtml = items.map(it => {
                const cls = it.val === true ? "met" : it.val === false ? "not-met" : "unknown";
                return `<div class="grade-item"><div class="grade-cell ${cls}" title="${it.label}">${it.key}</div><div class="grade-label">${it.label}</div></div>`;
            }).join("");

            gradeHtml = `
            <div class="detail-section" style="grid-column: 1/-1">
                <h4>GRADE Consensus Quality (8 items)</h4>
                <div class="grade-grid">${gridHtml}</div>
                <div class="detail-row" style="margin-top:8px">
                    <span class="label">Criteria Met</span>
                    <span class="value">${s.grade_met != null ? s.grade_met + "/8" : "N/A"}</span>
                </div>
            </div>`;
        }

        // Authors
        const authors = e.authors && e.authors.length > 0
            ? e.authors.slice(0, 3).join(", ") + (e.authors.length > 3 ? ` et al.` : "")
            : "Unknown authors";

        return `
        <div class="result-card" id="result-card-${index}">
            <div class="result-header">
                <div class="score-ring">
                    <svg viewBox="0 0 100 100">
                        <circle class="score-ring-bg" cx="50" cy="50" r="42"/>
                        <circle class="score-ring-fill" cx="50" cy="50" r="42"
                            stroke="${normColor}"
                            stroke-dasharray="${circumference}"
                            stroke-dashoffset="${offset}"
                            transform="rotate(-90, 50, 50)"/>
                        <text x="50" y="46" text-anchor="middle" dominant-baseline="middle"
                              font-family="JetBrains Mono,Fira Code,monospace" font-size="19" font-weight="700"
                              fill="${normColor}">${s.normalized_score.toFixed(0)}%</text>
                        <text x="50" y="64" text-anchor="middle" dominant-baseline="middle"
                              font-family="JetBrains Mono,Fira Code,monospace" font-size="10" font-weight="500"
                              fill="#9ca3af">${s.final_score.toFixed(1)} / ${s.design_cap}</text>
                    </svg>
                </div>
                <div class="result-meta">
                    <div class="result-title">${escapeHtml(e.title || r.filename)}</div>
                    <div class="result-subtitle">
                        ${escapeHtml(authors)} ${e.year ? `(${e.year})` : ""} ${e.journal ? `— ${escapeHtml(e.journal)}` : ""}
                    </div>
                    <span class="category-badge category-${s.category}">${s.category_label}</span>
                    ${s.methodology_tool && s.methodology_tool !== "Generic" ? `<span class="methodology-badge">${escapeHtml(s.methodology_tool)}${s.methodology_tool === "PEDro" && s.pedro_score != null ? ": " + s.pedro_score + "/10" : ""}${s.methodology_tool === "AMSTAR-2" && s.amstar2_met != null ? ": " + s.amstar2_met + "/16" : ""}${s.methodology_tool === "NOS" && s.nos_score != null ? ": " + s.nos_score + "/9" : ""}${s.methodology_tool === "GRADE" && s.grade_met != null ? ": " + s.grade_met + "/8" : ""}</span>` : ""}
                </div>
            </div>

            <div class="result-details">
                <!-- Study Info -->
                <div class="detail-section">
                    <h4>Study Information</h4>
                    <div class="detail-row"><span class="label">Design</span><span class="value">${escapeHtml(designLabel(e.study_design))}</span></div>
                    <div class="detail-row"><span class="label">Sample Size</span><span class="value">${e.sample_size != null ? e.sample_size : "—"}</span></div>
                    <div class="detail-row"><span class="label">Population</span><span class="value">${escapeHtml(popLabel(e.population_type))}</span></div>
                    <div class="detail-row"><span class="label">Sport</span><span class="value">${escapeHtml(e.sport || "—")}</span></div>
                    <div class="detail-row"><span class="label">Context</span><span class="value">${escapeHtml(ctxLabel(e.ecological_context))}</span></div>
                    <div class="detail-row"><span class="label">Control Group</span><span class="value ${e.has_control_group === true ? "value-positive" : e.has_control_group === false ? "value-negative" : "value-neutral"}">${e.has_control_group === true ? "Yes" : e.has_control_group === false ? "No" : "—"}</span></div>
                    <div class="detail-row"><span class="label">Registered Protocol</span><span class="value ${e.registered_protocol === true ? "value-positive" : "value-neutral"}">${e.registered_protocol === true ? "Yes" : e.registered_protocol === false ? "No" : "—"}</span></div>
                    ${e.doi ? `<div class="detail-row"><span class="label">DOI</span><span class="value">${escapeHtml(e.doi)}</span></div>` : ""}
                </div>

                <!-- Scoring Breakdown -->
                <div class="detail-section">
                    <h4>Scoring Breakdown</h4>
                    <div class="detail-row"><span class="label">Design Cap</span><span class="value">${s.design_cap}/10</span></div>
                    <div class="detail-row"><span class="label">Base Methodology</span><span class="value">${s.base_methodology_score.toFixed(1)}</span></div>
                    <div class="detail-row"><span class="label">Sample Adj.</span><span class="value ${s.sample_size_adjustment > 0 ? "value-positive" : s.sample_size_adjustment < 0 ? "value-negative" : "value-neutral"}">${s.sample_size_adjustment > 0 ? "+" : ""}${s.sample_size_adjustment.toFixed(1)}</span></div>
                    ${s.large_sample_bonus > 0 ? `<div class="detail-row"><span class="label">Large Sample (N&ge;100)</span><span class="value value-positive">+${s.large_sample_bonus.toFixed(1)}</span></div>` : ""}
                    ${s.elite_exception_applied ? `<div class="detail-row"><span class="label">Elite Exception</span><span class="value value-positive">Applied</span></div>` : ""}
                    ${s.registered_protocol_bonus > 0 ? `<div class="detail-row"><span class="label">Registered Protocol</span><span class="value value-positive">+${s.registered_protocol_bonus.toFixed(1)}</span></div>` : ""}
                    <div class="detail-row"><span class="label">Institution Bonus</span><span class="value ${s.institutional_bonus > 0 ? "value-positive" : "value-neutral"}">${s.bonuses_nullified ? "Nullified (COI)" : (s.institutional_bonus > 0 ? "+" + s.institutional_bonus.toFixed(1) : "0.0")}</span></div>
                    <div class="detail-row"><span class="label">Journal Bonus</span><span class="value ${s.journal_bonus > 0 ? "value-positive" : "value-neutral"}">${s.bonuses_nullified ? "Nullified (COI)" : (s.journal_bonus > 0 ? "+" + s.journal_bonus.toFixed(1) : "0.0")}</span></div>
                    ${s.coi_detected ? `<div class="detail-row"><span class="label">COI Penalty (${escapeHtml(s.coi_severity || "obvious")})</span><span class="value value-negative">-${s.coi_penalty.toFixed(1)}</span></div>` : ""}
                    ${s.predatory_journal_detected ? `<div class="detail-row"><span class="label">Predatory Journal</span><span class="value value-negative">BLACK FLAG</span></div>` : ""}
                    <div class="detail-row detail-row-final"><span class="label">Final Score</span><span class="value" style="font-weight:700">${s.final_score.toFixed(1)} / ${s.design_cap}</span></div>
                    <div class="detail-row detail-row-final"><span class="label">Relative Quality</span><span class="value" style="font-weight:700;color:${normColor}">${s.normalized_score.toFixed(0)}%</span></div>
                </div>

                <!-- COI & Funding -->
                <div class="detail-section">
                    <h4>Funding &amp; Conflicts</h4>
                    <div class="detail-row"><span class="label">COI Detected</span><span class="value ${s.coi_detected ? "value-negative" : "value-positive"}">${s.coi_detected ? "YES (" + escapeHtml(s.coi_severity || "obvious") + ")" : "No"}</span></div>
                    ${e.coi_severity === "ambiguous" && !s.coi_detected ? `<div class="detail-row"><span class="label">COI Severity</span><span class="value" style="color:var(--yellow)">Ambiguous (not penalized)</span></div>` : ""}
                    ${e.funding_sources && e.funding_sources.length > 0
                        ? `<div class="detail-row"><span class="label">Funders</span><span class="value">${escapeHtml(e.funding_sources.join(", "))}</span></div>`
                        : `<div class="detail-row"><span class="label">Funders</span><span class="value value-neutral">Not reported</span></div>`}
                    ${e.product_tested ? `<div class="detail-row"><span class="label">Product Tested</span><span class="value">${escapeHtml(e.product_tested)}</span></div>` : ""}
                    ${e.conflict_of_interest_statement ? `<div style="margin-top:8px;font-size:12px;color:var(--text-secondary);line-height:1.5"><em>"${escapeHtml(truncate(e.conflict_of_interest_statement, 200))}"</em></div>` : ""}
                </div>

                <!-- Confidence -->
                <div class="detail-section">
                    <h4>Extraction Confidence</h4>
                    <div class="detail-row">
                        <span class="label">Data Extracted</span>
                        <span class="value">${c.extracted_fields}/${c.total_fields} fields (${c.confidence_pct.toFixed(0)}%)</span>
                    </div>
                    <div class="confidence-bar">
                        <div class="confidence-fill confidence-${c.level}" style="width:${c.confidence_pct}%"></div>
                    </div>
                    ${c.missing_fields.length > 0 ? `<div style="margin-top:8px;font-size:12px;color:var(--text-secondary)">Missing: ${escapeHtml(c.missing_fields.join(", "))}</div>` : ""}
                    ${e.extraction_notes ? `<div style="margin-top:8px;font-size:12px;color:var(--text-secondary)"><em>${escapeHtml(e.extraction_notes)}</em></div>` : ""}
                </div>

                ${pedroHtml}
                ${amstarHtml}
                ${nosHtml}
                ${gradeHtml}
            </div>

            <div class="result-explanation">
                <strong>Assessment</strong>${escapeHtml(s.explanation)}
            </div>
        </div>`;
    }

    // --- Helpers ---
    // Category-based score color (batch table "Score" column, absolute score)
    function getScoreColor(score, category) {
        if (category === "black_flag") return "var(--cat-black)";
        if (category === "error") return "var(--red)";
        if (score >= 8.5) return "var(--medal-gold)";
        if (score >= 7.0) return "var(--medal-silver)";
        if (score >= 5.0) return "var(--medal-bronze)";
        return "var(--cat-blue)";
    }

    // Quality-tier color (score ring and batch Quality% column, normalized)
    function getNormColor(pct) {
        if (pct >= 85) return "var(--medal-gold)";
        if (pct >= 70) return "var(--medal-silver)";
        if (pct >= 50) return "var(--medal-bronze)";
        if (pct >= 30) return "var(--cat-blue)";
        return "var(--cat-black)";
    }

    const DESIGN_LABELS = {
        meta_analysis: "Meta-Analysis",
        systematic_review: "Systematic Review",
        rct: "RCT",
        consensus_statement: "Consensus Statement",
        prospective_cohort: "Prospective Cohort",
        cross_sectional: "Cross-Sectional",
        case_series: "Case Series",
        case_study: "Case Study",
        narrative_review: "Narrative Review",
        expert_opinion: "Expert Opinion",
        other: "Other",
    };

    function designLabel(d) { return DESIGN_LABELS[d] || d || "—"; }

    const POP_LABELS = {
        elite: "Elite Athletes",
        professional: "Professional Athletes",
        sub_elite: "Sub-Elite",
        amateur: "Amateur",
        recreational: "Recreational",
        university_students: "University Students",
        youth_academy: "Youth Academy",
        general_population: "General Population",
        mixed: "Mixed",
        other: "Other",
    };

    function popLabel(p) { return POP_LABELS[p] || p || "—"; }

    const CTX_LABELS = {
        field: "Field (Ecological)",
        laboratory: "Laboratory",
        mixed: "Mixed",
        unclear: "Unclear",
    };

    function ctxLabel(c) { return CTX_LABELS[c] || c || "—"; }

    function escapeHtml(str) {
        if (!str) return "";
        const div = document.createElement("div");
        div.textContent = str;
        return div.innerHTML;
    }

    function truncate(str, len) {
        if (!str || str.length <= len) return str;
        return str.slice(0, len) + "...";
    }

})();
