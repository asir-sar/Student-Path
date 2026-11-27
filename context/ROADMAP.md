# Roadmap (v2)

Progress tracker for the v2 plan. Details, code skeletons and the reasoning behind every gate are in [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) §7; decisions are in [ARCHITECTURE.md](ARCHITECTURE.md). Check off tasks as they are completed, and log results in [DEVELOPMENT_LOG.md](DEVELOPMENT_LOG.md).

> The v1 roadmap (one chunk per module, `module_id` as key, regex normalizer) was replaced on 2026-11-25 after the data audit. Its code lives in `src/student_path/legacy/` and serves only as a comparison baseline.

---

## Phase 0: Foundations ✅ DONE (2026-11-25)

> **Goal:** a professional skeleton, so every later step is fast to run, test and undo.

- [x] **P0.1** git, `.gitignore`, public GitHub repo
- [x] **P0.2** uv: `pyproject.toml`, `uv.lock`, dependency groups, CPU-only torch
- [x] **P0.3** package layout `src/student_path/`, `sp` CLI, v1 code isolated in `legacy/`, PDF in `data/source/`
- [x] **P0.4** typed settings (`student_path/settings.py`) and matching `.env.example`
- [x] **P0.5** pre-commit (ruff lint + format), pyright, pytest wired in
- [x] **P0.6** `docker-compose.yml` with Qdrant (pinned tag); embedded mode stays the default for development
- [x] **P0.7** `CLAUDE.md`: commands, layout, conventions, "never" list

**Gate:** `uv run pytest` passes · `uv run sp --help` works · CI-ready checks run locally

---

## Phase 1: Data foundation v2 🟡 IN PROGRESS

> **Goal:** 201 validated, typed module records and a QA report you trust.

- [x] **P1.1** Probe: manifest with SHA-256, page count, text-layer check, bookmark count (`sp ingest probe`)
- [x] **P1.2** Re-run Docling once: OCR off, TableFormer `ACCURATE`, cell matching; cache `data/interim/docling.json`; text coverage ≥99.5% overall, no page <80% (`sp ingest coverage`)
- [x] **P1.3** Segment modules by PDF bookmarks (201 page ranges, PN as key) + tests (`sp ingest segment`)
- [ ] **P1.4** Field assembly with the 17 label anchors (field carried across tables and pages)
- [ ] **P1.5** Clean: NFKC, corpus-aware de-hyphenation (2,124 artifacts → fewer than 20)
- [ ] **P1.6** Page-break bleed repair (heuristic first, LLM returns offsets only)
- [ ] **P1.7** Rule-based typing (ECTS, SWS, workload, offering, languages, groups, people)
- [ ] **P1.8** Gemini normalization with schema + grounding check, cached
- [ ] **P1.9** Entity linking of prerequisites → PN; prerequisite graph
- [ ] **P1.10** Reconcile with the overview tables (pp. 5–16)
- [ ] **P1.11** Data-contract tests (201 records, unique PN, ECTS = overview, no artifacts)
- [ ] **P1.12** QA report, read 30 modules against the PDF, hand-label 20 gold modules

**Gate:** 201/201 records · unique PN · ≥99% core-field fill · ECTS equals the overview tables · field accuracy ≥95% on the gold set

---

## Phase 2: Evaluation harness and baselines ⬜

- [ ] **P2.1** Golden-set format (`eval/datasets/golden.jsonl`)
- [ ] **P2.2** ~80 programmatic questions from DuckDB (exact answers), paraphrased, about half in German
- [ ] **P2.3** ~70 hand-written: regulations, discovery (graded), planning, out-of-scope; migrate `data/test_questions.json` to PN keys
- [ ] **P2.4** Freeze dev/test split (70/30)
- [ ] **P2.5** Metrics module (EM, set F1, Recall@k, MRR, nDCG, faithfulness, citations, abstention, latency, cost)
- [ ] **P2.6** Calibrate the LLM judge against 30 own labels (≥85% agreement)
- [ ] **P2.7** Baselines B0 (naive RAG) and B1 (long-context Gemini); `sp eval`

**Gate:** per-type scorecards for B0 and B1 recorded in the development log

---

## Phase 3: Retrieval layer ⬜

- [ ] **P3.1** DuckDB store + parametrized `filter_modules`
- [ ] **P3.2** Entity resolver (PN, IDs incl. 5851/5853 ambiguity, DE/EN titles, typos)
- [ ] **P3.3** Views (`card`, `content_en/de`, `outcomes_en/de`) + BGE-M3 dense and sparse, cached
- [ ] **P3.4** Qdrant collection, payload indexes, versioned collection + alias
- [ ] **P3.5** Hybrid query (prefetch + RRF + group by PN)
- [ ] **P3.6** Reranker with CPU latency budget
- [ ] **P3.7** Regulations index (HybridChunker)
- [ ] **P3.8** Filter extraction (self-query) with validated enums
- [ ] **P3.9** Experiments E2, E3, E6

**Gate:** resolver ≥0.97 · list F1 = 1.0 · Recall@10 ≥0.90 · nDCG@10 ≥ B0 + 0.15 · search p95 ≤1.5 s

---

## Phase 4: Agent, generation and API ⬜

- [ ] **P4.1** Chat state and LangGraph graph (contextualize → route → tools → generate → verify)
- [ ] **P4.2** Router with structured output (8 intents, clarification)
- [ ] **P4.3** Typed read-only tools
- [ ] **P4.4** Prompts as versioned files; citations `[title · PN · p. X]`; abstention
- [ ] **P4.5** Number verifier
- [ ] **P4.6** FastAPI (SSE chat, module, search, plan, audit, feedback, PDF page links)
- [ ] **P4.7** Langfuse tracing

**Gate:** correctness ≥0.85 · faithfulness ≥0.90 · citation precision ≥0.95 · abstention ≥0.90 · p95 ≤6 s

---

## Phase 5: Planner, degree audit and adjustment ⬜

- [ ] **P5.1** `config/degree_rules.yaml` (pp. 17–18) + tests against the sample plans (pp. 20–21)
- [ ] **P5.2** Student profile model
- [ ] **P5.3** Degree audit ("what do I still need?")
- [ ] **P5.4** CP-SAT planner
- [ ] **P5.5** Adjustment as re-solve with fewest changes, with a diff
- [ ] **P5.6** Natural language → `PlanRequest` and plan explanations

**Gate:** 100% valid plans on 30 scenarios (Hypothesis) · solve ≤2 s · both sample plans pass the audit

---

## Phase 6: Product UI ⬜

- [ ] **P6.1** Decide Chainlit vs. Streamlit; add the `ui` dependency group
- [ ] **P6.2** Chat with module cards, comparison tables, planner board, profile panel, feedback
- [ ] **P6.3** Usability test with 3–5 students

**Gate:** five student tasks completed without help

---

## Phase 7: Hardening and release ⬜

- [ ] **P7.1** Docker Compose for the full stack
- [ ] **P7.2** GitHub Actions CI with eval regression gate
- [ ] **P7.3** New-catalogue re-ingestion with "what changed" report
- [ ] **P7.4** Budgets, caching, security and privacy checks
- [ ] **P7.5** README results table, demo, tag `v1.0`; delete `legacy/` once E1 is recorded

**Gate:** one-command start · CI green · eval report attached to the release

---

## Phase 8: Stretch ⬜

ColBERT late interaction · fine-tuned reranker or embeddings · guarded text-to-SQL · local LLM via vLLM/Ollama · prerequisite graph explorer · Baukasten image via VLM · multi-catalogue support.

---

*Last updated: 2026-11-25 · Current phase: 1 — Data foundation v2*
