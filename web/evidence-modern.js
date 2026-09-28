'use strict';
(() => {
  const $ = id => document.getElementById(id);
  const token = document.querySelector('meta[name="predictkit-token"]').content;
  const themes = ['solana-signal', 'trust-layer', 'studio-classic'];
  const themeSelect = $('evidence-theme');
  try {
    const theme = localStorage.getItem('predictkit-studio-theme');
    if (themes.includes(theme)) document.documentElement.dataset.theme = theme;
  } catch {}
  themeSelect.value = document.documentElement.dataset.theme;
  themeSelect.addEventListener('change', () => {
    if (!themes.includes(themeSelect.value)) return;
    document.documentElement.dataset.theme = themeSelect.value;
    try { localStorage.setItem('predictkit-studio-theme', themeSelect.value); } catch {}
  });

  const defaults = [
    ['files', 'Static artifact contracts'],
    ['approval', 'Founder approved exact brief and memo'],
    ['models', 'All eight roles have provider response IDs and usage'],
    ['parallel', 'Discovery task intervals overlap'],
    ['generated-browser', 'Generated live app browser tested'],
    ['chain', 'Meaningful Solana flow independently verified'],
    ['builders', 'Three independent builder rehearsals']
  ];
  const descriptions = {
    files: 'The coordinator checks the generated file contracts.',
    approval: 'The recorded approval binds the exact brief and build memo.',
    models: 'Actual provider identifiers and usage are required; fixtures do not qualify.',
    parallel: 'Recorded task intervals overlap. This alone does not prove live inference.',
    'generated-browser': 'The actual live-generated app needs separate browser testing.',
    chain: 'A complete chain-backed user flow needs independent verification.',
    builders: 'Three fresh builders must complete the agreed journey with outcomes recorded.'
  };
  let lastObserved = null;

  function render(checks) {
    const rows = document.createDocumentFragment();
    for (const check of checks) {
      const row = document.createElement('div');
      row.className = 'check' + (check.passed ? ' pass' : '');
      const symbol = document.createElement('span');
      symbol.className = 'check-symbol';
      symbol.setAttribute('aria-hidden', 'true');
      const icon = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
      icon.setAttribute('viewBox', '0 0 16 16');
      const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      path.setAttribute('d', check.passed ? 'm4 8 3 3 5-6' : 'M4 8h8');
      icon.append(path);
      symbol.append(icon);
      const content = document.createElement('div');
      const label = document.createElement('h3');
      const description = document.createElement('p');
      const status = document.createElement('span');
      label.textContent = check.label || check.name;
      description.textContent = descriptions[check.id] || check.detail || '';
      status.className = 'check-status';
      status.textContent = check.passed ? 'OBSERVED IN THIS RUN' : 'NOT YET PROVEN';
      content.append(label, description, status);
      row.append(symbol, content);
      rows.append(row);
    }
    $('checks').replaceChildren(rows);
    const observed = checks.filter(check => check.passed).length;
    $('observed-count').textContent = observed + ' / ' + checks.length + ' observed';
  }

  async function refresh() {
    const button = $('refresh');
    button.disabled = true;
    button.textContent = 'Reading evidence…';
    $('checks').setAttribute('aria-busy', 'true');
    $('status').classList.remove('connection-error');
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 12000);
    try {
      if (token.startsWith('__') || !/^https?:$/.test(location.protocol)) {
        throw new Error('Open the Evidence Desk through the local Python server.');
      }
      const response = await fetch('/api/readiness', {
        headers: { 'X-PredictKit-Token': token },
        cache: 'no-store',
        credentials: 'same-origin',
        signal: controller.signal
      });
      if (!response.ok) {
        throw new Error('The runtime rejected this evidence request (' + response.status + '). Reload the page to refresh the local session.');
      }
      const data = await response.json();
      if (!Array.isArray(data.checks)) throw new Error('The server returned an unrecognized evidence record.');
      render(data.checks);
      lastObserved = new Date();
      $('status').textContent = data.workshop_ready ? 'All declared release gates observed' : 'Release gates remain open';
      $('status-note').textContent = 'Read from the local runtime. No new work, paid call or transaction was launched.';
      $('provider-label').textContent = 'Recorded provider: ' + (data.provider || 'none');
      $('note').textContent = data.note || 'Each gate requires its own evidence.';
      $('checked-at').textContent = 'Last checked ' + lastObserved.toLocaleString();
    } catch (error) {
      $('status').classList.add('connection-error');
      $('status').textContent = lastObserved ? 'Connection lost · evidence may be stale' : 'Evidence is not connected';
      $('status-note').textContent = error.name === 'AbortError' ? 'The runtime did not respond. Refresh to try again.' : error.message;
      $('provider-label').textContent = lastObserved ? 'Showing the last observed record' : 'No current run verified';
    } finally {
      clearTimeout(timer);
      $('checks').setAttribute('aria-busy', 'false');
      button.disabled = false;
      button.innerHTML = 'Refresh evidence <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 7v5h-5M4 17v-5h5M6 7a7 7 0 0 1 12-1l2 3M4 15l2 3a7 7 0 0 0 12-1"/></svg>';
    }
  }

  render(defaults.map(([id, label]) => ({ id, label, passed: false })));
  $('refresh').addEventListener('click', refresh);
  refresh();
})();
