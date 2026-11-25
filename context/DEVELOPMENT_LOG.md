# Development Log

Chronological record of all development activity, decisions, and findings.

---

## 2026-10-10 — Project Kickoff & Architecture Evaluation

### What happened
- Evaluated the enterprise RAG technical guide (kept private, not in this repository) for applicability to the Student-Path Modulkatalog project
- **Finding:** ~70% of the enterprise architecture transfers directly. Core pipeline (Docling → BGE-M3 → Qdrant → LangGraph → LLM) is identical. Dropped: MySQL, employee knowledge, permissions, GDPR
- Reviewed existing [test.py](../src/student_path/legacy/regex_parser.py) — custom regex parser for pipe-delimited markdown tables
- **Decision:** Replace test.py approach with Docling-based parsing (ADR-001). test.py is too fragile for 600 pages and assumes pre-extracted markdown

### Artifacts created
- `context/PROJECT.md` — Project overview, scope, goals
- `context/ARCHITECTURE.md` — Adapted architecture, tech stack, ADRs
- `context/DEVELOPMENT_LOG.md` — This file
- `context/ROADMAP.md` — 4-phase implementation plan with checkboxes

### Key decisions
- Docling for PDF parsing (not custom regex)
- BGE-M3 for embeddings (bilingual DE/EN support)
- Qdrant for vector storage with hybrid search
- One module = one chunk strategy
- Cloud LLM API for simplicity (swap to local later)

### Open questions
- ~~Which cloud LLM to use?~~ → **Decided: Google Gemini**
- Streamlit vs React for frontend? (Streamlit recommended for MVP speed)

---

## 2026-10-10 — Phase 1 Implementation: Project Scaffolding & Pipeline Code

### What happened
- Created full project directory structure (`src/`, `data/`, `context/`)
- Built [parser.py](../src/student_path/legacy/parser.py) — Docling-based PDF parser with OCR and table extraction
- Built [normalizer.py](../src/student_path/legacy/normalizer.py) — transforms Docling output into structured per-module JSON with typed metadata
- Created [test_questions.json](../data/test_questions.json) — 15 test questions across all 4 intent types
- Set up `requirements.txt` (replaced by pyproject.toml in P0.2) and [.env.example](../.env.example)
- **LLM decision:** Google Gemini (user preference)

### Artifacts created
- `src/ingestion/parser.py` — Docling PDF parser (Task 1.1-1.2)
- `src/ingestion/normalizer.py` — Module normalizer with field mapping, type parsing, embedding text builder (Task 1.3)
- `data/test_questions.json` — 15 evaluation questions (Task 1.6)
- `requirements.txt` — All project dependencies
- `.env.example` — Environment variable template

### Key decisions
- Google Gemini as LLM API
- Normalizer supports both Markdown and Docling JSON input formats (flexibility)
- Embedding text is a concatenation of all meaningful fields (name, content, outcomes, etc.)
- Unmapped fields are preserved with `_raw_` prefix for debugging

### Blockers
- ⚠️ Terminal command execution blocked by Windows ACL permission issue — user must run commands manually

### Next steps (manual)
1. Create and activate Python venv
2. Install dependencies: `pip install -r requirements.txt`
3. Run parser: `python src/ingestion/parser.py --inspect`
4. Run normalizer: `python src/ingestion/normalizer.py --inspect`
5. Inspect output quality before proceeding to Phase 2

---

## 2026-11-25 — Data audit, approach evaluation & v2 plan

### What happened
- Profiled the PDF, the Docling output and `data/modules.json` before planning further.
- PDF: 603 pages, all with a text layer, so OCR is unnecessary. There are 204 bookmarks. All 188 numbered modules start exactly on their bookmarked page, so modules can be segmented by bookmark page ranges.
- True module count: 201, each with a unique PN.
- `module_id` is not unique: `5851` and `5853` each name two different modules, and 13 modules have no 4-digit ID. The primary key must be the PN.
- Current `modules.json`: 271 records. Real modules have about 48% of each field filled, and ECTS is present and correct for 32.8%. Some records merge several modules.
- Root causes: TOC rows match the new-module regex, headers that merge ID and title are missed, tables split at page breaks, and Docling repeats spanned columns.
- Spike (bookmark segmentation + 17 label anchors on the existing Docling JSON): fields found rose from 47% to 99% on average (98–100% per field).
- Remaining dirt: 50 `content` values with page-break fragments, 2,124 hyphenation artifacts, DE/EN interleaved in values.
- Compared 6 architectures in a weighted matrix (design judgments) and chose structured-first agentic hybrid RAG (score 90 vs. 51–63 for the others).

### Artifacts created/modified
- `context/IMPLEMENTATION_PLAN.md`: v2 plan with evidence, question taxonomy, approach evaluation, architecture, data model, phases P0–P8 with gates, eval strategy, AI workflow and risks.
- `context/blueprint.html`: visual companion (architecture, evidence chart, scores, roadmap, mindmap), published at https://claude.ai/artifact/8uqJCGV3eCWAnEfdXHssPk (private until shared).

### Key decisions (proposed, pending acceptance)
- ADR-005 bookmark segmentation · ADR-006 PN as primary key · ADR-007 OCR off and DoclingDocument JSON · ADR-008 deterministic first, LLM second, validate always · ADR-009 DuckDB as system of record · ADR-010 multi-view indexing (revises ADR-002) · ADR-011 router with typed read-only tools · ADR-012 CP-SAT planner with hand-encoded rules · ADR-013 evaluation-driven development with baselines B0 (naive RAG) and B1 (long context).
- Gemini stays the LLM.

### Open questions
- Chainlit or Streamlit for the UI?
- Langfuse Cloud free tier or self-hosted?
- Once accepted, fold ADR-005 to ADR-013 into ARCHITECTURE.md and the phases into ROADMAP.md.

### Next steps
- Week-1 kickoff checklist in IMPLEMENTATION_PLAN.md §7: git init, uv, CLAUDE.md, re-run Docling with OCR off, segment.py + tests, fields.py, clean.py.

---

## 2026-11-25 — P0.2: uv environment

### What happened
- Replaced `requirements.txt` with `pyproject.toml` + `uv.lock` (uv 0.11.21, Python 3.11).
- Dependency groups as in the plan: `ingest`, `ml`, `serve`, `eval`, `dev`. All five are default groups, so plain `uv sync` installs everything. The UI group is added in P6, once Chainlit vs. Streamlit is decided.
- Torch comes from the PyTorch CPU index (2.15.0+cpu).
- Added a `src/student_path/` package stub (uv_build backend). The existing `src/ingestion/` moves into it in P0.3.
- Synced the existing `.venv`. Mostly minor upgrades (e.g. docling 2.137 → 2.153, transformers 5.19 → 5.24). New: duckdb, rapidfuzz, ortools, langfuse, langgraph-checkpoint-sqlite, ruff, pyright, pytest, hypothesis, pre-commit.
- Smoke test passed: all key imports work, PDF bookmarks read (204), Qdrant hybrid collection created, Gemini structured-output API present, CP-SAT solves.

### Key decisions
- `google-genai` capped `<3`: the lock would have jumped 2.29 → 3.6 (a major version). Upgrade deliberately and re-check the P1.8 normalization code.

### Next steps
- P0.3: move `src/ingestion/` into `src/student_path/`, add the Typer CLI (`sp`) and config/settings.

---

## 2026-11-25 — P0.3: package layout, CLI, settings and legacy cleanup

### What happened
- Created the `student_path` package and removed `src/__init__.py`. Removed the `sys.path` hacks and argparse blocks from the v1 parser and normalizer; their parsing logic is unchanged.
- **Isolated everything from the v1 approach so nobody builds on it by mistake:** v1 parser, v1 normalizer and the old regex parser (`test.py`) now live in `src/student_path/legacy/` (git history kept), reachable only via `sp legacy parse|normalize`. Their outputs (`modules.json`, the OCR Docling JSON and Markdown) moved to `data/legacy/` (gitignored, nothing deleted). `data/modules.json` is **not** a usable dataset (about 47% of fields, merged/duplicate records); it is only the E1 baseline. `student_path.ingestion` is reserved for the v2 pipeline (P1).
- Rewrote `ROADMAP.md` (v2 phases with checkboxes) and `ARCHITECTURE.md` (v2 diagram, ADR-005 to ADR-014; ADR-002/003/004 marked superseded), so `context/` describes one approach only.
- Moved the PDF to `data/source/Modulkatalog-Master-Informatik.pdf`.
- New `src/student_path/settings.py`: pydantic-settings reading `.env`. Relative paths resolve against the project root; the API key is a `SecretStr`. `.env.example` now matches (Gemini model ids, `QDRANT_PATH` / `QDRANT_URL`, Langfuse placeholders).
- New `sp` CLI (Typer): `sp --version`, `sp config` (never prints secrets), `sp legacy parse|normalize`. Docling is imported lazily, so `--help` stays fast.
- Fixed finding F6(f): `--pages` is now passed to Docling (1-based, inclusive). Verified with pages 49–51, about 32 s.
- Regression check only (not an endorsement of the output): after the move, `sp legacy normalize` reproduces the previous `modules.json` byte for byte, so the E1 baseline is stable.
- `tests/test_cli.py`: 11 tests (version, secret masking, path resolution, page-range parsing), all passing. Ruff line length set to 110.

### Key decisions
- Settings live in the package (`src/student_path/settings.py`), not in `config/`, because code must be importable. `config/` will hold data files (degree rules, prompts).
- No empty stub modules for future phases; each subpackage is added when its phase starts.
- Legacy code stays out of `student_path.ingestion` and is excluded from linting/type checks; it is deleted once P1 has replaced it and E1 is recorded.

### Next steps
- P0.5: pre-commit (ruff), pyright. P0.6: docker-compose for Qdrant. P0.7: CLAUDE.md.

---

## 2026-11-25 — P0.5: pre-commit, ruff rules, pyright

### What happened
- `.pre-commit-config.yaml`: file hygiene hooks (pre-commit-hooks v6.0.0: whitespace, end of file, YAML/TOML, merge conflicts, private keys, files >1 MB) plus local hooks that run `ruff check --fix`, `ruff format` and `pyright` through uv, so they use the versions pinned in `uv.lock`. Installed as a git hook.
- Ruff lint rules: E, F, I, UP, B, SIM. Pyright in `standard` mode over `src` and `tests`.
- First full run: 0 ruff findings, 0 pyright errors in the new code, 11 tests passing. The hooks only stripped trailing spaces from the log's entry template.

### Key decisions
- Legacy code is excluded everywhere (ruff `force-exclude`, pre-commit global `exclude`, pyright `exclude`). Pre-commit passes file names explicitly, which bypasses ruff's `extend-exclude`, so the first run rewrote the legacy files. They were reverted and `force-exclude` was added, so the E1 baseline stays byte-for-byte unchanged.

### Next steps
- P0.6: `docker-compose.yml` for Qdrant. P0.7: `CLAUDE.md`. Then Phase 1.

---

## 2026-11-25 — P0.6 and P0.7: Qdrant server option, CLAUDE.md (Phase 0 done)

### What happened
- `docker-compose.yml`: Qdrant `v1.20.2` (pinned; matches qdrant-client 1.20), ports 6333/6334, named volume `qdrant_storage`, healthcheck, telemetry off. Verified: container healthy, server reports 1.20.2, `sp check` passes against it. Container stopped again afterwards (volume kept); embedded mode stays the default.
- `student_path/store/qdrant.py`: `get_qdrant_client()` is the single place that picks server mode (`QDRANT_URL` set) or embedded mode (`QDRANT_PATH`).
- `sp check`: environment readiness report. Source PDF and Qdrant are required (exit code 1 on failure); the Gemini key and model ids are warnings until P1.8.
- `CLAUDE.md`: what to read first, commands, layout, conventions (PN as key, structured LLM output, prompts as files), a "never" list (legacy code, `modules.json` as ground truth, private material, golden test split), and the per-step workflow.
- Tests: 14 passing (3 new for the Qdrant factory and `sp check`); ruff and pyright clean.
- A real API key was briefly typed into `.env.example` (tracked, public repo). It was never staged or committed: it was moved to `.env` (gitignored), and a `no-secrets-in-env-example` pre-commit hook now blocks values for `*KEY`, `*SECRET`, `*TOKEN` and `*PASSWORD` variables in `.env.example`.
- qdrant-client's "Failed to obtain server version" warning (from the deliberate unreachable-server test) leaked outside the test in full-suite runs, so it is filtered in the pytest config for that exact message only.

### Key decisions
- Server data lives in a Docker volume, separate from `data/qdrant/` (embedded files use a different on-disk format).

### Open questions
- Gemini model ids to pin in `.env` before P1.8 (check the current model list).

### Next steps
- Phase 1: P1.1 probe/manifest, P1.2 Docling re-run with OCR off, P1.3 bookmark segmentation with tests.

---

<!--
Template for new entries:

## YYYY-MM-DD — Title

### What happened
-

### Artifacts created/modified
-

### Key decisions
-

### Open questions
-

### Blockers
-

-->
