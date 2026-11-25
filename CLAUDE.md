# CLAUDE.md

Guidance for AI coding assistants (and humans) working in this repository.

## What this is

Student-Path: a RAG chatbot and semester planner for the M.Sc. Informatik module catalogue
(`data/source/Modulkatalog-Master-Informatik.pdf`, 603 pages, 201 modules). Architecture: structured-first
agentic hybrid RAG. It is a practice project: the owner writes the learning-critical code; assistants
scaffold, review and explain.

## Read first

1. `context/ROADMAP.md`: current phase and the next unchecked task
2. `context/IMPLEMENTATION_PLAN.md`: the step you are on (§7), its code skeleton and its gate
3. `context/ARCHITECTURE.md`: accepted decisions (ADR-005 to ADR-014). Do not contradict them silently; propose a new ADR instead
4. `context/DEVELOPMENT_LOG.md`: latest entries

## Commands

```bash
uv sync                              # install / update the environment (Python 3.11, CPU torch)
uv run sp --help                     # project CLI (sp config, sp check, sp legacy ...)
uv run sp check                      # is the environment ready? (PDF, Gemini settings, Qdrant)
uv run pytest                        # tests
uv run pre-commit run --all-files    # ruff lint + format, pyright, file checks
docker compose up -d                 # optional Qdrant server; then QDRANT_URL=http://localhost:6333
```

Add dependencies with `uv add --group <ingest|ml|serve|eval|dev> <pkg>`, never with pip.

## Layout

- `src/student_path/`: the package. `cli.py` (Typer `sp`), `settings.py` (pydantic-settings from `.env`),
  `store/` (backends). New phases add `ingestion/`, `retrieval/`, `agent/`, `planner/`, `api/` when they start
- `src/student_path/legacy/`: superseded v1 code, only the baseline for experiment E1
- `tests/`: pytest. `data/source/`: the PDF (tracked). `data/legacy/`, `data/interim/`, `data/processed/`,
  `data/qdrant/`: generated, gitignored
- `config/` (from P1/P5): data files such as `degree_rules.yaml` and `prompts/*.md`

## Conventions

- Primary key for modules is the exam number **PN**, never `module_id` (not unique: 5851, 5853)
- Pydantic models at every boundary; typed function signatures; ruff line length 110
- Settings only via `student_path.settings.get_settings()`; paths resolve against the project root
- Heavy imports (docling, torch, FlagEmbedding) inside the functions or commands that need them
- Extraction: deterministic first, LLM second, validate always. LLM calls use structured output, temperature 0,
  a grounding check, and a cache keyed by (prompt version, model, input)
- Prompts live in versioned files (`config/prompts/<name>-vN.md`), not inline strings
- SQL is parametrized; tools exposed to the agent are read-only
- Every new behaviour gets a test; data pipelines get data-contract tests (e.g. exactly 201 modules)

## Never

- Never build on or edit `src/student_path/legacy/` or `data/legacy/` (excluded from lint and types on purpose)
- Never treat `data/legacy/modules.json` as ground truth: it is about 47% complete with merged records
- Never commit `.env`, generated data, or `RAG_system_technical_guildline.md` (private enterprise material).
  Real keys go in `.env` only; `.env.example` holds empty placeholders (a pre-commit hook enforces this)
- Never hand-edit files in `data/processed/`; regenerate them with the pipeline
- Never change the golden test split (`eval/datasets/`, from P2) to make a metric pass
- Never let the LLM do ECTS arithmetic or rule checks; tools and the solver do that

## Workflow

- Work on a branch, one plan step per commit, commit messages naming the step (e.g. `P1.3: ...`)
- Before coding: restate the step's gate from the plan; write or name the check that proves it
- After coding: run tests and pre-commit, tick the box in `context/ROADMAP.md`, and add a short entry to
  `context/DEVELOPMENT_LOG.md` (what happened, decisions, numbers, next step)
- Report measured numbers, not impressions; say plainly when something failed or was skipped
