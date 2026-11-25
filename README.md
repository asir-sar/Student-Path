# Student-Path

A retrieval-augmented chatbot for the M.Sc. Informatik module catalogue (Modulkatalog) of the University of Passau. Students ask in German or English about modules (ECTS, prerequisites, exam formats, which courses fit their interests) and get help planning and adjusting their semesters.

**Status:** early development, phase 0–1 (data foundation). This is a practice project for applied AI and RAG engineering.

## Approach

Structured-first agentic hybrid RAG:

- **Ingestion.** The catalogue PDF is split into its 201 modules using the PDF's own bookmarks, then parsed with Docling (no OCR needed; the PDF is digital). Rows are anchored on the 17 fixed field labels, cleaned, normalized with Gemini into a Pydantic schema, and checked against the catalogue's own overview tables.
- **Knowledge layer:**
  - DuckDB module records, for facts and complete lists
  - a Qdrant hybrid index (BGE-M3 dense + sparse vectors), for meaning
  - a prerequisite graph
  - the degree rules as YAML
- **Answering.** A LangGraph router sends each question to a typed tool: module lookup, filters, hybrid search with reranking, regulation search, degree audit, or an OR-Tools CP-SAT semester planner. Gemini answers with module and page citations, and a verifier checks every number against the records.
- **Evaluation first.** A golden question set covers each question type, measured against two baselines (naive RAG and whole-catalogue long-context Gemini). Every phase ends with a metric gate.

The full plan is in [context/IMPLEMENTATION_PLAN.md](context/IMPLEMENTATION_PLAN.md). For a visual overview, download [context/blueprint.html](context/blueprint.html) and open it in a browser.

## Repository layout

| Path | Contents |
|---|---|
| `context/` | Project brief, architecture decisions, roadmap, development log, implementation plan |
| `CLAUDE.md` | Working guide for AI coding assistants: commands, conventions, what never to do |
| `src/student_path/` | The Python package: `cli.py` (the `sp` command), `settings.py` (typed settings from `.env`), `store/` (Qdrant client). The v2 ingestion pipeline is built here in phase P1 |
| `src/student_path/legacy/` | Superseded v1 parser/normalizer, kept only as a comparison baseline |
| `tests/` | pytest suite |
| `data/source/` | Source catalogue PDF (Stand 13.10.2025) |
| `data/test_questions.json` | First evaluation questions |

## Getting started (current state)

Requires [uv](https://docs.astral.sh/uv/). Dependencies are declared in `pyproject.toml` and pinned in `uv.lock`; PyTorch comes from the CPU-only index.

```bash
uv sync                                       # creates .venv (Python 3.11) with all dependency groups
uv run sp config                              # show the effective settings
uv run sp check                               # is everything ready? (PDF, Gemini settings, Qdrant)
uv run pytest                                 # tests
uv run pre-commit install                     # once: ruff, pyright and file checks on every commit
uv run pre-commit run --all-files             # run all checks manually
```

Every `sp` command has `--help`.

Qdrant runs embedded by default (files under `data/qdrant/`, no Docker needed). For the server, run `docker compose up -d` and set `QDRANT_URL=http://localhost:6333` in `.env`.

For a lighter environment, leave out groups, e.g. `uv sync --no-group ml`. The groups are `ingest`, `ml`, `serve`, `eval` and `dev`.

Copy `.env.example` to `.env` and add your Gemini API key and model ids before using the LLM steps.

The v2 ingestion pipeline (`sp ingest`) arrives in phase P1. The superseded v1 pipeline is still runnable as `sp legacy parse` / `sp legacy normalize` for comparison only; its output is incomplete. Generated data is not committed, because the pipeline rebuilds it.

## Data source

`data/source/Modulkatalog-Master-Informatik.pdf` is the official module catalogue of the M.Sc. Informatik programme at the University of Passau (Stand 13.10.2025, SHA-256 `1ddab2760962bfece10400035f8da10c426d65e12d02ebf830e4f4b965c291fc`). All rights to the catalogue remain with the university. It is included so the pipeline can be reproduced.
