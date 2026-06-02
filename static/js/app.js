// ── Utilitários ───────────────────────────────────────────────────────

function timeClass(ms) {
  if (!ms) return 'time-none';
  if (ms < 500)  return 'time-fast';
  if (ms < 1500) return 'time-medium';
  return 'time-slow';
}

function uptimeClass(pct) {
  if (pct === null || pct === undefined) return '';
  if (pct >= 99) return 'uptime-good';
  if (pct >= 90) return 'uptime-ok';
  return 'uptime-bad';
}

function now() { return new Date().toLocaleTimeString('pt-BR'); }

// ── Toast ─────────────────────────────────────────────────────────────

function showToast(message, type) {
  type = type || 'info';
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    document.body.appendChild(container);
  }
  const toast = document.createElement('div');
  toast.className = 'toast toast-' + type;
  toast.innerHTML =
    '<span class="toast-icon">' + (type==='success'?'✅':type==='error'?'🔴':type==='warning'?'🟡':'ℹ️') + '</span>' +
    '<span class="toast-msg">' + message + '</span>' +
    '<button class="toast-close" onclick="this.parentElement.remove()">✕</button>';
  container.appendChild(toast);
  setTimeout(function() { if (toast.parentElement) toast.remove(); }, 5000);
}

async function requestNotificationPermission() {
  if ('Notification' in window && Notification.permission === 'default') {
    await Notification.requestPermission();
  }
}

function sendBrowserNotification(title, body) {
  if ('Notification' in window && Notification.permission === 'granted') {
    new Notification(title, { body: body });
  }
}

var lastAlertId = null;

async function checkNewAlerts() {
  try {
    const res  = await fetch('/api/alerts?limit=1');
    const data = await res.json();
    if (!data.alerts.length) return;
    const latest = data.alerts[0];
    if (lastAlertId === null) { lastAlertId = latest.id; return; }
    if (latest.id !== lastAlertId) {
      lastAlertId = latest.id;
      const isDown = latest.new_status !== 'online';
      const msg    = isDown ? '🔴 ' + latest.name + ' saiu do ar!' : '🟢 ' + latest.name + ' voltou ao ar!';
      showToast(msg, isDown ? 'error' : 'success');
      sendBrowserNotification('Monitor de Links', msg);
    }
  } catch(e) {}
}

// ── Agendamento ───────────────────────────────────────────────────────

var refreshInterval = 60000;
var refreshTimer    = null;
var countdown       = 0;
var countdownTimer  = null;

async function loadInterval() {
  try {
    const res  = await fetch('/api/scheduler');
    const data = await res.json();
    refreshInterval = data.interval_seconds * 1000;
    document.getElementById('interval-select').value = data.interval_seconds;
  } catch(e) {}
}

async function updateInterval() {
  const seconds = parseInt(document.getElementById('interval-select').value);
  try {
    await fetch('/api/scheduler', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ interval_seconds: seconds }),
    });
    refreshInterval = seconds * 1000;
    restartTimer();
    showToast('Intervalo atualizado para ' + seconds + 's', 'success');
  } catch(e) {
    showToast('Erro ao atualizar intervalo', 'error');
  }
}

function restartTimer() {
  if (refreshTimer)   clearInterval(refreshTimer);
  if (countdownTimer) clearInterval(countdownTimer);
  refreshTimer   = setInterval(refresh, refreshInterval);
  countdown      = refreshInterval / 1000;
  countdownTimer = setInterval(updateCountdown, 1000);
}

function updateCountdown() {
  countdown--;
  if (countdown <= 0) countdown = refreshInterval / 1000;
  const el = document.getElementById('next-check');
  if (el) el.textContent = 'Próxima verificação em ' + countdown + 's';
}

// ── Cards ─────────────────────────────────────────────────────────────

function updateCards(results) {
  document.getElementById('count-online').textContent  = results.filter(function(r){ return r.status==='online'; }).length;
  document.getElementById('count-slow').textContent    = results.filter(function(r){ return r.status==='slow'; }).length;
  document.getElementById('count-offline').textContent = results.filter(function(r){ return r.status==='offline'; }).length;
  document.getElementById('count-total').textContent   = results.reduce(function(s,r){ return s+(r.total_checks||0); }, 0);
}

// ── Filtro de pesquisa ────────────────────────────────────────────────

function filterTable() {
  const input   = document.getElementById('search-input');
  const countEl = document.getElementById('search-count');
  if (!input) return;
  const query = input.value.toLowerCase().trim();
  const rows  = document.querySelectorAll('#status-table tr');
  let visible = 0;
  rows.forEach(function(row) {
    if (row.querySelector('td[colspan]')) return;
    const text = row.textContent.toLowerCase();
    if (!query || text.includes(query)) {
      row.style.display = '';
      visible++;
    } else {
      row.style.display = 'none';
    }
  });
  if (countEl) {
    countEl.textContent = query ? (visible + ' resultado(s)') : '';
  }
}

// ── Tabela ────────────────────────────────────────────────────────────

function updateTable(results) {
  const tbody = document.getElementById('status-table');
  if (!results.length) {
    tbody.innerHTML = '<tr><td colspan="7" class="loading">Nenhuma URL cadastrada.</td></tr>';
    return;
  }
  tbody.innerHTML = results.map(function(r) {
    const timeStr = r.response_time_ms ? r.response_time_ms + 'ms' : '—';
    const uptStr  = r.uptime_pct !== null && r.uptime_pct !== undefined ? r.uptime_pct + '%' : '—';
    return '<tr>' +
      '<td><span class="badge ' + r.status + '">' + r.status + '</span></td>' +
      '<td>' + r.name + '</td>' +
      '<td class="' + timeClass(r.response_time_ms) + '">' + timeStr + '</td>' +
      '<td class="' + uptimeClass(r.uptime_pct) + '">' + uptStr + '</td>' +
      '<td style="color:var(--muted)">' + r.category + '</td>' +
      '<td style="font-size:12px"><a href="' + r.url + '" target="_blank" style="color:var(--blue);text-decoration:none">' + r.url + '</a></td>' +
      '<td><button class="btn-danger" onclick="removeUrl(\'' + r.url + '\',\'' + r.name + '\')" title="Remover">🗑</button></td>' +
      '</tr>';
  }).join('');
  filterTable();
}

// ── Alertas ───────────────────────────────────────────────────────────

async function updateAlerts() {
  try {
    const res  = await fetch('/api/alerts?limit=5');
    const data = await res.json();
    const list = document.getElementById('alerts-list');
    if (!data.alerts.length) {
      list.innerHTML = '<div class="loading">Nenhum alerta registrado.</div>';
      return;
    }
    list.innerHTML = data.alerts.map(function(a) {
      const isDown = a.new_status !== 'online';
      const time   = a.triggered_at.slice(11,19);
      return '<div class="alert-item">' +
        '<span class="alert-icon">' + (isDown ? '🔴' : '🟢') + '</span>' +
        '<div class="alert-info">' +
        '<div class="alert-name">' + (isDown ? a.name+' saiu do ar' : a.name+' voltou ao ar') + '</div>' +
        '<div class="alert-detail">' + a.old_status + ' → ' + a.new_status + ' · ' + a.url + '</div>' +
        '</div>' +
        '<span class="alert-time">' + time + '</span>' +
        '</div>';
    }).join('');
  } catch(e) {}
}

// ── Refresh ───────────────────────────────────────────────────────────

async function refresh() {
  const label = document.getElementById('checking-label');
  label.textContent = '⟳ Verificando...';
  try {
    const res  = await fetch('/api/status');
    const data = await res.json();
    updateCards(data.results);
    updateTable(data.results);
    await updateAlerts();
    await checkNewAlerts();
    document.getElementById('last-update').textContent = 'Atualizado às ' + now();
    label.textContent = '';
    countdown = refreshInterval / 1000;
  } catch(e) {
    label.textContent = '⚠️ Erro ao atualizar';
  }
}

// ── Modal adicionar URL ───────────────────────────────────────────────

function openModal() {
  document.getElementById('modal-overlay').classList.add('open');
  document.getElementById('input-url').focus();
}

function closeModal() {
  document.getElementById('modal-overlay').classList.remove('open');
  document.getElementById('input-url').value = '';
  document.getElementById('input-name').value = '';
  document.getElementById('input-category').value = 'geral';
  document.getElementById('form-error').textContent = '';
}

async function addUrl() {
  const url      = document.getElementById('input-url').value.trim();
  const name     = document.getElementById('input-name').value.trim();
  const category = document.getElementById('input-category').value.trim() || 'geral';
  const errorEl  = document.getElementById('form-error');
  if (!url)  { errorEl.textContent = 'Informe a URL.';  return; }
  if (!name) { errorEl.textContent = 'Informe o nome.'; return; }
  if (!url.startsWith('http')) { errorEl.textContent = 'A URL deve começar com http:// ou https://'; return; }
  try {
    const res  = await fetch('/api/links', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: url, name: name, category: category }),
    });
    const data = await res.json();
    if (!res.ok) { errorEl.textContent = data.detail || 'Erro ao salvar.'; return; }
    closeModal();
    showToast('✅ ' + name + ' adicionado!', 'success');
    refresh();
  } catch(e) {
    errorEl.textContent = 'Erro de conexão.';
  }
}

async function removeUrl(url, name) {
  if (!confirm('Remover "' + name + '" do monitoramento?')) return;
  try {
    const res = await fetch('/api/links?url=' + encodeURIComponent(url), { method: 'DELETE' });
    if (res.ok) { showToast('🗑 ' + name + ' removido', 'warning'); refresh(); }
  } catch(e) {}
}

// ── Modal importar planilha ───────────────────────────────────────────

function openImportModal() {
  document.getElementById('import-overlay').classList.add('open');
  document.getElementById('import-result').innerHTML = '';
}

function closeImportModal() {
  document.getElementById('import-overlay').classList.remove('open');
  document.getElementById('import-file').value = '';
  document.getElementById('import-result').innerHTML = '';
}

async function importFile() {
  const fileInput = document.getElementById('import-file');
  const resultEl  = document.getElementById('import-result');
  if (!fileInput.files.length) { resultEl.innerHTML = '<p style="color:var(--red)">Selecione um arquivo.</p>'; return; }
  const formData = new FormData();
  formData.append('file', fileInput.files[0]);
  resultEl.innerHTML = '<p style="color:var(--muted)">⟳ Importando...</p>';
  try {
    const res  = await fetch('/api/links/import', { method: 'POST', body: formData });
    const data = await res.json();
    if (!res.ok) { resultEl.innerHTML = '<p style="color:var(--red)">Erro: ' + data.error + '</p>'; return; }
    let html = '';
    if (data.total > 0) {
      html += '<p style="color:var(--green)">✅ ' + data.total + ' URL(s) importada(s)!</p>';
      html += '<ul style="color:var(--green);font-size:12px;margin:6px 0 0 16px">';
      data.imported.forEach(function(n) { html += '<li>' + n + '</li>'; });
      html += '</ul>';
    }
    if (data.skipped.length) html += '<p style="color:var(--muted);margin-top:8px">⚠️ ' + data.skipped.length + ' já cadastrada(s)</p>';
    if (data.errors.length)  html += '<p style="color:var(--red);margin-top:8px">❌ ' + data.errors.length + ' erro(s)</p>';
    if (!data.total && !data.errors.length) html = '<p style="color:var(--muted)">Nenhuma URL nova encontrada.</p>';
    resultEl.innerHTML = html;
    if (data.total > 0) {
      showToast('✅ ' + data.total + ' URL(s) importada(s)!', 'success');
      setTimeout(function() { refresh(); closeImportModal(); }, 2000);
    }
  } catch(e) {
    resultEl.innerHTML = '<p style="color:var(--red)">Erro de conexão.</p>';
  }
}

// ── Teclado ───────────────────────────────────────────────────────────

document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') { closeModal(); closeImportModal(); }
});

// ── Inicialização ─────────────────────────────────────────────────────

(async function() {
  await requestNotificationPermission();
  await loadInterval();
  await refresh();
  restartTimer();
})();
