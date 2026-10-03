/**
 * search.js — Controller for Hybrid Document Search (Phase 16).
 * Calls POST /api/v1/retrieval/governance-search and renders ranked, authorized chunks.
 */
const SearchPage = (() => {
  const $ = id => document.getElementById(id);

  function _esc(str) {
    if (!str) return '';
    const d = document.createElement('div');
    d.textContent = String(str);
    return d.innerHTML;
  }

  async function executeSearch() {
    const qInput = $('search-query-input');
    const query = qInput ? qInput.value.trim() : '';
    if (!query) return;

    const clearance = $('filter-clearance')?.value || 'INTERNAL';
    const role = $('filter-role')?.value || 'reviewer';
    const dept = $('filter-department')?.value || 'Engineering';
    const topK = parseInt($('filter-top-k')?.value || '5', 10);

    const user = THRESHOLDAPI.getUser();
    const userId = user?.username || 'user-' + role;

    const accessContext = {
      user_id: userId,
      role: role,
      department: dept,
      clearance_level: clearance,
      is_admin: role === 'admin',
    };

    const resultsContainer = $('search-results');
    const loading = $('search-loading');
    const errorBox = $('search-error');
    const errorMsg = $('search-error-msg');
    const summary = $('search-summary');
    const submitBtn = $('search-submit-btn');

    if (errorBox) errorBox.style.display = 'none';
    if (loading) loading.style.display = 'block';
    if (resultsContainer) resultsContainer.innerHTML = '';
    if (submitBtn) submitBtn.disabled = true;

    try {
      const resp = await THRESHOLDAPI.retrieval.governanceSearch({
        query: query,
        access_context: accessContext,
        top_k: topK,
      });

      if (loading) loading.style.display = 'none';

      // Update summary bar
      if (summary) {
        summary.style.display = 'flex';
        $('stat-authorized-count').textContent = resp.authorized_result_count || 0;
        $('stat-denied-count').textContent = resp.denied_count || 0;
        $('stat-strategy').textContent = resp.fusion_strategy || 'RRF Fused';
        $('stat-latency').textContent = Math.round(resp.execution_time_ms || 0) + 'ms';
      }

      const results = resp.results || [];
      if (results.length === 0) {
        resultsContainer.innerHTML = `
          <div class="empty-state" style="padding:var(--space-10) var(--space-4); text-align:center;">
            <div class="empty-state-icon" style="font-size:32px; color:var(--text-tertiary); margin-bottom:var(--space-2);">
              <i class="fa-solid fa-shield-slash"></i>
            </div>
            <h3 class="text-base font-semi" style="margin-bottom:var(--space-1);">No Authorized Results Found</h3>
            <p class="text-sm text-secondary" style="max-width:420px; margin:0 auto;">
              ${resp.denied_count > 0
                ? `${resp.denied_count} candidate chunk(s) were found but filtered by security clearance policies.`
                : 'No document chunks matched your query.'}
            </p>
          </div>`;
        return;
      }

      // Render cards
      let html = '';
      results.forEach((item, index) => {
        const meta = item.metadata || {};
        const score = item.fused_score != null ? Number(item.fused_score).toFixed(4) : 'N/A';
        const semScore = item.semantic_score != null ? Number(item.semantic_score).toFixed(3) : '-';
        const keyScore = item.keyword_score != null ? Number(item.keyword_score).toFixed(3) : '-';

        html += `
          <div class="search-result-card">
            <div class="result-card-header">
              <div class="result-card-title">
                <span class="result-rank-badge">${item.rank || (index + 1)}</span>
                <span>${_esc(item.document_id || 'Document')}</span>
                <span class="badge badge-dot badge-success text-xs">Authorized</span>
              </div>
              <div class="flex items-center gap-2">
                <span class="result-score-badge" title="RRF Fused Score">Score: ${score}</span>
              </div>
            </div>
            <div class="result-card-text">
              ${_esc(item.text)}
            </div>
            <div class="result-card-footer">
              <span class="metadata-tag"><i class="fa-solid fa-hashtag"></i> ${_esc(item.chunk_id || 'chunk')}</span>
              ${meta.classification ? `<span class="metadata-tag"><i class="fa-solid fa-shield"></i> ${_esc(meta.classification)}</span>` : ''}
              ${meta.department ? `<span class="metadata-tag"><i class="fa-solid fa-building"></i> ${_esc(meta.department)}</span>` : ''}
              ${meta.document_type ? `<span class="metadata-tag"><i class="fa-solid fa-file-lines"></i> ${_esc(meta.document_type)}</span>` : ''}
              <span class="metadata-tag text-tertiary" style="margin-left:auto;">
                Sem: ${semScore} · Key: ${keyScore}
              </span>
            </div>
          </div>`;
      });

      resultsContainer.innerHTML = html;

    } catch (err) {
      if (loading) loading.style.display = 'none';
      if (errorBox) {
        errorBox.style.display = 'block';
        if (errorMsg) errorMsg.textContent = err.message || 'An unexpected error occurred during search.';
      }
    } finally {
      if (submitBtn) submitBtn.disabled = false;
    }
  }

  function init() {
    const form = $('search-form');
    if (form) {
      form.removeEventListener('submit', executeSearch);
      form.addEventListener('submit', e => {
        e.preventDefault();
        executeSearch();
      });
    }

    // Auto-populate role & clearance from current user if available
    const user = THRESHOLDAPI.getUser();
    if (user) {
      if (user.role && $('filter-role')) $('filter-role').value = user.role.toLowerCase();
      if (user.department && $('filter-department')) $('filter-department').value = user.department;
    }
  }

  return { init, executeSearch };
})();
