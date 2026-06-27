# tfg_exam_grader — context for Claude Code

## What this project is

TFG (Bachelor's thesis) project: an automatic grading system for open-ended exam
questions, working from scanned/photographed images.

It is **not** a machine-learning system. It is a hybrid pipeline that combines:

1. OCR (Tesseract via `pytesseract`) on the input image
2. Question/answer parsing
3. Reference-answer generation (currently a controlled mock; a Claude-backed
   cached generator exists in `src/reference_db.py` but is not wired into the
   main pipeline yet)
4. Semantic grading: weighted key-concept detection + **polarity check
   (negation/contradiction)** + global cosine similarity + length penalty +
   minimum-floor rule
5. Final grade and concept-level feedback
6. Optional LLM factuality verifier (`src/ai/verifier.py`, endpoint
   `/api/verify_answer`) as a non-destructive second opinion

The grading logic is in `src/ai/semantic_grader.py`. The data model lives in
`src/ai/models.py` (`ReferenceAnswer`, `RubricItem`).

### Polarity / negation detection (in `semantic_grader.py`)

Before crediting a key concept, the grader checks its **polarity** within the
clause where it appears (`split_clauses` + `concept_polarity`). A concept that
the student NEGATES ("la mitocondria **no** produce ATP") is moved to
`negated_concepts` and does **not** count toward the score. The negator list is
deliberately conservative (`no`, `ni`, `nunca`, `tampoco`, `jamas`, plus
"en lugar de / en vez de / lejos de") to avoid punishing correct answers:
- "no solo … sino" is treated as emphatic, not negation;
- negation in a different clause ("a diferencia del cloroplasto, que no…") does
  not leak onto the concept.

This fixes the worst failure mode (a flat-out wrong answer scoring ~9.8 just for
containing the keywords). It is purely deterministic, so interpretability holds.
What it still cannot catch is **misattribution without local negation**
("la respiración celular es cosa del cloroplasto") — that is the job of the
optional LLM verifier below.

### Per-concept synonyms (paraphrase support)

Each `key_concept` may carry an optional `synonyms` list: paraphrases the teacher
accepts as equivalent to the term (e.g. `{"concept": "LIFO", "weight": 0.4,
"synonyms": ["último en entrar primero en salir", ...]}`). The grader credits the
concept if the term, a synonym (substring), **or all the synonym's content tokens
(stopwords removed) with the 0.80 fuzzy threshold** appear. It is **additive** —a
concept without `synonyms` behaves exactly as before, so `validate.py` (40 cases)
is unaffected— and **respects negation** via `phrase_polarity` (a negated synonym,
"sin ningún dato ni etiqueta", does not credit the concept). Exposed in the API
as `KeyConcept.synonyms`. On the `exam_bank`, synonyms moved the agreement from
ρ=0.872 / MAE 1.44 to **ρ=0.931 / MAE 0.96** (discrepancies 24%→9%).

### Deterministic score calibration (`src/ai/calibration.py`)

`ScoreCalibrator` (method `"linear"` o `"isotonic"`) aprende un mapeo monótono
nota_grader → nota_profesor a partir de pares (cruda, humana). Corrige el desfase
de ESCALA sin alterar el orden (Spearman invariante). Validado en held-out sobre
Mohler: MAE 4,18 → 1,42 en test. Complementa a `/api/calibrate_grade` (LLM
few-shot) con una vía determinista. Caveat: reproduce la leniencia del profesor de
referencia (si sus notas no discriminan, la calibración tampoco).

### Optional factuality verifier (`src/ai/verifier.py`)

`verify_factuality(...)` asks Claude (temperature 0) to classify each key concept
as `correcto | negado | atribucion_erronea | ausente` and whether the answer
contains a contradiction. The endpoint `/api/verify_answer` returns the
deterministic grade **plus** this verification and a `needs_review` flag; it
never silently rewrites the grade. Use it as a second opinion for the cases the
deterministic grader cannot see. Requires `ANTHROPIC_API_KEY`; on failure the
endpoint returns 502 (caller can fall back to deterministic-only).

## Working language and style

- **Code:** English (identifiers, comments, docstrings).
- **Conversation, commit messages, thesis text:** Spanish.
- **Tone for the LaTeX memory:** natural, critical, defensible.
  Avoid grandiloquent or AI-sounding phrasing.

## How to run things

Activa primero el venv (`.venv_mac/bin/python ...` o `source .venv_mac/bin/activate`).

- Validation suite (40 cases, incl. 5 de negación/polaridad):
  `PYTHONPATH=src .venv_mac/bin/python src/validate.py`
- Correlación de Spearman vs nota humana de referencia:
  `PYTHONPATH=src .venv_mac/bin/python experiments/evau2026_spearman.py`
- Banco de exámenes por nivel (Primaria→Máster) con concordancia y discrepancias:
  `PYTHONPATH=src .venv_mac/bin/python experiments/banco_examenes.py`
  (datos en `src/ai/exam_bank.py`; análisis en `experiments/HALLAZGOS_banco.md`)
- Robustez (negación + verificador): `set -a; . ./.env; set +a` y luego
  `PYTHONPATH=src .venv_mac/bin/python experiments/evau2026_robustez.py`
- OCR test on a sample image: `.venv_mac/bin/python src/test_ocr.py`
- Full pipeline test: `.venv_mac/bin/python src/test_full_pipeline.py`
- Semantic grader unit test (vive en `src/ai/`, no en `src/`):
  `PYTHONPATH=src .venv_mac/bin/python src/ai/test_semanticgrader.py`
  o como módulo: `cd src && ../.venv_mac/bin/python -m ai.test_semanticgrader`

Los tests dentro de `src/ai/` y `src/ocr/` usan imports estilo paquete
(`from ai.semantic_grader import ...`), por lo que requieren `PYTHONPATH=src`
o ejecutarse con `-m` desde `src/`. Sin eso fallan con `ModuleNotFoundError`.

Tesseract must be installed locally. On macOS:
`brew install tesseract tesseract-lang`.

## Web demo (para la defensa)

App FastAPI en `src/web/` con frontend estático (HTML/CSS/JS plano).
Chart.js cargado vía CDN; sin frameworks JS.

Levantar localmente (desde la raíz del proyecto):

```
PYTHONPATH=src .venv_mac/bin/uvicorn web.app:app --reload --port 8000
```

Y abrir `http://127.0.0.1:8000`.

### Pestañas

- **Corregir** — sub-modos:
  - *Individual*: selector con los 35 casos pre-calibrados o modo
    personalizado. En custom hay también `+ Términos bonus` (vocabulario
    técnico aditivo, p.ej. Filosofía). Resultado con score animado, comparativa
    ideal vs alumno con resaltado, métricas y botón **"Explicar nota con IA"**
    (llama a Claude para devolver una justificación en lenguaje natural).
  - *Lote*: pega/sube CSV/TXT con N respuestas (separador `---`), todas se
    corrigen contra la misma rúbrica. Histograma de notas, stats agregadas y
    **tabla "Top errores de la clase"** (conceptos que más han faltado) con
    botón para convertir cualquiera en antipatrón.
- **Materias** — catálogo con tarjetas (Bio, Filosofía, Historia, Lengua,
  Inglés, Economía, Mates, Física). Cada pregunta es un preset que vuelca
  rúbrica + bonus_terms al modo Corregir.
- **Procesar imagen** — dos modos:
  - *Imagen simple (Tesseract)*: el OCR clásico para una pregunta + respuesta.
    Botón "Descargar como Word (.docx)".
  - *Examen estructurado (Vision IA)*: para tablas, formularios, exámenes
    complejos (formulación química, fill-in-the-blanks, etc.) donde Tesseract
    no llega. Claude Vision extrae la estructura (filas, columnas, cada celda
    clasificada como `printed`/`student`/`blank`). La tabla se muestra
    editable. El profesor puede generar las respuestas correctas con IA o
    introducirlas a mano. La corrección final se hace celda a celda con el
    grader determinista (normalización + fuzzy match + sinónimos del
    profesor) → **la IA solo se usa para extraer, no para juzgar**.
- **Aula del Profesor** — sub-pestañas:
  - *Asistente IA*: Claude propone `ideal_answer` + `key_concepts` para una
    pregunta. Botones "Usar en Corregir" y "Crear antipatrones con estos errores".
  - *Calibración con ejemplos*: profesor da N ejemplos (respuesta + nota) y la UI
    muestra dos calibraciones en paralelo: (1) **determinista sin IA**
    (`/api/calibrate_deterministic`, `ScoreCalibrator`, ≥2 ejemplos) con el mapeo
    aprendido y una tabla del ajuste; (2) **Claude** few-shot
    (`/api/calibrate_grade`, ≥1 ejemplo, best-effort: degrada si no hay API key).
    Botones para guardar/cargar ejemplos de la BD SQLite (`data/calibration.db`)
    indexados por pregunta.
  - *Sinónimos y antipatrones*: CRUD sobre `data/teacher_config.json`,
    aplicado en runtime a todas las correcciones.
  - *Mates/Física (experimental)*: corrección paso a paso delegada al LLM con
    carry-through. **Fuera del alcance core del TFG**: rompe interpretabilidad
    y se etiqueta como tal en la UI.
- **Validación** — dos tarjetas: (1) reproduce `validate.py` (40 casos) con
  donut/barras Chart.js; (2) **Concordancia con el profesor**: corre
  `/api/correlation` sobre el gold set y muestra Spearman/Pearson/MAE/RMSE, un
  diagrama de dispersión humano-vs-sistema con diagonal de acuerdo perfecto, y
  el Spearman por pregunta.
- **Historial** — localStorage en navegador, persistente entre recargas.

### Endpoints (`/api/docs`)

`GET /api/cases`, `POST /api/grade`, `POST /api/grade_case`,
`POST /api/grade_batch`, `POST /api/ocr`, `POST /api/export_docx`,
`GET /api/validate`, `POST /api/explain_grade`, `POST /api/generate_reference`,
`POST /api/calibrate_grade`, `POST /api/calibrate_deterministic`,
`GET|POST /api/teacher_config`,
`GET|POST|DELETE /api/calibration/examples`, `GET /api/calibration/questions`,
`POST /api/grade_steps` (experimental),
`POST /api/extract_structured`, `POST /api/generate_solutions`,
`POST /api/grade_structured`, `POST /api/grade_numeric`,
`POST /api/grade_writing`, `POST /api/verify_answer`,
`GET /api/correlation`.

### Dependencias externas

- **Tesseract** en PATH para OCR (`brew install tesseract tesseract-lang`).
  Sin él, `/api/ocr` devuelve 503 con instrucciones.
- **`ANTHROPIC_API_KEY`** en `.env` o entorno para los endpoints que llaman a
  Claude: `generate_reference`, `calibrate_grade`, `explain_grade`,
  `grade_steps`. Sin ella, devuelven 502.
- `data/teacher_config.json` y `data/calibration.db` se crean al primer uso.
  Están en `.gitignore` (sensibles).

Para deploy futuro: un Dockerfile mínimo con `apt-get install tesseract-ocr
tesseract-ocr-spa` + el venv basta.

## Known incoherences between code and thesis

These were detected when reviewing `MemoriaTFG.pdf` against the source.

### Resolved

- ✅ **#4 — Synonym expansion** (commit `51568d5`). `expand_with_synonyms`
  is now bidirectional (any group element triggers expansion of all others)
  and the duplicate variant in the `producir` list is deduped.
- ✅ **#5 — Init filenames** (commit `4e335a6`). `src/ai/init.py` and
  `src/ocr/init_.py` renamed to `__init__.py`; package imports now work.

### Pending — code is correct as-is, thesis sections need to be aligned

Planned for the next memory revision session. Do not touch the code for these.

1. **Min-floor / length-penalty order.** Section 4.6.7 of the memory writes
   `Nota = max(min_floor, 0.95·c + 0.05·s) · length_penalty`, but
   `semantic_grader.py` applies length penalty *before* the `max` — i.e.
   `max((0.95·c + 0.05·s) · length_penalty, min_floor)`. The code is the
   intended behavior (the floor protects against any degradation, length
   included). Rewrite 4.6.7 to match.
2. **OCR preprocessing.** Sections 4.2 and 4.3 of the memory describe
   binarization and denoising as essential. The actual `extract_text_from_image`
   in `extractor.py` runs Tesseract on the raw image (`# SIN PREPROCESADO`).
   Decision: keep the code as-is and rewrite the memory to explain that
   preprocessing was tested, degraded results, and was therefore dropped.
3. **Length penalty asymmetry.** The memory says the length factor penalizes
   answers that are too short *or* too long. The code only penalizes short
   answers (no upper bound). Decision: keep the code as-is (a long answer
   that still covers the rubric is not worse than a short one) and correct
   the memory.

## Improvements to consider after the incoherences are fixed

- **Wire `reference_db.py` into the pipeline.** It already calls Claude,
  validates the JSON, and caches to `data/reference_cache.json`. Replace the
  `MockReferenceGenerator` in `test_full_pipeline.py` with a path that uses
  `get_reference(question)`. Keep the mock available for offline tests.
- ✅ **Expanded `validate.py`** to 40 cases across two subjects (Biología,
  Informática) incl. 5 de negación/polaridad, with per-topic and per-subject
  accuracy breakdown. Future: añadir Física o Química para llegar a 3–4
  asignaturas como pedía el plan original.
- ✅ **Negation / polarity detection** (deterministic) — done in
  `semantic_grader.py`. A negated concept no longer counts. See the section
  above. The remaining gap (misattribution without local negation) is covered
  by the optional LLM verifier.
- ✅ **Factuality verifier (anti-patterns, LLM second opinion)** —
  `src/ai/verifier.py` + `/api/verify_answer`. Flags negated/misattributed
  concepts and contradictions without rewriting the grade. A deterministic
  per-concept forbidden-phrase list could still be added as a cheaper,
  offline complement.
- ✅ **Spearman correlation** vs human-graded answers — done.
  Metrics in `src/ai/metrics.py` (Spearman/Pearson/MAE/RMSE, pure Python, no
  scipy). Gold set in `experiments/gold_dataset.py` (30 respuestas con nota
  humana de referencia, claramente etiquetadas como asignadas por el autor, no
  por un tribunal real). Runner: `experiments/evau2026_spearman.py`. Resultado
  actual: rho≈0.87, r≈0.91, MAE≈1.2/10. El siguiente paso (no imprescindible)
  sería repetirlo con correcciones de profesores reales y medir además la
  concordancia inter-profesor.

## Out of scope for this TFG

- Deep learning, fine-tuning, or training any model.
- Heavy NLP libraries beyond what's already in `requirements.txt`.
- Anything that breaks interpretability of the final grade.

## Conventions

- Don't reformat unrelated files when editing.
- Don't change public function signatures of `SemanticGrader` or
  `ReferenceAnswer` without flagging it — they are referenced from multiple
  call sites and from the thesis text.
- After any change to grading logic, run `python src/validate.py` and report
  which cases pass/fail.
- Never commit `.env`, `data/reference_cache.json`, or `__pycache__/`.

## Working mode

- Apply edits directly without asking for confirmation on each change.
- Run shell commands as needed (`git mv`, `python validate.py`, etc.)
  without asking permission first.
- **Before handing control back**, do a final review pass:
  - List every file you modified.
  - Run the relevant tests (`python src/validate.py` or whatever fits the task).
  - Report which tests pass and which fail.
  - Flag anything you changed that you're not 100% sure about.
- If a task can't be finished (e.g. missing dependency, broken venv),
  stop and report — don't improvise workarounds without asking.
- Never push to remote or run `git commit` automatically. Leave commits to me.