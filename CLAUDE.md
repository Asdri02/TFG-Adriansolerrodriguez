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
4. Semantic grading: weighted key-concept detection + global cosine similarity
   + length penalty + minimum-floor rule
5. Final grade and concept-level feedback

The grading logic is in `src/ai/semantic_grader.py`. The data model lives in
`src/ai/models.py` (`ReferenceAnswer`, `RubricItem`).

## Working language and style

- **Code:** English (identifiers, comments, docstrings).
- **Conversation, commit messages, thesis text:** Spanish.
- **Tone for the LaTeX memory:** natural, critical, defensible.
  Avoid grandiloquent or AI-sounding phrasing.

## How to run things

Activa primero el venv (`.venv_mac/bin/python ...` o `source .venv_mac/bin/activate`).

- Validation suite (10 cases): `.venv_mac/bin/python src/validate.py`
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
- **Expand `validate.py`** from 10 cases to 30–50 spread across 3–4 subjects.
  Report per-category accuracy.
- **Conceptual-error detection (anti-patterns).** Add a small per-concept
  list of forbidden phrasings (e.g. concept "mitocondria" + phrase
  "es el núcleo" → strong penalty). Justify as a natural extension of the
  concept-based approach.
- **Spearman correlation** between system grades and a small set of
  human-graded answers, as a more meaningful validation metric than the
  current pass/fail bands.

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