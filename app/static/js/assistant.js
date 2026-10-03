/**
 * assistant.js — Governance AI Assistant & Action Chat
 * Supports:
 * 1. Governance-Aware RAG Q&A (POST /api/v1/rag/ask) with interactive source citations & context controls
 * 2. Action Chat (POST /api/v1/chat/send) with live action preview & review
 */
const AssistantPage = (() => {
  let mode = 'rag'; // 'rag' | 'action'
  let convId = null;
  let isThinking = false;
  let messages = [];
  let ragHistory = [];
  let actionHistory = [];
  let lastRetrievedSources = [];

  /* ── State Persistence ────────────────────────────────────── */
  function _saveState() {
    try {
      localStorage.setItem('THRESHOLD_chat_state_v2', JSON.stringify({
        mode,
        convId,
        messages,
        ragHistory,
        actionHistory,
      }));
    } catch (e) {}
  }

  function _loadState() {
    try {
      const state = JSON.parse(localStorage.getItem('THRESHOLD_chat_state_v2'));
      if (state) {
        if (state.mode) mode = state.mode;
        if (state.convId) convId = state.convId;
        if (state.ragHistory) ragHistory = state.ragHistory;
        if (state.actionHistory) actionHistory = state.actionHistory;
        if (state.messages && Array.isArray(state.messages)) {
          messages = state.messages;
          const refs = r();
          if (refs.msgs && messages.length > 0) {
            refs.msgs.querySelector('.chat-welcome')?.remove();
            messages.forEach(m => _appendMsg(m.role, m.content, m.ts || new Date(), true, m.sources));
          }
        }
      }
    } catch (e) {}
  }

  /* ── DOM refs ────────────────────────────────────────────── */
  const $ = id => document.getElementById(id);
  const r = () => ({
    msgs:          $('chat-messages'),
    ta:            $('chat-textarea'),
    send:          $('chat-send-btn'),
    clear:         $('chat-clear-btn'),
    newConv:       $('new-conversation-btn'),
    charCount:     $('char-count'),
    // Mode toggles
    modeRagBtn:    $('mode-rag-btn'),
    modeActionBtn: $('mode-action-btn'),
    contextBar:    $('rag-context-bar'),
    // RAG controls
    clearance:     $('rag-clearance'),
    role:          $('rag-role'),
    dept:          $('rag-dept'),
    topK:          $('rag-top-k'),
    brandLabel:    $('assistant-brand-label'),
    subtitle:      $('assistant-subtitle'),
    // RAG side panel
    ragPanel:      $('rag-sources-panel'),
    ragList:       $('rag-sources-list'),
    ragEmpty:      $('rag-sources-empty'),
    ragSummary:    $('rag-sources-summary'),
    ragAuthCount:  $('rag-auth-count'),
    ragDeniedCount:$('rag-denied-count'),
    ragLatency:    $('rag-latency'),
    sourcesBadge:  $('sources-count-badge'),
    // Action preview side panel
    actionPanel:   $('action-preview-card'),
    actionEmpty:   $('action-preview-empty'),
    actionBody:    $('action-preview-body'),
    actionFooter:  $('action-preview-footer'),
    // History list
    histList:      $('conversation-history-list'),
  });

  /* ── Mode Switching ───────────────────────────────────────── */
  function setMode(newMode) {
    mode = newMode;
    const refs = r();

    if (mode === 'rag') {
      refs.modeRagBtn?.classList.add('active');
      refs.modeRagBtn?.style.setProperty('background', 'var(--color-primary)', 'important');
      refs.modeRagBtn?.style.setProperty('color', '#fff', 'important');
      refs.modeActionBtn?.classList.remove('active');
      refs.modeActionBtn?.style.setProperty('background', 'transparent', 'important');
      refs.modeActionBtn?.style.setProperty('color', 'var(--text-secondary)', 'important');

      if (refs.contextBar) refs.contextBar.style.display = 'flex';
      if (refs.ragPanel) refs.ragPanel.style.display = '';
      if (refs.actionPanel) refs.actionPanel.style.display = 'none';
      if (refs.brandLabel) refs.brandLabel.textContent = 'THRESHOLD Governance RAG';
      if (refs.subtitle) refs.subtitle.textContent = 'Grounded, source-attributed RAG answer generation with security context enforcement';
      if (refs.ta) refs.ta.placeholder = 'Ask about enterprise AI security policies or guidelines…';
    } else {
      refs.modeActionBtn?.classList.add('active');
      refs.modeActionBtn?.style.setProperty('background', 'var(--color-primary)', 'important');
      refs.modeActionBtn?.style.setProperty('color', '#fff', 'important');
      refs.modeRagBtn?.classList.remove('active');
      refs.modeRagBtn?.style.setProperty('background', 'transparent', 'important');
      refs.modeRagBtn?.style.setProperty('color', 'var(--text-secondary)', 'important');

      if (refs.contextBar) refs.contextBar.style.display = 'none';
      if (refs.ragPanel) refs.ragPanel.style.display = 'none';
      if (refs.actionPanel) refs.actionPanel.style.display = '';
      if (refs.brandLabel) refs.brandLabel.textContent = 'THRESHOLD Action Chat';
      if (refs.subtitle) refs.subtitle.textContent = 'Interact with governed AI operations and infrastructure actions';
      if (refs.ta) refs.ta.placeholder = 'Describe an action you want the AI to perform…';
    }
    _renderHistoryList();
    _saveState();
  }

  /* ── Message Rendering ────────────────────────────────────── */
  function _appendMsg(role, content, ts, skipScroll=false, sources=[]) {
    const refs = r();
    if (!refs.msgs) return;
    refs.msgs.querySelector('.chat-welcome')?.remove();
    const time = _rel(ts || new Date());
    const isUser = role === 'user';
    const div = document.createElement('div');
    div.className = `message-row ${isUser ? 'user' : 'THRESHOLD'}`;

    let formattedBody = _fmt(content);
    if (!isUser && mode === 'rag') {
      formattedBody = _linkCitations(formattedBody);
    }

    div.innerHTML = `
      <div class="message-avatar ${isUser ? 'user' : 'THRESHOLD'}">${isUser ? '<i class="fa-solid fa-user"></i>' : 'AI'}</div>
      <div class="message-content">
        <div class="message-bubble ${isUser ? 'user' : 'THRESHOLD'}">${formattedBody}</div>
        <div class="message-meta">
          <span class="message-time">${isUser ? 'You' : 'THRESHOLD AI'} · ${time}</span>
          ${!isUser && sources && sources.length > 0 ? `<span class="badge badge-outline-primary text-xs" style="padding:0 4px;font-size:10px;">${sources.length} sources cited</span>` : ''}
        </div>
      </div>`;

    refs.msgs.appendChild(div);

    // Attach citation click handlers
    div.querySelectorAll('.source-citation-badge').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        const srcId = btn.dataset.sourceId;
        _highlightSource(srcId);
      });
    });

    if (!skipScroll) {
      setTimeout(() => { if (refs.msgs) refs.msgs.scrollTop = refs.msgs.scrollHeight; }, 30);
    }
  }

  function _linkCitations(html) {
    // Matches [Source X] or [SOURCE_X] or [Source_X]
    return html.replace(/\[(?:Source|SOURCE)[_\s]?(\d+)\]/gi, (match, p1) => {
      const canonicalId = `SOURCE_${p1}`;
      return `<button type="button" class="source-citation-badge" data-source-id="${canonicalId}"><i class="fa-solid fa-bookmark" style="font-size:9px;"></i> Source ${p1}</button>`;
    });
  }

  function _showThinking(text = 'THRESHOLD is analysing your request…') {
    const refs = r();
    if (!refs.msgs) return;
    const div = document.createElement('div');
    div.id = 'thinking-row';
    div.className = 'message-row THRESHOLD';
    div.innerHTML = `
      <div class="message-avatar THRESHOLD">AI</div>
      <div class="message-content">
        <div class="thinking-bubble">
          <div class="loading-dots"><span></span><span></span><span></span></div>
          <span class="thinking-text text-sm">${_esc(text)}</span>
        </div>
      </div>`;
    refs.msgs.appendChild(div);
    setTimeout(() => { if (refs.msgs) refs.msgs.scrollTop = refs.msgs.scrollHeight; }, 30);
  }

  /* ── RAG Source Side Panel ────────────────────────────────── */
  function _renderRAGSources(sources, meta, latencyMs) {
    const refs = r();
    if (!refs.ragList) return;
    lastRetrievedSources = sources || [];

    if (!sources || sources.length === 0) {
      refs.ragEmpty?.classList.remove('hidden');
      if (refs.ragEmpty) refs.ragEmpty.style.display = '';
      if (refs.ragList) refs.ragList.style.display = 'none';
      if (refs.ragSummary) refs.ragSummary.style.display = 'none';
      if (refs.sourcesBadge) refs.sourcesBadge.textContent = '0 sources';
      return;
    }

    refs.ragEmpty?.classList.add('hidden');
    if (refs.ragEmpty) refs.ragEmpty.style.display = 'none';
    if (refs.ragList) refs.ragList.style.display = 'block';
    if (refs.ragSummary) refs.ragSummary.style.display = 'block';

    const authCount = meta?.authorized_result_count ?? sources.length;
    const deniedCount = meta?.denied_count ?? 0;
    if (refs.ragAuthCount) refs.ragAuthCount.textContent = authCount;
    if (refs.ragDeniedCount) refs.ragDeniedCount.textContent = deniedCount;
    if (refs.ragLatency) refs.ragLatency.textContent = `${Math.round(latencyMs || 0)}ms`;
    if (refs.sourcesBadge) refs.sourcesBadge.textContent = `${sources.length} sources`;

    refs.ragList.innerHTML = sources.map(s => {
      const classLevel = (s.classification || 'INTERNAL').toUpperCase();
      const classBadge = classLevel === 'RESTRICTED' ? 'badge-danger' :
                         classLevel === 'CONFIDENTIAL' ? 'badge-warning' :
                         classLevel === 'INTERNAL' ? 'badge-primary' : 'badge-neutral';
      const scorePct = s.fused_score ? Math.round(s.fused_score * 100) : null;

      return `
        <div class="rag-source-item" id="source-card-${_esc(s.source_id)}">
          <div class="flex items-center justify-between gap-2 mb-1">
            <span class="badge badge-primary font-mono text-xs">${_esc(s.source_id)}</span>
            <div class="flex items-center gap-1">
              <span class="badge ${classBadge} text-xs">${_esc(classLevel)}</span>
              ${s.is_cited ? '<span class="badge badge-success text-xs"><i class="fa-solid fa-check mr-1"></i>Cited</span>' : ''}
            </div>
          </div>
          <div class="font-medium text-xs text-primary mb-1">${_esc(s.document_id)}</div>
          <div class="font-mono text-xs text-tertiary mb-2" style="font-size:10px;">${_esc(s.chunk_id)}</div>
          ${s.department ? `<div class="text-xs text-secondary mb-1"><i class="fa-solid fa-building text-tertiary mr-1"></i>${_esc(s.department)}</div>` : ''}
          ${s.source_reference ? `<div class="text-xs text-tertiary italic mb-2">${_esc(s.source_reference)}</div>` : ''}
          ${scorePct !== null ? `
            <div class="flex items-center justify-between text-xs text-tertiary pt-2 border-t border-color" style="font-size:10px;">
              <span>Hybrid Fusion Score</span>
              <span class="font-mono font-bold text-primary">${scorePct}%</span>
            </div>
          ` : ''}
        </div>
      `;
    }).join('');
  }

  function _highlightSource(sourceId) {
    const card = document.getElementById(`source-card-${sourceId}`);
    if (card) {
      document.querySelectorAll('.rag-source-item').forEach(c => c.classList.remove('highlighted'));
      card.classList.add('highlighted');
      card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      setTimeout(() => card.classList.remove('highlighted'), 3000);
    }
  }

  /* ── Action Preview (Action Chat Mode) ────────────────────── */
  function _renderPreview(preview) {
    const refs = r();
    if (!refs.actionBody || !preview) return;

    refs.actionEmpty?.classList.add('hidden');
    refs.actionBody.style.display = '';
    if (refs.actionFooter) refs.actionFooter.style.display = '';

    const confPct = Math.round((preview.confidence || 0) * 100);
    const riskColor = { low:'success', medium:'warning', high:'danger', critical:'danger' }[preview.risk_level] || 'neutral';

    refs.actionBody.innerHTML = `
      <div class="action-preview-body" style="padding:var(--space-5)">
        <div class="action-field">
          <span class="action-field-label">Intent</span>
          <span class="action-field-value">${_esc(preview.intent||'—')}</span>
        </div>
        <div class="action-field">
          <span class="action-field-label">Operation</span>
          <span class="action-field-value font-mono text-sm">${_esc(preview.operation||preview.operation_type||'—')}</span>
        </div>
        <div class="action-field">
          <span class="action-field-label">Target Resource</span>
          <span class="action-field-value">${_esc(preview.target_resource||'—')}</span>
        </div>
        <div class="action-field">
          <span class="action-field-label">Confidence</span>
          <div class="confidence-bar-wrap">
            <div class="progress-bar-wrap flex-1">
              <div class="progress-bar-fill ${confPct >= 80 ? 'success' : confPct >= 50 ? '' : 'danger'}" style="width:${confPct}%"></div>
            </div>
            <span class="confidence-value">${confPct}%</span>
          </div>
        </div>
        <div class="action-field">
          <span class="action-field-label">Risk Level</span>
          <span class="badge badge-${riskColor} badge-dot">${preview.risk_level||'—'}</span>
        </div>
      </div>`;

    if (refs.actionFooter && preview.action_id) {
      refs.actionFooter.innerHTML = `
        <button class="btn btn-success btn-sm" onclick="AssistantPage.approveAction('${preview.action_id}')">
          <i class="fa-solid fa-check"></i> Approve
        </button>
        <button class="btn btn-outline-danger btn-sm" onclick="AssistantPage.rejectAction('${preview.action_id}')">
          <i class="fa-solid fa-xmark"></i> Reject
        </button>`;
    }
  }

  function _clearPreview() {
    const refs = r();
    if (refs.actionBody) { refs.actionBody.innerHTML = ''; refs.actionBody.style.display = 'none'; }
    if (refs.actionFooter) { refs.actionFooter.innerHTML = ''; refs.actionFooter.style.display = 'none'; }
    refs.actionEmpty?.classList.remove('hidden');
  }

  /* ── Send Message Handler ─────────────────────────────────── */
  async function send() {
    const refs = r();
    if (isThinking || !refs.ta) return;
    const text = refs.ta.value.trim();
    if (!text) return;

    refs.ta.value = '';
    _autoResize(refs.ta);
    if (refs.send) refs.send.disabled = true;

    messages.push({ role: 'user', content: text, ts: new Date() });
    _appendMsg('user', text);
    _saveState();
    isThinking = true;

    if (mode === 'rag') {
      _showThinking('Searching hybrid knowledge index & enforcing access policies…');
      try {
        const payload = {
          question: text,
          top_k: parseInt(refs.topK?.value || '5', 10),
          access_context: {
            user_id: 'USER-WEB',
            role: refs.role?.value || 'EMPLOYEE',
            department: refs.dept?.value || 'Information Security',
            clearance_level: refs.clearance?.value || 'INTERNAL',
          },
        };

        const res = await THRESHOLDAPI.rag.ask(payload);
        $('thinking-row')?.remove();

        const answer = res.answer || 'No grounded answer could be generated.';
        _appendMsg('assistant', answer, new Date(), false, res.sources);
        messages.push({ role: 'assistant', content: answer, ts: new Date(), sources: res.sources });

        _renderRAGSources(res.sources, res.retrieval_metadata, res.execution_time_ms);
        _addHistoryItem('rag', text);
        _saveState();
      } catch (err) {
        $('thinking-row')?.remove();
        const errMsg = err.message || 'Governance RAG generation failed.';
        _appendMsg('assistant', `⚠️ **Governance Alert**: ${errMsg}`);
      } finally {
        isThinking = false;
        if (refs.send) refs.send.disabled = false;
        refs.ta?.focus();
      }
    } else {
      // Action Chat
      _showThinking('THRESHOLD AI is analyzing infrastructure action…');
      try {
        const res = await THRESHOLDAPI.chat.send({
          message: text,
          conversation_id: convId,
        });
        convId = res.conversation_id || convId;
        $('thinking-row')?.remove();
        const responseText = res.response || res.message || 'Action evaluated.';
        _appendMsg('assistant', responseText);
        messages.push({ role: 'assistant', content: responseText, ts: new Date() });
        if (res.action_preview) _renderPreview(res.action_preview);
        _addHistoryItem('action', text);
        _saveState();
      } catch (err) {
        $('thinking-row')?.remove();
        _appendMsg('assistant', `Error: ${err.message}`);
      } finally {
        isThinking = false;
        if (refs.send) refs.send.disabled = false;
        refs.ta?.focus();
      }
    }
  }

  /* ── Approve / Reject Actions ────────────────────────────── */
  async function approveAction(actionId) {
    try {
      await THRESHOLDAPI.review.approve(actionId, 'Approved from AI Assistant');
      if (typeof Toast !== 'undefined') Toast.success('Action approved');
      _clearPreview();
    } catch (e) {
      if (typeof Toast !== 'undefined') Toast.danger('Approval failed', e.message);
    }
  }

  async function rejectAction(actionId) {
    if (confirm('Reject this action?')) {
      try {
        await THRESHOLDAPI.review.reject(actionId, 'Rejected from AI Assistant');
        if (typeof Toast !== 'undefined') Toast.danger('Action rejected');
        _clearPreview();
      } catch (e) {
        if (typeof Toast !== 'undefined') Toast.danger('Error', e.message);
      }
    }
  }

  /* ── History List Management ──────────────────────────────── */
  function _addHistoryItem(hMode, text) {
    const list = hMode === 'rag' ? ragHistory : actionHistory;
    if (!list.find(h => h.text === text)) {
      list.unshift({ text, ts: new Date(), mode: hMode });
      if (list.length > 20) list.pop();
      _renderHistoryList();
      _saveState();
    }
  }

  function _renderHistoryList() {
    const refs = r();
    if (!refs.histList) return;
    const currentList = mode === 'rag' ? ragHistory : actionHistory;

    if (!currentList || currentList.length === 0) {
      refs.histList.innerHTML = `
        <div class="empty-state" style="padding:var(--space-8) var(--space-4)">
          <span class="text-xs text-tertiary">No recent inquiries yet</span>
        </div>`;
      return;
    }

    refs.histList.innerHTML = currentList.map(h => `
      <div class="history-item" data-query="${_esc(h.text)}">
        <div class="history-item-title">${_esc(h.text)}</div>
        <div class="history-item-meta">${_rel(h.ts)}</div>
      </div>
    `).join('');

    refs.histList.querySelectorAll('.history-item').forEach(el => {
      el.addEventListener('click', () => {
        if (refs.ta) {
          refs.ta.value = el.dataset.query || '';
          _autoResize(refs.ta);
          if (refs.send) refs.send.disabled = !refs.ta.value.trim();
          refs.ta.focus();
        }
      });
    });
  }

  /* ── Suggested Prompts ────────────────────────────────────── */
  function _initSuggested() {
    document.querySelectorAll('.suggested-prompt-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const refs = r();
        if (!refs.ta) return;
        refs.ta.value = btn.dataset.prompt || btn.textContent.trim();
        _autoResize(refs.ta);
        if (refs.send) refs.send.disabled = !refs.ta.value.trim();
        refs.ta.focus();
      });
    });
  }

  /* ── Helpers ──────────────────────────────────────────────── */
  function _autoResize(ta) {
    ta.style.height = 'auto';
    ta.style.height = Math.min(ta.scrollHeight, 140) + 'px';
  }
  function _esc(s) { const d = document.createElement('div'); d.textContent = String(s||''); return d.innerHTML; }
  function _rel(ts) {
    if (!ts) return 'now';
    const diff = Date.now() - new Date(ts).getTime();
    const m = Math.floor(diff / 60000);
    return m < 1 ? 'just now' : m < 60 ? `${m}m ago` : `${Math.floor(m/60)}h ago`;
  }
  function _fmt(content) {
    let s = _esc(content);
    s = s.replace(/`([^`]+)`/g, '<code class="font-mono text-xs" style="background:var(--bg-surface-2);padding:1px 5px;border-radius:4px">$1</code>');
    s = s.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    s = s.replace(/\n/g, '<br>');
    return s;
  }

  /* ── Initialization ───────────────────────────────────────── */
  function init() {
    _loadState();
    const refs = r();

    // Bind mode toggle buttons
    refs.modeRagBtn?.addEventListener('click', () => setMode('rag'));
    refs.modeActionBtn?.addEventListener('click', () => setMode('action'));

    // Bind inputs
    refs.send?.addEventListener('click', send);
    refs.ta?.addEventListener('keydown', e => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        send();
      }
    });
    refs.ta?.addEventListener('input', () => {
      _autoResize(refs.ta);
      if (refs.send) refs.send.disabled = !refs.ta.value.trim();
      if (refs.charCount) refs.charCount.textContent = refs.ta.value.length;
    });

    // Bind clear & new conversation
    refs.clear?.addEventListener('click', () => {
      convId = null;
      messages = [];
      if (refs.msgs) refs.msgs.innerHTML = `
        <div class="chat-welcome">
          <div class="chat-welcome-icon"><i class="fa-solid fa-book-shield"></i></div>
          <h2 class="chat-welcome-title">Ask Governance &amp; Security Questions</h2>
          <p class="chat-welcome-desc">Every answer is strictly grounded in retrieved and authorized enterprise policy documents with verifiable source citations.</p>
        </div>`;
      _clearPreview();
      _renderRAGSources([], {}, 0);
      _saveState();
    });

    refs.newConv?.addEventListener('click', () => {
      convId = null;
      messages = [];
      if (refs.msgs) refs.msgs.innerHTML = '';
      _clearPreview();
      _renderRAGSources([], {}, 0);
      _saveState();
    });

    _initSuggested();
    setMode(mode || 'rag');
  }

  return { init, send, setMode, approveAction, rejectAction };
})();
