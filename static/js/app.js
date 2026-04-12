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

    let selectedFiles = [];
    let analysisResults = [];

    // --- Health check ---
    async function checkHealth() {
        try {
            const res = await fetch("/api/health");
            const data = await res.json();
            if (data.api_key_configured) {
                statusDot.classList.remove("offline");
                statusText.textContent = "AI Ready";
            } else {
                statusDot.classList.add("offline");
                statusText.textContent = "API Key Missing";
            }
        } catch {
            statusDot.classList.add("offline");
            statusText.textContent = "Offline";
        }
    }
    checkHealth();

    // --- Toast ---
    function showToast(msg, type = "error") {
        toast.textContent = msg;
        toast.className = `toast toast-${type} show`;
        setTimeout(() => toast.classList.remove("show"), 4000);
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

        analyzeBtn.disabled = true;
        progressBar.classList.add("active");
        progressFill.classList.remove("determinate");
        progressText.textContent = `Analyzing ${selectedFiles.length} paper${selectedFiles.length > 1 ? "s" : ""}... This may take a minute.`;
        resultsSection.classList.remove("active");

        const formData = new FormData();
        const isBatch = selectedFiles.length > 1;

        if (isBatch) {
            for (const f of selectedFiles) {
                formData.append("files", f);
            }
        } else {
            formData.append("file", selectedFiles[0]);
        }

        try {
            const endpoint = isBatch ? "/api/analyze/batch" : "/api/analyze";
            const res = await fetch(endpoint, { method: "POST", body: formData });

            if (!res.ok) {
                const err = await res.json().catch(() => ({ detail: "Unknown error" }));
                throw new Error(err.detail || `HTTP ${res.status}`);
            }

            const data = await res.json();
            analysisResults = isBatch ? data : [data];

            renderResults();
            resultsSection.classList.add("active");
            resultsSection.scrollIntoView({ behavior: "smooth" });
        } catch (err) {
            showToast(err.message);
        } finally {
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
                { key: "C1", val: pc.c1_eligibility_specified, desc: true },
                { key: "C2", val: pc.c2_random_allocation },
                { key: "C3", val: pc.c3_concealed_allocation },
                { key: "C4", val: pc.c4_baseline_comparable },
                { key: "C5", val: pc.c5_blinding_subjects },
                { key: "C6", val: pc.c6_blinding_therapists },
                { key: "C7", val: pc.c7_blinding_assessors },
                { key: "C8", val: pc.c8_adequate_followup },
                { key: "C9", val: pc.c9_intention_to_treat },
                { key: "C10", val: pc.c10_between_group },
                { key: "C11", val: pc.c11_point_variability },
            ];
            const cellsHtml = cells.map(c => {
                let cls = "unknown";
                if (c.desc) cls = c.val === true ? "descriptive" : c.val === false ? "not-met" : "unknown";
                else cls = c.val === true ? "met" : c.val === false ? "not-met" : "unknown";
                return `<div class="pedro-cell ${cls}" title="${c.key}">${c.key}</div>`;
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
                    ${s.large_sample_bonus > 0 ? `<div class="detail-row"><span class="label">Large Sample (N&gt;500)</span><span class="value value-positive">+${s.large_sample_bonus.toFixed(1)}</span></div>` : ""}
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
            </div>

            <div class="result-explanation">
                <strong>Assessment:</strong> ${escapeHtml(s.explanation)}
            </div>
        </div>`;
    }

    // --- Helpers ---
    function getScoreColor(score, category) {
        if (category === "black_flag" || category === "error") return "var(--red)";
        if (score >= 8.5) return "var(--accent)";
        if (score >= 7.0) return "var(--green)";
        if (score >= 5.0) return "var(--yellow)";
        if (score >= 3.0) return "var(--orange)";
        return "var(--red)";
    }

    function getNormColor(pct) {
        if (pct >= 85) return "var(--accent)";
        if (pct >= 70) return "var(--green)";
        if (pct >= 50) return "var(--yellow)";
        if (pct >= 30) return "var(--orange)";
        return "var(--red)";
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
