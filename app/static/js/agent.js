/**
 * agent.js — Controller for Controlled AI Agent Workspace (Phase 16).
 * Handles task execution via POST /api/v1/agent/execute and displays step-by-step pipeline state.
 */
const AgentPage = (() => {
  const $ = id => document.getElementById(id);

  function _esc(str) {
    if (!str) return '';
    const d = document.createElement('div');
    d.textContent = String(str);
    return d.innerHTML;
  }

  function _resetStepper() {
    ['step-validation', 'step-routing', 'step-policy', 'step-auth', 'step-output'].forEach(id => {
      const el = $(id);
      if (el) el.className = 'pipeline-step-item';
    });
    $('agent-status-badge').className = 'badge badge-neutral';
    $('agent-status-badge').textContent = 'In Progress';
  }

  async function executeAgentTask() {
    const input = $('agent-request-input');
    const reqText = input ? input.value.trim() : '';
    if (!reqText) return;

    const clearance = $('agent-clearance')?.value || 'INTERNAL';
    const role = $('agent-role')?.value || 'reviewer';
    const user = THRESHOLDAPI.getUser();
    const userId = user?.username || 'user-' + role;

    const accessContext = {
      user_id: userId,
      role: role,
      department: user?.department || 'Engineering',
      clearance_level: clearance,
      is_admin: role === 'admin',
    };

    const submitBtn = $('agent-submit-btn');
    const resultCard = $('agent-result-card');
    const resultOutput = $('agent-result-output');
    const statusBadge = $('agent-status-badge');

    if (submitBtn) submitBtn.disabled = true;
    _resetStepper();
    if (resultCard) resultCard.style.display = 'none';

    // Step 1: Validation active
    $('step-validation')?.classList.add('active');

    try {
      const orchestrator = $('agent-orchestrator')?.value || 'langgraph';
      const apiCall = orchestrator === 'langgraph'
        ? (THRESHOLDAPI.agent.executeGraph || THRESHOLDAPI.agent.execute)
        : THRESHOLDAPI.agent.execute;

      const resp = await apiCall({
        request: reqText,
        access_context: accessContext,
      });

      // Pipeline update
      $('step-validation')?.classList.remove('active');
      $('step-validation')?.classList.add('success');
      $('step-meta-validation').textContent = `Request ID: ${resp.request_id || 'verified'}`;

      $('step-routing')?.classList.add('success');
      $('step-meta-routing').textContent = `Mapped Capability: ${resp.capability || 'Resolved'}`;

      if (resp.status === 'DENIED') {
        $('step-policy')?.classList.add('denied');
        $('step-meta-policy').textContent = `Policy Verdict: DENY (Access Restricted)`;
        $('step-auth')?.classList.add('denied');
        $('step-meta-auth').textContent = `Tool Execution Blocked`;
        $('step-output')?.classList.add('denied');

        statusBadge.className = 'badge badge-danger';
        statusBadge.textContent = 'ACCESS DENIED';
      } else if (resp.status === 'REVIEW_REQUIRED' || resp.status === 'PENDING_REVIEW') {
        $('step-policy')?.classList.add('active');
        $('step-meta-policy').textContent = `Policy Verdict: REQUIRES REVIEW`;
        $('step-auth')?.classList.add('active');
        $('step-meta-auth').textContent = `Pending Compliance Sign-off`;
        $('step-output')?.classList.add('active');

        statusBadge.className = 'badge badge-warning';
        statusBadge.textContent = 'REVIEW REQUIRED';
      } else {
        $('step-policy')?.classList.add('success');
        $('step-meta-policy').textContent = `Policy Verdict: ALLOW`;
        $('step-auth')?.classList.add('success');
        $('step-meta-auth').textContent = `Approved Registered Tool Executed`;
        $('step-output')?.classList.add('success');
        $('step-meta-output').textContent = `Output Validated · No Leaks Detected`;

        statusBadge.className = 'badge badge-success';
        statusBadge.textContent = 'SUCCESS';
      }

      // Display results
      if (resultCard && resultOutput) {
        resultCard.style.display = 'block';
        $('agent-audit-ref').textContent = resp.audit_reference || 'N/A';
        $('agent-latency').textContent = (resp.execution_time_ms ? Math.round(resp.execution_time_ms) : 0) + 'ms';

        let content = '';
        if (resp.result && typeof resp.result === 'object') {
          content = JSON.stringify(resp.result, null, 2);
        } else if (resp.message) {
          content = resp.message;
        } else {
          content = JSON.stringify(resp, null, 2);
        }
        resultOutput.textContent = content;
      }

      // Refresh recent audit feed
      loadAuditFeed();

    } catch (err) {
      statusBadge.className = 'badge badge-danger';
      statusBadge.textContent = 'ERROR';
      $('step-validation')?.classList.add('denied');
      $('step-meta-validation').textContent = `Error: ${err.message || 'Workflow failed'}`;

      if (resultCard && resultOutput) {
        resultCard.style.display = 'block';
        resultOutput.textContent = `Execution Error: ${err.message}`;
      }
    } finally {
      if (submitBtn) submitBtn.disabled = false;
    }
  }

  async function loadAuditFeed() {
    const list = $('agent-audit-list');
    if (!list) return;

    try {
      const data = await THRESHOLDAPI.agent.audit(15);
      const items = data.items || [];
      if (items.length === 0) {
        list.innerHTML = `
          <div class="empty-state" style="padding:var(--space-4) 0; text-align:center;">
            <span class="text-xs text-tertiary">No agent audit records yet.</span>
          </div>`;
        return;
      }

      let html = '';
      items.forEach(it => {
        const isSuccess = it.execution_status === 'SUCCESS';
        const isDeny = it.execution_status === 'DENY' || it.execution_status === 'DENIED';
        const badgeClass = isSuccess ? 'badge-success' : isDeny ? 'badge-danger' : 'badge-warning';

        html += `
          <div style="background:var(--bg-surface-2); border:1px solid var(--border-color); border-radius:var(--border-radius-sm); padding:var(--space-2) var(--space-3); font-size:var(--font-size-xs);">
            <div class="flex items-center justify-between" style="margin-bottom:2px;">
              <span class="font-semi text-primary">${_esc(it.selected_capability || 'CAPABILITY')}</span>
              <span class="badge ${badgeClass} text-xs">${_esc(it.execution_status || 'UNKNOWN')}</span>
            </div>
            <div class="text-tertiary font-mono" style="font-size:10px;">
              User: ${_esc(it.user_id)} · Role: ${_esc(it.role)}
            </div>
            <div class="text-tertiary flex items-center justify-between" style="font-size:10px; margin-top:2px;">
              <span>Policy: ${_esc(it.policy_decision)}</span>
              <span>${it.execution_time_ms ? Math.round(it.execution_time_ms) + 'ms' : ''}</span>
            </div>
          </div>`;
      });
      list.innerHTML = html;
    } catch (e) {
      console.debug('Failed to load agent audit feed:', e);
    }
  }

  function init() {
    const form = $('agent-form');
    if (form) {
      form.removeEventListener('submit', executeAgentTask);
      form.addEventListener('submit', e => {
        e.preventDefault();
        executeAgentTask();
      });
    }

    // Bind preset buttons
    document.querySelectorAll('.agent-preset-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const text = btn.dataset.preset;
        if (text && $('agent-request-input')) {
          $('agent-request-input').value = text;
          executeAgentTask();
        }
      });
    });

    const refreshBtn = $('refresh-audit-btn');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', loadAuditFeed);
    }

    loadAuditFeed();
  }

  return { init, executeAgentTask, loadAuditFeed };
})();
