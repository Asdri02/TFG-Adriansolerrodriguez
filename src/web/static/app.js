// app.js — lógica de la página web del corrector semántico.

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

const STORAGE = {
  theme: 'tfg.theme',
  history: 'tfg.history',
};

// ────────────────────────────────────────────────────────────────────────────
// Tema
// ────────────────────────────────────────────────────────────────────────────

function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem(STORAGE.theme, theme);
}

const savedTheme = localStorage.getItem(STORAGE.theme)
  || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
applyTheme(savedTheme);

$('#btn-theme').addEventListener('click', () => {
  const current = document.documentElement.getAttribute('data-theme');
  const next = current === 'dark' ? 'light' : 'dark';
  applyTheme(next);
  // re-pintar gráficos si están vivos
  for (const chart of Object.values(CHARTS)) chart?.update();
});

// ────────────────────────────────────────────────────────────────────────────
// Navegación (landing + tabs)
// ────────────────────────────────────────────────────────────────────────────

function showLanding() {
  $$('.tab-panel').forEach((p) => p.classList.remove('active'));
  $('#tab-landing').classList.add('active');
  $('#tab-nav').classList.add('hidden');
  $$('.tab').forEach((b) => b.classList.remove('active'));
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function activateTab(name) {
  $$('.tab-panel').forEach((p) => p.classList.toggle('active', p.id === `tab-${name}`));
  $$('.tab').forEach((b) => b.classList.toggle('active', b.dataset.tab === name));
  $('#tab-nav').classList.remove('hidden');
  if (name === 'history') renderHistory();
}

$$('.tab').forEach((b) => b.addEventListener('click', () => activateTab(b.dataset.tab)));
$('#btn-home').addEventListener('click', showLanding);

// Cards de landing + cualquier botón con data-go (empty state, etc.)
document.addEventListener('click', (e) => {
  const target = e.target.closest('[data-go]');
  if (target) activateTab(target.dataset.go);
});

// ────────────────────────────────────────────────────────────────────────────
// Estado
// ────────────────────────────────────────────────────────────────────────────

let CASES = [];
const CHARTS = { donut: null, subject: null, topic: null, scatter: null, perq: null };

// ────────────────────────────────────────────────────────────────────────────
// Carga inicial de casos
// ────────────────────────────────────────────────────────────────────────────

async function loadCases() {
  const res = await fetch('/api/cases');
  CASES = await res.json();
  const select = $('#case-select');
  for (const c of CASES) {
    const opt = document.createElement('option');
    opt.value = String(c.id);
    opt.textContent = `[${String(c.id).padStart(2, '0')}] ${c.subject} · ${c.topic} — ${c.desc}`;
    select.appendChild(opt);
  }
}

loadCases().catch((err) => console.error('Error cargando casos', err));

// ────────────────────────────────────────────────────────────────────────────
// Selector de caso vs personalizado
// ────────────────────────────────────────────────────────────────────────────

$('#case-select').addEventListener('change', (e) => {
  const id = parseInt(e.target.value, 10);
  if (!id) {
    showCustomRef();
    return;
  }
  const c = CASES.find((x) => x.id === id);
  if (!c) return;
  showCaseRef(c);
  $('#student-answer').value = c.student_answer;
});

function showCaseRef(c) {
  $('#reference-custom').classList.add('hidden');
  $('#reference-view').classList.remove('hidden');
  $('#ref-subject').textContent = c.subject;
  $('#ref-level').textContent = c.education_level;
  $('#ref-question').textContent = c.question;
  $('#ref-ideal').textContent = c.ideal_answer;

  const concepts = $('#ref-concepts');
  concepts.innerHTML = '';
  for (const k of c.key_concepts) {
    const chip = document.createElement('span');
    chip.className = 'concept-chip';
    chip.innerHTML = `${escapeHtml(k.concept)} <span class="w">· ${k.weight.toFixed(2)}</span>`;
    concepts.appendChild(chip);
  }
}

function showCustomRef() {
  $('#reference-view').classList.add('hidden');
  $('#reference-custom').classList.remove('hidden');
}

// ────────────────────────────────────────────────────────────────────────────
// Conceptos personalizados (parser)
// ────────────────────────────────────────────────────────────────────────────

function parseCustomConcepts(raw) {
  const lines = raw.split('\n').map((l) => l.trim()).filter(Boolean);
  const concepts = [];
  for (const line of lines) {
    const idx = line.lastIndexOf(':');
    if (idx === -1) throw new Error(`Línea sin peso: «${line}» (usa formato concepto:peso)`);
    const concept = line.slice(0, idx).trim();
    const weight = parseFloat(line.slice(idx + 1).trim());
    if (!concept || Number.isNaN(weight)) {
      throw new Error(`No puedo parsear: «${line}»`);
    }
    concepts.push({ concept, weight });
  }
  if (!concepts.length) throw new Error('Añade al menos un concepto clave.');
  return concepts;
}

// ────────────────────────────────────────────────────────────────────────────
// Corregir
// ────────────────────────────────────────────────────────────────────────────

$('#btn-grade').addEventListener('click', async () => {
  const studentAnswer = $('#student-answer').value.trim();
  if (!studentAnswer) {
    alert('Escribe la respuesta del alumno.');
    return;
  }

  const caseId = parseInt($('#case-select').value, 10);
  let body, url;

  if (caseId) {
    url = '/api/grade_case';
    body = { case_id: caseId, student_answer: studentAnswer };
  } else {
    const question = $('#cust-question').value.trim();
    const ideal = $('#cust-ideal').value.trim();
    if (!question || !ideal) {
      alert('Completa pregunta y respuesta ideal.');
      return;
    }
    let conceptList;
    try {
      conceptList = parseCustomConcepts($('#cust-concepts').value);
    } catch (e) {
      alert(e.message);
      return;
    }
    url = '/api/grade';
    body = {
      student_answer: studentAnswer,
      reference: {
        question,
        subject: $('#cust-subject').value.trim() || 'General',
        education_level: $('#cust-level').value.trim() || 'Bachillerato',
        ideal_answer: ideal,
        key_concepts: conceptList,
      },
    };
  }

  const btn = $('#btn-grade');
  btn.disabled = true;
  btn.textContent = 'Corrigiendo...';

  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      alert(`Error: ${err.detail || res.statusText}`);
      return;
    }

    const data = await res.json();
    renderResult(data, studentAnswer);
    saveToHistory(data, studentAnswer);
    updateHistoryBadge();
  } finally {
    btn.disabled = false;
    btn.textContent = 'Corregir';
  }
});

$('#btn-reset').addEventListener('click', () => {
  $('#student-answer').value = '';
  $('#result-card').classList.add('hidden');
});

// ────────────────────────────────────────────────────────────────────────────
// Render del resultado
// ────────────────────────────────────────────────────────────────────────────

function renderResult(data, studentAnswer) {
  const card = $('#result-card');
  card.classList.remove('hidden');
  card.scrollIntoView({ behavior: 'smooth', block: 'start' });

  const score = data.score_over_10;
  animateScore('#score-big', score, 2);
  // se anima en la siguiente frame para que se vea la transición CSS
  requestAnimationFrame(() => {
    $('#score-fill').style.width = `${(score / 10) * 100}%`;
  });
  $('#feedback').textContent = data.feedback;

  $('#m-concept').textContent = data.concept_ratio.toFixed(3);
  $('#m-similarity').textContent = data.similarity_ratio.toFixed(3);
  $('#m-length').textContent = data.length_penalty.toFixed(3);

  const banner = $('#antipattern-banner');
  const hits = data.antipatterns_hit || [];
  if (hits.length) {
    banner.classList.remove('hidden');
    $('#antipattern-text').textContent =
      hits.map((h) => `«${h.phrase}» asociado a «${h.concept}» (×${h.penalty})`).join('; ');
  } else {
    banner.classList.add('hidden');
  }

  renderComparison(data, studentAnswer);
  fillListAnimated('#list-detected', data.detected_concepts, 'Ninguno');
  fillListAnimated('#list-partial', data.partial_concepts, 'Ninguno');
  fillListAnimated('#list-missing', data.missing_concepts, 'Ninguno');
}

function animateScore(sel, target, decimals) {
  const el = $(sel);
  const start = performance.now();
  const duration = 700;
  const startVal = 0;

  function step(now) {
    const t = Math.min((now - start) / duration, 1);
    const eased = 1 - Math.pow(1 - t, 3);
    const value = startVal + (target - startVal) * eased;
    el.textContent = value.toFixed(decimals);
    if (t < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}

function fillListAnimated(sel, items, emptyText) {
  const ul = $(sel);
  ul.innerHTML = '';
  if (!items.length) {
    const li = document.createElement('li');
    li.textContent = emptyText;
    li.style.color = 'var(--muted)';
    ul.appendChild(li);
    return;
  }
  items.forEach((x, i) => {
    const li = document.createElement('li');
    li.textContent = x;
    li.style.animationDelay = `${i * 60}ms`;
    ul.appendChild(li);
  });
}

// ── Comparativa ideal vs alumno con resaltado de conceptos ─────────────

function renderComparison(data, studentAnswer) {
  const ideal = data.reference.ideal_answer;
  const concepts = data.reference.key_concepts;
  const detectedSet = new Set(data.detected_concepts);
  const partialSet = new Set(data.partial_concepts);

  function classFor(concept) {
    if (detectedSet.has(concept)) return 'detected';
    if (partialSet.has(concept)) return 'partial';
    return 'missing';
  }

  $('#compare-ideal').innerHTML = highlightConcepts(
    ideal,
    concepts.map((c) => ({ text: c.concept, cls: classFor(c.concept) }))
  );

  // En la respuesta del alumno solo marcamos los detectados/parciales (lo que ha "acertado")
  const studentHighlights = concepts
    .filter((c) => detectedSet.has(c.concept) || partialSet.has(c.concept))
    .map((c) => ({ text: c.concept, cls: classFor(c.concept) }));

  $('#compare-student').innerHTML = highlightConcepts(studentAnswer, studentHighlights);
}

function highlightConcepts(text, items) {
  if (!text) return '';
  let html = escapeHtml(text);
  // Ordenar por longitud descendente para que las frases más largas se marquen primero
  // y no se descompongan en sub-tokens (ej: "respiración celular" antes que "celular")
  const sorted = [...items].sort((a, b) => b.text.length - a.text.length);
  for (const item of sorted) {
    const escapedConcept = escapeRegex(item.text);
    const re = new RegExp(`(${escapedConcept})`, 'giu');
    html = html.replace(re, `<span class="hl ${item.cls}">$1</span>`);
  }
  return html;
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function escapeRegex(s) {
  return String(s).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

// ────────────────────────────────────────────────────────────────────────────
// OCR
// ────────────────────────────────────────────────────────────────────────────

$('#ocr-image').addEventListener('change', (e) => {
  const file = e.target.files[0];
  const preview = $('#ocr-preview');
  if (!file) {
    preview.classList.add('hidden');
    preview.src = '';
    return;
  }
  preview.src = URL.createObjectURL(file);
  preview.classList.remove('hidden');
});

$('#btn-ocr').addEventListener('click', async () => {
  const file = $('#ocr-image').files[0];
  if (!file) {
    alert('Selecciona una imagen primero.');
    return;
  }

  const fd = new FormData();
  fd.append('image', file);
  fd.append('lang', 'spa');

  const btn = $('#btn-ocr');
  btn.disabled = true;
  btn.textContent = 'Procesando...';

  try {
    const res = await fetch('/api/ocr', { method: 'POST', body: fd });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      alert(`Error: ${err.detail || res.statusText}`);
      return;
    }
    const data = await res.json();
    $('#ocr-question').textContent = data.question || '(no detectada)';
    $('#ocr-answer').textContent = data.student_answer || '(no detectada)';
    $('#ocr-raw').textContent = data.raw_text;
    $('#ocr-result').classList.remove('hidden');
    $('#ocr-result').scrollIntoView({ behavior: 'smooth', block: 'start' });
  } finally {
    btn.disabled = false;
    btn.textContent = 'Extraer texto';
  }
});

$('#btn-send-to-grade').addEventListener('click', () => {
  const question = $('#ocr-question').textContent;
  const answer = $('#ocr-answer').textContent;

  $('#case-select').value = '';
  showCustomRef();
  $('#cust-question').value = question === '(no detectada)' ? '' : question;
  $('#cust-ideal').value = '';
  $('#cust-concepts').value = '';
  $('#student-answer').value = answer === '(no detectada)' ? '' : answer;

  activateTab('grade');
  $('#cust-ideal').focus();
});

// ────────────────────────────────────────────────────────────────────────────
// Dashboard
// ────────────────────────────────────────────────────────────────────────────

$('#btn-validate').addEventListener('click', async () => {
  const btn = $('#btn-validate');
  btn.disabled = true;
  btn.textContent = 'Ejecutando...';

  try {
    const res = await fetch('/api/validate');
    if (!res.ok) {
      alert('Error ejecutando validación');
      return;
    }
    renderDashboard(await res.json());
  } finally {
    btn.disabled = false;
    btn.textContent = 'Ejecutar 40 casos';
  }
});

$('#btn-correlation').addEventListener('click', async () => {
  const btn = $('#btn-correlation');
  btn.disabled = true;
  btn.textContent = 'Calculando...';
  try {
    const res = await fetch('/api/correlation');
    if (!res.ok) {
      alert('Error calculando la correlación');
      return;
    }
    renderCorrelation(await res.json());
  } finally {
    btn.disabled = false;
    btn.textContent = 'Calcular correlación';
  }
});

function renderCorrelation(data) {
  $('#correlation-body').classList.remove('hidden');

  const fmt = (v) => (v >= 0 ? '+' : '') + v.toFixed(3);
  $('#stat-spearman').textContent = fmt(data.spearman);
  $('#stat-pearson').textContent = fmt(data.pearson);
  $('#stat-mae').textContent = data.mae.toFixed(2);
  $('#stat-rmse').textContent = data.rmse.toFixed(2);
  $('#stat-corr-n').textContent = data.n;
  $('#correlation-note').textContent = data.note || '';

  if (typeof Chart === 'undefined') {
    console.warn('Chart.js no cargado todavía');
    return;
  }

  const colorAccent = themeColor('--accent') || '#4f8cff';
  const colorMuted = themeColor('--muted');
  const colorSuccess = themeColor('--success');
  const colorWarning = themeColor('--warning');
  Chart.defaults.color = themeColor('--text');
  Chart.defaults.borderColor = themeColor('--border');

  // ── Dispersión: nota humana (x) vs nota del sistema (y) ───────────────
  CHARTS.scatter?.destroy();
  CHARTS.scatter = new Chart($('#chart-scatter'), {
    data: {
      datasets: [
        {
          type: 'line',
          label: 'Acuerdo perfecto',
          data: [{ x: 0, y: 0 }, { x: 10, y: 10 }],
          borderColor: colorMuted,
          borderDash: [6, 6],
          borderWidth: 1,
          pointRadius: 0,
          fill: false,
        },
        {
          type: 'scatter',
          label: 'Respuestas',
          data: data.points.map((p) => ({ x: p.human, y: p.system, _a: p.answer })),
          backgroundColor: colorAccent,
          pointRadius: 5,
          pointHoverRadius: 7,
        },
      ],
    },
    options: {
      responsive: true,
      scales: {
        x: { type: 'linear', min: 0, max: 10, title: { display: true, text: 'Nota humana' } },
        y: { type: 'linear', min: 0, max: 10, title: { display: true, text: 'Nota del sistema' } },
      },
      plugins: {
        legend: { display: true },
        tooltip: {
          callbacks: {
            label: (ctx) => {
              const p = ctx.raw;
              if (p._a === undefined) return '';
              return `humano ${p.x} · sistema ${p.y}`;
            },
            afterLabel: (ctx) => {
              const a = ctx.raw._a;
              return a ? a.slice(0, 60) + (a.length > 60 ? '…' : '') : '';
            },
          },
        },
      },
    },
  });

  // ── Spearman por pregunta ────────────────────────────────────────────
  const labels = data.per_question.map((q) => q.question.slice(0, 28) + '…');
  CHARTS.perq?.destroy();
  CHARTS.perq = new Chart($('#chart-perq'), {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: 'Spearman ρ',
        data: data.per_question.map((q) => q.spearman),
        backgroundColor: data.per_question.map((q) =>
          q.spearman >= 0.85 ? colorSuccess : colorWarning),
      }],
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      scales: { x: { min: 0, max: 1 } },
      plugins: { legend: { display: false } },
    },
  });
}

function renderDashboard(data) {
  $('#dashboard-body').classList.remove('hidden');

  $('#stat-pass').textContent = data.passed;
  $('#stat-expected').textContent = data.expected_fails;
  $('#stat-unexpected').textContent = data.unexpected_fails;
  $('#stat-conformant').textContent = `${data.conformant_pct}%`;

  $('#stat-unexpected').parentElement.classList.toggle(
    'has-fails', data.unexpected_fails > 0
  );

  renderCharts(data);

  const tbody = $('#cases-tbody');
  tbody.innerHTML = '';
  for (const c of data.cases) {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${String(c.id).padStart(2, '0')}</td>
      <td>${escapeHtml(c.subject)}</td>
      <td>${escapeHtml(c.topic)}</td>
      <td>${escapeHtml(c.desc)}</td>
      <td><strong>${c.score.toFixed(2)}</strong></td>
      <td>${c.nota_min.toFixed(1)}–${c.nota_max.toFixed(1)}</td>
      <td><span class="status-pill ${c.status}">${statusLabel(c.status)}</span></td>
    `;
    tbody.appendChild(tr);
  }
}

function statusLabel(status) {
  if (status === 'pass') return 'PASS';
  if (status === 'expected_fail') return 'FAIL esperado';
  return 'FAIL inesperado';
}

function themeColor(varName) {
  return getComputedStyle(document.documentElement).getPropertyValue(varName).trim();
}

function renderCharts(data) {
  if (typeof Chart === 'undefined') {
    console.warn('Chart.js no cargado todavía');
    return;
  }

  const colorPass = themeColor('--success');
  const colorExpected = themeColor('--warning');
  const colorUnexpected = themeColor('--danger');
  const colorMuted = themeColor('--muted');
  const colorBorder = themeColor('--border');
  const colorText = themeColor('--text');

  Chart.defaults.color = colorText;
  Chart.defaults.borderColor = colorBorder;

  // ── Donut: conformidad global ────────────────────────────────────────
  CHARTS.donut?.destroy();
  CHARTS.donut = new Chart($('#chart-donut'), {
    type: 'doughnut',
    data: {
      labels: ['PASS', 'FAIL esperado', 'FAIL inesperado'],
      datasets: [{
        data: [data.passed, data.expected_fails, data.unexpected_fails],
        backgroundColor: [colorPass, colorExpected, colorUnexpected],
        borderWidth: 0,
        hoverOffset: 6,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '68%',
      plugins: {
        legend: { position: 'bottom', labels: { padding: 14, boxWidth: 12 } },
      },
    },
  });

  // ── Bar por asignatura ────────────────────────────────────────────────
  CHARTS.subject?.destroy();
  CHARTS.subject = new Chart($('#chart-subject'), {
    type: 'bar',
    data: barDataFromBuckets(data.per_subject, colorPass, colorExpected, colorUnexpected),
    options: stackedBarOptions(colorMuted, colorBorder),
  });

  // ── Bar por tema (horizontal) ─────────────────────────────────────────
  CHARTS.topic?.destroy();
  CHARTS.topic = new Chart($('#chart-topic'), {
    type: 'bar',
    data: barDataFromBuckets(data.per_topic, colorPass, colorExpected, colorUnexpected),
    options: { ...stackedBarOptions(colorMuted, colorBorder), indexAxis: 'y' },
  });
}

function barDataFromBuckets(buckets, colorPass, colorExpected, colorUnexpected) {
  const labels = Object.keys(buckets).sort();
  return {
    labels,
    datasets: [
      { label: 'PASS', backgroundColor: colorPass, data: labels.map((k) => buckets[k].pass) },
      { label: 'FAIL esperado', backgroundColor: colorExpected, data: labels.map((k) => buckets[k].expected_fail) },
      { label: 'FAIL inesperado', backgroundColor: colorUnexpected, data: labels.map((k) => buckets[k].unexpected_fail) },
    ],
  };
}

function stackedBarOptions(colorMuted, colorBorder) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { position: 'bottom', labels: { padding: 14, boxWidth: 12 } },
      tooltip: { mode: 'index', intersect: false },
    },
    scales: {
      x: { stacked: true, grid: { color: colorBorder }, ticks: { color: colorMuted } },
      y: { stacked: true, grid: { color: colorBorder }, ticks: { color: colorMuted }, beginAtZero: true },
    },
  };
}

// ────────────────────────────────────────────────────────────────────────────
// Historial
// ────────────────────────────────────────────────────────────────────────────

function loadHistory() {
  try { return JSON.parse(localStorage.getItem(STORAGE.history) || '[]'); }
  catch { return []; }
}

function persistHistory(items) {
  localStorage.setItem(STORAGE.history, JSON.stringify(items));
}

function saveToHistory(data, studentAnswer) {
  const items = loadHistory();
  items.unshift({
    id: Date.now(),
    timestamp: new Date().toISOString(),
    score: data.score_over_10,
    feedback: data.feedback,
    detected: data.detected_concepts,
    partial: data.partial_concepts,
    missing: data.missing_concepts,
    concept_ratio: data.concept_ratio,
    similarity_ratio: data.similarity_ratio,
    length_penalty: data.length_penalty,
    student_answer: studentAnswer,
    reference: data.reference,
  });
  persistHistory(items.slice(0, 50));  // tope sano
}

function updateHistoryBadge() {
  const n = loadHistory().length;
  $('#history-count').textContent = n;
}

function renderHistory() {
  const items = loadHistory();
  const list = $('#history-list');
  const empty = $('#history-empty');

  if (!items.length) {
    list.classList.add('hidden');
    empty.classList.remove('hidden');
    return;
  }

  empty.classList.add('hidden');
  list.classList.remove('hidden');
  list.innerHTML = '';

  for (const item of items) {
    const li = document.createElement('li');
    li.className = 'history-item';
    li.dataset.id = item.id;

    const scoreClass = item.score >= 7 ? 'good' : item.score >= 4 ? 'mid' : 'bad';
    const when = new Date(item.timestamp);
    const whenStr = when.toLocaleString('es-ES', {
      day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit',
    });

    const subject = item.reference?.subject || 'Personalizado';
    const question = item.reference?.question || '(sin pregunta)';

    li.innerHTML = `
      <div class="history-score ${scoreClass}">${item.score.toFixed(1)}</div>
      <div class="history-meta">
        <span class="history-question">${escapeHtml(question)}</span>
        <span class="history-answer">${escapeHtml(item.student_answer)}</span>
        <div class="history-tags">
          <span class="chip secondary">${escapeHtml(subject)}</span>
          <span class="chip secondary">${item.detected.length} ✓ · ${item.missing.length} ✗</span>
        </div>
      </div>
      <div class="history-time">${whenStr}</div>
    `;

    li.addEventListener('click', () => replayHistoryItem(item));
    list.appendChild(li);
  }
}

function replayHistoryItem(item) {
  // Reconstruye el resultado y lo enseña en la pestaña de Corregir
  activateTab('grade');
  $('#case-select').value = '';
  showCustomRef();
  $('#cust-question').value = item.reference?.question || '';
  $('#cust-subject').value = item.reference?.subject || 'General';
  $('#cust-level').value = item.reference?.education_level || 'Bachillerato';
  $('#cust-ideal').value = item.reference?.ideal_answer || '';
  $('#cust-concepts').value = (item.reference?.key_concepts || [])
    .map((c) => `${c.concept}:${c.weight}`).join('\n');
  $('#student-answer').value = item.student_answer;

  // Reusa renderResult con la forma que espera
  const data = {
    score_over_10: item.score,
    feedback: item.feedback,
    detected_concepts: item.detected,
    partial_concepts: item.partial,
    missing_concepts: item.missing,
    concept_ratio: item.concept_ratio,
    similarity_ratio: item.similarity_ratio,
    length_penalty: item.length_penalty,
    reference: item.reference,
  };
  renderResult(data, item.student_answer);
}

$('#btn-clear-history').addEventListener('click', () => {
  if (!loadHistory().length) return;
  if (!confirm('¿Vaciar todo el historial?')) return;
  persistHistory([]);
  updateHistoryBadge();
  renderHistory();
});

updateHistoryBadge();

// ════════════════════════════════════════════════════════════════════════════
// Mode switch (Individual / Lote)
// ════════════════════════════════════════════════════════════════════════════

$$('.mode-btn').forEach((b) => {
  b.addEventListener('click', () => {
    $$('.mode-btn').forEach((x) => x.classList.toggle('active', x === b));
    const mode = b.dataset.mode;
    $$('.mode-pane').forEach((p) => p.classList.toggle('active', p.id === `mode-${mode}`));
  });
});

// ════════════════════════════════════════════════════════════════════════════
// Lote (batch grading)
// ════════════════════════════════════════════════════════════════════════════

let BATCH_LAST_RESULTS = null;
let CHART_HIST = null;

// Selector de caso para lote: si selecciona un caso, vuelca pregunta/ideal/conceptos
$('#batch-case-select').addEventListener('change', (e) => {
  const id = parseInt(e.target.value, 10);
  if (!id) {
    // Personalizado — no tocar
    return;
  }
  const c = CASES.find((x) => x.id === id);
  if (!c) return;
  $('#batch-question').value = c.question;
  $('#batch-subject').value = c.subject;
  $('#batch-level').value = c.education_level;
  $('#batch-ideal').value = c.ideal_answer;
  $('#batch-concepts').value = c.key_concepts.map((k) => `${k.concept}:${k.weight}`).join('\n');
});

// Cuenta respuestas en vivo
$('#batch-answers').addEventListener('input', updateBatchCount);

function updateBatchCount() {
  const n = parseBatchAnswers().length;
  $('#batch-count').textContent = `${n} respuesta${n === 1 ? '' : 's'} detectada${n === 1 ? '' : 's'}`;
}

function parseBatchAnswers() {
  const raw = $('#batch-answers').value;
  if (!raw.trim()) return [];
  // Si contiene "---" usamos eso como separador (respuestas multi-línea)
  if (raw.includes('---')) {
    return raw.split(/\n?---\n?/).map((s) => s.trim()).filter(Boolean)
      .map((text, i) => ({ id: `Alumno ${i + 1}`, text }));
  }
  // Si no, una por línea
  return raw.split('\n').map((s) => s.trim()).filter(Boolean)
    .map((text, i) => ({ id: `Alumno ${i + 1}`, text }));
}

// Upload CSV (alumno, respuesta) — parser simple, sin libs
$('#batch-csv').addEventListener('change', async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  const text = await file.text();
  const rows = parseCSV(text);
  // Soporta cabecera opcional alumno,respuesta
  const start = rows[0] && /alumno|nombre|id/i.test(rows[0][0] || '') ? 1 : 0;
  const lines = [];
  for (let i = start; i < rows.length; i++) {
    const [id, ...rest] = rows[i];
    const answer = rest.join(',').trim();
    if (!answer) continue;
    lines.push(answer);  // dejamos formato textarea simple (una por línea)
  }
  $('#batch-answers').value = lines.join('\n---\n');
  updateBatchCount();
});

function parseCSV(text) {
  // Parser CSV minimalista — soporta comillas dobles
  const rows = [];
  let row = [];
  let cell = '';
  let inQuotes = false;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (inQuotes) {
      if (ch === '"' && text[i + 1] === '"') { cell += '"'; i++; }
      else if (ch === '"') inQuotes = false;
      else cell += ch;
    } else {
      if (ch === '"') inQuotes = true;
      else if (ch === ',') { row.push(cell); cell = ''; }
      else if (ch === '\n' || ch === '\r') {
        if (cell || row.length) { row.push(cell); rows.push(row); }
        row = []; cell = '';
        if (ch === '\r' && text[i + 1] === '\n') i++;
      } else cell += ch;
    }
  }
  if (cell || row.length) { row.push(cell); rows.push(row); }
  return rows;
}

// Upload TXT (respuestas separadas por --- o doble salto)
$('#batch-txt').addEventListener('change', async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  const text = await file.text();
  // Normalizamos: si hay --- los respetamos, si no, separamos por doble salto
  const parts = text.includes('---')
    ? text.split(/\n?---\n?/)
    : text.split(/\n\s*\n/);
  const clean = parts.map((s) => s.trim()).filter(Boolean);
  $('#batch-answers').value = clean.join('\n---\n');
  updateBatchCount();
});

$('#btn-batch-clear').addEventListener('click', () => {
  $('#batch-answers').value = '';
  $('#batch-csv').value = '';
  $('#batch-txt').value = '';
  $('#batch-result-card').classList.add('hidden');
  updateBatchCount();
});

$('#btn-batch-grade').addEventListener('click', async () => {
  const answers = parseBatchAnswers();
  if (!answers.length) {
    alert('Pega o sube al menos una respuesta.');
    return;
  }

  const question = $('#batch-question').value.trim();
  const ideal = $('#batch-ideal').value.trim();
  if (!question || !ideal) {
    alert('Define la pregunta y la respuesta ideal.');
    return;
  }

  let conceptList;
  try {
    conceptList = parseCustomConcepts($('#batch-concepts').value);
  } catch (err) {
    alert(err.message);
    return;
  }

  const body = {
    reference: {
      question,
      subject: $('#batch-subject').value.trim() || 'General',
      education_level: $('#batch-level').value.trim() || 'Bachillerato',
      ideal_answer: ideal,
      key_concepts: conceptList,
    },
    answers,
  };

  const btn = $('#btn-batch-grade');
  btn.disabled = true;
  btn.textContent = 'Corrigiendo...';

  try {
    const res = await fetch('/api/grade_batch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      alert(`Error: ${err.detail || res.statusText}`);
      return;
    }
    const data = await res.json();
    BATCH_LAST_RESULTS = data;
    renderBatchResult(data);
  } finally {
    btn.disabled = false;
    btn.textContent = 'Corregir todas';
  }
});

function renderBatchResult(data) {
  const card = $('#batch-result-card');
  card.classList.remove('hidden');
  card.scrollIntoView({ behavior: 'smooth', block: 'start' });

  // Stats
  const stats = data.stats;
  const statsEl = $('#batch-stats');
  statsEl.innerHTML = `
    <div class="stat highlight"><span class="stat-num">${stats.mean}</span><span class="stat-label">Media</span></div>
    <div class="stat"><span class="stat-num">${stats.median}</span><span class="stat-label">Mediana</span></div>
    <div class="stat"><span class="stat-num">${stats.pass_count}/${stats.count}</span><span class="stat-label">Aprobados (≥5)</span></div>
    <div class="stat"><span class="stat-num">${stats.min} – ${stats.max}</span><span class="stat-label">Rango</span></div>
  `;

  // Histograma
  if (typeof Chart !== 'undefined') {
    CHART_HIST?.destroy();
    CHART_HIST = new Chart($('#chart-histogram'), {
      type: 'bar',
      data: {
        labels: data.histogram.labels,
        datasets: [{
          label: 'Nº alumnos',
          data: data.histogram.values,
          backgroundColor: themeColor('--primary'),
          borderRadius: 4,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { display: false }, ticks: { color: themeColor('--muted') } },
          y: {
            beginAtZero: true,
            grid: { color: themeColor('--border') },
            ticks: { precision: 0, color: themeColor('--muted') },
          },
        },
      },
    });
  }

  // Tabla
  const tbody = $('#batch-tbody');
  tbody.innerHTML = '';
  for (const r of data.results) {
    const tr = document.createElement('tr');
    const snippet = r.answer.length > 90 ? r.answer.slice(0, 90) + '…' : r.answer;
    const scoreClass = r.score >= 7 ? 'detected' : r.score >= 5 ? 'partial' : 'missing';
    tr.innerHTML = `
      <td>${escapeHtml(r.id)}</td>
      <td><span class="muted" title="${escapeHtml(r.answer)}">${escapeHtml(snippet)}</span></td>
      <td><strong class="status-pill ${scoreClass === 'detected' ? 'pass' : scoreClass === 'partial' ? 'expected_fail' : 'unexpected_fail'}">${r.score.toFixed(2)}</strong></td>
      <td>${r.detected.map(escapeHtml).join(', ') || '—'}</td>
      <td>${r.missing.map(escapeHtml).join(', ') || '—'}</td>
    `;
    tbody.appendChild(tr);
  }
}

$('#btn-batch-export').addEventListener('click', () => {
  if (!BATCH_LAST_RESULTS) return;
  const rows = [['alumno', 'nota', 'detectados', 'faltantes', 'respuesta']];
  for (const r of BATCH_LAST_RESULTS.results) {
    rows.push([
      r.id,
      r.score.toFixed(2),
      r.detected.join('; '),
      r.missing.join('; '),
      r.answer,
    ]);
  }
  const csv = rows.map((row) => row.map(csvField).join(',')).join('\n');
  downloadFile('correccion_lote.csv', csv, 'text/csv;charset=utf-8');
});

function csvField(v) {
  const s = String(v ?? '');
  if (/[",\n]/.test(s)) return `"${s.replace(/"/g, '""')}"`;
  return s;
}

function downloadFile(name, content, mime) {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = name;
  document.body.appendChild(a); a.click();
  document.body.removeChild(a); URL.revokeObjectURL(url);
}

// Cuando se cargan los casos, también pueblamos el selector de lote
const _origLoad = loadCases;
async function loadBatchCases() {
  if (!CASES.length) await _origLoad();
  const select = $('#batch-case-select');
  for (const c of CASES) {
    const opt = document.createElement('option');
    opt.value = String(c.id);
    opt.textContent = `[${String(c.id).padStart(2, '0')}] ${c.subject} · ${c.topic}`;
    select.appendChild(opt);
  }
}
loadBatchCases().catch(console.error);

// ════════════════════════════════════════════════════════════════════════════
// Aula del Profesor — sub-tab nav
// ════════════════════════════════════════════════════════════════════════════

$$('.subnav-btn').forEach((b) => {
  b.addEventListener('click', () => {
    $$('.subnav-btn').forEach((x) => x.classList.toggle('active', x === b));
    const sub = b.dataset.sub;
    $$('.sub-pane').forEach((p) => p.classList.toggle('active', p.id === `sub-${sub}`));
    if (sub === 'lexicon') loadTeacherConfig();
  });
});

// ════════════════════════════════════════════════════════════════════════════
// Asistente IA: generar referencia
// ════════════════════════════════════════════════════════════════════════════

let AI_LAST_RESULT = null;

$('#btn-ai-generate').addEventListener('click', async () => {
  const question = $('#ai-question').value.trim();
  if (!question) { alert('Escribe la pregunta.'); return; }

  const body = {
    question,
    subject: $('#ai-subject').value.trim() || 'General',
    education_level: $('#ai-level').value.trim() || 'Bachillerato',
    force: $('#ai-force').checked,
  };

  const btn = $('#btn-ai-generate');
  btn.disabled = true;
  const orig = btn.innerHTML;
  btn.innerHTML = '<span>✨</span> Generando...';

  try {
    const res = await fetch('/api/generate_reference', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      alert(`Error: ${err.detail || res.statusText}`);
      return;
    }
    const data = await res.json();
    AI_LAST_RESULT = data;
    renderAIResult(data);
  } finally {
    btn.disabled = false;
    btn.innerHTML = orig;
  }
});

function renderAIResult(data) {
  const card = $('#ai-result-card');
  card.classList.remove('hidden');
  $('#ai-ideal').textContent = data.ideal_answer;

  const conceptsEl = $('#ai-concepts');
  conceptsEl.innerHTML = '';
  for (const k of data.key_concepts) {
    const chip = document.createElement('span');
    chip.className = 'concept-chip';
    chip.innerHTML = `${escapeHtml(k.concept)} <span class="w">· ${k.weight.toFixed(2)}</span>`;
    conceptsEl.appendChild(chip);
  }

  const mistakes = data.common_mistakes || [];
  const ul = $('#ai-mistakes');
  ul.innerHTML = '';
  if (!mistakes.length) {
    const li = document.createElement('li');
    li.textContent = '(la IA no propuso errores frecuentes para esta pregunta)';
    li.style.color = 'var(--muted)';
    ul.appendChild(li);
  } else {
    for (const m of mistakes) {
      const li = document.createElement('li');
      li.textContent = m;
      ul.appendChild(li);
    }
  }
}

// "Usar en Corregir" → vuelca al form custom del modo Individual
$('#btn-ai-use').addEventListener('click', () => {
  if (!AI_LAST_RESULT) return;
  activateTab('grade');
  // Forzar modo Individual
  document.querySelector('.mode-btn[data-mode="individual"]')?.click();

  $('#case-select').value = '';
  showCustomRef();
  $('#cust-question').value = AI_LAST_RESULT.question;
  $('#cust-subject').value = AI_LAST_RESULT.subject;
  $('#cust-level').value = AI_LAST_RESULT.education_level;
  $('#cust-ideal').value = AI_LAST_RESULT.ideal_answer;
  $('#cust-concepts').value = AI_LAST_RESULT.key_concepts
    .map((c) => `${c.concept}:${c.weight}`).join('\n');
  $('#student-answer').focus();
});

// "Crear antipatrones con estos errores" → rellena el form de antipatrones
$('#btn-ai-copy-mistakes').addEventListener('click', () => {
  if (!AI_LAST_RESULT) return;
  const mistakes = AI_LAST_RESULT.common_mistakes || [];
  if (!mistakes.length) {
    alert('La IA no propuso errores para esta pregunta.');
    return;
  }
  // Vamos al sub-tab lexicon y rellenamos el form
  document.querySelector('.subnav-btn[data-sub="lexicon"]')?.click();
  // Suponemos que el primer concepto clave es el más relevante
  const concept = AI_LAST_RESULT.key_concepts[0]?.concept || '';
  $('#ap-concept').value = concept;
  $('#ap-forbidden').value = mistakes.join(', ');
  $('#ap-penalty').value = '0.5';
  $('#ap-concept').scrollIntoView({ behavior: 'smooth', block: 'center' });
});

// Botón "Generar con IA" dentro del form custom de Corregir
$('#btn-ai-fill').addEventListener('click', async () => {
  const question = $('#cust-question').value.trim();
  if (!question) { alert('Escribe la pregunta primero.'); return; }

  const btn = $('#btn-ai-fill');
  btn.disabled = true;
  const orig = btn.innerHTML;
  btn.innerHTML = '<span>✨</span> Generando...';

  try {
    const res = await fetch('/api/generate_reference', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        question,
        subject: $('#cust-subject').value.trim() || 'General',
        education_level: $('#cust-level').value.trim() || 'Bachillerato',
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      alert(`Error: ${err.detail || res.statusText}`);
      return;
    }
    const data = await res.json();
    $('#cust-ideal').value = data.ideal_answer;
    $('#cust-concepts').value = data.key_concepts
      .map((c) => `${c.concept}:${c.weight}`).join('\n');
  } finally {
    btn.disabled = false;
    btn.innerHTML = orig;
  }
});

// ════════════════════════════════════════════════════════════════════════════
// Calibración con ejemplos (few-shot)
// ════════════════════════════════════════════════════════════════════════════

let CAL_EXAMPLES = [];

function renderCalExamples() {
  const el = $('#cal-examples-list');
  el.innerHTML = '';
  if (!CAL_EXAMPLES.length) {
    const div = document.createElement('div');
    div.className = 'muted small';
    div.style.padding = '8px 0';
    div.textContent = 'Aún no hay ejemplos. Añade al menos uno.';
    el.appendChild(div);
    return;
  }
  CAL_EXAMPLES.forEach((ex, idx) => {
    const div = document.createElement('div');
    div.className = 'example-item';
    const snippet = ex.answer.length > 90 ? ex.answer.slice(0, 90) + '…' : ex.answer;
    div.innerHTML = `
      <span class="ex-text" title="${escapeHtml(ex.answer)}">${escapeHtml(snippet)}</span>
      <span class="ex-score">${ex.score.toFixed(1)}</span>
      <button class="ex-del" title="Eliminar">✕</button>
    `;
    div.querySelector('.ex-del').addEventListener('click', () => {
      CAL_EXAMPLES.splice(idx, 1);
      renderCalExamples();
    });
    el.appendChild(div);
  });
}

$('#btn-cal-add').addEventListener('click', () => {
  const answer = $('#cal-new-answer').value.trim();
  const score = parseFloat($('#cal-new-score').value);
  if (!answer) { alert('Pega la respuesta del ejemplo.'); return; }
  if (Number.isNaN(score) || score < 0 || score > 10) {
    alert('La nota debe ser un número entre 0 y 10.');
    return;
  }
  CAL_EXAMPLES.push({ answer, score });
  $('#cal-new-answer').value = '';
  $('#cal-new-score').value = '';
  renderCalExamples();
});

$('#btn-cal-run').addEventListener('click', async () => {
  const question = $('#cal-question').value.trim();
  const ideal = $('#cal-ideal').value.trim();
  const student = $('#cal-student').value.trim();
  if (!question || !ideal) { alert('Define la pregunta y la respuesta ideal.'); return; }
  if (!student) { alert('Pega la respuesta a evaluar.'); return; }
  if (!CAL_EXAMPLES.length) { alert('Añade al menos un ejemplo.'); return; }

  let conceptList;
  try {
    conceptList = parseCustomConcepts($('#cal-concepts').value);
  } catch (e) {
    alert(e.message);
    return;
  }

  const body = {
    reference: {
      question,
      subject: 'General',
      education_level: 'Bachillerato',
      ideal_answer: ideal,
      key_concepts: conceptList,
    },
    student_answer: student,
    examples: CAL_EXAMPLES,
  };

  const btn = $('#btn-cal-run');
  btn.disabled = true;
  const orig = btn.innerHTML;
  btn.innerHTML = '<span>✨</span> Calibrando...';

  try {
    // 1) Calibración DETERMINISTA (sin IA). Requiere ≥2 ejemplos.
    let detData = null;
    if (CAL_EXAMPLES.length >= 2) {
      const detRes = await fetch('/api/calibrate_deterministic', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (detRes.ok) detData = await detRes.json();
      else {
        const err = await detRes.json().catch(() => ({}));
        alert(`Error en la calibración determinista: ${err.detail || detRes.statusText}`);
      }
    }

    // 2) Calibración con Claude (opcional, requiere API key). Best-effort.
    let llmData = null, llmError = null;
    try {
      const llmRes = await fetch('/api/calibrate_grade', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (llmRes.ok) llmData = await llmRes.json();
      else llmError = (await llmRes.json().catch(() => ({}))).detail || llmRes.statusText;
    } catch (e) { llmError = e.message; }

    if (!detData && !llmData) return;
    renderCalResult(detData, llmData, llmError);
  } finally {
    btn.disabled = false;
    btn.innerHTML = orig;
  }
});

function renderCalResult(det, llm, llmError) {
  const card = $('#cal-result-card');
  card.classList.remove('hidden');
  card.scrollIntoView({ behavior: 'smooth', block: 'start' });

  // Nota cruda del grader (la trae cualquiera de los dos endpoints).
  const raw = det ? det.score_grader : (llm ? llm.score_grader : null);
  $('#cal-score-grader').textContent = raw != null ? raw.toFixed(2) : '—';

  // Calibración determinista.
  if (det) {
    $('#cal-score-cal').textContent = det.score_calibrated.toFixed(2);
    $('#cal-mapping').textContent =
      `Mapeo aprendido (${det.method}): ${det.mapping}. ` +
      `Error medio sobre los ejemplos: ${det.mae_examples_before} → ${det.mae_examples_after}.`;
    $('#cal-cal-note').textContent = det.note || '';
    const tb = $('#cal-fit-tbody');
    tb.innerHTML = '';
    for (const r of det.fit) {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>${escapeHtml((r.answer || '').slice(0, 60))}</td>
        <td>${r.teacher.toFixed(1)}</td>
        <td>${r.raw.toFixed(2)}</td>
        <td><strong>${r.calibrated.toFixed(2)}</strong></td>`;
      tb.appendChild(tr);
    }
  } else {
    $('#cal-score-cal').textContent = '—';
    $('#cal-mapping').textContent = 'Añade al menos 2 ejemplos para la calibración determinista.';
    $('#cal-cal-note').textContent = '';
    $('#cal-fit-tbody').innerHTML = '';
  }

  // Calibración con Claude (opcional).
  if (llm) {
    $('#cal-score-llm').textContent = llm.score_llm.toFixed(2);
    $('#cal-reasoning').textContent = llm.reasoning || '(sin justificación)';
  } else {
    $('#cal-score-llm').textContent = '—';
    $('#cal-reasoning').textContent = llmError
      ? `IA no disponible (${llmError})` : '(no solicitada)';
  }

  const detail = (det && det.grader_detail) || (llm && llm.grader_detail) || {};
  fillListAnimated('#cal-list-detected', detail.detected || [], 'Ninguno');
  fillListAnimated('#cal-list-missing', detail.missing || [], 'Ninguno');
}

renderCalExamples();

// ════════════════════════════════════════════════════════════════════════════
// Sinónimos y antipatrones (teacher_config)
// ════════════════════════════════════════════════════════════════════════════

let TEACHER_CFG = { synonyms: [], antipatterns: [] };

async function loadTeacherConfig() {
  try {
    const res = await fetch('/api/teacher_config');
    if (res.ok) TEACHER_CFG = await res.json();
  } catch {}
  renderSynList();
  renderApList();
}

function renderSynList() {
  const el = $('#syn-list');
  el.innerHTML = '';
  if (!TEACHER_CFG.synonyms.length) {
    el.innerHTML = '<div class="muted small" style="padding:8px 0">Sin sinónimos aún.</div>';
    return;
  }
  TEACHER_CFG.synonyms.forEach((g, idx) => {
    const div = document.createElement('div');
    div.className = 'lex-item';
    div.innerHTML = `
      <div>
        <span class="lex-key">${escapeHtml(g.canonical)}</span>
        <span class="lex-value">↔ ${g.variants.map(escapeHtml).join(', ')}</span>
      </div>
      <button class="lex-del" title="Eliminar">✕</button>
    `;
    div.querySelector('.lex-del').addEventListener('click', () => {
      TEACHER_CFG.synonyms.splice(idx, 1);
      renderSynList();
    });
    el.appendChild(div);
  });
}

function renderApList() {
  const el = $('#ap-list');
  el.innerHTML = '';
  if (!TEACHER_CFG.antipatterns.length) {
    el.innerHTML = '<div class="muted small" style="padding:8px 0">Sin antipatrones aún.</div>';
    return;
  }
  TEACHER_CFG.antipatterns.forEach((ap, idx) => {
    const div = document.createElement('div');
    div.className = 'lex-item';
    div.innerHTML = `
      <div>
        <span class="lex-key">${escapeHtml(ap.concept)}</span>
        <span class="lex-value">⛔ ${ap.forbidden.map(escapeHtml).join(', ')} <em>(×${ap.penalty})</em></span>
      </div>
      <button class="lex-del" title="Eliminar">✕</button>
    `;
    div.querySelector('.lex-del').addEventListener('click', () => {
      TEACHER_CFG.antipatterns.splice(idx, 1);
      renderApList();
    });
    el.appendChild(div);
  });
}

$('#btn-syn-add').addEventListener('click', () => {
  const canonical = $('#syn-canonical').value.trim();
  const variants = $('#syn-variants').value.split(',').map((s) => s.trim()).filter(Boolean);
  if (!canonical) { alert('Falta el término canónico.'); return; }
  if (!variants.length) { alert('Indica al menos una variante.'); return; }
  TEACHER_CFG.synonyms.push({ canonical, variants });
  $('#syn-canonical').value = '';
  $('#syn-variants').value = '';
  renderSynList();
});

$('#btn-ap-add').addEventListener('click', () => {
  const concept = $('#ap-concept').value.trim();
  const forbidden = $('#ap-forbidden').value.split(',').map((s) => s.trim()).filter(Boolean);
  const penalty = parseFloat($('#ap-penalty').value);
  if (!concept) { alert('Falta el concepto.'); return; }
  if (!forbidden.length) { alert('Indica al menos una frase prohibida.'); return; }
  if (Number.isNaN(penalty) || penalty < 0 || penalty > 1) {
    alert('Penalización entre 0 y 1.'); return;
  }
  TEACHER_CFG.antipatterns.push({ concept, forbidden, penalty });
  $('#ap-concept').value = '';
  $('#ap-forbidden').value = '';
  $('#ap-penalty').value = '0.5';
  renderApList();
});

$('#btn-lex-save').addEventListener('click', async () => {
  const btn = $('#btn-lex-save');
  btn.disabled = true;
  btn.textContent = 'Guardando...';
  try {
    const res = await fetch('/api/teacher_config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(TEACHER_CFG),
    });
    if (!res.ok) {
      alert('Error guardando');
      return;
    }
    TEACHER_CFG = await res.json();
    btn.textContent = '✓ Guardado';
    setTimeout(() => { btn.textContent = 'Guardar cambios'; }, 1400);
  } finally {
    btn.disabled = false;
  }
});

$('#btn-lex-reload').addEventListener('click', loadTeacherConfig);

// ════════════════════════════════════════════════════════════════════════════
// Materias (catálogo con presets)
// ════════════════════════════════════════════════════════════════════════════

const MATERIAS = [
  {
    name: 'Biología', icon: '🧬',
    desc: 'Procesos celulares, herencia, ecología.',
    questions: [
      {
        question: '¿Cuál es la función principal de la mitocondria?',
        ideal_answer: 'La mitocondria es el orgánulo celular encargado de producir energía en forma de ATP mediante la respiración celular.',
        key_concepts: [
          { concept: 'orgánulo', weight: 0.15 },
          { concept: 'energía', weight: 0.25 },
          { concept: 'ATP', weight: 0.35 },
          { concept: 'respiración celular', weight: 0.25 },
        ],
      },
      {
        question: '¿Qué es la fotosíntesis y dónde ocurre?',
        ideal_answer: 'La fotosíntesis es el proceso por el que las plantas convierten energía lumínica en glucosa y oxígeno usando CO2 y agua. Ocurre en los cloroplastos.',
        key_concepts: [
          { concept: 'energía lumínica', weight: 0.20 },
          { concept: 'glucosa', weight: 0.25 },
          { concept: 'oxígeno', weight: 0.15 },
          { concept: 'dióxido de carbono', weight: 0.15 },
          { concept: 'cloroplasto', weight: 0.25 },
        ],
      },
    ],
  },
  {
    name: 'Filosofía', icon: '🤔',
    desc: 'Lenguaje técnico premiado con bonus aditivo.',
    questions: [
      {
        question: '¿Qué es el idealismo trascendental de Kant?',
        ideal_answer: 'Doctrina que sostiene que el conocimiento no consiste en que el sujeto se adecúe a los objetos, sino los objetos al sujeto: el espacio y el tiempo son formas a priori de la sensibilidad y las categorías son condiciones de posibilidad de la experiencia.',
        key_concepts: [
          { concept: 'sujeto', weight: 0.20 },
          { concept: 'objeto', weight: 0.15 },
          { concept: 'a priori', weight: 0.25 },
          { concept: 'categoría', weight: 0.20 },
          { concept: 'experiencia', weight: 0.20 },
        ],
        bonus_terms: [
          { term: 'noúmeno', weight: 0.05 },
          { term: 'fenómeno', weight: 0.05 },
          { term: 'sensibilidad', weight: 0.04 },
          { term: 'entendimiento', weight: 0.04 },
        ],
      },
    ],
  },
  {
    name: 'Historia', icon: '🏛️',
    desc: 'Causas, consecuencias, hechos clave.',
    questions: [
      {
        question: '¿Cuáles fueron las principales causas de la Revolución Francesa?',
        ideal_answer: 'Las causas fueron la crisis económica y financiera del Estado, la desigualdad de los estamentos (Antiguo Régimen), la influencia de la Ilustración y el descontento social del Tercer Estado.',
        key_concepts: [
          { concept: 'crisis económica', weight: 0.25 },
          { concept: 'Antiguo Régimen', weight: 0.25 },
          { concept: 'Ilustración', weight: 0.25 },
          { concept: 'Tercer Estado', weight: 0.25 },
        ],
      },
    ],
  },
  {
    name: 'Lengua y Literatura', icon: '📖',
    desc: 'Movimientos, géneros, recursos.',
    questions: [
      {
        question: 'Define qué es la Generación del 98 y nombra dos autores representativos.',
        ideal_answer: 'Grupo de escritores españoles influidos por la crisis del 98, que reflexionan sobre la decadencia de España y renuevan el lenguaje literario. Autores: Miguel de Unamuno, Pío Baroja, Antonio Machado, Azorín.',
        key_concepts: [
          { concept: 'crisis del 98', weight: 0.30 },
          { concept: 'España', weight: 0.20 },
          { concept: 'Unamuno', weight: 0.25 },
          { concept: 'Machado', weight: 0.25 },
        ],
      },
    ],
  },
  {
    name: 'Inglés', icon: '🇬🇧',
    desc: 'Gramática y vocabulario.',
    questions: [
      {
        question: 'Explain the difference between Present Perfect and Past Simple in English.',
        ideal_answer: 'Past Simple describes completed actions in a finished time period. Present Perfect describes actions connected to the present, often with unfinished time or relevance to now.',
        key_concepts: [
          { concept: 'completed', weight: 0.25 },
          { concept: 'finished time', weight: 0.25 },
          { concept: 'present', weight: 0.25 },
          { concept: 'relevance', weight: 0.25 },
        ],
      },
    ],
  },
  {
    name: 'Economía', icon: '💹',
    desc: 'Macro, micro, mercados.',
    questions: [
      {
        question: '¿Qué es la inflación y cómo se mide?',
        ideal_answer: 'Aumento sostenido y generalizado del nivel de precios de bienes y servicios en una economía durante un periodo. Se mide habitualmente con el IPC (Índice de Precios al Consumo).',
        key_concepts: [
          { concept: 'precios', weight: 0.30 },
          { concept: 'sostenido', weight: 0.20 },
          { concept: 'generalizado', weight: 0.20 },
          { concept: 'IPC', weight: 0.30 },
        ],
      },
    ],
  },
  {
    name: 'Matemáticas', icon: '∑',
    desc: 'Ejercicios cuantitativos — usa la pestaña experimental.',
    questions: [],
    redirect_to: 'steps',
    redirect_label: 'Mates necesita corrección paso a paso (experimental).',
  },
  {
    name: 'Física', icon: '⚛️',
    desc: 'Ejercicios cuantitativos — usa la pestaña experimental.',
    questions: [],
    redirect_to: 'steps',
    redirect_label: 'Física necesita corrección paso a paso (experimental).',
  },
];

function renderMaterias() {
  const grid = $('#materias-grid');
  if (!grid || grid.children.length) return;
  for (const m of MATERIAS) {
    const card = document.createElement('div');
    card.className = 'materia-card';

    const header = `
      <div class="materia-header">
        <div class="materia-icon">${m.icon}</div>
        <div>
          <h3 class="materia-name">${escapeHtml(m.name)}</h3>
          <p class="materia-desc">${escapeHtml(m.desc)}</p>
        </div>
      </div>`;

    let body;
    if (m.redirect_to) {
      body = `
        <p class="muted small">${escapeHtml(m.redirect_label)}</p>
        <div class="actions">
          <button class="ghost btn-go-steps">Ir a Mates/Física experimental →</button>
        </div>`;
    } else {
      const items = m.questions.map((q, i) => (
        `<li><button class="materia-q-btn" data-materia="${escapeHtml(m.name)}" data-idx="${i}">${escapeHtml(q.question)}</button></li>`
      )).join('');
      body = `<ul class="materia-questions">${items}</ul>`;
    }

    card.innerHTML = header + body;
    grid.appendChild(card);
  }

  // delegated handlers
  grid.addEventListener('click', (e) => {
    const goSteps = e.target.closest('.btn-go-steps');
    if (goSteps) {
      activateTab('teacher');
      document.querySelector('.subnav-btn[data-sub="steps"]')?.click();
      return;
    }
    const qbtn = e.target.closest('.materia-q-btn');
    if (qbtn) {
      const materia = MATERIAS.find((m) => m.name === qbtn.dataset.materia);
      const q = materia?.questions[parseInt(qbtn.dataset.idx, 10)];
      if (!q) return;
      loadPresetIntoCorregir(materia, q);
    }
  });
}

function loadPresetIntoCorregir(materia, preset) {
  activateTab('grade');
  document.querySelector('.mode-btn[data-mode="individual"]')?.click();
  $('#case-select').value = '';
  showCustomRef();
  $('#cust-question').value = preset.question;
  $('#cust-subject').value = materia.name;
  $('#cust-level').value = 'Bachillerato';
  $('#cust-ideal').value = preset.ideal_answer;
  $('#cust-concepts').value = preset.key_concepts.map((c) => `${c.concept}:${c.weight}`).join('\n');
  $('#cust-bonus').value = (preset.bonus_terms || []).map((b) => `${b.term}:${b.weight}`).join('\n');
  $('#student-answer').value = '';
  $('#student-answer').focus();
}

renderMaterias();

// ════════════════════════════════════════════════════════════════════════════
// Bonus terms parser + integration in grade flow
// ════════════════════════════════════════════════════════════════════════════

function parseBonusTerms(raw) {
  if (!raw.trim()) return [];
  const lines = raw.split('\n').map((l) => l.trim()).filter(Boolean);
  const out = [];
  for (const line of lines) {
    const idx = line.lastIndexOf(':');
    if (idx === -1) throw new Error(`Bonus sin peso: «${line}»`);
    const term = line.slice(0, idx).trim();
    const weight = parseFloat(line.slice(idx + 1).trim());
    if (!term || Number.isNaN(weight)) throw new Error(`Bonus inválido: «${line}»`);
    out.push({ term, weight });
  }
  return out;
}

// Reemplazo del handler de grade para incluir bonus_terms del custom form
const _origGradeBtn = $('#btn-grade');
_origGradeBtn.replaceWith(_origGradeBtn.cloneNode(true));  // limpia listeners anteriores
$('#btn-grade').addEventListener('click', async () => {
  const studentAnswer = $('#student-answer').value.trim();
  if (!studentAnswer) { alert('Escribe la respuesta del alumno.'); return; }

  const caseId = parseInt($('#case-select').value, 10);
  let body, url;

  if (caseId) {
    url = '/api/grade_case';
    body = { case_id: caseId, student_answer: studentAnswer };
  } else {
    const question = $('#cust-question').value.trim();
    const ideal = $('#cust-ideal').value.trim();
    if (!question || !ideal) { alert('Completa pregunta y respuesta ideal.'); return; }
    let conceptList, bonusList;
    try {
      conceptList = parseCustomConcepts($('#cust-concepts').value);
      bonusList = parseBonusTerms($('#cust-bonus').value);
    } catch (e) { alert(e.message); return; }
    url = '/api/grade';
    body = {
      student_answer: studentAnswer,
      reference: {
        question,
        subject: $('#cust-subject').value.trim() || 'General',
        education_level: $('#cust-level').value.trim() || 'Bachillerato',
        ideal_answer: ideal,
        key_concepts: conceptList,
        bonus_terms: bonusList,
      },
    };
  }

  const btn = $('#btn-grade');
  btn.disabled = true; btn.textContent = 'Corrigiendo...';
  try {
    const res = await fetch(url, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      alert(`Error: ${err.detail || res.statusText}`); return;
    }
    const data = await res.json();
    LAST_GRADE_RESULT = { data, studentAnswer };
    renderResult(data, studentAnswer);
    renderBonus(data.bonus_hits || []);
    saveToHistory(data, studentAnswer);
    updateHistoryBadge();
  } finally {
    btn.disabled = false; btn.textContent = 'Corregir';
  }
});

function renderBonus(hits) {
  const block = $('#bonus-block');
  const ul = $('#list-bonus');
  ul.innerHTML = '';
  if (!hits.length) { block.classList.add('hidden'); return; }
  block.classList.remove('hidden');
  for (const h of hits) {
    const li = document.createElement('li');
    li.textContent = `${h.term} (+${h.weight.toFixed(2)})`;
    ul.appendChild(li);
  }
}

// ════════════════════════════════════════════════════════════════════════════
// Explicar nota con IA
// ════════════════════════════════════════════════════════════════════════════

let LAST_GRADE_RESULT = null;

$('#btn-explain').addEventListener('click', async () => {
  if (!LAST_GRADE_RESULT) { alert('Primero corrige una respuesta.'); return; }
  const { data, studentAnswer } = LAST_GRADE_RESULT;

  const btn = $('#btn-explain');
  btn.disabled = true;
  const orig = btn.innerHTML;
  btn.innerHTML = '<span>✨</span> Pensando...';

  const ref = data.reference;
  try {
    const res = await fetch('/api/explain_grade', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        reference: {
          question: ref.question,
          subject: ref.subject,
          education_level: ref.education_level,
          ideal_answer: ref.ideal_answer,
          key_concepts: ref.key_concepts,
          bonus_terms: ref.bonus_terms || [],
        },
        student_answer: studentAnswer,
        grade_result: data,
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      alert(`Error: ${err.detail || res.statusText}`); return;
    }
    const out = await res.json();
    const p = $('#explain-text');
    p.textContent = out.explanation;
    p.classList.remove('hidden');
  } finally {
    btn.disabled = false; btn.innerHTML = orig;
  }
});

// ════════════════════════════════════════════════════════════════════════════
// Export OCR a Word
// ════════════════════════════════════════════════════════════════════════════

$('#btn-export-docx').addEventListener('click', async () => {
  const question = $('#ocr-question').textContent;
  const answer = $('#ocr-answer').textContent;
  const raw = $('#ocr-raw').textContent;
  const body = {
    question: question === '(no detectada)' ? '' : question,
    answer: answer === '(no detectada)' ? '' : answer,
    raw_text: raw,
    title: 'Examen transcrito',
  };
  const res = await fetch('/api/export_docx', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) { alert('Error generando .docx'); return; }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = 'examen.docx';
  document.body.appendChild(a); a.click();
  document.body.removeChild(a); URL.revokeObjectURL(url);
});

// ════════════════════════════════════════════════════════════════════════════
// Top errores del lote
// ════════════════════════════════════════════════════════════════════════════

const _origRenderBatch = renderBatchResult;
renderBatchResult = function (data) {
  _origRenderBatch(data);
  renderTopErrors(data);
};

function renderTopErrors(data) {
  const total = data.results.length;
  const counter = new Map();
  for (const r of data.results) {
    for (const c of r.missing) counter.set(c, (counter.get(c) || 0) + 1);
  }
  const sorted = [...counter.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10);

  const tbody = $('#batch-errors-tbody');
  tbody.innerHTML = '';
  if (!sorted.length) {
    tbody.innerHTML = '<tr><td colspan="4" class="muted small" style="text-align:center">Ningún concepto faltó a más de un alumno 🎉</td></tr>';
    return;
  }
  for (const [concept, n] of sorted) {
    const pct = Math.round((n / total) * 100);
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><strong>${escapeHtml(concept)}</strong></td>
      <td>${n} / ${total}</td>
      <td>
        <div class="score-bar" style="max-width:160px"><div class="score-fill" style="width:${pct}%;background:var(--danger)"></div></div>
        <span class="muted small">${pct}%</span>
      </td>
      <td><button class="ghost" data-add-ap="${escapeHtml(concept)}">+ Añadir antipatrón</button></td>
    `;
    tbody.appendChild(tr);
  }
  // Cuando pulses, abre el sub-tab lexicon con el concepto pre-rellenado
  tbody.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-add-ap]');
    if (!btn) return;
    activateTab('teacher');
    document.querySelector('.subnav-btn[data-sub="lexicon"]')?.click();
    $('#ap-concept').value = btn.dataset.addAp;
    $('#ap-concept').scrollIntoView({ behavior: 'smooth', block: 'center' });
  }, { once: true });
}

// ════════════════════════════════════════════════════════════════════════════
// SQLite calibration (BD server-side)
// ════════════════════════════════════════════════════════════════════════════

$('#btn-cal-load-db').addEventListener('click', async () => {
  const question = $('#cal-question').value.trim();
  if (!question) { alert('Define la pregunta primero.'); return; }
  const res = await fetch(`/api/calibration/examples?question=${encodeURIComponent(question)}`);
  if (!res.ok) { alert('Error cargando de BD'); return; }
  const items = await res.json();
  if (!items.length) {
    alert(`No hay ejemplos guardados para esta pregunta.`);
    return;
  }
  // Merge sin duplicar
  for (const it of items) {
    if (!CAL_EXAMPLES.some((e) => e.answer === it.answer && e.score === it.score)) {
      CAL_EXAMPLES.push({ answer: it.answer, score: it.score });
    }
  }
  renderCalExamples();
});

$('#btn-cal-save-db').addEventListener('click', async () => {
  const question = $('#cal-question').value.trim();
  if (!question) { alert('Define la pregunta primero.'); return; }
  if (!CAL_EXAMPLES.length) { alert('No hay ejemplos que guardar.'); return; }
  const subject = '';
  let ok = 0;
  for (const ex of CAL_EXAMPLES) {
    const res = await fetch('/api/calibration/examples', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, subject, answer: ex.answer, score: ex.score }),
    });
    if (res.ok) ok++;
  }
  alert(`Guardados ${ok}/${CAL_EXAMPLES.length} ejemplos en BD.`);
});

// ════════════════════════════════════════════════════════════════════════════
// Mates/Física experimental (paso a paso)
// ════════════════════════════════════════════════════════════════════════════

$('#btn-steps-grade').addEventListener('click', async () => {
  const subject = $('#steps-subject').value;
  const question = $('#steps-question').value.trim();
  const answer = $('#steps-answer').value.trim();
  const max_points = parseFloat($('#steps-max').value) || 10;
  if (!question || !answer) { alert('Completa enunciado y respuesta.'); return; }

  const btn = $('#btn-steps-grade');
  btn.disabled = true;
  const orig = btn.innerHTML;
  btn.innerHTML = '<span>✨</span> Corrigiendo...';

  try {
    const res = await fetch('/api/grade_steps', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ subject, question, student_answer: answer, max_points }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      alert(`Error: ${err.detail || res.statusText}`); return;
    }
    renderStepsResult(await res.json(), max_points);
  } finally {
    btn.disabled = false; btn.innerHTML = orig;
  }
});

// ════════════════════════════════════════════════════════════════════════════
// OCR estructurado (Claude Vision)
// ════════════════════════════════════════════════════════════════════════════

let VISION_STRUCTURE = null;     // estructura extraída (editable)
let VISION_SOLUTIONS = [];       // [{row, col, correct}]

// Toggle modo simple/estructurado en OCR
$$('[data-ocr-mode]').forEach((b) => {
  b.addEventListener('click', () => {
    $$('[data-ocr-mode]').forEach((x) => x.classList.toggle('active', x === b));
    const mode = b.dataset.ocrMode;
    $$('.ocr-pane').forEach((p) => p.classList.toggle('active', p.id === `ocr-${mode}`));
  });
});

// Preview imagen
$('#ocr-vision-image').addEventListener('change', (e) => {
  const file = e.target.files[0];
  const preview = $('#ocr-vision-preview');
  if (!file) { preview.classList.add('hidden'); preview.src = ''; return; }
  preview.src = URL.createObjectURL(file);
  preview.classList.remove('hidden');
});

// Extraer estructura
$('#btn-vision-extract').addEventListener('click', async () => {
  const file = $('#ocr-vision-image').files[0];
  if (!file) { alert('Sube una imagen primero.'); return; }

  const fd = new FormData();
  fd.append('image', file);

  const btn = $('#btn-vision-extract');
  btn.disabled = true;
  const orig = btn.innerHTML;
  btn.innerHTML = '<span>✨</span> Extrayendo...';

  try {
    const res = await fetch('/api/extract_structured', { method: 'POST', body: fd });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      alert(`Error: ${err.detail || res.statusText}`); return;
    }
    VISION_STRUCTURE = await res.json();
    VISION_SOLUTIONS = [];
    renderVisionTable();
  } finally {
    btn.disabled = false; btn.innerHTML = orig;
  }
});

function renderVisionTable() {
  if (!VISION_STRUCTURE) return;
  const card = $('#vision-result-card');
  card.classList.remove('hidden');
  $('#vision-grade-card').classList.add('hidden');

  $('#vision-title').textContent = VISION_STRUCTURE.title || 'Estructura extraída';
  $('#vision-instructions').textContent = VISION_STRUCTURE.instructions || '';

  const thead = $('#vision-thead');
  const tbody = $('#vision-tbody');
  thead.innerHTML = '';
  tbody.innerHTML = '';

  const headers = VISION_STRUCTURE.headers && VISION_STRUCTURE.headers.length
    ? VISION_STRUCTURE.headers
    : VISION_STRUCTURE.rows[0]?.map((_, i) => `Col ${i + 1}`) || [];

  const trh = document.createElement('tr');
  trh.innerHTML = '<th>#</th>' + headers.map((h) => `<th>${escapeHtml(h)}</th>`).join('') + '<th>Correcta</th>';
  thead.appendChild(trh);

  VISION_STRUCTURE.rows.forEach((row, ri) => {
    const tr = document.createElement('tr');
    tr.innerHTML = `<td class="muted small">${ri + 1}</td>`;

    row.forEach((cell, ci) => {
      const td = document.createElement('td');
      td.className = `cell-${cell.kind || 'student'}`;
      td.innerHTML = `
        <div><span class="cell-kind ${cell.kind || 'student'}" title="${cell.kind}"></span>
          <input class="cell-input" type="text" value="${escapeHtml(cell.text || '')}"
                 data-row="${ri}" data-col="${ci}" data-field="text">
        </div>`;
      tr.appendChild(td);
    });

    // Columna "Correcta" como input que abarca todas las celdas student/blank de la fila
    const td = document.createElement('td');
    const solCount = row.filter((c) => c.kind !== 'printed').length;
    if (solCount === 0) {
      td.innerHTML = '<span class="muted small">(fila contextual)</span>';
    } else {
      // Mostramos un input por cada celda evaluable
      td.innerHTML = row.map((cell, ci) => {
        if (cell.kind === 'printed') return '';
        const sol = VISION_SOLUTIONS.find((s) => s.row === ri && s.col === ci);
        const val = sol?.correct || '';
        return `<div style="margin:2px 0">
          <small class="muted">${escapeHtml(headers[ci] || 'col')}</small>
          <input class="cell-input cell-correct" type="text" value="${escapeHtml(val)}"
                 data-row="${ri}" data-col="${ci}">
        </div>`;
      }).join('');
    }
    tr.appendChild(td);

    tbody.appendChild(tr);
  });

  // Listeners: editar texto del alumno / celda
  tbody.addEventListener('input', (e) => {
    const inp = e.target.closest('.cell-input');
    if (!inp) return;
    const r = parseInt(inp.dataset.row, 10);
    const c = parseInt(inp.dataset.col, 10);
    if (inp.classList.contains('cell-correct')) {
      const idx = VISION_SOLUTIONS.findIndex((s) => s.row === r && s.col === c);
      if (idx >= 0) VISION_SOLUTIONS[idx].correct = inp.value;
      else VISION_SOLUTIONS.push({ row: r, col: c, correct: inp.value });
    } else if (inp.dataset.field === 'text') {
      VISION_STRUCTURE.rows[r][c].text = inp.value;
    }
  });
}

// Generar correcciones con IA
$('#btn-vision-solutions').addEventListener('click', async () => {
  if (!VISION_STRUCTURE) return;
  const btn = $('#btn-vision-solutions');
  btn.disabled = true;
  const orig = btn.innerHTML;
  btn.innerHTML = '<span>✨</span> Generando...';

  try {
    const res = await fetch('/api/generate_solutions', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        structure: VISION_STRUCTURE,
        subject: $('#ocr-vision-subject').value.trim() || 'General',
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      alert(`Error: ${err.detail || res.statusText}`); return;
    }
    const data = await res.json();
    VISION_SOLUTIONS = data.solutions || [];
    renderVisionTable();
  } finally {
    btn.disabled = false; btn.innerHTML = orig;
  }
});

// Corregir
$('#btn-vision-grade').addEventListener('click', async () => {
  if (!VISION_STRUCTURE) return;
  if (!VISION_SOLUTIONS.length) {
    alert('Rellena la columna "Correcta" manualmente o usa "Generar correcciones con IA".');
    return;
  }

  const res = await fetch('/api/grade_structured', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      structure: VISION_STRUCTURE,
      solutions: VISION_SOLUTIONS,
      fuzzy_threshold: 0.80,
      points_per_cell: 1.0,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    alert(`Error: ${err.detail || res.statusText}`); return;
  }
  renderVisionGrade(await res.json());
});

function renderVisionGrade(data) {
  const card = $('#vision-grade-card');
  card.classList.remove('hidden');
  card.scrollIntoView({ behavior: 'smooth', block: 'start' });

  animateScore('#vision-score', data.score_over_10, 2);
  requestAnimationFrame(() => {
    $('#vision-fill').style.width = `${data.score_over_10 * 10}%`;
  });
  $('#vision-feedback').textContent =
    `${data.earned}/${data.max_points} puntos · ${data.score_pct}% acierto`;

  const tbody = $('#vision-grade-tbody');
  tbody.innerHTML = '';
  const headers = VISION_STRUCTURE.headers || [];
  for (const c of data.cells) {
    const tr = document.createElement('tr');
    tr.className = `row-${c.verdict}`;
    const colName = headers[c.col] || `Col ${c.col + 1}`;
    const verdictLabel = {
      correct: '✓ Correcto',
      partial: `~ Parcial (sim ${c.similarity.toFixed(2)})`,
      wrong: '✗ Incorrecto',
      blank: '— En blanco',
    }[c.verdict] || c.verdict;
    tr.innerHTML = `
      <td>${c.row + 1}</td>
      <td>${escapeHtml(colName)}</td>
      <td>${escapeHtml(c.student_text || '(vacío)')}</td>
      <td>${escapeHtml(c.correct)}</td>
      <td class="verdict-${c.verdict}">${verdictLabel}</td>
      <td>${c.points.toFixed(2)} / ${c.points_max.toFixed(2)}</td>
    `;
    tbody.appendChild(tr);
  }
}

// ════════════════════════════════════════════════════════════════════════════
// Plantillas de examen reutilizables
// ════════════════════════════════════════════════════════════════════════════

let CURRENT_TEMPLATE = null;
let CURRENT_TEMPLATE_GRADINGS = [];

async function loadTemplates() {
  const res = await fetch('/api/templates');
  if (!res.ok) return [];
  return await res.json();
}

async function renderTemplatesGrid() {
  const list = await loadTemplates();
  const grid = $('#templates-list');
  if (!grid) return;
  grid.innerHTML = '';
  if (!list.length) {
    grid.innerHTML = '<div class="muted small" style="padding:14px;border:1px dashed var(--border);border-radius:8px">No tienes plantillas todavía. Crea la primera con el botón de abajo o importa un modelo predefinido.</div>';
    return;
  }
  for (const t of list) {
    const card = document.createElement('div');
    card.className = 'template-card';
    card.innerHTML = `
      <button class="template-card-delete" title="Eliminar plantilla" data-del-id="${t.id}" data-del-name="${escapeHtml(t.name)}">✕</button>
      <h3 class="template-card-name">${escapeHtml(t.name)}</h3>
      <div class="template-card-meta">
        <span class="chip">${escapeHtml(t.subject || 'General')}</span>
        ${t.education_level ? `<span class="chip secondary">${escapeHtml(t.education_level)}</span>` : ''}
      </div>
      <div class="template-card-stats">
        <div class="template-stat"><span class="template-stat-num">${t.gradings_count}</span><span class="template-stat-label">alumnos</span></div>
        <div class="template-stat"><span class="template-stat-num">${t.gradings_mean ?? '—'}</span><span class="template-stat-label">nota media</span></div>
      </div>
    `;
    card.addEventListener('click', (e) => {
      // Si el click viene del botón eliminar, no abrir la plantilla
      if (e.target.closest('.template-card-delete')) return;
      openTemplateView(t.id);
    });
    card.querySelector('.template-card-delete').addEventListener('click', async (e) => {
      e.stopPropagation();
      const id = e.currentTarget.dataset.delId;
      const name = e.currentTarget.dataset.delName;
      if (!confirm(`¿Eliminar la plantilla "${name}" y todas sus correcciones?`)) return;
      const r = await fetch(`/api/templates/${id}`, { method: 'DELETE' });
      if (!r.ok) { alert('Error eliminando'); return; }
      renderTemplatesGrid();
    });
    grid.appendChild(card);
  }
}

renderTemplatesGrid();

// ── Modelos predefinidos ───────────────────────────────────────────────────

const PRESET_TEMPLATES = [
  {
    name: 'Formulación inorgánica · básica',
    subject: 'Química',
    education_level: 'Bachillerato',
    icon: '🧪',
    description: '5 fórmulas comunes con las 3 nomenclaturas (Sistemática, Stock, Tradicional).',
    structure: {
      type: 'table',
      title: 'Formulación inorgánica',
      headers: ['Fórmula', 'Sistemática', 'Stock', 'Tradicional'],
      rows: [
        [
          { role: 'context', text: 'Fe₂O₃' },
          { role: 'evaluable', correct: 'Trióxido de dihierro' },
          { role: 'evaluable', correct: 'Óxido de hierro (III)' },
          { role: 'evaluable', correct: 'Óxido férrico' },
        ],
        [
          { role: 'context', text: 'NaCl' },
          { role: 'evaluable', correct: 'Cloruro de sodio' },
          { role: 'evaluable', correct: 'Cloruro de sodio' },
          { role: 'evaluable', correct: 'Sal común' },
        ],
        [
          { role: 'context', text: 'CuO' },
          { role: 'evaluable', correct: 'Monóxido de cobre' },
          { role: 'evaluable', correct: 'Óxido de cobre (II)' },
          { role: 'evaluable', correct: 'Óxido cúprico' },
        ],
        [
          { role: 'context', text: 'NH₃' },
          { role: 'evaluable', correct: 'Trihidruro de nitrógeno' },
          { role: 'none' },
          { role: 'evaluable', correct: 'Amoníaco' },
        ],
        [
          { role: 'context', text: 'HCl' },
          { role: 'evaluable', correct: 'Cloruro de hidrógeno' },
          { role: 'none' },
          { role: 'evaluable', correct: 'Ácido clorhídrico' },
        ],
      ],
    },
  },
  {
    name: 'Verbos irregulares · inglés',
    subject: 'Inglés',
    education_level: 'Bachillerato',
    icon: '🇬🇧',
    description: 'Past Simple, Past Participle y traducción de 6 verbos irregulares frecuentes.',
    structure: {
      type: 'table',
      title: 'Irregular verbs',
      headers: ['Infinitive', 'Past Simple', 'Past Participle', 'Spanish'],
      rows: [
        [{ role: 'context', text: 'go' }, { role: 'evaluable', correct: 'went' }, { role: 'evaluable', correct: 'gone' }, { role: 'evaluable', correct: 'ir' }],
        [{ role: 'context', text: 'see' }, { role: 'evaluable', correct: 'saw' }, { role: 'evaluable', correct: 'seen' }, { role: 'evaluable', correct: 'ver' }],
        [{ role: 'context', text: 'write' }, { role: 'evaluable', correct: 'wrote' }, { role: 'evaluable', correct: 'written' }, { role: 'evaluable', correct: 'escribir' }],
        [{ role: 'context', text: 'take' }, { role: 'evaluable', correct: 'took' }, { role: 'evaluable', correct: 'taken' }, { role: 'evaluable', correct: 'tomar' }],
        [{ role: 'context', text: 'come' }, { role: 'evaluable', correct: 'came' }, { role: 'evaluable', correct: 'come' }, { role: 'evaluable', correct: 'venir' }],
        [{ role: 'context', text: 'buy' }, { role: 'evaluable', correct: 'bought' }, { role: 'evaluable', correct: 'bought' }, { role: 'evaluable', correct: 'comprar' }],
      ],
    },
  },
  {
    name: 'Análisis morfológico · lengua',
    subject: 'Lengua y Literatura',
    education_level: 'ESO/Bachillerato',
    icon: '📖',
    description: 'Categoría gramatical, género, número y rasgo de 5 palabras.',
    structure: {
      type: 'table',
      title: 'Análisis morfológico',
      headers: ['Palabra', 'Categoría', 'Género', 'Número', 'Rasgo'],
      rows: [
        [{ role: 'context', text: 'casas' }, { role: 'evaluable', correct: 'sustantivo' }, { role: 'evaluable', correct: 'femenino' }, { role: 'evaluable', correct: 'plural' }, { role: 'none' }],
        [{ role: 'context', text: 'corriendo' }, { role: 'evaluable', correct: 'verbo' }, { role: 'none' }, { role: 'none' }, { role: 'evaluable', correct: 'gerundio' }],
        [{ role: 'context', text: 'aquellos' }, { role: 'evaluable', correct: 'determinante' }, { role: 'evaluable', correct: 'masculino' }, { role: 'evaluable', correct: 'plural' }, { role: 'evaluable', correct: 'demostrativo' }],
        [{ role: 'context', text: 'rápidamente' }, { role: 'evaluable', correct: 'adverbio' }, { role: 'none' }, { role: 'none' }, { role: 'evaluable', correct: 'modo' }],
        [{ role: 'context', text: 'ella' }, { role: 'evaluable', correct: 'pronombre' }, { role: 'evaluable', correct: 'femenino' }, { role: 'evaluable', correct: 'singular' }, { role: 'evaluable', correct: 'personal' }],
      ],
    },
  },
  {
    name: 'Tabla periódica · básica',
    subject: 'Química',
    education_level: 'ESO',
    icon: '⚛️',
    description: 'Nombre, número atómico y grupo de 6 elementos.',
    structure: {
      type: 'table',
      title: 'Elementos químicos básicos',
      headers: ['Símbolo', 'Nombre', 'Nº atómico', 'Grupo'],
      rows: [
        [{ role: 'context', text: 'H' }, { role: 'evaluable', correct: 'Hidrógeno' }, { role: 'evaluable', correct: '1' }, { role: 'evaluable', correct: '1' }],
        [{ role: 'context', text: 'O' }, { role: 'evaluable', correct: 'Oxígeno' }, { role: 'evaluable', correct: '8' }, { role: 'evaluable', correct: '16' }],
        [{ role: 'context', text: 'Fe' }, { role: 'evaluable', correct: 'Hierro' }, { role: 'evaluable', correct: '26' }, { role: 'evaluable', correct: '8' }],
        [{ role: 'context', text: 'Na' }, { role: 'evaluable', correct: 'Sodio' }, { role: 'evaluable', correct: '11' }, { role: 'evaluable', correct: '1' }],
        [{ role: 'context', text: 'Cl' }, { role: 'evaluable', correct: 'Cloro' }, { role: 'evaluable', correct: '17' }, { role: 'evaluable', correct: '17' }],
        [{ role: 'context', text: 'C' }, { role: 'evaluable', correct: 'Carbono' }, { role: 'evaluable', correct: '6' }, { role: 'evaluable', correct: '14' }],
      ],
    },
  },
  {
    name: 'Fechas clave · Historia de España',
    subject: 'Historia',
    education_level: 'Bachillerato',
    icon: '🏛️',
    description: 'Año (pista) → evento y consecuencia principal.',
    structure: {
      type: 'table',
      title: 'Hitos de la Historia contemporánea de España',
      headers: ['Año', 'Evento', 'Consecuencia principal'],
      rows: [
        [{ role: 'context', text: '1492' }, { role: 'evaluable', correct: 'Descubrimiento de América' }, { role: 'evaluable', correct: 'Inicio de la Edad Moderna española' }],
        [{ role: 'context', text: '1808' }, { role: 'evaluable', correct: 'Inicio de la Guerra de Independencia' }, { role: 'evaluable', correct: 'Constitución de Cádiz (1812)' }],
        [{ role: 'context', text: '1898' }, { role: 'evaluable', correct: 'Pérdida de Cuba, Puerto Rico y Filipinas' }, { role: 'evaluable', correct: 'Crisis de identidad y Generación del 98' }],
        [{ role: 'context', text: '1931' }, { role: 'evaluable', correct: 'Proclamación de la II República' }, { role: 'evaluable', correct: 'Nueva constitución democrática' }],
        [{ role: 'context', text: '1978' }, { role: 'evaluable', correct: 'Constitución española' }, { role: 'evaluable', correct: 'Consolidación del Estado de Derecho' }],
      ],
    },
  },
];

function renderPresetTemplates() {
  const grid = $('#preset-templates-list');
  if (!grid) return;
  grid.innerHTML = '';
  for (const m of PRESET_TEMPLATES) {
    const card = document.createElement('div');
    card.className = 'template-card preset';
    const evaluables = m.structure.rows.reduce(
      (n, row) => n + row.filter((c) => c.role === 'evaluable').length, 0
    );
    card.innerHTML = `
      <h3 class="template-card-name">${m.icon} ${escapeHtml(m.name)}</h3>
      <div class="template-card-meta">
        <span class="chip">${escapeHtml(m.subject)}</span>
        <span class="chip secondary">${escapeHtml(m.education_level)}</span>
      </div>
      <p class="muted small" style="margin:6px 0 0">${escapeHtml(m.description)}</p>
      <div class="template-card-stats">
        <div class="template-stat"><span class="template-stat-num">${m.structure.rows.length}</span><span class="template-stat-label">filas</span></div>
        <div class="template-stat"><span class="template-stat-num">${evaluables}</span><span class="template-stat-label">celdas a corregir</span></div>
      </div>
    `;
    card.addEventListener('click', async () => {
      if (!confirm(`¿Importar "${m.name}" como plantilla nueva?`)) return;
      const res = await fetch('/api/templates', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: m.name,
          subject: m.subject,
          education_level: m.education_level,
          structure: m.structure,
        }),
      });
      if (!res.ok) { alert('Error importando'); return; }
      const tpl = await res.json();
      await renderTemplatesGrid();
      openTemplateView(tpl.id);
    });
    grid.appendChild(card);
  }
}

renderPresetTemplates();

// ── Modal helpers ──────────────────────────────────────────────────────────

function openModal(id) { $('#' + id).classList.remove('hidden'); }
function closeModal(id) { $('#' + id).classList.add('hidden'); }

document.addEventListener('click', (e) => {
  const closer = e.target.closest('[data-close-modal]');
  if (closer) closeModal(closer.dataset.closeModal);
});

// ── Crear plantilla ─────────────────────────────────────────────────────

$('#btn-template-new').addEventListener('click', () => {
  // Reset
  $('#new-tpl-name').value = '';
  $('#new-tpl-subject').value = '';
  $('#new-tpl-level').value = 'Bachillerato';
  $('#manual-headers').value = 'Pregunta,Respuesta correcta';
  $('#manual-nrows').value = '5';
  $('#tpl-blank-image').value = '';
  $('#tpl-corrected-image').value = '';
  $('#tpl-blank-preview').classList.add('hidden');
  $('#tpl-corrected-preview').classList.add('hidden');
  $$('.mode-btn[data-create-mode]').forEach((b, i) => b.classList.toggle('active', i === 0));
  $$('.create-pane').forEach((p, i) => p.classList.toggle('active', i === 0));
  openModal('modal-template-new');
});

// Toggle create modes
$$('[data-create-mode]').forEach((b) => {
  b.addEventListener('click', () => {
    $$('[data-create-mode]').forEach((x) => x.classList.toggle('active', x === b));
    const mode = b.dataset.createMode;
    $$('.create-pane').forEach((p) => p.classList.toggle('active', p.id === `create-${mode}`));
  });
});

// Previews
$('#tpl-blank-image').addEventListener('change', (e) => {
  const f = e.target.files[0];
  const p = $('#tpl-blank-preview');
  if (!f) { p.classList.add('hidden'); return; }
  p.src = URL.createObjectURL(f);
  p.classList.remove('hidden');
});
$('#tpl-corrected-image').addEventListener('change', (e) => {
  const f = e.target.files[0];
  const p = $('#tpl-corrected-preview');
  if (!f) { p.classList.add('hidden'); return; }
  p.src = URL.createObjectURL(f);
  p.classList.remove('hidden');
});

$('#btn-template-create').addEventListener('click', async () => {
  const name = $('#new-tpl-name').value.trim();
  if (!name) { alert('Pon un nombre a la plantilla.'); return; }
  const subject = $('#new-tpl-subject').value.trim() || 'General';
  const level = $('#new-tpl-level').value.trim() || 'Bachillerato';

  const activeMode = $$('[data-create-mode]').find?.((b) => b.classList.contains('active'))
    || document.querySelector('[data-create-mode].active');
  const mode = activeMode.dataset.createMode;

  const btn = $('#btn-template-create');
  btn.disabled = true; btn.textContent = 'Creando...';

  try {
    let structure;
    if (mode === 'manual') {
      const headers = $('#manual-headers').value.split(',').map((s) => s.trim()).filter(Boolean);
      const nrows = parseInt($('#manual-nrows').value, 10) || 5;
      structure = {
        type: 'table', title: name, headers,
        rows: Array.from({ length: nrows }, () =>
          headers.map((_, i) => ({ role: i === 0 ? 'context' : 'evaluable', text: '', correct: '' })),
        ),
      };
    } else {
      const inputId = mode === 'blank' ? 'tpl-blank-image' : 'tpl-corrected-image';
      const file = $('#' + inputId).files[0];
      if (!file) { alert('Sube una imagen primero.'); return; }
      const fd = new FormData();
      fd.append('image', file);
      fd.append('mode', mode);
      fd.append('subject', subject);
      const res = await fetch('/api/templates/from_image', { method: 'POST', body: fd });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        alert(`Error extrayendo: ${err.detail || res.statusText}`);
        return;
      }
      const data = await res.json();
      structure = data.structure;
    }

    const res = await fetch('/api/templates', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, subject, education_level: level, structure }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      alert(`Error creando: ${err.detail || res.statusText}`); return;
    }
    const tpl = await res.json();
    closeModal('modal-template-new');
    await renderTemplatesGrid();
    openTemplateView(tpl.id);
  } finally {
    btn.disabled = false; btn.textContent = 'Crear plantilla';
  }
});

// ── Vista de plantilla ─────────────────────────────────────────────────

async function openTemplateView(id) {
  const res = await fetch(`/api/templates/${id}`);
  if (!res.ok) { alert('No se pudo cargar la plantilla'); return; }
  CURRENT_TEMPLATE = await res.json();
  $('#view-tpl-name').textContent = CURRENT_TEMPLATE.name;
  $('#view-tpl-subject').textContent = CURRENT_TEMPLATE.subject || 'General';
  $('#view-tpl-level').textContent = CURRENT_TEMPLATE.education_level || '';

  renderTplEditTable();
  $$('.subnav-btn[data-tplsub]').forEach((b, i) => b.classList.toggle('active', i === 0));
  $$('.tpl-sub').forEach((p, i) => p.classList.toggle('active', i === 0));

  $('#apply-student-name').value = '';
  $('#apply-image').value = '';
  $('#apply-preview').classList.add('hidden');
  $('#apply-result').classList.add('hidden');

  await refreshTemplateGradings();
  openModal('modal-template-view');
}

function renderTplEditTable() {
  const s = CURRENT_TEMPLATE.structure;
  const t = $('#tpl-edit-table');
  const headers = s.headers && s.headers.length ? s.headers : s.rows[0]?.map((_, i) => `Col ${i + 1}`) || [];
  let html = '<thead><tr>' + headers.map((h) => `<th>${escapeHtml(h)}</th>`).join('') + '</tr></thead><tbody>';
  s.rows.forEach((row, ri) => {
    html += '<tr class="tpl-edit-row">';
    row.forEach((cell, ci) => {
      const role = cell.role || 'evaluable';
      const text = role === 'context' ? (cell.text || '') : (cell.correct || '');
      html += `<td>
        <select class="tpl-role-select" data-r="${ri}" data-c="${ci}" data-kind="role">
          <option value="context"${role==='context'?' selected':''}>contexto</option>
          <option value="evaluable"${role==='evaluable'?' selected':''}>evaluable</option>
          <option value="none"${role==='none'?' selected':''}>no aplica</option>
        </select>
        <input class="tpl-cell-input" data-r="${ri}" data-c="${ci}" data-kind="text"
               type="text" value="${escapeHtml(text)}" ${role==='none'?'disabled':''}>
      </td>`;
    });
    html += '</tr>';
  });
  html += '</tbody>';
  t.innerHTML = html;
}

// Listener ÚNICO en la tabla (delegación). Antes se añadía dentro de
// renderTplEditTable y al re-render se acumulaban (1, 2, 4, 8…), causando
// que la página colgase tras 4-5 cambios de rol.
$('#tpl-edit-table').addEventListener('change', handleTplCellChange);
$('#tpl-edit-table').addEventListener('input', handleTplCellChange);

function handleTplCellChange(e) {
  const el = e.target;
  if (!CURRENT_TEMPLATE) return;
  const r = parseInt(el.dataset.r, 10), c = parseInt(el.dataset.c, 10);
  if (Number.isNaN(r) || Number.isNaN(c)) return;
  const row = CURRENT_TEMPLATE.structure.rows[r];
  if (!row || !row[c]) return;
  const cell = row[c];

  if (el.dataset.kind === 'role') {
    cell.role = el.value;
    // Actualizamos SOLO el input gemelo (mismo <td>), sin redibujar la tabla.
    const input = el.closest('td')?.querySelector('.tpl-cell-input');
    if (input) {
      input.disabled = (el.value === 'none');
      if (el.value === 'context')     input.value = cell.text || '';
      else if (el.value === 'evaluable') input.value = cell.correct || '';
      else input.value = '';
    }
  } else if (el.dataset.kind === 'text') {
    if (cell.role === 'context') cell.text = el.value;
    else if (cell.role === 'evaluable') cell.correct = el.value;
  }
}

$('#btn-tpl-save').addEventListener('click', async () => {
  if (!CURRENT_TEMPLATE) return;
  const res = await fetch(`/api/templates/${CURRENT_TEMPLATE.id}`, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ structure: CURRENT_TEMPLATE.structure }),
  });
  if (!res.ok) { alert('Error guardando'); return; }
  CURRENT_TEMPLATE = await res.json();
  alert('Plantilla guardada.');
  renderTemplatesGrid();
});

$('#btn-tpl-delete').addEventListener('click', async () => {
  if (!CURRENT_TEMPLATE) return;
  if (!confirm(`¿Eliminar la plantilla "${CURRENT_TEMPLATE.name}" y todas sus correcciones?`)) return;
  const res = await fetch(`/api/templates/${CURRENT_TEMPLATE.id}`, { method: 'DELETE' });
  if (!res.ok) { alert('Error eliminando'); return; }
  closeModal('modal-template-view');
  renderTemplatesGrid();
});

// Sub-tabs dentro de modal de plantilla
$$('[data-tplsub]').forEach((b) => {
  b.addEventListener('click', async () => {
    $$('[data-tplsub]').forEach((x) => x.classList.toggle('active', x === b));
    const sub = b.dataset.tplsub;
    $$('.tpl-sub').forEach((p) => p.classList.toggle('active', p.id === `tpl-sub-${sub}`));
    if (sub === 'gradings') await refreshTemplateGradings();
    if (sub === 'stats') await renderTemplateStats();
  });
});

// Aplicar a alumno
$('#apply-image').addEventListener('change', (e) => {
  const f = e.target.files[0];
  const p = $('#apply-preview');
  if (!f) { p.classList.add('hidden'); return; }
  p.src = URL.createObjectURL(f);
  p.classList.remove('hidden');
});

$('#btn-apply-grade').addEventListener('click', async () => {
  if (!CURRENT_TEMPLATE) return;
  const name = $('#apply-student-name').value.trim();
  const file = $('#apply-image').files[0];
  if (!name) { alert('Pon el nombre del alumno.'); return; }
  if (!file) { alert('Sube la foto del examen del alumno.'); return; }

  const fd = new FormData();
  fd.append('image', file);
  fd.append('student_name', name);

  const btn = $('#btn-apply-grade');
  btn.disabled = true;
  const orig = btn.innerHTML;
  btn.innerHTML = '<span>✨</span> Corrigiendo...';

  try {
    const res = await fetch(`/api/templates/${CURRENT_TEMPLATE.id}/grade_image`, {
      method: 'POST', body: fd,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      alert(`Error: ${err.detail || res.statusText}`); return;
    }
    renderApplyResult(await res.json());
    await refreshTemplateGradings();
    renderTemplatesGrid();  // refresca counts
  } finally {
    btn.disabled = false; btn.innerHTML = orig;
  }
});

function renderApplyResult(data) {
  const wrap = $('#apply-result');
  wrap.classList.remove('hidden');
  const score = data.score_over_10;
  const scoreClass = score >= 7 ? 'good' : score >= 5 ? 'mid' : 'bad';
  const cellRows = (data.grade_result.cells || []).map((c) => `
    <tr class="row-${c.verdict}">
      <td>${c.row + 1}</td>
      <td>${escapeHtml(CURRENT_TEMPLATE.structure.headers[c.col] || `Col ${c.col + 1}`)}</td>
      <td>${escapeHtml(c.student_text || '(vacío)')}</td>
      <td>${escapeHtml(c.correct)}</td>
      <td class="verdict-${c.verdict}">${{correct:'✓ Correcto', partial:'~ Parcial', wrong:'✗ Incorrecto', blank:'— En blanco'}[c.verdict] || c.verdict}</td>
      <td>${c.points.toFixed(2)} / ${c.points_max.toFixed(2)}</td>
    </tr>`).join('');
  wrap.innerHTML = `
    <div class="score-block">
      <div class="score-big history-score ${scoreClass}">${score.toFixed(2)}</div>
      <div class="score-info">
        <div class="score-bar"><div class="score-fill" style="width:${score*10}%"></div></div>
        <p class="feedback">${data.earned}/${data.max_points} puntos · alumno: <strong>${escapeHtml(data.student_name)}</strong></p>
      </div>
    </div>
    <div class="table-wrap" style="margin-top:14px">
      <table class="cases-table">
        <thead><tr><th>Fila</th><th>Columna</th><th>Alumno</th><th>Correcta</th><th>Veredicto</th><th>Puntos</th></tr></thead>
        <tbody>${cellRows}</tbody>
      </table>
    </div>
  `;
}

async function refreshTemplateGradings() {
  if (!CURRENT_TEMPLATE) return;
  const res = await fetch(`/api/templates/${CURRENT_TEMPLATE.id}/gradings`);
  if (!res.ok) return;
  CURRENT_TEMPLATE_GRADINGS = await res.json();
  $('#view-tpl-gcount').textContent = CURRENT_TEMPLATE_GRADINGS.length;

  const tbody = $('#gradings-tbody');
  tbody.innerHTML = '';
  if (!CURRENT_TEMPLATE_GRADINGS.length) {
    tbody.innerHTML = '<tr><td colspan="4" class="muted small" style="text-align:center;padding:14px">Sin correcciones todavía. Ve a "Aplicar a alumno" para empezar.</td></tr>';
    return;
  }
  for (const g of CURRENT_TEMPLATE_GRADINGS) {
    const tr = document.createElement('tr');
    const scoreClass = g.score_over_10 >= 7 ? 'verdict-correct' : g.score_over_10 >= 5 ? 'verdict-partial' : 'verdict-wrong';
    tr.innerHTML = `
      <td><strong>${escapeHtml(g.student_name)}</strong></td>
      <td class="${scoreClass}">${g.score_over_10.toFixed(2)}</td>
      <td class="muted small">${new Date(g.created_at + 'Z').toLocaleString('es-ES')}</td>
      <td><button class="ghost del-grading" data-id="${g.id}">Eliminar</button></td>
    `;
    tbody.appendChild(tr);
  }
  tbody.querySelectorAll('.del-grading').forEach((b) => {
    b.addEventListener('click', async () => {
      if (!confirm('¿Eliminar esta corrección?')) return;
      await fetch(`/api/templates/${CURRENT_TEMPLATE.id}/gradings/${b.dataset.id}`, { method: 'DELETE' });
      await refreshTemplateGradings();
      renderTemplatesGrid();
    });
  });
}

async function renderTemplateStats() {
  if (!CURRENT_TEMPLATE) return;
  const res = await fetch(`/api/templates/${CURRENT_TEMPLATE.id}/stats`);
  if (!res.ok) return;
  const s = await res.json();

  $('#tpl-stats-numbers').innerHTML = `
    <div class="stat highlight"><span class="stat-num">${s.mean ?? '—'}</span><span class="stat-label">Media</span></div>
    <div class="stat"><span class="stat-num">${s.median ?? '—'}</span><span class="stat-label">Mediana</span></div>
    <div class="stat"><span class="stat-num">${s.count}</span><span class="stat-label">Alumnos</span></div>
    <div class="stat"><span class="stat-num">${s.min ?? '—'} – ${s.max ?? '—'}</span><span class="stat-label">Rango</span></div>
  `;

  const tbody = $('#tpl-top-errors-tbody');
  tbody.innerHTML = '';
  if (!s.top_errors || !s.top_errors.length) {
    tbody.innerHTML = '<tr><td colspan="3" class="muted small" style="text-align:center;padding:14px">Sin errores agregados todavía.</td></tr>';
    return;
  }
  for (const e of s.top_errors) {
    const pct = Math.round(e.count / e.total * 100);
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${escapeHtml(e.item)}</td>
      <td>${e.count} / ${e.total}</td>
      <td>${pct}%</td>
    `;
    tbody.appendChild(tr);
  }
}

$('#btn-reload-gradings').addEventListener('click', refreshTemplateGradings);

$('#btn-export-gradings').addEventListener('click', () => {
  if (!CURRENT_TEMPLATE_GRADINGS.length) { alert('No hay correcciones que exportar.'); return; }
  const rows = [['alumno', 'nota', 'fecha']];
  for (const g of CURRENT_TEMPLATE_GRADINGS) {
    rows.push([g.student_name, g.score_over_10.toFixed(2), g.created_at]);
  }
  const csv = rows.map((r) => r.map(csvField).join(',')).join('\n');
  downloadFile(`${CURRENT_TEMPLATE.name}_notas.csv`, csv, 'text/csv;charset=utf-8');
});

function renderStepsResult(data, maxPoints) {
  const card = $('#steps-result-card');
  card.classList.remove('hidden');
  card.scrollIntoView({ behavior: 'smooth', block: 'start' });

  const score = data.score || 0;
  animateScore('#steps-score', score, 2);
  requestAnimationFrame(() => {
    $('#steps-fill').style.width = `${(score / maxPoints) * 100}%`;
  });
  $('#steps-summary').textContent = data.summary || '';

  const carry = $('#steps-carry');
  if (data.carry_through_note) {
    carry.classList.remove('hidden');
    carry.innerHTML = `<strong>Carry-through aplicado:</strong> ${escapeHtml(data.carry_through_note)}`;
  } else carry.classList.add('hidden');

  const tbody = $('#steps-tbody');
  tbody.innerHTML = '';
  for (const s of (data.steps || [])) {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><strong>${escapeHtml(s.name || '—')}</strong></td>
      <td class="${s.ok ? 'step-ok-yes' : 'step-ok-no'}">${s.ok ? '✓' : '✗'}</td>
      <td>${(s.points_obtained ?? 0).toFixed(2)} / ${(s.points_max ?? 0).toFixed(2)}</td>
      <td class="muted small">${escapeHtml(s.comment || '')}</td>
    `;
    tbody.appendChild(tr);
  }
}

// ────────────────────────────────────────────────────────────────────────────
// Deep-link de demostración (#demo=<pestaña>): activa una pestaña y, en algunas,
// dispara su acción principal. Útil para documentación y capturas. Inocuo en uso
// normal: solo se ejecuta si la URL incluye el hash #demo=.
// ────────────────────────────────────────────────────────────────────────────
async function runDemoFromHash() {
  const m = (location.hash || '').match(/^#demo=([a-z]+)(?::([a-z]+))?/i);
  if (!m) return;
  const tab = m[1].toLowerCase();
  const sub = (m[2] || '').toLowerCase();
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  // En modo demo desactivamos la animación de los gráficos para que rendericen
  // su estado final de inmediato (útil para capturas en navegador headless).
  if (window.Chart) window.Chart.defaults.animation = false;

  activateTab(tab);
  if (tab === 'grade') {
    for (let i = 0; i < 60 && !CASES.length; i++) await sleep(100);
    const sel = document.querySelector('#case-select');
    if (sel) {
      sel.value = '2';
      sel.dispatchEvent(new Event('change'));
      await sleep(200);
      document.querySelector('#btn-grade')?.click();
      await sleep(1500);
      window.scrollTo(0, 0); // encuadre desde arriba para capturas
    }
  } else if (tab === 'dashboard') {
    document.querySelector('#btn-validate')?.click();
    await sleep(900);
    document.querySelector('#btn-correlation')?.click();
  } else if (tab === 'correlation') {
    activateTab('dashboard');
    await sleep(200);
    document.querySelector('#btn-correlation')?.click();
    await sleep(2600); // fetch + render de los gráficos
    const card = document.querySelector('#correlation-body')?.closest('.card');
    if (card) window.scrollTo(0, card.getBoundingClientRect().top + window.pageYOffset - 70);
  } else if (tab === 'teacher' && sub) {
    document.querySelector(`.subnav-btn[data-sub="${sub}"]`)?.click();
    if (sub === 'calibrate') {
      await sleep(200);
      const set = (id, v) => { const el = document.querySelector(id); if (el) el.value = v; };
      set('#cal-question', '¿Cuál es la función de la mitocondria?');
      set('#cal-ideal', 'La mitocondria es el orgánulo de la respiración celular donde se produce ATP.');
      set('#cal-concepts', 'respiración celular:0.5\nATP:0.5');
      set('#cal-student', 'La mitocondria produce ATP mediante la respiración celular.');
      CAL_EXAMPLES.length = 0;
      CAL_EXAMPLES.push(
        { answer: 'La mitocondria es el orgánulo de la respiración celular donde se produce ATP.', score: 9 },
        { answer: 'Produce energía en la célula.', score: 6 },
        { answer: 'No lo sé.', score: 2 },
      );
      renderCalExamples();
      await sleep(150);
      document.querySelector('#btn-cal-run')?.click();
      await sleep(2800);
      window.scrollTo(0, 0); // encuadre desde arriba para capturas
    }
  }
}
window.addEventListener('load', () => { runDemoFromHash().catch(() => {}); });
