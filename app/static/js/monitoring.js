/**
 * monitoring.js — System Observability & Telemetry UI
 * Periodically polls /api/v1/monitoring/summary and /metrics
 */
const MonitoringPage = (() => {
  let timer = null;
  let isPolling = false;

  const $ = id => document.getElementById(id);
  const r = () => ({
    refreshBtn:      $('mon-refresh-btn'),
    autoRefresh:     $('mon-auto-refresh'),
    lastUpdated:     $('mon-last-updated'),
    copyPromBtn:     $('copy-prom-btn'),
    promPreview:     $('prom-metrics-preview'),
    // Probes
    probeLiveness:   $('text-probe-liveness'),
    probeReadiness:  $('text-probe-readiness'),
    probeDb:         $('text-probe-db'),
    probeRai:        $('text-probe-rai'),
    iconLiveness:    $('icon-probe-liveness'),
    iconReadiness:   $('icon-probe-readiness'),
    subtextLiveness: $('subtext-probe-liveness'),
    subtextReadiness:$('subtext-probe-readiness'),
    subsystemDbBadge:$('subsystem-db-badge'),
    // Telemetry Counters
    telemetryHttp:   $('telemetry-http'),
    telemetryRag:    $('telemetry-rag'),
    telemetryAgent:  $('telemetry-agent'),
    telemetryInj:    $('telemetry-injections'),
    // Environment
    envAppName:      $('env-app-name'),
    envAppVersion:   $('env-app-version'),
    envAppEnv:       $('env-app-env'),
  });

  async function refresh() {
    if (isPolling) return;
    isPolling = true;
    const refs = r();

    try {
      // 1. Fetch JSON monitoring summary
      const summary = await THRESHOLDAPI.monitoring.getSummary();
      _renderSummary(summary);
    } catch (e) {
      console.error('Failed to load monitoring summary:', e);
      _renderError(e.message);
    }

    try {
      // 2. Fetch raw Prometheus metrics
      const resp = await fetch('/metrics');
      if (resp.ok) {
        const text = await resp.text();
        if (refs.promPreview) refs.promPreview.textContent = text;
      }
    } catch (e) {
      if (refs.promPreview) refs.promPreview.textContent = '# Could not scrape /metrics: ' + e.message;
    } finally {
      isPolling = false;
      if (refs.lastUpdated) refs.lastUpdated.textContent = 'Updated ' + new Date().toLocaleTimeString();
    }
  }

  function _renderSummary(data) {
    const refs = r();
    if (!data) return;

    // Environment
    if (refs.envAppName) refs.envAppName.textContent = data.app_name || 'THRESHOLD AI';
    if (refs.envAppVersion) refs.envAppVersion.textContent = 'v' + (data.version || '1.0.0');
    if (refs.envAppEnv) {
      refs.envAppEnv.textContent = (data.environment || 'production').toUpperCase();
    }

    // Liveness
    const live = data.liveness || {};
    const isLive = live.status === 'HEALTHY' || live.status === 'UP' || live.status === 'ok';
    if (refs.probeLiveness) {
      refs.probeLiveness.textContent = isLive ? 'HEALTHY' : 'UNHEALTHY';
      refs.probeLiveness.className = `probe-status-text ${isLive ? 'text-success' : 'text-danger'}`;
    }
    if (refs.iconLiveness) {
      refs.iconLiveness.className = `probe-icon-wrapper ${isLive ? 'healthy' : 'unhealthy'}`;
    }
    if (refs.subtextLiveness) {
      refs.subtextLiveness.textContent = `Uptime: ${live.uptime_seconds ? Math.round(live.uptime_seconds) + 's' : 'Active'}`;
    }

    // Readiness
    const ready = data.readiness || {};
    const isReady = ready.status === 'READY' || ready.status === 'UP' || ready.status === 'ok';
    if (refs.probeReadiness) {
      refs.probeReadiness.textContent = isReady ? 'READY' : 'DEGRADED';
      refs.probeReadiness.className = `probe-status-text ${isReady ? 'text-success' : 'text-danger'}`;
    }
    if (refs.iconReadiness) {
      refs.iconReadiness.className = `probe-icon-wrapper ${isReady ? 'healthy' : 'unhealthy'}`;
    }
    if (refs.subtextReadiness) {
      refs.subtextReadiness.textContent = isReady ? 'All subsystems operational' : (ready.reason || 'Subsystem check failed');
    }

    // Database check
    const checks = ready.checks || {};
    const dbCheck = checks.database;
    const isDbOk = dbCheck === 'CONNECTED' || dbCheck === 'READY' || dbCheck === 'OK' || dbCheck === true;
    if (refs.probeDb) {
      refs.probeDb.textContent = isDbOk ? 'CONNECTED' : 'DISCONNECTED';
      refs.probeDb.className = `probe-status-text ${isDbOk ? 'text-success' : 'text-danger'}`;
    }
    if (refs.subsystemDbBadge) {
      refs.subsystemDbBadge.textContent = isDbOk ? 'UP (Healthy)' : 'ERROR';
      refs.subsystemDbBadge.className = `badge ${isDbOk ? 'badge-success' : 'badge-danger'} text-xs`;
    }

    // Telemetry Counters
    const telem = data.telemetry || {};
    if (refs.telemetryHttp) refs.telemetryHttp.textContent = (telem.total_http_requests || 0).toLocaleString();
    if (refs.telemetryRag) refs.telemetryRag.textContent = (telem.total_rag_requests || 0).toLocaleString();
    if (refs.telemetryAgent) refs.telemetryAgent.textContent = (telem.total_agent_executions || 0).toLocaleString();
    if (refs.telemetryInj) refs.telemetryInj.textContent = (telem.total_prompt_injections_detected || 0).toLocaleString();
  }

  function _renderError(msg) {
    const refs = r();
    if (refs.probeLiveness) {
      refs.probeLiveness.textContent = 'UNREACHABLE';
      refs.probeLiveness.className = 'probe-status-text text-danger';
    }
    if (refs.lastUpdated) refs.lastUpdated.textContent = 'Failed to update: ' + msg;
  }

  function _setupAutoRefresh() {
    const refs = r();
    if (timer) clearInterval(timer);

    if (refs.autoRefresh?.checked) {
      timer = setInterval(refresh, 10000);
    }
  }

  function init() {
    const refs = r();
    refs.refreshBtn?.addEventListener('click', refresh);
    refs.autoRefresh?.addEventListener('change', _setupAutoRefresh);

    refs.copyPromBtn?.addEventListener('click', () => {
      const text = refs.promPreview?.textContent || '';
      navigator.clipboard.writeText(text).then(() => {
        if (typeof Toast !== 'undefined') Toast.success('Prometheus metrics copied to clipboard');
      });
    });

    refresh();
    _setupAutoRefresh();
  }

  return { init, refresh };
})();
