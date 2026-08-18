/**
 * profile.js — GET/PUT /api/v1/profile
 */
const ProfilePage = (() => {
  async function load() {
    try {
      const data = await THRESHOLDAPI.profile.get();
      _populate(data);
    } catch (e) { console.warn('[Profile]', e.message); }
  }

  function _populate(data) {
    const set  = (id, v) => { const el = document.getElementById(id); if (el) el.value = v || ''; };
    const setText = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = v || ''; };
    set('profile-name',       data.name);
    set('profile-role',       data.role);
    set('profile-email',      data.email);
    set('profile-department', data.department);
    setText('display-name',   data.name || 'Admin User');
    setText('display-role',   data.role || 'User');
    setText('display-dept',   data.department || '');
    // Avatar initials
    _updateAvatarInitials('profile-avatar', data.name);

    // Stats
    setText('stat-total-actions',  data.total_actions ?? '—');
    setText('stat-reviews-done',   data.reviews_completed ?? '—');
    setText('stat-last-login',     data.last_login ? _rel(data.last_login) : '—');
    setText('stat-joined',         data.joined_at  ? new Date(data.joined_at).getFullYear() : '—');
    // Activity
    if (data.recent_activity?.length) _renderActivity(data.recent_activity);
    // Sync navbar
    const navName = document.getElementById('nav-user-name');
    if (navName && data.name) navName.textContent = data.name;
    _updateAvatarInitials('nav-user-avatar', data.name);
  }

  function _updateAvatarInitials(id, name) {
    const el = document.getElementById(id);
    if (!el || !name) return;
    const initials = typeof window.getInitials === 'function'
      ? window.getInitials(name)
      : name.trim().slice(0, 2).toUpperCase();
    let textUpdated = false;
    el.childNodes.forEach(node => {
      if (node.nodeType === Node.TEXT_NODE && node.textContent.trim()) {
        node.textContent = initials;
        textUpdated = true;
      }
    });
    if (!textUpdated) {
      el.insertBefore(document.createTextNode(initials), el.firstChild);
    }
  }

  function _renderActivity(items) {
    const list = document.getElementById('profile-activity-list');
    if (!list) return;
    const esc = s => { const d = document.createElement('div'); d.textContent = String(s||''); return d.innerHTML; };
    const rel = ts => { if(!ts) return ''; const m=Math.floor((Date.now()-new Date(ts).getTime())/60000); return m<1?'just now':m<60?`${m}m ago`:`${Math.floor(m/60)}h ago`; };
    const icons = { action:'fa-bolt', review:'fa-eye', approve:'fa-check', reject:'fa-xmark', login:'fa-right-to-bracket' };
    const bgs   = { action:'blue', review:'yellow', approve:'green', reject:'red', login:'cyan' };
    list.innerHTML = items.map(item => `
      <div class="activity-item">
        <div class="activity-icon ${bgs[item.type]||''}">
          <i class="fa-solid ${icons[item.type]||'fa-circle'}"></i>
        </div>
        <div class="activity-content">
          <div class="activity-title">${esc(item.description||'—')}</div>
          <div class="activity-meta">
            <span class="activity-time">${rel(item.timestamp)}</span>
          </div>
        </div>
      </div>`).join('');
  }

  async function save() {
    const btn = document.getElementById('save-profile-btn');
    if (btn) btn.disabled = true;
    try {
      const payload = {
        name:       document.getElementById('profile-name')?.value.trim(),
        email:      document.getElementById('profile-email')?.value.trim(),
        department: document.getElementById('profile-department')?.value.trim(),
      };
      await THRESHOLDAPI.profile.update(payload);
      // Reflect changes immediately
      const dName = document.getElementById('display-name');
      const dDept = document.getElementById('display-dept');
      if (dName && payload.name) dName.textContent = payload.name;
      if (dDept && payload.department) dDept.textContent = payload.department;
      _updateAvatarInitials('profile-avatar', payload.name);
      _updateAvatarInitials('nav-user-avatar', payload.name);
      const navName = document.getElementById('nav-user-name');
      if (navName && payload.name) navName.textContent = payload.name;
      if (typeof Toast !== 'undefined') Toast.success('Profile saved');
    } catch (e) {
      if (typeof Toast !== 'undefined') Toast.danger('Save failed', e.message);
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  function init() {
    load();
    document.getElementById('save-profile-btn')?.addEventListener('click', save);
    // Live name sync
    document.getElementById('profile-name')?.addEventListener('input', e => {
      const val = e.target.value.trim();
      const d = document.getElementById('display-name');
      if (d) d.textContent = val || 'Admin User';
      if (val) {
        _updateAvatarInitials('profile-avatar', val);
        _updateAvatarInitials('nav-user-avatar', val);
        const navName = document.getElementById('nav-user-name');
        if (navName) navName.textContent = val;
      }
    });
    document.getElementById('profile-department')?.addEventListener('input', e => {
      const d = document.getElementById('display-dept');
      if (d) d.textContent = e.target.value;
    });
    // Avatar upload
    document.getElementById('avatar-edit-btn')?.addEventListener('click', () => {
      document.getElementById('avatar-upload')?.click();
    });
    document.getElementById('change-password-btn')?.addEventListener('click', () => {
      if (typeof Modal !== 'undefined') Modal.open('change-password-modal');
    });
  }

  document.addEventListener('DOMContentLoaded', init);
  return { init, load };
})();
