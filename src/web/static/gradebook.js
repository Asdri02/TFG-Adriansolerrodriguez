/* Cuaderno del Profesor — SPA mínima en vanilla JS.
   Flujo: clase → alumnos / exámenes → corregir toda la clase de una vez. */

const $ = (sel, root = document) => root.querySelector(sel);
const el = (tag, attrs = {}, html = "") => {
  const n = document.createElement(tag);
  Object.entries(attrs).forEach(([k, v]) => {
    if (k === "class") n.className = v;
    else if (k === "html") n.innerHTML = v;
    else n.setAttribute(k, v);
  });
  if (html) n.innerHTML = html;
  return n;
};
const esc = (s) => (s ?? "").toString().replace(/[&<>"]/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

async function api(method, url, body) {
  const opts = { method, headers: { "Content-Type": "application/json" } };
  if (body !== undefined) opts.body = JSON.stringify(body);
  const r = await fetch(url, opts);
  if (!r.ok) {
    let detail = r.statusText;
    try { detail = (await r.json()).detail || detail; } catch {}
    throw new Error(detail);
  }
  return r.status === 204 ? null : r.json();
}

const state = { classes: [], currentClass: null, view: "students", currentExam: null };

// ── Clases ────────────────────────────────────────────────────────────────
async function loadClasses() {
  state.classes = await api("GET", "/api/gradebook/classes");
  const box = $("#gb-classes");
  box.innerHTML = "";
  if (!state.classes.length) box.append(el("p", { class: "muted" }, "Aún no hay clases."));
  state.classes.forEach((c) => {
    const node = el("div", { class: "gb-class" + (state.currentClass?.id === c.id ? " active" : "") });
    node.innerHTML = `<div class="gb-class-name">${esc(c.name)}</div>
      <div class="gb-class-meta">${esc(c.subject || "—")} · ${c.students_count} alumnos · ${c.exams_count} exámenes</div>`;
    node.onclick = () => selectClass(c);
    box.append(node);
  });
}

$("#gb-create-class").onclick = async () => {
  const name = $("#gb-new-class-name").value.trim();
  if (!name) return alert("Pon un nombre a la clase.");
  try {
    const c = await api("POST", "/api/gradebook/classes", {
      name, subject: $("#gb-new-class-subject").value, academic_year: $("#gb-new-class-year").value,
    });
    $("#gb-new-class-name").value = $("#gb-new-class-subject").value = $("#gb-new-class-year").value = "";
    await loadClasses();
    selectClass(c);
  } catch (e) { alert(e.message); }
};

async function selectClass(c) {
  state.currentClass = c; state.view = "students"; state.currentExam = null;
  await loadClasses();
  renderMain();
}

// ── Panel principal ───────────────────────────────────────────────────────
function renderMain() {
  const main = $("#gb-main");
  main.innerHTML = "";
  const c = state.currentClass;
  if (!c) { main.append(el("div", { class: "gb-empty card" }, "Selecciona o crea una clase.")); return; }

  const head = el("div", {}, `<h2 style="margin:0 0 2px;">${esc(c.name)}</h2>
     <p class="muted" style="margin:0 0 12px;">${esc(c.subject || "—")} · ${esc(c.academic_year || "")}</p>`);
  const nav = el("div", { class: "gb-subnav" });
  ["students:Alumnos", "exams:Exámenes"].forEach((s) => {
    const [v, label] = s.split(":");
    const b = el("button", { class: "subnav-btn" + (state.view === v ? " active" : "") }, label);
    b.onclick = () => { state.view = v; state.currentExam = null; renderMain(); };
    nav.append(b);
  });
  const del = el("button", { class: "ghost", style: "margin-left:auto;font-size:13px;" }, "Eliminar clase");
  del.onclick = async () => {
    if (!confirm(`¿Eliminar la clase "${c.name}" con sus alumnos, exámenes y notas?`)) return;
    await api("DELETE", `/api/gradebook/classes/${c.id}`);
    state.currentClass = null; await loadClasses(); renderMain();
  };
  const navWrap = el("div", { style: "display:flex;align-items:center;" });
  navWrap.append(nav, del);
  main.append(head, navWrap);

  const panel = el("div");
  main.append(panel);
  if (state.view === "students") renderStudents(panel);
  else if (state.currentExam) renderGrading(panel);
  else renderExams(panel);
}

// ── Alumnos ───────────────────────────────────────────────────────────────
async function renderStudents(panel) {
  const c = state.currentClass;
  const students = await api("GET", `/api/gradebook/classes/${c.id}/students`);
  const card = el("div", { class: "card" });
  card.append(el("h3", { style: "margin-top:0;" }, `Alumnos (${students.length})`));

  if (!students.length) card.append(el("p", { class: "gb-empty" }, "Sin alumnos. Pégalos abajo (uno por línea)."));
  else {
    const list = el("div");
    students.forEach((s) => {
      const row = el("div", { style: "display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid var(--border);" });
      row.innerHTML = `<span>${esc(s.name)}</span>`;
      const x = el("button", { class: "gb-x", title: "Quitar alumno" }, "✕");
      x.onclick = async () => { await api("DELETE", `/api/gradebook/students/${s.id}`); renderMain(); };
      row.append(x); list.append(row);
    });
    card.append(list);
  }

  const ta = el("textarea", { placeholder: "Ana García\nLuis Pérez\nMaría López", style: "width:100%;min-height:90px;margin-top:12px;" });
  const add = el("button", { class: "primary", style: "margin-top:8px;" }, "Añadir alumnos");
  add.onclick = async () => {
    const names = ta.value.split("\n").map((n) => n.trim()).filter(Boolean);
    if (!names.length) return;
    await api("POST", `/api/gradebook/classes/${c.id}/students/bulk`, { names });
    ta.value = ""; await loadClasses(); renderMain();
  };
  card.append(el("label", { class: "muted", style: "display:block;margin-top:12px;font-size:13px;" }, "Pegar listado (uno por línea)"), ta, add);
  panel.append(card);
}

// ── Exámenes ──────────────────────────────────────────────────────────────
async function renderExams(panel) {
  const c = state.currentClass;
  const exams = await api("GET", `/api/gradebook/classes/${c.id}/exams`);

  const list = el("div", { class: "card" });
  list.append(el("h3", { style: "margin-top:0;" }, `Exámenes (${exams.length})`));
  if (!exams.length) list.append(el("p", { class: "gb-empty" }, "Sin exámenes todavía."));
  const MODE_LABEL = { conceptual: "Conceptos", numeric: "Resultado (Mates/Física)", writing: "Redacción (Inglés/Lengua)" };
  exams.forEach((e) => {
    const mode = e.rubric?.grading_mode || "conceptual";
    const row = el("div", { style: "display:flex;justify-content:space-between;align-items:center;padding:10px 0;border-bottom:1px solid var(--border);" });
    row.innerHTML = `<div><strong>${esc(e.title)}</strong>
      <span class="gb-pill" style="background:var(--primary-soft);color:var(--primary);margin-left:6px;">${MODE_LABEL[mode] || mode}</span>
      <div class="gb-class-meta">${esc(e.exam_date || "sin fecha")} · ${esc(e.subject || "")}
      · ${e.graded_count} corregidos${e.mean_score != null ? " · media " + e.mean_score : ""}</div></div>`;
    const open = el("button", { class: "primary", style: "font-size:13px;" }, "Corregir / ver");
    open.onclick = () => { state.currentExam = e; renderMain(); };
    const x = el("button", { class: "gb-x", title: "Eliminar examen" }, "✕");
    x.onclick = async () => {
      if (!confirm(`¿Eliminar el examen "${e.title}" y sus notas?`)) return;
      await api("DELETE", `/api/gradebook/exams/${e.id}`); renderMain();
    };
    const actions = el("div", { style: "display:flex;gap:6px;align-items:center;" });
    actions.append(open, x); row.append(actions); list.append(row);
  });
  panel.append(list);

  // Formulario de nuevo examen + rúbrica (con modo de corrección)
  const form = el("div", { class: "card", style: "margin-top:16px;" });
  form.innerHTML = `<h3 style="margin-top:0;">Nuevo examen</h3>
    <div class="gb-row">
      <div class="field"><label>Título</label><input id="ex-title" placeholder="Examen Tema 3"></div>
      <div class="field"><label>Fecha</label><input id="ex-date" type="date"></div>
      <div class="field"><label>Asignatura</label><input id="ex-subject" value="${esc(c.subject || "")}"></div>
    </div>
    <div class="field"><label>Tipo de corrección</label>
      <select id="ex-mode">
        <option value="conceptual">Conceptos (Bio, Historia, Filosofía, Química, Economía…)</option>
        <option value="numeric">Resultado numérico (Matemáticas / Física)</option>
        <option value="writing">Redacción con rúbrica IA (Inglés / Lengua)</option>
      </select>
    </div>
    <div class="field"><label>Pregunta / enunciado</label><input id="ex-question" placeholder="¿Qué es la mitocondria?"></div>

    <div id="ex-fields-conceptual">
      <div class="field"><label>Respuesta ideal</label><textarea id="ex-ideal" style="min-height:60px;" placeholder="Respuesta modelo completa..."></textarea></div>
      <div class="field"><label>Conceptos clave y peso (uno por línea: <code>concepto : peso</code>)</label>
        <textarea id="ex-concepts" style="min-height:90px;" placeholder="orgánulo : 0.2&#10;energía : 0.3&#10;ATP : 0.3&#10;respiración celular : 0.2"></textarea></div>
    </div>

    <div id="ex-fields-numeric" class="gb-hidden">
      <div class="gb-row">
        <div class="field"><label>Resultado esperado</label><input id="ex-expected" placeholder="x = -3  ·  9.8 m/s^2"></div>
        <div class="field"><label>Tipo</label><select id="ex-kind"><option value="math">Matemáticas</option><option value="physics">Física (valor + unidad)</option></select></div>
      </div>
      <p class="muted" style="font-size:13px;">Se compara el resultado final del alumno por equivalencia (interpretable, sin IA).</p>
    </div>

    <div id="ex-fields-writing" class="gb-hidden">
      <div class="field"><label>Rúbrica IA</label>
        <select id="ex-writing-subject"><option value="lengua">Lengua (tema, estructura, argumentación, expresión)</option><option value="ingles">Inglés (task, grammar, vocabulary, coherence)</option></select></div>
      <p class="muted" style="font-size:13px;">⚠ Corrige un LLM (no interpretable) y requiere ANTHROPIC_API_KEY. Una llamada por alumno.</p>
    </div>

    <button class="primary" id="ex-create">Crear examen</button>`;
  panel.append(form);

  const toggleFields = () => {
    const m = $("#ex-mode").value;
    $("#ex-fields-conceptual").className = m === "conceptual" ? "" : "gb-hidden";
    $("#ex-fields-numeric").className = m === "numeric" ? "" : "gb-hidden";
    $("#ex-fields-writing").className = m === "writing" ? "" : "gb-hidden";
  };
  $("#ex-mode").onchange = toggleFields;

  $("#ex-create").onclick = async () => {
    const title = $("#ex-title").value.trim();
    const question = $("#ex-question").value.trim();
    const subject = $("#ex-subject").value;
    const mode = $("#ex-mode").value;
    if (!title) return alert("Pon un título.");
    if (!question) return alert("Pon la pregunta o enunciado.");

    let rubric;
    if (mode === "conceptual") {
      const concepts = $("#ex-concepts").value.split("\n").map((l) => l.trim()).filter(Boolean).map((l) => {
        const i = l.lastIndexOf(":");
        const concept = (i >= 0 ? l.slice(0, i) : l).trim();
        const weight = i >= 0 ? parseFloat(l.slice(i + 1)) : 1;
        return { concept, weight: isNaN(weight) ? 1 : weight };
      }).filter((k) => k.concept);
      if (!concepts.length) return alert("Añade al menos un concepto clave.");
      rubric = { question, subject, ideal_answer: $("#ex-ideal").value, key_concepts: concepts };
    } else if (mode === "numeric") {
      const expected = $("#ex-expected").value.trim();
      if (!expected) return alert("Indica el resultado esperado.");
      rubric = { question, expected, kind: $("#ex-kind").value };
    } else {
      rubric = { question, subject: $("#ex-writing-subject").value };
    }

    try {
      await api("POST", `/api/gradebook/classes/${c.id}/exams`, {
        title, exam_date: $("#ex-date").value, subject, grading_mode: mode, rubric,
      });
      await loadClasses(); renderMain();
    } catch (e) { alert(e.message); }
  };
}

// ── Corregir toda la clase ────────────────────────────────────────────────
let gbChart = null;
async function renderGrading(panel) {
  const exam = state.currentExam;
  const data = await api("GET", `/api/gradebook/exams/${exam.id}/grades`);

  const back = el("button", { class: "ghost", style: "font-size:13px;margin-bottom:10px;" }, "← Volver a exámenes");
  back.onclick = () => { state.currentExam = null; renderMain(); };
  panel.append(back);

  const info = el("div", { class: "card" });
  info.innerHTML = `<h3 style="margin-top:0;">${esc(exam.title)}</h3>
    <p class="muted" style="margin:0 0 4px;">${esc(exam.exam_date || "sin fecha")} · ${esc(exam.subject || "")}</p>
    <p style="margin:0;"><strong>Pregunta:</strong> ${esc(exam.rubric?.question || "")}</p>`;
  panel.append(info);

  // Tabla: una fila por alumno con su respuesta y su nota
  const card = el("div", { class: "card", style: "margin-top:16px;" });
  card.append(el("h3", { style: "margin-top:0;" }, "Respuestas de la clase"));

  const bulkHelp = el("details", { style: "margin-bottom:10px;" });
  bulkHelp.innerHTML = `<summary class="muted" style="cursor:pointer;">Pegar todas las respuestas en bloque (separadas por una línea con <code>---</code>)</summary>`;
  const bulkTa = el("textarea", { style: "width:100%;min-height:90px;margin-top:8px;", placeholder: "Respuesta de Ana...\n---\nRespuesta de Luis...\n---\nRespuesta de María..." });
  const bulkBtn = el("button", { class: "ghost", style: "margin-top:6px;font-size:13px;" }, "Repartir por orden de lista");
  bulkHelp.append(bulkTa, bulkBtn);
  card.append(bulkHelp);

  const table = el("table", { class: "gb-grade-table" });
  table.innerHTML = `<thead><tr><th style="width:22%;">Alumno</th><th>Respuesta</th><th style="width:70px;">Nota</th></tr></thead>`;
  const tbody = el("tbody");
  const rowRefs = [];
  data.grades.forEach((g) => {
    const tr = el("tr");
    const ta = el("textarea", { "data-sid": g.student_id }, "");
    ta.value = g.answer || "";
    const scoreCell = el("td", { class: "gb-score" + (g.graded ? (g.score >= 5 ? " pass" : " fail") : "") },
      g.graded ? g.score.toFixed(2) : "—");
    const nameTd = el("td", {}, `<strong>${esc(g.student_name)}</strong>`);
    const ansTd = el("td"); ansTd.append(ta);
    tr.append(nameTd, ansTd, scoreCell);
    tbody.append(tr);
    rowRefs.push({ sid: g.student_id, ta, scoreCell });
  });
  table.append(tbody);
  card.append(table);

  bulkBtn.onclick = () => {
    const parts = bulkTa.value.split(/^\s*---\s*$/m).map((s) => s.trim());
    rowRefs.forEach((r, i) => { if (parts[i] !== undefined) r.ta.value = parts[i]; });
  };

  const toolbar = el("div", { class: "gb-toolbar" });
  const gradeBtn = el("button", { class: "primary" }, "Corregir y guardar toda la clase");
  const statusSpan = el("span", { class: "muted" }, "");
  toolbar.append(gradeBtn, statusSpan);
  card.append(toolbar);
  panel.append(card);

  // Estadísticas + histograma
  const statsCard = el("div", { class: "card", style: "margin-top:16px;" });
  statsCard.id = "gb-stats";
  panel.append(statsCard);
  renderStats(data.stats);

  gradeBtn.onclick = async () => {
    const answers = rowRefs.map((r) => ({ student_id: r.sid, text: r.ta.value.trim() }))
      .filter((a) => a.text);
    if (!answers.length) return alert("No hay ninguna respuesta para corregir.");
    gradeBtn.disabled = true; statusSpan.textContent = "Corrigiendo…";
    try {
      const res = await api("POST", `/api/gradebook/exams/${exam.id}/grade_class`, { answers });
      const byId = Object.fromEntries(res.grades.filter((g) => g.graded).map((g) => [g.student_id, g.score]));
      rowRefs.forEach((r) => {
        if (byId[r.sid] != null) {
          r.scoreCell.textContent = byId[r.sid].toFixed(2);
          r.scoreCell.className = "gb-score " + (byId[r.sid] >= 5 ? "pass" : "fail");
        }
      });
      renderStats(res.stats);
      statusSpan.textContent = `✓ ${res.graded_count} corregidos y guardados`;
      loadClasses();
    } catch (e) { alert(e.message); statusSpan.textContent = ""; }
    finally { gradeBtn.disabled = false; }
  };
}

function renderStats(s) {
  const card = $("#gb-stats");
  if (!card) return;
  if (!s.count) { card.innerHTML = `<p class="gb-empty">Aún sin notas. Pega las respuestas y pulsa corregir.</p>`; return; }
  card.innerHTML = `<h3 style="margin-top:0;">Resultados de la clase</h3>
    <div class="stats">
      <div class="stat"><span class="stat-num">${s.mean}</span><span class="stat-label">Media</span></div>
      <div class="stat"><span class="stat-num">${s.median}</span><span class="stat-label">Mediana</span></div>
      <div class="stat"><span class="stat-num">${s.pass_count}</span><span class="stat-label">Aprobados</span></div>
      <div class="stat"><span class="stat-num">${s.fail_count}</span><span class="stat-label">Suspensos</span></div>
      <div class="stat"><span class="stat-num">${s.min}–${s.max}</span><span class="stat-label">Rango</span></div>
      <div class="stat"><span class="stat-num">${s.pending}</span><span class="stat-label">Pendientes</span></div>
    </div>
    <canvas id="gb-histo" height="120" style="margin-top:16px;"></canvas>`;
  const ctx = $("#gb-histo");
  if (gbChart) gbChart.destroy();
  if (window.Chart && ctx) {
    gbChart = new Chart(ctx, {
      type: "bar",
      data: { labels: s.histogram.labels, datasets: [{ label: "Alumnos", data: s.histogram.values,
        backgroundColor: "#2563eb" }] },
      options: { plugins: { legend: { display: false } }, scales: { y: { ticks: { precision: 0 } } } },
    });
  }
}

loadClasses();
