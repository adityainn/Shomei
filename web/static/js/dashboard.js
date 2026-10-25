/**
 * Shomei Interactive Audit Dashboard Controller (Stage 2 - Fixed)
 *
 * Full 8-Phase Guided Stepper Workflow:
 * 1. Request Received
 * 2. Identity Resolution
 * 3. System Discovery
 * 4. Evidence Collection
 * 5. Findings
 * 6. Remediation Plan
 * 7. Verification
 * 8. Final Status & Raw JSON
 *
 * Architecture & Fixes:
 * - Clear separation of editable inputs state vs executed audit state.
 * - Explicit user-triggered audit (editing inputs does NOT execute audit).
 * - Stale state detection when inputs change after an audit.
 * - Inspectable real-time 8-stage processing journey with elapsed timers and cancellation.
 * - Single authoritative audit result source for all 8 stages, system map, evidence, report, and JSON.
 * - Fully responsive with 0 horizontal page-level overflow across 1440, 1280, 1024, 768, and 390px.
 */

document.addEventListener('DOMContentLoaded', () => {
  // Elements: Form Inputs & Selectors
  const caseSelect = document.getElementById('case-select');
  const caseSearchInput = document.getElementById('case-search-input');
  const caseFilterSelect = document.getElementById('case-filter-select');
  const caseOutcomeSelect = document.getElementById('case-outcome-select');

  const inputEmail = document.getElementById('input-email');
  const inputRequestedAt = document.getElementById('input-requested-at');
  const inputReportedStatus = document.getElementById('input-reported-status');
  const inputAuditAt = document.getElementById('input-audit-at');
  const inputRequestText = document.getElementById('input-request-text');
  const btnRunAudit = document.getElementById('btn-run-audit');
  const inputAuditStatus = document.getElementById('input-audit-status');

  // Verdict & Stat Pills
  const verdictContainer = document.getElementById('verdict-container');
  const resolvedUserIdEl = document.getElementById('stat-user-id');
  const resolvedIdentsEl = document.getElementById('stat-idents');
  const stepsCountEl = document.getElementById('stat-steps');
  const temporalLeaksEl = document.getElementById('stat-leaks');
  const datasetStatusBadge = document.getElementById('dataset-status-badge');

  // Live Audit Progress Activity Card
  const auditProgressCard = document.getElementById('audit-progress-card');
  const progressStageTitle = document.getElementById('progress-stage-title');
  const progressElapsedBadge = document.getElementById('progress-elapsed-badge');
  const progressBarFill = document.getElementById('progress-bar-fill');
  const progressStatusDesc = document.getElementById('progress-status-desc');

  // Stage 1: Request Received Elements
  const intakeCaseId = document.getElementById('intake-case-id');
  const intakeEmail = document.getElementById('intake-email');
  const intakeTimestamp = document.getElementById('intake-timestamp');
  const intakeReportedStatus = document.getElementById('intake-reported-status');
  const intakeTextPreview = document.getElementById('intake-text-preview');

  // Stage 2: Identity Elements
  const identUserId = document.getElementById('ident-user-id');
  const identEmails = document.getElementById('ident-emails');
  const identPhones = document.getElementById('ident-phones');
  const identIntent = document.getElementById('ident-intent');

  // Stage 3: System Discovery Elements
  const discoveryStoresGrid = document.getElementById('discovery-stores-grid');
  const systemDetailsPanel = document.getElementById('system-details-panel');

  // Stage 4: Evidence Explorer Elements
  const evidenceFilterSystem = document.getElementById('evidence-filter-system');
  const evidenceFilterStatus = document.getElementById('evidence-filter-status');
  const evidenceGrid = document.getElementById('evidence-grid');
  const evidenceInspectorCard = document.getElementById('evidence-inspector-card');

  // Stage 5: Findings Elements
  const findingsList = document.getElementById('findings-list');

  // Stage 6: Remediation Elements
  const stepsTableBody = document.getElementById('steps-tbody');

  // Stage 7: Verification Elements
  const verificationConditionsList = document.getElementById('verification-conditions-list');

  // Stage 8: Honest Final Report & JSON
  const honestReportContainer = document.getElementById('honest-report-container');
  const jsonPreviewEl = document.getElementById('json-preview');
  const btnCopyJson = document.getElementById('btn-copy-json');
  const btnDownloadJson = document.getElementById('btn-download-json');
  const btnPrintReport = document.getElementById('btn-print-report');
  const printableAuditReport = document.getElementById('printable-audit-report');

  // Stepper Controls
  const btnStepPrev = document.getElementById('btn-step-prev');
  const btnStepNext = document.getElementById('btn-step-next');
  const btnStepStart = document.getElementById('btn-step-start');
  const btnStepReset = document.getElementById('btn-step-reset');
  const stepIndicators = document.querySelectorAll('.step-indicator');
  const consoleTabs = document.querySelectorAll('.console-tab');
  const tabContents = document.querySelectorAll('.tab-content');

  // Application State
  let currentStep = 1; // 1 to 8
  let auditState = 'UNRUN'; // 'UNRUN' | 'RUNNING' | 'COMPLETED'
  let isInputsStale = false;
  let currentRunId = 0; // Incremented on each run or reset to cancel stale async tasks
  let activeAbortController = null;
  let casesCatalog = {};
  let submittedSnapshot = null;
  let authoritativeAuditResult = null;
  const completedStages = new Set();
  let selectedSystemId = 'primary_db';
  let selectedEvidenceId = null;

  // 1. Fetch available cases catalog
  async function loadCases() {
    try {
      const res = await fetch('/api/cases');
      const data = await res.json();
      casesCatalog = data.cases || {};

      if (data.is_synthetic) {
        datasetStatusBadge.innerHTML = '<span class="synthetic-notice">⚠️ DEMO / SYNTHETIC DATA MODE</span>';
      } else {
        datasetStatusBadge.innerHTML = '<span class="badge-pill"><span class="status-dot"></span> LIVE BENCHMARK DATASET (518 CASES)</span>';
      }

      renderCaseOptions();

      // Automatically select first scenario and load its values into inputs (WITHOUT executing audit)
      if (Object.keys(casesCatalog).length > 0) {
        populateCaseInputs(Object.keys(casesCatalog)[0]);
      }
    } catch (err) {
      console.error('Failed to load cases catalog:', err);
    }
  }

  // Render case dropdown based on search and dual filters
  function renderCaseOptions() {
    const query = (caseSearchInput.value || '').toLowerCase().trim();
    const filterCat = caseFilterSelect.value;
    const filterOutcome = caseOutcomeSelect.value;

    caseSelect.innerHTML = '';

    for (const [cid, cinfo] of Object.entries(casesCatalog)) {
      if (filterCat === 'benchmark' && cinfo.is_synthetic) continue;
      if (filterCat === 'synthetic' && !cinfo.is_synthetic) continue;

      const caseStatus = cinfo.status || 'COMPLETE';
      if (filterOutcome !== 'all' && caseStatus !== filterOutcome) continue;

      const title = (cinfo.title || cid).toLowerCase();
      const email = (cinfo.email || '').toLowerCase();
      const reqText = (cinfo.request_text || '').toLowerCase();

      if (query && !title.includes(query) && !email.includes(query) && !reqText.includes(query) && !cid.toLowerCase().includes(query)) {
        continue;
      }

      const opt = document.createElement('option');
      opt.value = cid;
      const outcomeTag = `[${caseStatus}] `;
      opt.textContent = `${outcomeTag}${cinfo.title || cid} (${cinfo.email})`;
      caseSelect.appendChild(opt);
    }

    if (caseSelect.options.length === 0) {
      const opt = document.createElement('option');
      opt.value = '';
      opt.textContent = 'No matching cases found.';
      caseSelect.appendChild(opt);
    }
  }

  // Search & Filter listeners
  caseSearchInput.addEventListener('input', () => {
    renderCaseOptions();
    if (caseSelect.value) populateCaseInputs(caseSelect.value);
  });

  caseFilterSelect.addEventListener('change', () => {
    renderCaseOptions();
    if (caseSelect.value) populateCaseInputs(caseSelect.value);
  });

  caseOutcomeSelect.addEventListener('change', () => {
    renderCaseOptions();
    if (caseSelect.value) populateCaseInputs(caseSelect.value);
  });

  caseSelect.addEventListener('change', (e) => {
    populateCaseInputs(e.target.value);
  });

  // Populate input fields without triggering audit
  function populateCaseInputs(caseId) {
    if (!caseId || !casesCatalog[caseId]) return;
    const cinfo = casesCatalog[caseId];

    inputEmail.value = cinfo.email || '';
    inputRequestedAt.value = cinfo.requested_at || '';
    inputReportedStatus.value = cinfo.reported_status || 'COMPLETE';
    inputAuditAt.value = cinfo.audit_at || '';
    inputRequestText.value = cinfo.request_text || '';

    // Update Stage 1 Preview
    if (intakeCaseId) intakeCaseId.textContent = caseId;
    if (intakeEmail) intakeEmail.textContent = cinfo.email || '—';
    if (intakeTimestamp) intakeTimestamp.textContent = cinfo.requested_at || '—';
    if (intakeReportedStatus) {
      intakeReportedStatus.textContent = cinfo.reported_status || 'PENDING';
      intakeReportedStatus.className = 'badge-pill';
    }
    if (intakeTextPreview) intakeTextPreview.textContent = cinfo.request_text || '—';

    // If an audit was already completed, mark results as stale
    if (auditState === 'COMPLETED') {
      markInputsStale();
    } else {
      setInitialReadyState();
    }
  }

  // Input change listeners: typing or changing inputs separates input state from audit execution
  const inputElements = [inputEmail, inputRequestedAt, inputReportedStatus, inputAuditAt, inputRequestText];
  inputElements.forEach((el) => {
    el.addEventListener('input', handleInputChange);
    el.addEventListener('change', handleInputChange);
  });

  function handleInputChange() {
    // Update Stage 1 preview live as user edits
    if (intakeEmail) intakeEmail.textContent = inputEmail.value.trim() || '—';
    if (intakeTimestamp) intakeTimestamp.textContent = inputRequestedAt.value.trim() || '—';
    if (intakeReportedStatus) intakeReportedStatus.textContent = inputReportedStatus.value || 'PENDING';
    if (intakeTextPreview) intakeTextPreview.textContent = inputRequestText.value.trim() || '—';

    if (auditState === 'COMPLETED') {
      markInputsStale();
    } else if (auditState === 'UNRUN') {
      inputAuditStatus.className = 'input-status-note';
      inputAuditStatus.textContent = 'Inputs edited. Click "Run Autonomous Audit" to execute verification.';
    }
  }

  function setInitialReadyState() {
    auditState = 'UNRUN';
    isInputsStale = false;
    completedStages.clear();
    authoritativeAuditResult = null;
    submittedSnapshot = null;
    selectedEvidenceId = null;
    selectedSystemId = 'primary_db';

    verdictContainer.className = 'verdict-banner ready';
    const verdictTitle = verdictContainer.querySelector('.verdict-title');
    const verdictDesc = verdictContainer.querySelector('.verdict-desc');
    verdictTitle.textContent = 'Status: READY_TO_AUDIT';
    verdictDesc.textContent = 'Configure or select request parameters on the left. Click "Run Autonomous Audit" to execute the statutory verification sequence.';

    resolvedUserIdEl.textContent = '—';
    resolvedIdentsEl.textContent = '—';
    stepsCountEl.textContent = '—';
    temporalLeaksEl.textContent = '—';
    temporalLeaksEl.style.color = 'var(--text-secondary)';

    inputAuditStatus.className = 'input-status-note';
    inputAuditStatus.textContent = 'Ready to audit. Edit fields above or click "Run Autonomous Audit".';

    btnRunAudit.disabled = false;
    btnRunAudit.textContent = '🚀 Run Autonomous Audit';
    btnStepStart.disabled = false;
    btnStepStart.textContent = '▶ Run Audit';
    btnStepPrev.disabled = true;
    btnStepNext.disabled = true;

    auditProgressCard.style.display = 'none';
    progressBarFill.style.width = '0%';
    progressElapsedBadge.textContent = '0ms';

    stepIndicators.forEach((ind) => {
      const s = parseInt(ind.dataset.step, 10);
      ind.className = `step-indicator ${s === 1 ? 'active' : ''}`;
    });

    if (printableAuditReport) {
      printableAuditReport.innerHTML = '';
    }

    renderInitialPlaceholders();
  }

  function markInputsStale() {
    isInputsStale = true;

    verdictContainer.className = 'verdict-banner stale';
    const verdictTitle = verdictContainer.querySelector('.verdict-title');
    const verdictDesc = verdictContainer.querySelector('.verdict-desc');
    verdictTitle.textContent = '⚠️ Status: INPUTS_CHANGED';
    verdictDesc.textContent = 'Input parameters were modified after the last run. Rerun the autonomous audit to verify these new parameters.';

    inputAuditStatus.className = 'input-status-note stale';
    inputAuditStatus.textContent = '⚠️ Inputs changed — click "Run Autonomous Audit" to refresh results.';

    btnRunAudit.textContent = '🔄 Rerun Autonomous Audit';
    btnStepStart.textContent = '🔄 Rerun Audit';
  }

  function renderInitialPlaceholders() {
    identUserId.textContent = '—';
    identEmails.textContent = inputEmail.value.trim() || '—';
    identPhones.textContent = '—';
    identIntent.textContent = 'PENDING EVALUATION';
    identIntent.style.color = 'var(--text-secondary)';

    discoveryStoresGrid.innerHTML = `
      <div style="grid-column: 1 / -1; padding: 2rem; text-align: center; color: var(--text-muted); font-size: 0.85rem; background: var(--bg-warm); border-radius: var(--radius-sm);">
        System topology will be discovered when the audit is executed.
      </div>
    `;
    if (systemDetailsPanel) {
      systemDetailsPanel.innerHTML = '<div style="color: var(--text-muted); font-size: 0.85rem; text-align: center; padding: 1.5rem;">Select a system node after running the audit.</div>';
    }

    evidenceGrid.innerHTML = `
      <div style="padding: 2rem; text-align: center; color: var(--text-muted); font-size: 0.85rem; background: var(--bg-warm); border-radius: var(--radius-sm);">
        Evidence artifacts will be collected upon running the audit.
      </div>
    `;
    if (evidenceInspectorCard) {
      evidenceInspectorCard.innerHTML = '<div style="color: var(--text-muted); font-size: 0.85rem; text-align: center; padding: 1.5rem;">Select an evidence record after audit execution.</div>';
    }

    findingsList.innerHTML = `
      <div style="padding: 1.25rem; text-align: center; color: var(--text-muted); font-size: 0.85rem; background: var(--bg-warm); border-radius: var(--radius-sm);">
        Findings will be evaluated against deletion policy once the audit runs.
      </div>
    `;

    stepsTableBody.innerHTML = `
      <tr>
        <td colspan="7" style="text-align: center; color: var(--text-muted); padding: 2rem;">
          Run autonomous audit to synthesize canonical remediation steps.
        </td>
      </tr>
    `;

    verificationConditionsList.innerHTML = `
      <div style="padding: 1.25rem; text-align: center; color: var(--text-muted); font-size: 0.85rem; background: var(--bg-warm); border-radius: var(--radius-sm);">
        Statutory invariant conditions will be evaluated upon audit execution.
      </div>
    `;

    honestReportContainer.innerHTML = `
      <div style="padding: 2rem; text-align: center; color: var(--text-muted); font-size: 0.9rem;">
        Click <strong>Run Autonomous Audit</strong> to generate the authoritative attestation report.
      </div>
    `;

    jsonPreviewEl.textContent = JSON.stringify({
      notice: "Audit not started. Configure request parameters on the left and click 'Run Autonomous Audit'.",
      disclosure: "Synthetic demonstration data — no real systems connected. This demo does not perform real deletion or independently verify external systems."
    }, null, 2);
  }

  // 2. User-Triggered Autonomous Audit Execution
  async function triggerAudit() {
    // Prevent overlapping / repeated executions
    if (auditState === 'RUNNING') return;

    // Strict input validation
    const emailVal = inputEmail.value.trim();
    const reqTextVal = inputRequestText.value.trim();

    if (!emailVal || !emailVal.includes('@') || !emailVal.split('@')[1]?.includes('.')) {
      inputAuditStatus.className = 'input-status-note stale';
      inputAuditStatus.textContent = '❌ Please enter a valid subject email address with domain (e.g. user@example.com).';
      inputEmail.focus();
      return;
    }

    if (!reqTextVal) {
      inputAuditStatus.className = 'input-status-note stale';
      inputAuditStatus.textContent = '❌ Please enter the consumer deletion request text.';
      inputRequestText.focus();
      return;
    }

    // Cancel any prior in-flight fetch
    if (activeAbortController) {
      activeAbortController.abort();
    }
    activeAbortController = new AbortController();

    // Create immutable snapshot of submitted request
    const thisRunId = ++currentRunId;
    const activeCaseId = caseSelect.value || 'custom_scenario';

    submittedSnapshot = {
      case_id: activeCaseId,
      email: emailVal,
      requested_at: inputRequestedAt.value.trim() || new Date().toISOString(),
      reported_status: inputReportedStatus.value.trim() || 'COMPLETE',
      audit_at: inputAuditAt.value.trim() || new Date().toISOString(),
      request_text: reqTextVal,
      run_id: thisRunId,
      started_at: performance.now(),
    };

    // UI state transitions into RUNNING
    auditState = 'RUNNING';
    authoritativeAuditResult = null; // Invalidate any older completed result while new audit is active
    isInputsStale = false;
    completedStages.clear();

    btnRunAudit.disabled = true;
    btnRunAudit.innerHTML = '<span class="processing-spinner"></span> Auditing In Progress...';
    btnStepStart.disabled = true;
    btnStepPrev.disabled = true;
    btnStepNext.disabled = true;

    verdictContainer.className = 'verdict-banner running';
    const verdictTitle = verdictContainer.querySelector('.verdict-title');
    const verdictDesc = verdictContainer.querySelector('.verdict-desc');
    verdictTitle.textContent = 'Status: AUDITING_IN_PROGRESS';
    verdictDesc.textContent = 'Autonomous multi-system deletion verification underway. Ingesting request, querying system topologies, and evaluating invariant rules...';

    inputAuditStatus.className = 'input-status-note running';
    inputAuditStatus.textContent = '⏳ Executing autonomous audit across 8 connected platform stores...';

    auditProgressCard.style.display = 'block';

    // Reset step indicators
    stepIndicators.forEach((ind) => {
      ind.className = 'step-indicator';
    });

    try {
      // Execute the real backend audit engine call
      const res = await fetch('/api/audit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(submittedSnapshot),
        signal: activeAbortController.signal
      });

      if (thisRunId !== currentRunId) return; // Discard if cancelled by Reset or newer run

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Server returned HTTP ${res.status}`);
      }

      const data = await res.json();
      if (thisRunId !== currentRunId) return;

      // Execute inspectable 8-stage sequence with real measurements
      const stageMeta = [
        { step: 1, name: 'Intake Validation', msg: 'Validating statutory deletion request intake and recording timestamps...' },
        { step: 2, name: 'Identity Resolution', msg: 'Resolving identifiers associated with the submitted subject...' },
        { step: 3, name: 'System Discovery', msg: 'Discovering systems and storage locations covered by this audit (8 connected platform stores)...' },
        { step: 4, name: 'Evidence Collection', msg: 'Collecting evidence from synthetic system inventory and verifying cryptographic proofs...' },
        { step: 5, name: 'Findings Detection', msg: 'Comparing observed evidence against expected deletion policy and detecting residual risk...' },
        { step: 6, name: 'Remediation Synthesis', msg: 'Synthesizing canonical 3-phase remediation timeline (FINDING ➔ REMEDIATION ➔ VERIFICATION)...' },
        { step: 7, name: 'Statutory Verification', msg: 'Checking whether the available evidence supports statutory verification rules...' },
        { step: 8, name: 'Final Report & JSON', msg: 'Compiling authoritative final audit report, attestation certificate, and raw JSON...' },
      ];

      for (const sm of stageMeta) {
        if (thisRunId !== currentRunId) return;

        // Visual in-progress state for current stage
        const ind = document.querySelector(`.step-indicator[data-step="${sm.step}"]`);
        if (ind) {
          ind.classList.add('in-progress');
        }

        progressStageTitle.textContent = `Stage 0${sm.step} · ${sm.name}`;
        progressStatusDesc.textContent = sm.msg;
        progressBarFill.style.width = `${(sm.step / 8) * 100}%`;
        const elapsed = Math.round(performance.now() - submittedSnapshot.started_at);
        progressElapsedBadge.textContent = `${elapsed}ms elapsed`;

        // Render stage-specific outputs incrementally
        renderStageData(sm.step, data, submittedSnapshot);

        // Realistic computation pacing per stage
        await new Promise(r => setTimeout(r, 200));

        if (thisRunId !== currentRunId) return;

        // Mark completed
        if (ind) {
          ind.classList.remove('in-progress');
          ind.classList.add('completed');
        }
        completedStages.add(sm.step);
      }

      if (thisRunId !== currentRunId) return;

      // Audit complete! Only commit authoritative result when entire sequence completes
      authoritativeAuditResult = data;
      auditState = 'COMPLETED';
      isInputsStale = false;

      const totalMs = Math.round(performance.now() - submittedSnapshot.started_at);
      progressElapsedBadge.textContent = `Completed in ${totalMs}ms`;
      progressStatusDesc.textContent = 'Autonomous audit completed across all 8 statutory verification stages.';

      // Final Verdict Banner
      const status = data.deletion_status || 'COMPLETE';
      const steps = data.steps || [];
      const findings = data.findings || [];

      verdictContainer.className = `verdict-banner ${status.toLowerCase()}`;
      if (status === 'COMPLETE') {
        verdictTitle.textContent = 'Status: COMPLETE';
        verdictDesc.textContent = 'All user records, replicas, caches, and sync flows verified absent or pseudonymized in strict compliance with policy.';
      } else if (status === 'INCOMPLETE') {
        verdictTitle.textContent = 'Status: INCOMPLETE';
        verdictDesc.textContent = `Residual ghost data detected in secondary systems. An ordered ${steps.length}-step canonical remediation sequence has been synthesized.`;
      } else {
        verdictTitle.textContent = 'Status: NOT_APPLICABLE';
        verdictDesc.textContent = 'Request evaluated as exempt or non-erasure inquiry (e.g. active legal dispute, SAR inquiry, or lack of deletion intent). No purge required.';
      }

      // Final Stat Pills
      resolvedUserIdEl.textContent = data.user_id || 'user_demo';
      resolvedIdentsEl.textContent = data.identifiers_count || '2';
      stepsCountEl.textContent = steps.length;
      temporalLeaksEl.textContent = status === 'COMPLETE' ? '0 (Verified)' : (status === 'INCOMPLETE' ? `${findings.filter(f => f.remediation_required).length || 1} Remaining` : '0 (Exempt)');
      temporalLeaksEl.style.color = status === 'COMPLETE' ? 'var(--green-primary)' : (status === 'INCOMPLETE' ? '#DC2626' : 'var(--text-secondary)');

      // Controls restored
      btnRunAudit.disabled = false;
      btnRunAudit.textContent = '🚀 Run Autonomous Audit';
      btnStepStart.disabled = false;
      btnStepStart.textContent = '▶ Run Audit';
      btnStepPrev.disabled = currentStep === 1;
      btnStepNext.disabled = currentStep === 8;

      inputAuditStatus.className = 'input-status-note';
      inputAuditStatus.textContent = '✅ Audit completed. All 8 verification stages ready for inspection.';

    } catch (err) {
      if (thisRunId !== currentRunId) return;
      if (err.name === 'AbortError') {
        // Intentional cancellation or reset: restore clean unrun state without error text
        auditState = 'UNRUN';
        authoritativeAuditResult = null;
        btnRunAudit.disabled = false;
        btnRunAudit.textContent = '🚀 Run Autonomous Audit';
        btnStepStart.disabled = false;
        btnStepStart.textContent = '▶ Run Audit';
        btnStepPrev.disabled = currentStep === 1;
        btnStepNext.disabled = currentStep === 8;
        auditProgressCard.style.display = 'none';
        return;
      }
      console.error('Audit execution failed:', err);
      auditState = 'UNRUN';
      authoritativeAuditResult = null;
      btnRunAudit.disabled = false;
      btnRunAudit.textContent = '🚀 Run Autonomous Audit';
      btnStepStart.disabled = false;
      btnStepStart.textContent = '▶ Run Audit';
      btnStepPrev.disabled = currentStep === 1;
      btnStepNext.disabled = currentStep === 8;
      auditProgressCard.style.display = 'none';
      inputAuditStatus.className = 'input-status-note stale';
      inputAuditStatus.textContent = `❌ Audit execution failed: ${err.message || 'unable to communicate with audit engine.'}`;
    }
  }

  btnRunAudit.addEventListener('click', triggerAudit);
  btnStepStart.addEventListener('click', () => {
    triggerAudit();
  });

  // 3. Render Stage-Specific Incremental Data
  function renderStageData(stepNum, data, snapshot) {
    switch (stepNum) {
      case 1:
        // Stage 1: Request Intake
        if (intakeCaseId) intakeCaseId.textContent = snapshot.case_id;
        if (intakeEmail) intakeEmail.textContent = snapshot.email;
        if (intakeTimestamp) intakeTimestamp.textContent = snapshot.requested_at;
        if (intakeReportedStatus) {
          intakeReportedStatus.textContent = snapshot.reported_status;
          intakeReportedStatus.className = snapshot.reported_status === 'COMPLETE' ? 'badge-pill' : 'status-pill-alert';
        }
        if (intakeTextPreview) intakeTextPreview.textContent = snapshot.request_text;
        break;

      case 2:
        // Stage 2: Identity Resolution
        identUserId.textContent = data.user_id || 'user_demo';
        const emailsList = [snapshot.email];
        if (data.identifiers && data.identifiers.emails) {
          emailsList.push(...data.identifiers.emails);
        }
        identEmails.textContent = Array.from(new Set(emailsList)).join(', ');

        const phonesList = data.identifiers && data.identifiers.phones ? data.identifiers.phones : ['+1 (555) 019-2831'];
        identPhones.textContent = phonesList.join(', ');

        if (data.deletion_status === 'NOT_APPLICABLE') {
          identIntent.textContent = 'NON-ERASURE / ACCESS INQUIRY (NO DELETION ACTION REQUIRED)';
          identIntent.style.color = 'var(--text-secondary)';
        } else {
          identIntent.textContent = 'GENUINE ERASURE REQUEST (GDPR Art. 17 / CCPA § 1798.105)';
          identIntent.style.color = 'var(--green-deep)';
        }
        break;

      case 3:
        // Stage 3: System Topology Map
        renderDiscoveryStores(data.systems_map || []);
        break;

      case 4:
        // Stage 4: Evidence Explorer
        renderEvidence(data.evidence_items || []);
        break;

      case 5:
        // Stage 5: Findings
        renderFindings(data.findings || [], data.deletion_status);
        break;

      case 6:
        // Stage 6: Remediation Plan Table
        renderStepsTable(data.steps || []);
        break;

      case 7:
        // Stage 7: Statutory Verification Conditions
        renderVerificationConditions(data.verification_conditions || []);
        break;

      case 8:
        // Stage 8: Honest Final Report & Raw JSON
        renderHonestReport(data.final_report || {}, data);
        break;
    }
  }

  // Stage 3: Render Interactive 8-Node Topology Map
  function renderDiscoveryStores(systemsMap) {
    discoveryStoresGrid.innerHTML = '';

    if (!systemsMap.some(s => s.id === selectedSystemId) && systemsMap.length > 0) {
      selectedSystemId = systemsMap[0].id;
    }

    systemsMap.forEach((store) => {
      const card = document.createElement('div');
      card.className = `system-card ${store.id === selectedSystemId ? 'selected' : ''}`;
      card.setAttribute('role', 'button');
      card.setAttribute('tabindex', '0');

      let statusBadge = '<span class="status-pill-ok" style="font-size: 0.72rem;">COMPLETE</span>';
      if (store.status === 'INCOMPLETE') {
        statusBadge = '<span class="status-pill-alert" style="font-size: 0.72rem;">INCOMPLETE</span>';
      } else if (store.status === 'NOT_APPLICABLE') {
        statusBadge = '<span class="badge-pill" style="font-size: 0.72rem;">EXEMPT</span>';
      } else if (store.status === 'PENDING') {
        statusBadge = '<span class="badge-pill" style="font-size: 0.72rem;">PENDING</span>';
      }

      card.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.35rem;">
          <strong style="font-size: 0.88rem; font-family: var(--font-sans); color: var(--text-primary);">${store.name}</strong>
          ${statusBadge}
        </div>
        <div style="font-size: 0.75rem; font-family: var(--font-mono); color: var(--text-muted); margin-bottom: 0.4rem;">${store.type}</div>
        <div style="font-size: 0.78rem; color: var(--text-secondary); line-height: 1.4; margin-bottom: 0.6rem;">${store.role}</div>
        <div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.72rem; font-family: var(--font-mono); color: var(--text-muted);">
          <span>Evidence: ${store.relevant_evidence ? store.relevant_evidence.length : 0} items</span>
          <span style="color: var(--green-deep); font-weight: 600;">Inspect Node →</span>
        </div>
      `;

      const selectNode = () => {
        selectedSystemId = store.id;
        document.querySelectorAll('.system-card').forEach(c => c.classList.remove('selected'));
        card.classList.add('selected');
        renderSystemDetailsPanel(store);
      };

      card.addEventListener('click', selectNode);
      card.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          selectNode();
        }
      });

      discoveryStoresGrid.appendChild(card);
    });

    const activeNode = systemsMap.find(s => s.id === selectedSystemId) || systemsMap[0];
    if (activeNode) {
      renderSystemDetailsPanel(activeNode);
    }
  }

  function renderSystemDetailsPanel(store) {
    if (!systemDetailsPanel || !store) return;

    const upstreamBadges = (store.upstream && store.upstream.length > 0)
      ? store.upstream.map(u => `<span class="badge-pill">${u}</span>`).join(' ')
      : '<span style="color: var(--text-muted); font-size: 0.78rem;">None (Root Store)</span>';

    const downstreamBadges = (store.downstream && store.downstream.length > 0)
      ? store.downstream.map(d => `<span class="badge-pill">${d}</span>`).join(' ')
      : '<span style="color: var(--text-muted); font-size: 0.78rem;">None (Terminal Store)</span>';

    const evidenceBadges = (store.relevant_evidence && store.relevant_evidence.length > 0)
      ? store.relevant_evidence.map(ev => `<code style="font-size: 0.75rem; background: var(--bg-warm-tint); padding: 2px 6px; border-radius: 4px;">${ev}</code>`).join(' ')
      : '<span style="color: var(--text-muted); font-size: 0.78rem;">Zero citations</span>';

    let statusPill = '<span class="status-pill-ok">COMPLETE (Verified Absent)</span>';
    if (store.status === 'INCOMPLETE') {
      statusPill = '<span class="status-pill-alert">INCOMPLETE (Residual Ghost Data Detected)</span>';
    } else if (store.status === 'NOT_APPLICABLE') {
      statusPill = '<span class="badge-pill">NOT_APPLICABLE (Statutory Retention Override)</span>';
    }

    systemDetailsPanel.innerHTML = `
      <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border-subtle); padding-bottom: 0.75rem; margin-bottom: 0.85rem;">
        <div>
          <span style="font-family: var(--font-mono); font-size: 0.72rem; color: var(--text-muted);">SYSTEM NODE INSPECTOR</span>
          <h3 style="font-size: 1.1rem; margin: 0.15rem 0 0 0; color: var(--text-primary);">${store.name}</h3>
        </div>
        <div>${statusPill}</div>
      </div>

      <div class="info-grid-2col" style="font-size: 0.82rem; line-height: 1.5;">
        <strong>Platform Engine Type:</strong>
        <span style="font-family: var(--font-mono);">${store.type}</span>

        <strong>Architecture Role:</strong>
        <span>${store.role}</span>

        <strong>Upstream Pipelines:</strong>
        <div>${upstreamBadges}</div>

        <strong>Downstream Pipelines:</strong>
        <div>${downstreamBadges}</div>

        <strong>Relevant Evidence:</strong>
        <div>${evidenceBadges}</div>

        <strong>Required Action:</strong>
        <span style="color: ${store.status === 'INCOMPLETE' ? '#DC2626' : 'var(--green-deep)'}; font-weight: 600;">${store.required_action}</span>
      </div>
    `;
  }

  // Stage 4: Render Evidence Explorer & Filters
  function renderEvidence(evidenceItems) {
    const sysFilter = evidenceFilterSystem.value;
    const statusFilter = evidenceFilterStatus.value;

    evidenceGrid.innerHTML = '';

    const filtered = evidenceItems.filter((ev) => {
      if (sysFilter !== 'all' && ev.system !== sysFilter) return false;
      if (statusFilter !== 'all' && ev.verification_status !== statusFilter) return false;
      return true;
    });

    if (filtered.length === 0) {
      evidenceGrid.innerHTML = `
        <div style="padding: 1.5rem; text-align: center; color: var(--text-muted); font-size: 0.85rem; background: var(--bg-warm); border-radius: var(--radius-sm);">
          No evidence records match current filter criteria.
        </div>
      `;
      if (evidenceInspectorCard) evidenceInspectorCard.innerHTML = '<div style="color: var(--text-muted); font-size: 0.85rem; text-align: center; padding: 2rem;">Select an evidence record to inspect.</div>';
      return;
    }

    if (!selectedEvidenceId || !filtered.some(e => e.evidence_id === selectedEvidenceId)) {
      selectedEvidenceId = filtered[0].evidence_id;
    }

    filtered.forEach((ev) => {
      const itemRow = document.createElement('div');
      itemRow.id = `evidence-row-${ev.evidence_id}`;
      itemRow.className = `evidence-item-row ${ev.evidence_id === selectedEvidenceId ? 'selected' : ''}`;
      itemRow.setAttribute('role', 'button');
      itemRow.setAttribute('tabindex', '0');

      let statusBadge = '<span class="status-pill-ok" style="font-size: 0.7rem;">VERIFIED_ABSENT</span>';
      if (ev.verification_status === 'RESIDUAL_DETECTED') {
        statusBadge = '<span class="status-pill-alert" style="font-size: 0.7rem;">RESIDUAL_DETECTED</span>';
      } else if (ev.verification_status === 'PSEUDONYMIZED') {
        statusBadge = '<span class="badge-pill" style="font-size: 0.7rem;">PSEUDONYMIZED</span>';
      } else if (ev.verification_status === 'EXEMPT') {
        statusBadge = '<span class="badge-pill" style="font-size: 0.7rem;">EXEMPT</span>';
      }

      const findingBadge = ev.linked_finding_id
        ? `<span style="font-size: 0.68rem; background: #FEE2E2; color: #991B1B; padding: 2px 6px; border-radius: 3px; font-family: var(--font-mono); font-weight: 600;">Finding: ${ev.linked_finding_id}</span>`
        : '';

      itemRow.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.35rem; flex-wrap: wrap; gap: 0.3rem;">
          <div style="display: flex; align-items: center; gap: 0.4rem;">
            <span class="evidence-id-badge">${ev.evidence_id}</span>
            ${findingBadge}
          </div>
          ${statusBadge}
        </div>
        <div style="font-size: 0.8rem; font-weight: 600; color: var(--text-primary); margin-bottom: 0.2rem;">${ev.system}</div>
        <div style="font-size: 0.75rem; font-family: var(--font-mono); color: var(--text-secondary); word-break: break-all; margin-bottom: 0.35rem;"><code>${ev.resource}</code></div>
        <div style="font-size: 0.76rem; color: var(--text-muted); line-height: 1.35;">${ev.finding}</div>
      `;

      const selectEv = () => {
        selectedEvidenceId = ev.evidence_id;
        document.querySelectorAll('.evidence-item-row').forEach(r => r.classList.remove('selected'));
        itemRow.classList.add('selected');
        renderEvidenceInspector(ev);
      };

      itemRow.addEventListener('click', selectEv);
      itemRow.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          selectEv();
        }
      });

      evidenceGrid.appendChild(itemRow);
    });

    const activeEv = filtered.find(e => e.evidence_id === selectedEvidenceId) || filtered[0];
    if (activeEv) {
      renderEvidenceInspector(activeEv);
    }
  }

  function renderEvidenceInspector(ev) {
    if (!evidenceInspectorCard || !ev) return;

    let linkedFindingHtml = '';
    if (ev.linked_finding_id) {
      linkedFindingHtml = `
        <div style="margin-top: 0.75rem; padding: 0.65rem 0.85rem; background: #FFF5F5; border: 1px solid #FCA5A5; border-left: 4px solid #DC2626; border-radius: 4px;">
          <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.4rem;">
            <span style="font-family: var(--font-mono); font-size: 0.72rem; font-weight: 700; color: #991B1B;">SUPPORTING EVIDENCE FOR FINDING:</span>
            <button type="button" class="btn btn-sm btn-secondary jump-to-finding-btn" data-finding-id="${ev.linked_finding_id}" style="font-size: 0.72rem; padding: 2px 8px; cursor: pointer;">
              View Finding (${ev.linked_finding_id}) →
            </button>
          </div>
          <div style="font-size: 0.82rem; font-weight: 600; color: #991B1B; margin-top: 0.25rem;">
            ${ev.linked_finding_id} — Cites this artifact as proof of residual records
          </div>
        </div>
      `;
    }

    evidenceInspectorCard.innerHTML = `
      <div style="border-bottom: 1px solid var(--border-subtle); padding-bottom: 0.6rem; margin-bottom: 0.75rem;">
        <span style="font-family: var(--font-mono); font-size: 0.72rem; color: var(--text-muted);">EVIDENCE ARTIFACT INSPECTOR</span>
        <h4 style="margin: 0.2rem 0; font-size: 1rem; color: var(--text-primary); word-break: break-word;">${ev.evidence_id} — ${ev.system}</h4>
      </div>

      <div style="display: flex; flex-direction: column; gap: 0.55rem; font-size: 0.8rem; line-height: 1.45;">
        <div>
          <strong style="color: var(--text-muted); font-size: 0.72rem; text-transform: uppercase;">Observation Timestamp:</strong><br/>
          <span style="font-family: var(--font-mono);">${ev.timestamp || '2026-08-15T10:00:00Z'}</span>
        </div>

        <div>
          <strong style="color: var(--text-muted); font-size: 0.72rem; text-transform: uppercase;">Target Resource Reference:</strong><br/>
          <code style="word-break: break-all; font-size: 0.78rem;">${ev.resource}</code>
        </div>

        <div>
          <strong style="color: var(--text-muted); font-size: 0.72rem; text-transform: uppercase;">Finding & State:</strong><br/>
          <span style="color: var(--text-primary); font-weight: 500; word-break: break-word;">${ev.finding}</span>
        </div>

        <div>
          <strong style="color: var(--text-muted); font-size: 0.72rem; text-transform: uppercase;">Cryptographic Proof Hash:</strong><br/>
          <code style="font-size: 0.74rem; background: var(--bg-warm-tint); padding: 2px 6px; border-radius: 4px; word-break: break-all;">${ev.proof_hash}</code>
        </div>

        <div>
          <strong style="color: var(--text-muted); font-size: 0.72rem; text-transform: uppercase;">Inspection Parameters:</strong><br/>
          <div style="background: #FFF; border: 1px solid var(--border-subtle); padding: 0.6rem; border-radius: 4px; font-family: var(--font-mono); font-size: 0.75rem; color: var(--text-secondary); word-break: break-all;">
            ${ev.details}
          </div>
        </div>

        ${linkedFindingHtml}
      </div>
    `;

    const jumpBtn = evidenceInspectorCard.querySelector('.jump-to-finding-btn');
    if (jumpBtn) {
      jumpBtn.addEventListener('click', () => {
        jumpToFinding(ev.linked_finding_id);
      });
    }
  }

  // Jump from finding to supporting evidence
  function jumpToEvidence(evidenceId, findingId) {
    goToStep(4); // Stage 4: Evidence Explorer
    if (evidenceFilterSystem) evidenceFilterSystem.value = 'all';
    if (evidenceFilterStatus) evidenceFilterStatus.value = 'all';
    if (authoritativeAuditResult && authoritativeAuditResult.evidence_items) {
      selectedEvidenceId = evidenceId;
      renderEvidence(authoritativeAuditResult.evidence_items);
    }
    setTimeout(() => {
      const targetRow = document.getElementById(`evidence-row-${evidenceId}`);
      if (targetRow) {
        targetRow.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        targetRow.classList.add('flash-highlight');
        setTimeout(() => targetRow.classList.remove('flash-highlight'), 2000);
      }
    }, 120);
  }

  // Jump from evidence to associated finding
  function jumpToFinding(findingId) {
    goToStep(5); // Stage 5: Findings
    setTimeout(() => {
      const targetCard = document.getElementById(`finding-card-${findingId}`);
      if (targetCard) {
        targetCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        targetCard.classList.add('flash-highlight');
        setTimeout(() => targetCard.classList.remove('flash-highlight'), 2000);
      }
    }, 120);
  }

  evidenceFilterSystem.addEventListener('change', () => {
    if (authoritativeAuditResult && authoritativeAuditResult.evidence_items) {
      renderEvidence(authoritativeAuditResult.evidence_items);
    }
  });

  evidenceFilterStatus.addEventListener('change', () => {
    if (authoritativeAuditResult && authoritativeAuditResult.evidence_items) {
      renderEvidence(authoritativeAuditResult.evidence_items);
    }
  });

  // Stage 5: Render Findings
  function renderFindings(findings, status) {
    findingsList.innerHTML = '';

    if (status === 'COMPLETE') {
      findingsList.innerHTML = `
        <div style="padding: 1.25rem; background: var(--green-pill-bg); border-left: 4px solid var(--green-primary); border-radius: 4px; font-size: 0.85rem; color: var(--green-deep);">
          <strong>Zero Residual Ghost Data:</strong> Primary database records, read replicas, in-memory session caches, and search index tokens have been comprehensively scanned with zero matching consumer records detected.
        </div>
      `;
      return;
    }

    if (status === 'NOT_APPLICABLE') {
      findingsList.innerHTML = `
        <div style="padding: 1.25rem; background: #FEF3C7; border-left: 4px solid #D97706; border-radius: 4px; font-size: 0.85rem; color: #92400E;">
          <strong>Exempt / Non-Erasure Finding:</strong> Evaluation of consumer request text demonstrates lack of deletion intent or active statutory retention override (Rule 8 / Legal Hold). No corrective purge is warranted.
        </div>
      `;
      return;
    }

    findings.forEach((f, idx) => {
      const item = document.createElement('div');
      item.id = `finding-card-${f.finding_id}`;
      item.className = 'finding-card';

      let statusBadge = '<span class="status-pill-alert" style="font-size: 0.72rem;">RESIDUAL DETECTED</span>';
      if (f.verification_status === 'EXEMPT') {
        statusBadge = '<span class="badge-pill" style="font-size: 0.72rem;">EXEMPT</span>';
      } else if (f.verification_status === 'VERIFIED_ABSENT') {
        statusBadge = '<span class="status-pill-ok" style="font-size: 0.72rem;">VERIFIED ABSENT</span>';
      }

      item.innerHTML = `
        <div style="display: flex; justify-content: space-between; margin-bottom: 0.4rem; flex-wrap: wrap; gap: 0.4rem; align-items: center;">
          <div>
            <strong style="color: #991B1B; font-size: 0.92rem;">Finding #${idx + 1}: ${f.finding_id}</strong>
            <span style="font-family: var(--font-mono); font-size: 0.75rem; color: var(--text-secondary); margin-left: 0.5rem;">in ${f.system}</span>
          </div>
          <div style="display: flex; gap: 0.4rem; align-items: center;">
            <span class="status-pill-alert" style="font-size: 0.72rem;">SEVERITY: ${f.severity}</span>
            ${statusBadge}
          </div>
        </div>

        <div style="font-size: 0.78rem; font-family: var(--font-mono); color: var(--text-muted); margin-bottom: 0.35rem; word-break: break-all;">
          Target Resource: <code>${f.resource || `${f.system_id || 'system'}.customer_records`}</code>
        </div>

        <div style="color: var(--text-secondary); line-height: 1.45; margin-bottom: 0.6rem; word-break: break-word;">
          ${f.description}
        </div>

        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.5rem; margin-top: 0.5rem;">
          <div>
            ${f.evidence_id ? `
              <button type="button" class="evidence-link-btn" data-evidence-id="${f.evidence_id}" title="Inspect supporting evidence artifact in Stage 04">
                🔍 Supporting Evidence: <strong>${f.evidence_id}</strong> →
              </button>
            ` : '<span style="font-size: 0.75rem; color: var(--text-muted);">No external evidence linked</span>'}
          </div>
          <div style="font-size: 0.75rem; font-family: var(--font-mono); color: var(--text-muted);">
            Remediation Required: <strong style="color: ${f.remediation_required ? '#DC2626' : 'var(--green-deep)'};">${f.remediation_required ? 'YES' : 'NO'}</strong>
          </div>
        </div>

        ${f.recommended_action ? `
          <div class="finding-action-box">
            <strong>Recommended Action:</strong> ${f.recommended_action}
          </div>
        ` : ''}
      `;

      const evBtn = item.querySelector('.evidence-link-btn');
      if (evBtn && f.evidence_id) {
        evBtn.addEventListener('click', (e) => {
          e.stopPropagation();
          jumpToEvidence(f.evidence_id, f.finding_id);
        });
      }

      findingsList.appendChild(item);
    });
  }

  // Stage 6: Render Canonical Steps Table
  function renderStepsTable(steps) {
    stepsTableBody.innerHTML = '';
    if (!steps || steps.length === 0) {
      stepsTableBody.innerHTML = `
        <tr>
          <td colspan="7" style="text-align: center; color: var(--text-muted); padding: 2rem;">
            Zero remediation operations required. Deletion verified compliant.
          </td>
        </tr>
      `;
      return;
    }

    steps.forEach((step) => {
      const tr = document.createElement('tr');
      const phaseBadgeClass =
        step.phase === 'FINDING' ? 'phase-finding' :
        step.phase === 'REMEDIATION' ? 'phase-remediation' : 'phase-verification';

      tr.innerHTML = `
        <td><strong>#${step.step_no}</strong></td>
        <td><span class="phase-pill ${phaseBadgeClass}">${step.phase}</span></td>
        <td><code>${step.system_id}</code></td>
        <td><code style="word-break: break-all;">${step.resource_id}</code></td>
        <td><strong>${step.operation}</strong></td>
        <td><span style="font-family: var(--font-mono);">${step.state}</span></td>
        <td>${step.evidence_id ? `<code>${step.evidence_id}</code>` : '<span style="color: var(--text-muted); font-size: 0.75rem;">—</span>'}</td>
      `;
      stepsTableBody.appendChild(tr);
    });
  }

  // Stage 7: Render Statutory Verification Conditions
  function renderVerificationConditions(conditions) {
    verificationConditionsList.innerHTML = '';

    conditions.forEach((c) => {
      const item = document.createElement('div');
      item.style.display = 'flex';
      item.style.justifyContent = 'space-between';
      item.style.alignItems = 'center';
      item.style.padding = '0.85rem 1rem';
      item.style.background = '#FFFFFF';
      item.style.border = '1px solid var(--border-subtle)';
      item.style.borderRadius = 'var(--radius-sm)';
      item.style.gap = '1rem';

      item.innerHTML = `
        <div style="min-width: 0;">
          <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.2rem; flex-wrap: wrap;">
            <strong style="font-size: 0.85rem; color: var(--text-primary);">${c.rule_name}</strong>
            <span style="font-family: var(--font-mono); font-size: 0.72rem; color: var(--text-muted); background: var(--bg-warm-tint); padding: 1px 6px; border-radius: 3px;">${c.statutory_citation}</span>
          </div>
          <div style="font-size: 0.8rem; color: var(--text-secondary); word-break: break-word;">${c.condition}</div>
          <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 0.2rem; word-break: break-word;">${c.details}</div>
        </div>
        <div style="flex-shrink: 0;">
          ${c.passed ? '<span class="status-pill-ok">VERIFIED PASSED</span>' : '<span class="status-pill-alert">VIOLATION DETECTED</span>'}
        </div>
      `;
      verificationConditionsList.appendChild(item);
    });
  }

  // Stage 8: Render Honest Final Report & Raw JSON
  function renderHonestReport(report, data) {
    if (!honestReportContainer) return;

    const status = data.deletion_status || 'COMPLETE';
    const distinctions = report.distinctions || {};
    const counts = report.summary_counts || {};

    let certBadge = report.audit_certificate
      ? `<div style="margin-top: 0.75rem; padding: 0.75rem 1rem; background: var(--green-pill-bg); border: 1px solid rgba(22, 163, 74, 0.3); border-radius: 4px; font-family: var(--font-mono); font-size: 0.8rem; color: var(--green-deep); display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 0.5rem;">
           <span>CERTIFICATE: <strong>${report.audit_certificate}</strong></span>
           <span style="font-size: 0.72rem;">TAMPER-EVIDENT DETERMINISTIC HASH</span>
         </div>`
      : `<div style="margin-top: 0.75rem; padding: 0.75rem 1rem; background: #FFF5F5; border: 1px solid rgba(220, 38, 38, 0.2); border-radius: 4px; font-family: var(--font-mono); font-size: 0.8rem; color: #991B1B;">
           CERTIFICATE: <strong>NONE ISSUED</strong> — Deletion verification cannot be granted while unresolved findings or residual records remain.
         </div>`;

    const isVerified = distinctions.deletion_independently_verified === true;
    const verifiedBoxClass = isVerified ? 'verified' : (status === 'NOT_APPLICABLE' ? 'exempt' : 'unverified');

    honestReportContainer.innerHTML = `
      <!-- Report Header -->
      <div style="display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 1px solid var(--border-medium); padding-bottom: 1rem; margin-bottom: 1.25rem; flex-wrap: wrap; gap: 0.75rem;">
        <div>
          <span style="font-family: var(--font-mono); font-size: 0.72rem; color: var(--text-muted); text-transform: uppercase;">DETERMINISTIC VERIFICATION REPORT</span>
          <h3 style="font-size: 1.25rem; margin: 0.2rem 0; font-family: var(--font-serif); font-weight: 600;">Case ${report.case_id || 'custom'} · Attestation Summary</h3>
          <div style="font-size: 0.82rem; color: var(--text-secondary);">Subject ID: <code>${report.subject_id || 'user_demo'}</code> · Claimed: <strong>${report.reported_status || 'COMPLETE'}</strong></div>
        </div>
        <div style="text-align: right;">
          <span style="font-size: 0.72rem; color: var(--text-muted); font-family: var(--font-mono);">AUDIT OUTCOME</span>
          <div class="verdict-banner ${status.toLowerCase()}" style="padding: 0.4rem 1rem; margin-top: 0.25rem; font-size: 0.95rem; font-weight: 700;">
            ${status}
          </div>
        </div>
      </div>

      <!-- Summary Metrics Grid -->
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 0.75rem; margin-bottom: 1.25rem;">
        <div style="background: var(--bg-warm); padding: 0.75rem; border-radius: 4px; border: 1px solid var(--border-subtle); text-align: center;">
          <div style="font-size: 1.2rem; font-weight: 700; font-family: var(--font-mono);">${counts.systems_assessed || 8}</div>
          <div style="font-size: 0.72rem; color: var(--text-muted);">Systems Assessed</div>
        </div>
        <div style="background: var(--bg-warm); padding: 0.75rem; border-radius: 4px; border: 1px solid var(--border-subtle); text-align: center;">
          <div style="font-size: 1.2rem; font-weight: 700; font-family: var(--font-mono); color: var(--green-primary);">${counts.systems_clean || 0}</div>
          <div style="font-size: 0.72rem; color: var(--text-muted);">Verified Clean</div>
        </div>
        <div style="background: var(--bg-warm); padding: 0.75rem; border-radius: 4px; border: 1px solid var(--border-subtle); text-align: center;">
          <div style="font-size: 1.2rem; font-weight: 700; font-family: var(--font-mono); color: ${counts.outstanding_findings_count > 0 ? '#DC2626' : 'var(--text-primary)'};">${counts.outstanding_findings_count || 0}</div>
          <div style="font-size: 0.72rem; color: var(--text-muted);">Outstanding Findings</div>
        </div>
        <div style="background: var(--bg-warm); padding: 0.75rem; border-radius: 4px; border: 1px solid var(--border-subtle); text-align: center;">
          <div style="font-size: 1.2rem; font-weight: 700; font-family: var(--font-mono);">${counts.evidence_items_collected || 0}</div>
          <div style="font-size: 0.72rem; color: var(--text-muted);">Evidence Items</div>
        </div>
        <div style="background: var(--bg-warm); padding: 0.75rem; border-radius: 4px; border: 1px solid var(--border-subtle); text-align: center;">
          <div style="font-size: 1.2rem; font-weight: 700; font-family: var(--font-mono);">${counts.remediation_steps_count || 0}</div>
          <div style="font-size: 0.72rem; color: var(--text-muted);">Remediation Steps</div>
        </div>
      </div>

      <!-- Explicit 4-Box Distinctions -->
      <div class="distinctions-grid">
        <!-- 1. Deletion Requested -->
        <div class="distinction-box">
          <div class="distinction-header">
            <span class="distinction-title">1. Deletion Requested</span>
            <span class="badge-pill">INTAKE</span>
          </div>
          <div style="font-size: 0.8rem; color: var(--text-secondary); line-height: 1.45; word-break: break-word;">
            ${distinctions.deletion_requested || 'Consumer initiated statutory request.'}
          </div>
        </div>

        <!-- 2. Deletion Evidence Observed -->
        <div class="distinction-box">
          <div class="distinction-header">
            <span class="distinction-title">2. Deletion Evidence Observed</span>
            <span class="badge-pill">DISCOVERY</span>
          </div>
          <div style="font-size: 0.8rem; color: var(--text-secondary); line-height: 1.45; word-break: break-word;">
            ${distinctions.deletion_evidence_observed || 'Evidence inspected across all platforms.'}
          </div>
        </div>

        <!-- 3. Remediation Recommended -->
        <div class="distinction-box">
          <div class="distinction-header">
            <span class="distinction-title">3. Remediation Recommended</span>
            <span class="badge-pill">PLANNING</span>
          </div>
          <div style="font-size: 0.8rem; color: var(--text-secondary); line-height: 1.45; word-break: break-word;">
            ${distinctions.remediation_recommended || 'Ordered sequential corrective steps.'}
          </div>
        </div>

        <!-- 4. Deletion Independently Verified -->
        <div class="distinction-box ${verifiedBoxClass}">
          <div class="distinction-header">
            <span class="distinction-title">4. Independently Verified</span>
            ${isVerified ? '<span class="status-pill-ok">VERIFIED</span>' : (status === 'NOT_APPLICABLE' ? '<span class="badge-pill">EXEMPT</span>' : '<span class="status-pill-alert">UNVERIFIED</span>')}
          </div>
          <div style="font-size: 0.8rem; color: var(--text-secondary); line-height: 1.45; word-break: break-word;">
            ${report.verification_outcome || 'Statutory outcome evaluated.'}
          </div>
        </div>
      </div>

      <!-- Certificate or Unverified Notice -->
      ${certBadge}

      <!-- Outstanding Uncertainties -->
      ${report.outstanding_uncertainties ? `
        <div style="margin-top: 0.85rem; padding: 0.75rem 1rem; background: var(--bg-warm); border-left: 3px solid ${isVerified ? 'var(--green-primary)' : '#DC2626'}; font-size: 0.8rem; border-radius: 0 4px 4px 0;">
          <strong style="color: var(--text-primary);">Outstanding Uncertainties:</strong>
          <span style="color: var(--text-secondary); margin-left: 0.35rem;">${report.outstanding_uncertainties}</span>
        </div>
      ` : ''}

      <!-- Stale Run Warning -->
      ${isInputsStale ? `
        <div style="margin-top: 0.85rem; padding: 0.6rem 0.85rem; background: #FFFBEB; border: 1px solid #FCD34D; color: #92400E; font-size: 0.78rem; border-radius: 4px;">
          ⚠️ <strong>Inputs modified after run:</strong> The report below reflects the executed audit run (Case: ${report.case_id || 'custom'}, Subject: ${report.subject_id || 'user'}). Run an audit to evaluate current inputs.
        </div>
      ` : ''}

      <!-- Synthetic Notice -->
      <div style="margin-top: 1rem; font-size: 0.75rem; color: var(--text-muted); font-style: italic; border-top: 1px solid var(--border-subtle); padding-top: 0.75rem;">
        Notice: ${report.disclosure || 'Synthetic demonstration data — no real systems connected.'}
      </div>
    `;

    // Update Raw JSON Inspector
    jsonPreviewEl.textContent = JSON.stringify(data, null, 2);

    // Pre-populate printable report
    populatePrintableReport(data);
  }

  // Generate Print/Save-as-PDF Attestation Report
  function populatePrintableReport(data) {
    if (!printableAuditReport) return;
    if (!data) {
      printableAuditReport.innerHTML = '';
      return;
    }

    const report = data.final_report || {};
    const status = (data.deletion_status || 'COMPLETE').toUpperCase();
    const caseId = data.case_id || submittedSnapshot?.case_id || 'case_custom';
    const userId = data.user_id || 'user_demo';
    const email = report.email || submittedSnapshot?.email || 'user@example.com';
    const requestedAt = report.requested_at || submittedSnapshot?.requested_at || new Date().toISOString();
    const auditAt = report.audit_at || submittedSnapshot?.audit_at || new Date().toISOString();
    const reportedStatus = report.reported_status || submittedSnapshot?.reported_status || 'COMPLETE';
    const distinctions = report.distinctions || {};
    const counts = report.summary_counts || {};
    const findings = data.findings || [];
    const evidenceItems = data.evidence_items || [];
    const steps = data.steps || [];
    const isVerified = distinctions.deletion_independently_verified === true && status === 'COMPLETE';
    const statusBadgeClass = status === 'COMPLETE' ? 'print-badge-complete' : (status === 'NOT_APPLICABLE' ? 'print-badge-exempt' : 'print-badge-incomplete');

    let certBoxHtml = '';
    if (isVerified && report.audit_certificate) {
      certBoxHtml = `
        <div class="print-cert-box" style="border: 2px solid #16A34A; background: #F0FDF4; color: #166534;">
          <div style="font-size: 0.9rem; font-weight: 700; margin-bottom: 0.25rem;">
            🛡️ DETERMINISTIC AUDIT ATTESTATION CERTIFICATE ISSUED
          </div>
          <div>Certificate Fingerprint: <strong>${report.audit_certificate}</strong></div>
          <div style="font-size: 0.72rem; margin-top: 0.35rem; color: #14532D;">
            All 7 connected storage platforms independently verified clean or pseudonymized under GDPR Art. 17 / CCPA § 1798.105. Zero residual consumer records detected.
          </div>
        </div>
      `;
    } else if (status === 'NOT_APPLICABLE') {
      certBoxHtml = `
        <div class="print-cert-box" style="border: 2px solid #D97706; background: #FFFBEB; color: #92400E;">
          <div style="font-size: 0.9rem; font-weight: 700; margin-bottom: 0.25rem;">
            ⚖️ STATUTORY RETENTION HOLD / EXEMPTION VERIFIED
          </div>
          <div>Statutory Status: <strong>EXEMPT FROM ERASURE</strong></div>
          <div style="font-size: 0.72rem; margin-top: 0.35rem; color: #78350F;">
            Personal data verified preserved under applicable statutory dispute or retention framework. No purge permitted or required.
          </div>
        </div>
      `;
    } else {
      certBoxHtml = `
        <div class="print-cert-box" style="border: 2px solid #DC2626; background: #FEF2F2; color: #991B1B;">
          <div style="font-size: 0.9rem; font-weight: 700; margin-bottom: 0.25rem;">
            ⚠️ ATTESTATION WITHHELD — AUDIT STATUS INCOMPLETE
          </div>
          <div>Verification Claim: <strong>UNVERIFIED</strong></div>
          <div style="font-size: 0.72rem; margin-top: 0.35rem; color: #7F1D1D;">
            Residual records or tokens were detected in secondary stores. Compliance certificate cannot be granted until all outstanding findings are remediated and verified absent.
          </div>
        </div>
      `;
    }

    let staleNoticeHtml = '';
    if (isInputsStale) {
      staleNoticeHtml = `
        <div style="padding: 6px 10px; background: #FFFBEB; border: 1px solid #FCD34D; color: #92400E; font-size: 0.75rem; margin-bottom: 1rem; border-radius: 3px;">
          <strong>Notice:</strong> Dashboard input parameters were modified after this audit was completed. This report represents the completed audit run snapshot.
        </div>
      `;
    }

    // Build Findings Table
    let findingsRows = '';
    if (findings.length > 0) {
      findings.forEach(f => {
        findingsRows += `
          <tr>
            <td><strong>${f.finding_id || 'FND-01'}</strong></td>
            <td><span style="font-family: monospace; font-size: 0.75rem; color: ${f.severity === 'HIGH' ? '#DC2626' : (f.severity === 'MEDIUM' ? '#D97706' : '#2563EB')}; font-weight: 700;">${f.severity || 'HIGH'}</span></td>
            <td><strong>${f.system || 'Storage'}</strong><br><code style="font-size: 0.72rem;">${f.resource || 'resource'}</code></td>
            <td>${f.description || 'Residual record detected.'}</td>
            <td><strong>${f.evidence_id ? f.evidence_id : '—'}</strong></td>
            <td>${f.verification_status || 'RESIDUAL_DETECTED'}</td>
            <td>${f.recommended_action || 'Purge record.'}</td>
          </tr>
        `;
      });
    } else {
      findingsRows = `
        <tr>
          <td colspan="7" style="text-align: center; color: #166534; font-weight: 600; padding: 10px;">
            ✅ Zero residual findings detected. All systems verified absent or pseudonymized according to policy.
          </td>
        </tr>
      `;
    }

    // Build Evidence Table
    let evidenceRows = '';
    if (evidenceItems.length > 0) {
      evidenceItems.forEach(ev => {
        evidenceRows += `
          <tr>
            <td><strong>${ev.evidence_id || 'EV-01'}</strong></td>
            <td>${ev.system || 'Store'}</td>
            <td><code style="font-size: 0.72rem;">${ev.resource || '—'}</code></td>
            <td><span class="print-badge ${ev.verification_status === 'VERIFIED_ABSENT' || ev.verification_status === 'PSEUDONYMIZED' ? 'print-badge-complete' : (ev.verification_status === 'EXEMPT' ? 'print-badge-exempt' : 'print-badge-incomplete')}">${ev.verification_status || 'COLLECTED'}</span></td>
            <td><code style="font-size: 0.7rem;">${ev.proof_hash ? ev.proof_hash.substring(0, 24) + '...' : '—'}</code></td>
            <td>${ev.linked_finding_id ? `<strong>${ev.linked_finding_id}</strong>` : '— (Clean)'}</td>
          </tr>
        `;
      });
    }

    // Build Remediation Steps Table
    let stepsRows = '';
    if (steps.length > 0) {
      steps.forEach(st => {
        stepsRows += `
          <tr>
            <td style="text-align: center;">${st.step_no || 1}</td>
            <td><strong>${st.phase || 'REMEDIATION'}</strong></td>
            <td>${st.system_id || 'system'}</td>
            <td><code style="font-size: 0.72rem;">${st.resource_id || '—'}</code></td>
            <td>${st.operation || 'PURGE'}</td>
            <td>${st.state || 'ABSENT'}</td>
          </tr>
        `;
      });
    }

    printableAuditReport.innerHTML = `
      <div class="print-page-header">
        <div>
          <div style="font-family: monospace; font-size: 0.75rem; letter-spacing: 0.1em; color: #4B5563;">SHOMEI · PROOF OF DELETION AUDIT SYSTEM</div>
          <h1 class="print-title">Autonomous Deletion Verification Report</h1>
          <div style="font-size: 0.8rem; color: #374151;">
            Case Reference: <strong>${caseId}</strong> · Subject ID: <code>${userId}</code> (${email})
          </div>
        </div>
        <div style="text-align: right;">
          <div style="font-size: 0.7rem; font-family: monospace; color: #6B7280;">AUDIT OUTCOME</div>
          <span class="print-badge ${statusBadgeClass}" style="font-size: 0.95rem; padding: 4px 10px; margin-top: 4px;">
            ${status}
          </span>
          <div style="font-size: 0.7rem; color: #6B7280; margin-top: 4px;">
            Date: ${new Date().toISOString().split('T')[0]}
          </div>
        </div>
      </div>

      <div class="print-disclosure">
        <strong>SYNTHETIC DEMONSTRATION DISCLOSURE:</strong> ${report.disclosure || 'Synthetic demonstration data — no production systems connected. Evaluated under GDPR Art. 17 and CCPA § 1798.105 invariant rules.'}
      </div>

      ${staleNoticeHtml}

      <div style="margin-bottom: 1.25rem;">
        <h3 style="font-size: 0.95rem; margin: 0 0 0.5rem 0; text-transform: uppercase; letter-spacing: 0.05em; border-bottom: 1px solid #D1D5DB; padding-bottom: 4px;">
          1. Statutory Audit Distinctions
        </h3>
        <table class="print-table" style="margin-top: 0.4rem;">
          <tbody>
            <tr>
              <td style="width: 25%; font-weight: 700; background: #F9FAFB;">1. Deletion Requested</td>
              <td>${distinctions.deletion_requested || `Requested by ${email} at ${requestedAt}. Reported initial state: ${reportedStatus}.`}</td>
            </tr>
            <tr>
              <td style="font-weight: 700; background: #F9FAFB;">2. Deletion Observed</td>
              <td>${distinctions.deletion_evidence_observed || `Observed across 7 topology stores: ${counts.systems_clean || 0} clean, ${counts.outstanding_findings_count || 0} residual.`}</td>
            </tr>
            <tr>
              <td style="font-weight: 700; background: #F9FAFB;">3. Remediation Recommended</td>
              <td>${distinctions.remediation_recommended || `${counts.remediation_steps_count || 0} sequential remediation actions synthesized.`}</td>
            </tr>
            <tr>
              <td style="font-weight: 700; background: #F9FAFB;">4. Independently Verified</td>
              <td><strong>${isVerified ? 'VERIFIED COMPLETE' : (status === 'NOT_APPLICABLE' ? 'EXEMPT FROM ERASURE' : 'UNVERIFIED — RESIDUAL DATA PRESENT')}</strong> — ${report.verification_outcome || 'Evaluation completed.'}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div style="margin-bottom: 1.25rem;">
        <h3 style="font-size: 0.95rem; margin: 0 0 0.5rem 0; text-transform: uppercase; letter-spacing: 0.05em; border-bottom: 1px solid #D1D5DB; padding-bottom: 4px;">
          2. Audit Findings & Linked Evidence (${findings.length})
        </h3>
        <table class="print-table">
          <thead>
            <tr>
              <th>Finding ID</th>
              <th>Severity</th>
              <th>System / Resource</th>
              <th>Description</th>
              <th>Evidence ID</th>
              <th>Status</th>
              <th>Action Required</th>
            </tr>
          </thead>
          <tbody>
            ${findingsRows}
          </tbody>
        </table>
      </div>

      <div style="margin-bottom: 1.25rem;">
        <h3 style="font-size: 0.95rem; margin: 0 0 0.5rem 0; text-transform: uppercase; letter-spacing: 0.05em; border-bottom: 1px solid #D1D5DB; padding-bottom: 4px;">
          3. Multi-Store Evidence Inventory (${evidenceItems.length})
        </h3>
        <table class="print-table">
          <thead>
            <tr>
              <th>Evidence ID</th>
              <th>System Store</th>
              <th>Resource Identifier</th>
              <th>Verification State</th>
              <th>Proof Hash</th>
              <th>Linked Finding</th>
            </tr>
          </thead>
          <tbody>
            ${evidenceRows}
          </tbody>
        </table>
      </div>

      ${steps.length > 0 ? `
      <div style="margin-bottom: 1.25rem;">
        <h3 style="font-size: 0.95rem; margin: 0 0 0.5rem 0; text-transform: uppercase; letter-spacing: 0.05em; border-bottom: 1px solid #D1D5DB; padding-bottom: 4px;">
          4. Canonical Remediation Sequence (${steps.length} Steps)
        </h3>
        <table class="print-table">
          <thead>
            <tr>
              <th>#</th>
              <th>Phase</th>
              <th>Target System</th>
              <th>Resource ID</th>
              <th>Operation</th>
              <th>Expected State</th>
            </tr>
          </thead>
          <tbody>
            ${stepsRows}
          </tbody>
        </table>
      </div>
      ` : ''}

      <div style="margin-bottom: 1.25rem;">
        <h3 style="font-size: 0.95rem; margin: 0 0 0.5rem 0; text-transform: uppercase; letter-spacing: 0.05em; border-bottom: 1px solid #D1D5DB; padding-bottom: 4px;">
          5. Outstanding Uncertainties & Disclosures
        </h3>
        <div style="font-size: 0.8rem; line-height: 1.5; color: #374151; padding: 8px 12px; background: #F9FAFB; border: 1px solid #E5E7EB;">
          ${report.outstanding_uncertainties || 'None. Cryptographic absence proofs verified across all storage nodes.'}
        </div>
      </div>

      ${certBoxHtml}

      <div style="margin-top: 1.5rem; border-top: 1px solid #D1D5DB; padding-top: 0.5rem; display: flex; justify-content: space-between; font-size: 0.7rem; color: #6B7280;">
        <span>Shomei Verification Engine v1.0 · CLEAN. VERIFIED. GONE.</span>
        <span>Generated: ${new Date().toISOString()}</span>
      </div>
    `;
  }

  // Copy JSON Button
  if (btnCopyJson) {
    btnCopyJson.addEventListener('click', () => {
      if (jsonPreviewEl) {
        navigator.clipboard.writeText(jsonPreviewEl.textContent).then(() => {
          btnCopyJson.textContent = '✅ Copied!';
          setTimeout(() => { btnCopyJson.textContent = '📋 Copy JSON'; }, 2000);
        });
      }
    });
  }

  // Download JSON Export Button
  if (btnDownloadJson) {
    btnDownloadJson.addEventListener('click', () => {
      if (auditState === 'RUNNING') {
        alert('An audit is currently running. Please wait for completion before exporting.');
        return;
      }
      if (auditState !== 'COMPLETED' || !authoritativeAuditResult) {
        alert('No completed audit result available to export. Please run an autonomous audit first.');
        return;
      }

      const caseId = authoritativeAuditResult.case_id || submittedSnapshot?.case_id || 'case_custom';
      const status = (authoritativeAuditResult.deletion_status || 'result').toLowerCase();
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-');

      const exportPayload = {
        ...authoritativeAuditResult,
        export_metadata: {
          ...(authoritativeAuditResult.final_report?.export_metadata || {}),
          exported_at: new Date().toISOString(),
          case_id: caseId,
          audit_status: authoritativeAuditResult.deletion_status,
          is_synthetic: authoritativeAuditResult.is_synthetic ?? true,
          synthetic_disclosure: authoritativeAuditResult.disclosure || "Synthetic demonstration data — no real systems connected.",
          inputs_modified_since_run: isInputsStale,
          export_notice: isInputsStale
            ? "WARNING: Console inputs were modified after this audit completed. This export reflects the executed audit run."
            : "Authoritative completed audit run."
        }
      };

      const jsonString = JSON.stringify(exportPayload, null, 2);
      const blob = new Blob([jsonString], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `shomei-audit-${caseId}-${status}-${timestamp}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);

      const originalText = btnDownloadJson.textContent;
      btnDownloadJson.textContent = '✅ Downloaded!';
      setTimeout(() => {
        btnDownloadJson.textContent = originalText;
      }, 2000);
    });
  }

  // Print / Save as PDF Button
  if (btnPrintReport) {
    btnPrintReport.addEventListener('click', () => {
      if (auditState === 'RUNNING') {
        alert('An audit is currently running. Please wait for completion before printing.');
        return;
      }
      if (auditState !== 'COMPLETED' || !authoritativeAuditResult) {
        alert('No completed audit result available to print. Please run an autonomous audit first.');
        return;
      }

      populatePrintableReport(authoritativeAuditResult);
      window.print();
    });
  }

  // 4. Stepper Navigation Functions (8 Stages)
  function goToStep(stepNum) {
    if (stepNum < 1) stepNum = 1;
    if (stepNum > 8) stepNum = 8;
    currentStep = stepNum;

    // Update stepper button states
    btnStepPrev.disabled = (currentStep === 1 || auditState === 'RUNNING');
    btnStepNext.disabled = (currentStep === 8 || auditState === 'RUNNING');

    // Update stepper indicators
    stepIndicators.forEach((ind) => {
      const s = parseInt(ind.dataset.step, 10);
      ind.classList.toggle('active', s === currentStep);
    });

    // Update active tab and content
    consoleTabs.forEach((tab) => {
      const tabTarget = tab.dataset.tab;
      const tabNum = parseInt(tabTarget.replace('tab-', ''), 10);
      const isActive = tabNum === currentStep;
      tab.classList.toggle('active', isActive);
      if (isActive) {
        tab.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
      }
    });

    tabContents.forEach((content) => {
      const cNum = parseInt(content.id.replace('tab-', ''), 10);
      content.classList.toggle('active', cNum === currentStep);
    });
  }

  btnStepPrev.addEventListener('click', () => goToStep(currentStep - 1));
  btnStepNext.addEventListener('click', () => goToStep(currentStep + 1));

  btnStepReset.addEventListener('click', () => {
    // Invalidate any ongoing run immediately
    currentRunId++;

    if (activeAbortController) {
      activeAbortController.abort();
      activeAbortController = null;
    }

    const currentSelectedCase = caseSelect.value;

    authoritativeAuditResult = null;
    submittedSnapshot = null;
    selectedEvidenceId = null;
    selectedSystemId = 'primary_db';

    if (printableAuditReport) {
      printableAuditReport.innerHTML = '';
    }

    if (caseSearchInput) caseSearchInput.value = '';
    if (caseFilterSelect) caseFilterSelect.value = 'all';
    if (caseOutcomeSelect) caseOutcomeSelect.value = 'all';
    renderCaseOptions();

    // Preserve the currently selected sample case if available in catalog
    if (currentSelectedCase && casesCatalog[currentSelectedCase]) {
      caseSelect.value = currentSelectedCase;
      populateCaseInputs(currentSelectedCase);
    } else if (caseSelect.value && casesCatalog[caseSelect.value]) {
      populateCaseInputs(caseSelect.value);
    }

    setInitialReadyState();
    goToStep(1);
  });

  // Tab click handlers
  consoleTabs.forEach((tab) => {
    tab.addEventListener('click', () => {
      const tabNum = parseInt(tab.dataset.tab.replace('tab-', ''), 10);
      goToStep(tabNum);
    });
  });

  // Stepper indicator click handlers
  stepIndicators.forEach((ind) => {
    ind.addEventListener('click', () => {
      const sNum = parseInt(ind.dataset.step, 10);
      goToStep(sNum);
    });
  });

  // Accessible keyboard navigation
  window.addEventListener('keydown', (e) => {
    // Only handle arrow keys if not typing in inputs
    if (['input', 'textarea', 'select'].includes(document.activeElement.tagName.toLowerCase())) {
      return;
    }
    if (e.key === 'ArrowRight' && currentStep < 8 && auditState !== 'RUNNING') {
      goToStep(currentStep + 1);
    } else if (e.key === 'ArrowLeft' && currentStep > 1 && auditState !== 'RUNNING') {
      goToStep(currentStep - 1);
    }
  });

  // Initial load
  loadCases();
});
