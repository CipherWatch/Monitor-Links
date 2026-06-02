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

function now() {
  return new Date().toLocaleTimeString('pt-BR');
}


// ── Cards ─────────────────────────────────────────────────────────────

function updateCards(results) {
  document.getElementById('count-online').textContent  = results.filter(r => r.status === 'online').length;
  document.getElementById('count-slow').textContent    = results.filter(r => r.status === 'slow').length;
  document.getElementById('count-offline').textContent = results.filter(r => r.status === 'offline').length;
  document.getElementById('count-total').textContent   = results.reduce((s, r) => s + (r.total_checks || 0), 0);
}


// ── Tabela ────────────────────────────────────────────────────────────

function updateTable(results) {
  const tbody = document.getElementById('status-table');

  if (!results.length) {
    tbody.innerHTML = '<tr><td colspan="7" class="loading">Nenhuma URL cadastrada.</td></tr>';
    return;
  }

  tbody.innerHTML = results.map(r => `
    <tr>
      <td><span class="badge ${r.status}">${r.status}</span></td>
      <td>${r.name}</td>
      <td class="${timeClass(r.response_time_ms)}">${r.response_time_ms ? r.response_time_ms + 'ms' : '—'}</td>
      <td class="${uptimeClass(r.uptime_pct)}">${r.uptime_pct !== null ? r.uptime_pct + '%' : '—'}</td>
      <td style="color:var(--muted)">${r.category}</td>
      <td style="font-size:12px">
        <a href="${r.url}" target="_blank" style="color:var(--blue);text-decoration:none">${r.url}</a>
      </td>
      <td>
        <button class="btn-danger" onclick="removeUrl('${r.url}', '${r.name}')" title="Remover">🗑</button>
      </td>
    </tr>
  `).join('');
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

    list.innerHTML = data.alerts.map(a => {
      const isDown = a.new_status !== 'online';
      const icon   = isDown ? '🔴' : '🟢';
      const desc   = isDown ? `${a.name} saiu do ar` : `${a.name} voltou ao ar`;
      const time   = a.triggered_at.slice(11, 19);
      return `
        <div class="alert-item">
          <span class="alert-icon">${icon}</span>
          <div class="alert-info">
            <div class="alert-name">${desc}</div>
            <div class="alert-detail">${a.old_status} → ${a.new_status} · ${a.url}</div>
          </div>
          <span class="alert-time">${time}</span>
        </div>
      `;
    }).join('');
  } catch(e) {
    console.error('Erro alertas:', e);
  }
}


// ── Refresh principal ─────────────────────────────────────────────────

async function refresh() {
  const label = document.getElementById('checking-label');
  label.textContent = '⟳ Verificando...';
  try {
    const res  = await fetch('/api/status');
    const data = await res.json();
    updateCards(data.results);
    updateTable(data.results);
    await updateAlerts();
    document.getElementById('last-update').textContent = `Atualizado às ${now()}`;
    label.textContent = '';
  } catch(e) {
    label.textContent = '⚠️ Erro ao atualizar';
  }
}


// ── Modal ─────────────────────────────────────────────────────────────

function openModal() {
  document.getElementById('modal-overlay').classList.add('open');
  document.getElementById('input-url').focus();
  document.getElementById('form-error').textContent = '';
}

function closeModal() {
  document.getElementById('modal-overlay').classList.remove('open');
  document.getElementById('input-url').value = '';
  document.getElementById('input-name').value = '';
  document.getElementById('input-category').value = 'geral';
  document.getElementById('form-error').textContent = '';
}

// Fecha modal com ESC
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') closeModal();
});


// ── Adicionar URL ─────────────────────────────────────────────────────

async function addUrl() {
  const url      = document.getElementById('input-url').value.trim();
  const name     = document.getElementById('input-name').value.trim();
  const category = document.getElementById('input-category').value.trim() || 'geral';
  const errorEl  = document.getElementById('form-error');

  // Validação básica no front
  if (!url)  { errorEl.textContent = 'Informe a URL.';  return; }
  if (!name) { errorEl.textContent = 'Informe o nome.'; return; }
  if (!url.startsWith('http')) {
    errorEl.textContent = 'A URL deve começar com http:// ou https://';
    return;
  }

  try {
    const res = await fetch('/api/links', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url, name, category }),
    });

    const data = await res.json();

    if (!res.ok) {
      // Erro vindo da API (ex: URL já cadastrada)
      errorEl.textContent = data.detail || 'Erro ao salvar.';
      return;
    }

    closeModal();
    refresh(); // Atualiza a tabela imediatamente

  } catch(e) {
    errorEl.textContent = 'Erro de conexão com o servidor.';
  }
}


// ── Remover URL ───────────────────────────────────────────────────────

async function removeUrl(url, name) {
  if (!confirm(`Remover "${name}" do monitoramento?`)) return;

  try {
    const res = await fetch(`/api/links?url=${encodeURIComponent(url)}`, {
      method: 'DELETE',
    });

    if (res.ok) {
      refresh(); // Atualiza a tabela
    } else {
      const data = await res.json();
      alert('Erro: ' + (data.detail || 'Não foi possível remover.'));
    }
  } catch(e) {
    alert('Erro de conexão.');
  }
}


// ── Inicialização ─────────────────────────────────────────────────────

refresh();
setInterval(refresh, 30000);


// ── Modal de importação ───────────────────────────────────────────────

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

  if (!fileInput.files.length) {
    resultEl.innerHTML = '<p style="color:var(--red)">Selecione um arquivo.</p>';
    return;
  }

  const file    = fileInput.files[0];
  const formData = new FormData();
  formData.append('file', file);

  resultEl.innerHTML = '<p style="color:var(--muted)">⟳ Importando...</p>';

  try {
    const res  = await fetch('/api/links/import', {
      method: 'POST',
      body: formData,
    });
    const data = await res.json();

    if (!res.ok) {
      resultEl.innerHTML = `<p style="color:var(--red)">Erro: ${data.error}</p>`;
      return;
    }

    // Monta o resumo
    let html = '';

    if (data.total > 0) {
      html += `<p style="color:var(--green)">✅ ${data.total} URL(s) importada(s) com sucesso!</p>`;
      html += `<ul style="color:var(--green);font-size:12px;margin:6px 0 0 16px">`;
      data.imported.forEach(n => html += `<li>${n}</li>`);
      html += '</ul>';
    }

    if (data.skipped.length) {
      html += `<p style="color:var(--muted);margin-top:8px">⚠️ ${data.skipped.length} já cadastrada(s):</p>`;
      html += `<ul style="color:var(--muted);font-size:12px;margin:4px 0 0 16px">`;
      data.skipped.forEach(n => html += `<li>${n}</li>`);
      html += '</ul>';
    }

    if (data.errors.length) {
      html += `<p style="color:var(--red);margin-top:8px">❌ Erros:</p>`;
      html += `<ul style="color:var(--red);font-size:12px;margin:4px 0 0 16px">`;
      data.errors.forEach(e => html += `<li>${e}</li>`);
      html += '</ul>';
    }

    if (!data.total && !data.errors.length) {
      html = '<p style="color:var(--muted)">Nenhuma URL nova encontrada no arquivo.</p>';
    }

    resultEl.innerHTML = html;

    // Atualiza a tabela se importou algo
    if (data.total > 0) {
      setTimeout(() => { refresh(); closeImportModal(); }, 2000);
    }

  } catch(e) {
    resultEl.innerHTML = '<p style="color:var(--red)">Erro de conexão com o servidor.</p>';
  }
}


// ── Modal de importação ───────────────────────────────────────────────

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

  if (!fileInput.files.length) {
    resultEl.innerHTML = '<p style="color:var(--red)">Selecione um arquivo.</p>';
    return;
  }

  const file    = fileInput.files[0];
  const formData = new FormData();
  formData.append('file', file);

  resultEl.innerHTML = '<p style="color:var(--muted)">⟳ Importando...</p>';

  try {
    const res  = await fetch('/api/links/import', {
      method: 'POST',
      body: formData,
    });
    const data = await res.json();

    if (!res.ok) {
      resultEl.innerHTML = `<p style="color:var(--red)">Erro: ${data.error}</p>`;
      return;
    }

    // Monta o resumo
    let html = '';

    if (data.total > 0) {
      html += `<p style="color:var(--green)">✅ ${data.total} URL(s) importada(s) com sucesso!</p>`;
      html += `<ul style="color:var(--green);font-size:12px;margin:6px 0 0 16px">`;
      data.imported.forEach(n => html += `<li>${n}</li>`);
      html += '</ul>';
    }

    if (data.skipped.length) {
      html += `<p style="color:var(--muted);margin-top:8px">⚠️ ${data.skipped.length} já cadastrada(s):</p>`;
      html += `<ul style="color:var(--muted);font-size:12px;margin:4px 0 0 16px">`;
      data.skipped.forEach(n => html += `<li>${n}</li>`);
      html += '</ul>';
    }

    if (data.errors.length) {
      html += `<p style="color:var(--red);margin-top:8px">❌ Erros:</p>`;
      html += `<ul style="color:var(--red);font-size:12px;margin:4px 0 0 16px">`;
      data.errors.forEach(e => html += `<li>${e}</li>`);
      html += '</ul>';
    }

    if (!data.total && !data.errors.length) {
      html = '<p style="color:var(--muted)">Nenhuma URL nova encontrada no arquivo.</p>';
    }

    resultEl.innerHTML = html;

    // Atualiza a tabela se importou algo
    if (data.total > 0) {
      setTimeout(() => { refresh(); closeImportModal(); }, 2000);
    }

  } catch(e) {
    resultEl.innerHTML = '<p style="color:var(--red)">Erro de conexão com o servidor.</p>';
  }
}
