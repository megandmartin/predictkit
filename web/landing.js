'use strict';

(() => {
  const THEME_KEY = 'predictkit-studio-theme';
  const themes = new Set(['solana-signal', 'trust-layer', 'studio-classic']);
  const themeSelect = document.getElementById('theme');
  const probability = document.getElementById('probability');
  const result = document.getElementById('forecast-result');
  const outcomeButtons = [...document.querySelectorAll('[data-outcome]')];
  const scenarioButtons = [...document.querySelectorAll('[data-scenario]')];
  const examples = {
    builder: { question: 'Will the public demo ship before the sprint deadline?', initial: 68, history: [42, 44, 36, 51, 48, 62, 54, 63, 67, 68] },
    research: { question: 'Will our next research update support the original thesis?', initial: 54, history: [61, 58, 63, 54, 48, 51, 57, 49, 52, 54] },
    hackathon: { question: 'Will the team complete its end-to-end demo before judging?', initial: 76, history: [32, 39, 36, 49, 52, 46, 58, 65, 69, 73] }
  };
  let scenario = 'builder';
  let outcome = null;

  function applyTheme(theme) {
    if (!themes.has(theme)) return;
    document.documentElement.dataset.theme = theme;
    themeSelect.value = theme;
  }

  try { applyTheme(localStorage.getItem(THEME_KEY)); } catch { /* The page also works with storage blocked. */ }
  themeSelect.value = document.documentElement.dataset.theme;
  themeSelect.addEventListener('change', () => {
    applyTheme(themeSelect.value);
    try { localStorage.setItem(THEME_KEY, themeSelect.value); } catch { /* Keep this session's appearance. */ }
  });
  window.addEventListener('storage', event => {
    if (event.key === THEME_KEY && themes.has(event.newValue)) applyTheme(event.newValue);
  });

  function renderResult() {
    result.classList.toggle('scored', outcome !== null);
    if (!outcome) {
      result.textContent = 'Choose an outcome to see how your forecast scores.';
      return;
    }
    if (outcome === 'void') {
      result.textContent = 'VOID · No score. The question cannot be resolved under its rule.';
      return;
    }
    const estimate = Number(probability.value) / 100;
    const observed = outcome === 'yes' ? 1 : 0;
    const score = ((estimate - observed) ** 2).toFixed(4);
    result.textContent = `${outcome.toUpperCase()} · Brier score ${score}. Lower is better; a perfect forecast scores 0.`;
  }

  function renderForecast() {
    const value = Number(probability.value);
    document.getElementById('yes-probability').innerHTML = `${value}<span>%</span>`;
    document.getElementById('no-probability').innerHTML = `${100 - value}<span>%</span>`;
    probability.style.setProperty('--probability', `${value}%`);
    probability.setAttribute('aria-valuetext', `${value} percent chance of YES`);
    const series = [...examples[scenario].history, value];
    const points = series.map((p, index) => [index * 48, 144 - p * 1.25]);
    const path = points.map(([x, y], index) => `${index === 0 ? 'M' : 'L'}${x} ${y.toFixed(2)}`).join(' ');
    document.getElementById('forecast-line').setAttribute('d', path);
    document.getElementById('forecast-area').setAttribute('d', `${path}V154H0Z`);
    document.getElementById('forecast-end').setAttribute('cy', points.at(-1)[1]);
    renderResult();
  }

  probability.addEventListener('input', renderForecast);
  outcomeButtons.forEach(button => {
    button.addEventListener('click', () => {
      outcome = outcome === button.dataset.outcome ? null : button.dataset.outcome;
      outcomeButtons.forEach(item => item.setAttribute('aria-pressed', String(item.dataset.outcome === outcome)));
      renderResult();
    });
  });
  scenarioButtons.forEach(button => {
    button.addEventListener('click', () => {
      scenario = button.dataset.scenario;
      const example = examples[scenario];
      document.getElementById('forecast-title').textContent = example.question;
      probability.value = example.initial;
      outcome = null;
      scenarioButtons.forEach(item => {
        const selected = item === button;
        item.classList.toggle('selected', selected);
        item.setAttribute('aria-pressed', String(selected));
      });
      outcomeButtons.forEach(item => item.setAttribute('aria-pressed', 'false'));
      renderForecast();
    });
  });

  const copyButton = document.getElementById('copy-command');
  const command = document.getElementById('start-command');
  const copyStatus = document.getElementById('copy-status');
  copyButton.addEventListener('click', async () => {
    try {
      if (!navigator.clipboard?.writeText) throw new Error('Clipboard is unavailable.');
      await navigator.clipboard.writeText(command.textContent);
      copyButton.textContent = 'Copied';
      copyStatus.textContent = 'Command copied. Paste it into a terminal in the PredictKit project folder.';
    } catch {
      const range = document.createRange();
      range.selectNodeContents(command);
      const selection = window.getSelection();
      selection.removeAllRanges();
      selection.addRange(range);
      copyButton.textContent = 'Select command';
      copyStatus.textContent = 'Clipboard access is unavailable. The command is selected; copy it with your usual keyboard shortcut.';
    }
  });

  renderForecast();
})();
