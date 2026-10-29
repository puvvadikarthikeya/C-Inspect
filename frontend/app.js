/**
 * C-Inspect — Frontend Client Controller
 * Manages Monaco Editor, debounced live static analysis, squiggly markers,
 * SQLite submission checkpoints, recurring mistake history, and external compiler invocation.
 */

// --- Default Starter Code Template ---
const DEFAULT_C_CODE = `int main(void) {
    // Write your C code here
    return 0;
}`;

// --- Application State ---
const state = {
    editor: null,
    editorFallback: false,
    currentStudentId: "student_demo",
    currentFileName: "main.c",
    analysisTimer: null,
    debounceMs: 450,
    activeDiagnostics: [],
    ruleCatalog: {},
    currentFilter: "all",
    analysisSeq: 0,
    samples: [],
    lastCompilerResult: null,
    lastSubmissionResult: null,
    studentHistory: null
};

// --- DOM Elements ---
const el = {
    monacoContainer: document.getElementById("monaco-editor"),
    fallbackEditor: document.getElementById("fallback-editor"),
    studentSelect: document.getElementById("student-select"),
    sampleSelect: document.getElementById("sample-select"),
    stdinInput: document.getElementById("stdin-input"),
    btnNewStudent: document.getElementById("btn-new-student"),
    btnDownloadReport: document.getElementById("btn-download-report"),
    btnSaveCheckpoint: document.getElementById("btn-save-checkpoint"),
    btnRunCode: document.getElementById("btn-run-code"),
    debounceText: document.getElementById("debounce-text"),
    compilerStatusPill: document.getElementById("compiler-status-indicator"),
    compilerNameLabel: document.getElementById("compiler-name-label"),
    countErrors: document.getElementById("count-errors"),
    countWarnings: document.getElementById("count-warnings"),
    countInfos: document.getElementById("count-infos"),
    badgeDiagCount: document.getElementById("badge-diag-count"),
    diagnosticsList: document.getElementById("diagnostics-list"),
    terminalContent: document.getElementById("terminal-content"),
    tokensStream: document.getElementById("tokens-stream-container"),
    btnClearTerm: document.getElementById("btn-clear-term"),
    astTreeViewer: document.getElementById("ast-tree-viewer"),
    symbolTableViewer: document.getElementById("symbol-table-viewer"),
    stageLexerSummary: document.getElementById("stage-lexer-summary"),
    ruleCatalogCards: document.getElementById("rule-catalog-cards"),
    historyAvatar: document.getElementById("history-avatar"),
    historyStudentName: document.getElementById("history-student-name"),
    historySubStats: document.getElementById("history-sub-stats"),
    historyRuleBars: document.getElementById("history-rule-bars"),
    historySubmissionsList: document.getElementById("history-submissions-list"),
    historyFindingsList: document.getElementById("history-findings-list"),
    modalNewStudent: document.getElementById("modal-new-student"),
    btnCloseModal: document.getElementById("btn-close-modal"),
    btnCancelStudent: document.getElementById("btn-cancel-student"),
    btnCreateStudentConfirm: document.getElementById("btn-create-student-confirm"),
    newStudentNameInput: document.getElementById("new-student-name"),
    modalReportPopup: document.getElementById("modal-report-popup"),
    btnCloseReportModal: document.getElementById("btn-close-report-modal"),
    btnCloseReportPopup: document.getElementById("btn-close-report-popup"),
    btnModalDownloadReport: document.getElementById("btn-modal-download-report"),
    popStatErrors: document.getElementById("pop-stat-errors"),
    popStatWarnings: document.getElementById("pop-stat-warnings"),
    popStatRepeat: document.getElementById("pop-stat-repeat"),
    popStatNew: document.getElementById("pop-stat-new"),
    reportPreviewText: document.getElementById("report-preview-text")
};

// --- Initialization ---
document.addEventListener("DOMContentLoaded", async () => {
    initTabs();
    initTerminalTabs();
    initEventListeners();
    await loadStudentProfiles();
    await checkCompilerStatus();
    await loadRuleCatalog();
    await loadSamplePrograms();
    initEditor();
});

// --- Editor Setup (Monaco Editor with Fallback) ---
function initEditor() {
    if (window.require) {
        window.require.config({
            paths: { vs: "https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.45.0/min/vs" }
        });
        window.require(["vs/editor/editor.main"], () => {
            monaco.editor.defineTheme("cinspect-dark", {
                base: "vs-dark",
                inherit: true,
                rules: [
                    { token: "keyword", foreground: "38bdf8", fontStyle: "bold" },
                    { token: "type", foreground: "6ee7b7" },
                    { token: "identifier", foreground: "f8fafc" },
                    { token: "number", foreground: "f59e0b" },
                    { token: "string", foreground: "a7f3d0" },
                    { token: "comment", foreground: "64748b", fontStyle: "italic" }
                ],
                colors: {
                    "editor.background": "#0d1117",
                    "editor.foreground": "#f8fafc",
                    "editorLineNumber.foreground": "#475569",
                    "editorLineNumber.activeForeground": "#38bdf8",
                    "editor.lineHighlightBackground": "#161f30",
                    "editorCursor.foreground": "#38bdf8",
                    "editor.selectionBackground": "#1e3a5f"
                }
            });

            state.editor = monaco.editor.create(el.monacoContainer, {
                value: DEFAULT_C_CODE,
                language: "c",
                theme: "cinspect-dark",
                automaticLayout: true,
                fontSize: 14,
                fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
                lineNumbers: "on",
                minimap: { enabled: false },
                scrollBeyondLastLine: false,
                tabSize: 4,
                renderLineHighlight: "all"
            });

            state.editor.onDidChangeModelContent(() => {
                triggerDebouncedAnalysis();
            });

            // Initial analysis
            triggerDebouncedAnalysis(true);
        }, () => {
            setupFallbackEditor();
        });
    } else {
        setupFallbackEditor();
    }
}

function setupFallbackEditor() {
    state.editorFallback = true;
    el.monacoContainer.style.display = "none";
    el.fallbackEditor.style.display = "block";
    el.fallbackEditor.value = DEFAULT_C_CODE;
    el.fallbackEditor.addEventListener("input", () => triggerDebouncedAnalysis());
    triggerDebouncedAnalysis(true);
}

function getEditorCode() {
    if (state.editor) {
        return state.editor.getValue();
    }
    return el.fallbackEditor.value;
}

function setEditorCode(code) {
    if (state.editor) {
        state.editor.setValue(code);
    } else {
        el.fallbackEditor.value = code;
    }
    triggerDebouncedAnalysis(true);
}

// --- Live Debounced Static Analysis (PRD FR-02) ---
function triggerDebouncedAnalysis(immediate = false) {
    if (state.analysisTimer) {
        clearTimeout(state.analysisTimer);
    }

    el.debounceText.textContent = "Analyzing in " + state.debounceMs + "ms...";

    const delay = immediate ? 0 : state.debounceMs;
    state.analysisTimer = setTimeout(() => {
        performAnalysis();
    }, delay);
}

async function performAnalysis() {
    state.analysisSeq += 1;
    const currentSeq = state.analysisSeq;
    const code = getEditorCode();

    el.debounceText.textContent = "Running Static Checks...";

    try {
        const res = await fetch("/api/analyze", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                code: code,
                student_id: state.currentStudentId
            })
        });

        if (!res.ok) throw new Error("Analysis failed");
        const data = await res.json();

        // Ignore stale results
        if (currentSeq !== state.analysisSeq) return;

        state.activeDiagnostics = data.diagnostics || [];
        updateCounters(data.summary);
        updateEditorMarkers(data.diagnostics);
        renderDiagnosticsList(data.diagnostics);
        renderCompilerStages(data);

        el.debounceText.textContent = `Analysis Up to Date (${data.diagnostics.length} findings)`;
    } catch (err) {
        console.error(err);
        el.debounceText.textContent = "Analysis unavailable";
    }
}

// --- Update Monaco Squiggly Markers ---
function updateEditorMarkers(diagnostics) {
    if (!state.editor || !window.monaco) return;

    const markers = diagnostics.map(d => {
        let severity = monaco.MarkerSeverity.Warning;
        if (d.severity === "error") severity = monaco.MarkerSeverity.Error;
        else if (d.severity === "info") severity = monaco.MarkerSeverity.Info;

        let msg = `[${d.rule_id}] ${d.message}`;
        if (d.prior_recurrence && d.prior_recurrence > 0) {
            msg += ` (Repeated ${d.prior_recurrence}x in your history)`;
        }

        return {
            startLineNumber: d.line,
            startColumn: d.column,
            endLineNumber: d.end_line || d.line,
            endColumn: d.end_column || (d.column + 6),
            message: msg,
            severity: severity
        };
    });

    const model = state.editor.getModel();
    if (model) {
        monaco.editor.setModelMarkers(model, "cinspect", markers);
    }
}

// --- Render Diagnostics Panel ---
function renderDiagnosticsList(diagnostics) {
    el.diagnosticsList.innerHTML = "";

    const filtered = diagnostics.filter(d => {
        if (state.currentFilter === "all") return true;
        return d.severity === state.currentFilter;
    });

    if (filtered.length === 0) {
        el.diagnosticsList.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">✓</div>
                <div class="empty-title">Clean Source Code</div>
                <div class="empty-desc">No issues matching "${state.currentFilter}" found.</div>
            </div>
        `;
        return;
    }

    filtered.forEach((d, idx) => {
        const card = document.createElement("div");
        card.className = `diag-card ${d.severity}`;
        card.onclick = () => jumpToLine(d.line, d.column);

        // Recurrence tag
        let recurrenceBadgeHtml = "";
        if (d.prior_recurrence && d.prior_recurrence > 0) {
            recurrenceBadgeHtml = `
                <div class="recurrence-badge" title="Recurring Mistake Pattern across your past submissions">
                    <span>⚠️ Repeated Mistake:</span>
                    <span>Seen ${d.prior_recurrence} time${d.prior_recurrence > 1 ? 's' : ''} before</span>
                </div>
            `;
        }

        // Quick suggestion
        let suggestionHtml = "";
        if (d.suggestion) {
            suggestionHtml = `
                <div class="diag-suggestion">
                    <span class="suggestion-icon">💡 Fix:</span>
                    <span>${escapeHtml(d.suggestion)}</span>
                </div>
            `;
        }

        card.innerHTML = `
            <div class="diag-card-header">
                <div class="diag-meta-left">
                    <span class="severity-tag ${d.severity}">${d.severity}</span>
                    <span class="rule-id-label">${d.rule_id}</span>
                </div>
                <span class="location-tag">Line ${d.line}:${d.column}</span>
            </div>
            ${recurrenceBadgeHtml}
            <div class="diag-message">${escapeHtml(d.message)}</div>
            ${d.explanation ? `<div class="diag-explanation">${escapeHtml(d.explanation)}</div>` : ''}
            ${suggestionHtml}
            <div class="compiler-concept-tag">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 14 14"></polyline></svg>
                <span>Stage: ${d.compiler_concept || d.category}</span>
            </div>
        `;

        el.diagnosticsList.appendChild(card);
    });
}

function updateCounters(summary) {
    if (!summary) return;
    el.countErrors.textContent = `${summary.errors} Error${summary.errors !== 1 ? 's' : ''}`;
    el.countWarnings.textContent = `${summary.warnings} Warning${summary.warnings !== 1 ? 's' : ''}`;
    el.countInfos.textContent = `${summary.infos} Info`;
    el.badgeDiagCount.textContent = summary.total;
    if (summary.total === 0) {
        el.badgeDiagCount.classList.add("zero");
    } else {
        el.badgeDiagCount.classList.remove("zero");
    }
}

function jumpToLine(line, col) {
    if (state.editor) {
        state.editor.revealLineInCenter(line);
        state.editor.setPosition({ lineNumber: line, column: col });
        state.editor.focus();
    }
}

// --- Checkpoint / Submission (PRD Section 6 & 10) ---
async function saveCheckpointSubmission() {
    const code = getEditorCode();
    el.debounceText.textContent = "Saving Checkpoint to Database...";

    try {
        const res = await fetch("/api/submit", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                code: code,
                file_name: state.currentFileName,
                student_id: state.currentStudentId
            })
        });

        if (!res.ok) throw new Error("Submission checkpoint failed");
        const data = await res.json();
        state.lastSubmissionResult = data.submission;

        // Switch to history tab to show saved checkpoint
        activateTab("history");
        await loadStudentHistory();

        // Re-analyze so that recurrence badges immediately reflect the new submission!
        triggerDebouncedAnalysis(true);

        appendTerminalOutput(`\n[Checkpoint Recorded]: Submission saved with ID '${data.submission.submission_id}'. Findings persisted in SQLite.`);
    } catch (err) {
        console.error(err);
        appendTerminalOutput("\n[Checkpoint Error]: Failed to save submission.");
    }
}

// --- Compiler Run Flow (PRD FR-09 & FR-10) ---
async function runCompiler() {
    const code = getEditorCode();
    const stdinVal = el.stdinInput ? el.stdinInput.value : "";
    activateTerminalTab("compiler");
    el.terminalContent.textContent = "Invoking external compiler / educational runner...\n";

    try {
        const res = await fetch("/api/run", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ code: code, stdin: stdinVal })
        });

        if (!res.ok) throw new Error("Execution request failed");
        const data = await res.json();
        state.lastCompilerResult = data;

        let out = `--- Toolchain: ${data.compiler} ---\n`;
        out += `Exit Code: ${data.exit_code} (Execution Time: ${data.execution_time_ms}ms)\n\n`;
        if (data.compile_output) {
            out += `[Compiler Output]:\n${data.compile_output}\n\n`;
        }
        if (data.runtime_output) {
            out += `[Program Output]:\n${data.runtime_output}\n`;
        }

        el.terminalContent.textContent = out;

        // Automatically show inspection & compilation report popup
        showReportPopup();
    } catch (err) {
        el.terminalContent.textContent = `[Error]: Could not communicate with runner: ${err.message}`;
    }
}

// --- Compiler Stages Rendering (Milestone B Showcase) ---
function renderCompilerStages(data) {
    // 1. Tokens
    if (data.tokens) {
        el.stageLexerSummary.textContent = `Tokens Scanned: ${data.tokens.length}`;
        el.tokensStream.innerHTML = data.tokens.map(t => `
            <div class="token-chip" title="${t.type} at line ${t.line}:${t.column}">
                <span class="token-type-tag">${t.type}</span>
                <span class="token-val">${escapeHtml(t.value || "EOF")}</span>
                <span class="token-pos">L${t.line}:${t.column}</span>
            </div>
        `).join("");
    }

    // 2. AST
    if (data.ast) {
        el.astTreeViewer.textContent = JSON.stringify(data.ast, null, 2);
    }

    // 3. Symbol Table
    if (data.symbol_table) {
        el.symbolTableViewer.textContent = JSON.stringify(data.symbol_table, null, 2);
    }
}

// --- Student History & Recurrence Analytics ---
async function loadStudentHistory() {
    try {
        const res = await fetch(`/api/history?student_id=${state.currentStudentId}`);
        if (!res.ok) throw new Error("History fetch failed");
        const data = await res.json();
        state.studentHistory = data;

        // Update Header
        const selOption = el.studentSelect.options[el.studentSelect.selectedIndex];
        const studentName = selOption ? selOption.text : "Student";
        el.historyStudentName.textContent = studentName;
        el.historyAvatar.textContent = studentName.split(" ").map(w => w[0]).join("").slice(0, 2).toUpperCase();
        el.historySubStats.textContent = `${data.submissions_count} Checkpoints Recorded • ${data.rule_stats.length} Unique Mistake Rules Detected`;

        // Recurrence Bars
        if (!data.rule_stats || data.rule_stats.length === 0) {
            el.historyRuleBars.innerHTML = `<div class="placeholder-msg">No submissions yet for this student. Save a checkpoint with [Submit & Track] to begin tracking!</div>`;
        } else {
            const maxOccurrences = Math.max(...data.rule_stats.map(s => s.total_occurrences), 1);
            el.historyRuleBars.innerHTML = data.rule_stats.map(s => {
                const pct = Math.round((s.total_occurrences / maxOccurrences) * 100);
                return `
                    <div class="rule-bar-item">
                        <div class="rule-bar-header">
                            <span>${s.rule_id}</span>
                            <span>${s.total_occurrences} occurrence${s.total_occurrences > 1 ? 's' : ''} (${s.corrected_count} fixed)</span>
                        </div>
                        <div class="progress-track">
                            <div class="progress-fill" style="width: ${pct}%"></div>
                        </div>
                    </div>
                `;
            }).join("");
        }

        // Submissions timeline
        if (!data.submissions || data.submissions.length === 0) {
            el.historySubmissionsList.innerHTML = `<div class="placeholder-msg">No submissions recorded.</div>`;
        } else {
            el.historySubmissionsList.innerHTML = data.submissions.map(sub => `
                <div class="sub-timeline-card">
                    <div class="sub-timeline-top">
                        <span class="sub-filename">${escapeHtml(sub.file_name)}</span>
                        <span>${new Date(sub.submitted_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                    </div>
                    <div>Findings captured: <strong>${sub.findings_count}</strong></div>
                </div>
            `).join("");
        }

        // Recent findings & status management (FR-08)
        if (el.historyFindingsList) {
            if (!data.recent_findings || data.recent_findings.length === 0) {
                el.historyFindingsList.innerHTML = `<div class="placeholder-msg">No findings recorded in checkpoints yet.</div>`;
            } else {
                el.historyFindingsList.innerHTML = data.recent_findings.map(f => {
                    const st = f.status || "open";
                    let actionBtns = "";
                    if (st === "open") {
                        actionBtns = `
                            <button class="btn-finding-action correct" onclick="window.handleUpdateFindingStatus('${f.finding_id}', 'corrected')">✓ Mark Corrected</button>
                            <button class="btn-finding-action dismiss" onclick="window.handleUpdateFindingStatus('${f.finding_id}', 'dismissed')">✕ Dismiss</button>
                        `;
                    } else {
                        actionBtns = `
                            <button class="btn-finding-action" onclick="window.handleUpdateFindingStatus('${f.finding_id}', 'open')">↺ Reopen</button>
                        `;
                    }

                    return `
                        <div class="finding-item-card">
                            <div class="finding-item-top">
                                <div class="finding-item-left">
                                    <span class="severity-tag ${f.severity}">${f.severity}</span>
                                    <strong style="font-size:0.78rem;">${f.rule_id}</strong>
                                </div>
                                <span class="finding-status-tag ${st}">${st}</span>
                            </div>
                            <div class="finding-item-msg">${escapeHtml(f.message)}</div>
                            <div class="finding-item-meta">${escapeHtml(f.file_name)} • Line ${f.line_number}:${f.column_number} • ${new Date(f.submitted_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</div>
                            <div class="finding-actions">
                                ${actionBtns}
                            </div>
                        </div>
                    `;
                }).join("");
            }
        }
    } catch (err) {
        console.error(err);
    }
}

// Global handler for finding status transition (FR-08)
window.handleUpdateFindingStatus = async function(findingId, newStatus) {
    try {
        const res = await fetch(`/api/findings/${findingId}`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ status: newStatus })
        });
        if (res.ok) {
            await loadStudentHistory();
        }
    } catch (err) {
        console.error("Failed to update finding status:", err);
    }
};

// --- Profiles & Compiler Status ---
async function loadStudentProfiles() {
    try {
        const res = await fetch("/api/students");
        if (!res.ok) return;
        const students = await res.json();
        el.studentSelect.innerHTML = students.map(s => `
            <option value="${s.student_id}">${escapeHtml(s.display_name)}</option>
        `).join("");
        state.currentStudentId = el.studentSelect.value;
    } catch (err) {
        console.error(err);
    }
}

async function checkCompilerStatus() {
    try {
        const res = await fetch("/api/compiler-status");
        if (!res.ok) return;
        const info = await res.json();
        const dot = el.compilerStatusPill.querySelector(".status-dot");
        if (info.available) {
            dot.classList.add("active");
            el.compilerNameLabel.textContent = `${info.compiler.toUpperCase()} Available`;
        } else {
            dot.classList.remove("active");
            el.compilerNameLabel.textContent = "Safe Educational Runner";
        }
    } catch (err) {
        el.compilerNameLabel.textContent = "Runner Ready";
    }
}

async function loadRuleCatalog() {
    try {
        const res = await fetch("/api/rules");
        if (!res.ok) return;
        state.ruleCatalog = await res.json();
        el.ruleCatalogCards.innerHTML = Object.values(state.ruleCatalog).map(r => `
            <div class="catalog-card">
                <div class="cat-header">
                    <span class="cat-title">${escapeHtml(r.name)} (${r.rule_id})</span>
                    <span class="cat-stage">${escapeHtml(r.compiler_concept)}</span>
                </div>
                <div class="cat-desc">${escapeHtml(r.explanation)}</div>
                <div class="cat-fix"><strong>Suggested Fix:</strong> ${escapeHtml(r.suggestion)}</div>
            </div>
        `).join("");
    } catch (err) {
        console.error(err);
    }
}

// --- Sample Test Cases Loader ---
async function loadSamplePrograms() {
    try {
        const res = await fetch("/api/samples");
        if (!res.ok) return;
        state.samples = await res.json();
        if (el.sampleSelect) {
            el.sampleSelect.innerHTML = `<option value="">-- Choose Sample Program --</option>` +
                state.samples.map(s => `<option value="${escapeHtml(s.file_name)}">${escapeHtml(s.title)}</option>`).join("");
        }
    } catch (err) {
        console.error("Failed to load sample programs:", err);
    }
}

// --- Event Listeners ---
function initEventListeners() {
    // Sample Program selection
    if (el.sampleSelect) {
        el.sampleSelect.addEventListener("change", (e) => {
            const fname = e.target.value;
            if (!fname) return;
            const chosen = state.samples.find(s => s.file_name === fname);
            if (chosen) {
                state.currentFileName = chosen.file_name;
                const fnLabel = document.getElementById("current-filename");
                if (fnLabel) fnLabel.textContent = chosen.file_name;
                setEditorCode(chosen.code);
                appendTerminalOutput(`\n[Sample Loaded]: Loaded '${chosen.file_name}'. Running live static analysis...`);
            }
        });
    }

    // Student profile switch
    el.studentSelect.addEventListener("change", (e) => {
        state.currentStudentId = e.target.value;
        triggerDebouncedAnalysis(true);
        loadStudentHistory();
    });

    // Action buttons
    if (el.btnDownloadReport) {
        el.btnDownloadReport.addEventListener("click", () => showReportPopup());
    }
    if (el.btnCloseReportModal) {
        el.btnCloseReportModal.addEventListener("click", () => hideReportPopup());
    }
    if (el.btnCloseReportPopup) {
        el.btnCloseReportPopup.addEventListener("click", () => hideReportPopup());
    }
    if (el.btnModalDownloadReport) {
        el.btnModalDownloadReport.addEventListener("click", () => downloadReport());
    }
    el.btnSaveCheckpoint.addEventListener("click", () => saveCheckpointSubmission());
    el.btnRunCode.addEventListener("click", () => runCompiler());
    el.btnClearTerm.addEventListener("click", () => {
        el.terminalContent.textContent = "Terminal cleared.";
    });

    // Diagnostics filter pills
    document.querySelectorAll(".filter-pill").forEach(pill => {
        pill.addEventListener("click", () => {
            document.querySelectorAll(".filter-pill").forEach(p => p.classList.remove("active"));
            pill.classList.add("active");
            state.currentFilter = pill.getAttribute("data-filter");
            renderDiagnosticsList(state.activeDiagnostics);
        });
    });

    // New student modal
    el.btnNewStudent.addEventListener("click", () => {
        el.modalNewStudent.classList.add("active");
        el.newStudentNameInput.focus();
    });
    el.btnCloseModal.addEventListener("click", () => el.modalNewStudent.classList.remove("active"));
    el.btnCancelStudent.addEventListener("click", () => el.modalNewStudent.classList.remove("active"));
    el.btnCreateStudentConfirm.addEventListener("click", async () => {
        const name = el.newStudentNameInput.value.trim();
        if (!name) return;
        try {
            const res = await fetch("/api/students", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ display_name: name })
            });
            if (res.ok) {
                const newStudent = await res.json();
                el.modalNewStudent.classList.remove("active");
                el.newStudentNameInput.value = "";
                await loadStudentProfiles();
                el.studentSelect.value = newStudent.student_id;
                state.currentStudentId = newStudent.student_id;
                triggerDebouncedAnalysis(true);
                loadStudentHistory();
            }
        } catch (err) {
            console.error(err);
        }
    });
}

function initTabs() {
    document.querySelectorAll(".insp-tab").forEach(tab => {
        tab.addEventListener("click", () => {
            const viewName = tab.getAttribute("data-view");
            activateTab(viewName);
        });
    });
}

function activateTab(viewName) {
    document.querySelectorAll(".insp-tab").forEach(t => {
        t.classList.toggle("active", t.getAttribute("data-view") === viewName);
    });
    document.querySelectorAll(".insp-view").forEach(v => {
        v.classList.toggle("active", v.id === `view-${viewName}`);
    });
    if (viewName === "history") {
        loadStudentHistory();
    }
}

function initTerminalTabs() {
    document.querySelectorAll(".term-tab").forEach(tab => {
        tab.addEventListener("click", () => {
            const tabName = tab.getAttribute("data-tab");
            activateTerminalTab(tabName);
        });
    });
}

function activateTerminalTab(tabName) {
    document.querySelectorAll(".term-tab").forEach(t => {
        t.classList.toggle("active", t.getAttribute("data-tab") === tabName);
    });
    document.querySelectorAll(".term-pane").forEach(p => {
        p.classList.toggle("active", p.id === `tab-${tabName}`);
    });
}

function appendTerminalOutput(msg) {
    el.terminalContent.textContent += msg + "\n";
}

function escapeHtml(text) {
    if (!text) return "";
    return String(text)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// --- Diagnostics & Learning History Report Generator ---
function generateSimpleReport() {
    const selOption = el.studentSelect && el.studentSelect.selectedIndex >= 0 ? el.studentSelect.options[el.studentSelect.selectedIndex] : null;
    const studentName = selOption ? selOption.text : "Student";
    const filename = state.currentFileName || "main.c";
    const now = new Date().toLocaleString();

    // 1. DATA FROM ACTIVE DIAGNOSTICS (Current Code State)
    const diags = state.activeDiagnostics || [];
    const errors = diags.filter(d => d.severity === "error").length;
    const warnings = diags.filter(d => d.severity === "warning").length;
    const repetitive = diags.filter(d => d.prior_recurrence && d.prior_recurrence > 0).length;
    const newErrors = diags.length - repetitive;

    // 2. DATA FROM LEARNING HISTORY (Database Profile)
    const hist = state.studentHistory || {};
    const submissionsCount = hist.submissions_count || 0;
    const ruleStats = hist.rule_stats || [];
    const submissions = hist.submissions || [];

    const lines = [];
    lines.push("==================================================");
    lines.push("     C-INSPECT DIAGNOSTICS & LEARNING REPORT      ");
    lines.push("==================================================");
    lines.push(`Student : ${studentName}`);
    lines.push(`File    : ${filename}`);
    lines.push(`Date    : ${now}`);
    lines.push("");

    // SECTION 1: ACTIVE DIAGNOSTICS
    lines.push("--------------------------------------------------");
    lines.push("1. CURRENT DIAGNOSTICS (ACTIVE CODE FINDINGS)");
    lines.push("--------------------------------------------------");
    lines.push(`Total Issues      = ${diags.length}`);
    lines.push(`Errors            = ${errors}`);
    lines.push(`Warnings          = ${warnings}`);
    lines.push(`Repetitive Errors = ${repetitive} (repeated from previous submissions)`);
    lines.push(`New Errors        = ${newErrors}`);
    lines.push("");
    lines.push("Active Mistakes List (Under 1 Line Each):");

    if (diags.length === 0) {
        lines.push("✓ No mistakes found! Your active code is clean.");
    } else {
        diags.forEach((d, i) => {
            const isRepeat = d.prior_recurrence && d.prior_recurrence > 0;
            const tag = isRepeat ? `[REPEAT ${d.prior_recurrence}x]` : `[${d.severity.toUpperCase()}]`;
            const cleanMsg = (d.message || d.rule_id).replace(/\r?\n|\r/g, " ").replace(/\s+/g, " ").trim();
            lines.push(`${i + 1}. Line ${d.line}: ${tag} ${cleanMsg}`);
            if (d.suggestion) {
                const cleanFix = d.suggestion.replace(/\r?\n|\r/g, " ").replace(/\s+/g, " ").trim();
                lines.push(`   Suggested Fix: ${cleanFix}`);
            }
        });
    }

    lines.push("");
    // SECTION 2: LEARNING HISTORY
    lines.push("--------------------------------------------------");
    lines.push("2. LEARNING HISTORY (PERSISTENT STUDENT PROFILE)");
    lines.push("--------------------------------------------------");
    lines.push(`Checkpoints Saved : ${submissionsCount} submission(s) recorded in database`);

    if (ruleStats.length === 0) {
        lines.push("History Status    : No past mistakes on record yet. Click [Submit & Track] to checkpoint!");
    } else {
        const totalHistorical = ruleStats.reduce((sum, s) => sum + s.total_occurrences, 0);
        const totalCorrected = ruleStats.reduce((sum, s) => sum + s.corrected_count, 0);
        const totalOpen = ruleStats.reduce((sum, s) => sum + s.open_count, 0);

        lines.push(`All-Time Mistakes : ${totalHistorical} (${totalCorrected} marked fixed, ${totalOpen} open)`);
        lines.push("");
        lines.push("Mistake Hotspots History:");
        ruleStats.forEach(s => {
            lines.push(`- ${s.rule_id}: made ${s.total_occurrences} time(s) (${s.corrected_count} fixed)`);
        });

        if (submissions.length > 0) {
            lines.push("");
            lines.push("Recent Checkpoint Submissions:");
            submissions.slice(0, 3).forEach(sub => {
                const subTime = new Date(sub.submitted_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                lines.push(`- ${sub.file_name}: captured ${sub.findings_count} findings at ${subTime}`);
            });
        }
    }

    lines.push("");
    // SECTION 3: COMPILATION & EXECUTION OUTPUT
    lines.push("--------------------------------------------------");
    lines.push("3. COMPILATION & EXECUTION OUTPUT");
    lines.push("--------------------------------------------------");
    if (state.lastCompilerResult) {
        lines.push(`Compiler Toolchain: ${state.lastCompilerResult.compiler || "gcc"}`);
        lines.push(`Status            : ${state.lastCompilerResult.success ? "Success" : "Failed"} (Exit Code: ${state.lastCompilerResult.exit_code})`);
        lines.push(`Execution Time    : ${state.lastCompilerResult.execution_time_ms} ms`);
        if (state.lastCompilerResult.runtime_output) {
            lines.push("");
            lines.push("[Program Output]:");
            lines.push(state.lastCompilerResult.runtime_output.trim());
        }
        if (state.lastCompilerResult.compile_output && !state.lastCompilerResult.success) {
            lines.push("");
            lines.push("[Compiler Error]:");
            lines.push(state.lastCompilerResult.compile_output.trim());
        }
    } else {
        lines.push("Compiler Status   : Code not run yet (Click [Run (GCC)] to execute)");
    }

    lines.push("");
    lines.push("==================================================");
    lines.push("Advice: Review any active findings above, then click [Run] or [Submit]!");
    lines.push("==================================================");

    return lines.join("\n");
}

// Download report as plain text file
async function downloadReport() {
    if (!state.studentHistory) {
        await loadStudentHistory();
    }
    const reportContent = generateSimpleReport();
    const blob = new Blob([reportContent], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    const baseName = (state.currentFileName || "main.c").replace(/\.c$/i, "");
    link.href = url;
    link.download = `report_${baseName}.txt`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    appendTerminalOutput(`\n[Report Downloaded]: Saved 'report_${baseName}.txt' successfully.`);
}

// --- Popup Modal Display Logic ---
async function showReportPopup() {
    if (!el.modalReportPopup) return;

    // Ensure student history is fresh
    if (!state.studentHistory) {
        await loadStudentHistory();
    }

    const diags = state.activeDiagnostics || [];
    const errors = diags.filter(d => d.severity === "error").length;
    const warnings = diags.filter(d => d.severity === "warning").length;
    const repeat = diags.filter(d => d.prior_recurrence && d.prior_recurrence > 0).length;
    const newIssues = diags.length - repeat;

    if (el.popStatErrors) el.popStatErrors.textContent = errors;
    if (el.popStatWarnings) el.popStatWarnings.textContent = warnings;
    if (el.popStatRepeat) el.popStatRepeat.textContent = repeat;
    if (el.popStatNew) el.popStatNew.textContent = newIssues;

    const reportContent = generateSimpleReport();
    if (el.reportPreviewText) {
        el.reportPreviewText.textContent = reportContent;
    }

    el.modalReportPopup.classList.add("active");
}

function hideReportPopup() {
    if (el.modalReportPopup) {
        el.modalReportPopup.classList.remove("active");
    }
}
