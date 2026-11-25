# Development Log

Chronological record of all development activity, decisions, and findings.

---

## 2026-10-10 — Project Kickoff & Architecture Evaluation

### What happened
- Evaluated the enterprise RAG technical guide (kept private, not in this repository) for applicability to the Student-Path Modulkatalog project
- **Finding:** ~70% of the enterprise architecture transfers directly. Core pipeline (Docling → BGE-M3 → Qdrant → LangGraph → LLM) is identical. Dropped: MySQL, employee knowledge, permissions, GDPR
- Reviewed existing [test.py](../test.py) — custom regex parser for pipe-delimited markdown tables
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
- Built [parser.py](../src/ingestion/parser.py) — Docling-based PDF parser with OCR and table extraction
- Built [normalizer.py](../src/ingestion/normalizer.py) — transforms Docling output into structured per-module JSON with typed metadata
- Created [test_questions.json](../data/test_questions.json) — 15 test questions across all 4 intent types
- Set up [requirements.txt](../requirements.txt) and [.env.example](../.env.example)
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
