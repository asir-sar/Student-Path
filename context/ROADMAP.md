# Roadmap

Progress tracker for each phase. Check off tasks as they are completed.

---

## Phase 1: Data Foundation 🟡 IN PROGRESS

> **Goal:** Extract, parse, and structure all modules from the PDF into clean JSON with validated metadata.

- [ ] **1.1** Install Docling and run it on `Modulkatalog-Master-Informatik.pdf`
- [ ] **1.2** Inspect Docling output — verify table extraction quality on 5-10 sample modules
- [ ] **1.3** Build the module normalizer script (`src/ingestion/normalizer.py`)
  - Extract structured fields from Docling's markdown output
  - Map to the defined metadata schema (ADR-003)
  - Handle bilingual content separation (DE/EN)
  - Handle edge cases: multi-line values, hyphenation, missing fields
- [ ] **1.4** Run normalizer on full catalogue → `data/modules.json`
- [ ] **1.5** Quality check: inspect 20-30 random modules for parsing errors
- [ ] **1.6** Write 15-20 test questions with expected answers → `data/test_questions.json`

**Deliverable:** `data/modules.json` — complete structured dataset of all ~200-300 modules

---

## Phase 2: Ingestion Pipeline ⬜ NOT STARTED

> **Goal:** Embed all modules and index them in Qdrant with metadata, ready for hybrid search.

- [ ] **2.1** Set up Qdrant (local Docker or Qdrant Cloud free tier)
- [ ] **2.2** Implement BGE-M3 embedding generation (`src/ingestion/embedder.py`)
  - Dense vectors for semantic search
  - Sparse vectors for keyword search (module IDs, exact terms)
- [ ] **2.3** Build the ingestion script (`src/ingestion/ingest.py`)
  - Read `data/modules.json`
  - Generate embeddings per module
  - Upsert to Qdrant with full metadata payload
- [ ] **2.4** Verify: run raw Qdrant queries to confirm data is searchable
- [ ] **2.5** Test hybrid search (dense + sparse) with sample queries

**Deliverable:** Populated Qdrant collection with all modules, queryable via API

---

## Phase 3: Search, Agent & Chat ⬜ NOT STARTED

> **Goal:** Build the retrieval pipeline and LLM-powered chat that answers student questions with source references.

- [ ] **3.1** Implement hybrid search function (`src/search/retriever.py`)
  - Combined dense + sparse scoring
  - Metadata filtering (semester, ECTS, language, focus area)
- [ ] **3.2** Add reranker (bge-reranker-v2-m3) (`src/search/reranker.py`)
- [ ] **3.3** Build the LangGraph agent (`src/agent/agent.py`)
  - Intent classification (lookup / recommend / plan / compare)
  - Tool definitions for Qdrant search
  - System prompt for course recommendation context
- [ ] **3.4** Wire up LLM (OpenAI or Gemini API)
- [ ] **3.5** Build FastAPI backend (`src/api/main.py`)
  - `/chat` endpoint
  - `/search` endpoint (for debugging)
- [ ] **3.6** Evaluate quality with test questions (Ragas or manual scoring)

**Deliverable:** Working API that answers course questions with sources

---

## Phase 4: Frontend & Polish ⬜ NOT STARTED

> **Goal:** User-facing interface and quality improvements.

- [ ] **4.1** Build web UI (Streamlit MVP or React)
  - Chat interface
  - Filter sidebar (semester, ECTS, language)
  - Source reference display (module ID, name, page)
- [ ] **4.2** Semester planning feature
  - Multi-course selection with ECTS running total
  - Prerequisite checking
- [ ] **4.3** Quality polish
  - Run Ragas evaluation, document scores
  - Tune prompts and retrieval parameters
- [ ] **4.4** Document lessons learned for enterprise project transfer

**Deliverable:** Complete working prototype + documented learnings

---

## Target Directory Structure

```
Student-Path/
├── context/                    # Project tracking (you are here)
│   ├── PROJECT.md
│   ├── ARCHITECTURE.md
│   ├── DEVELOPMENT_LOG.md
│   └── ROADMAP.md
├── data/
│   ├── raw/                    # Docling output (intermediate)
│   ├── modules.json            # Final structured module data
│   └── test_questions.json     # Evaluation questions
├── src/
│   ├── ingestion/
│   │   ├── parser.py           # Docling PDF parsing
│   │   ├── normalizer.py       # Structured JSON extraction
│   │   ├── embedder.py         # BGE-M3 embedding generation
│   │   └── ingest.py           # Qdrant indexing
│   ├── search/
│   │   ├── retriever.py        # Hybrid search
│   │   └── reranker.py         # Result reranking
│   ├── agent/
│   │   └── agent.py            # LangGraph agent
│   └── api/
│       └── main.py             # FastAPI endpoints
├── frontend/                   # Web UI
├── tests/                      # Unit + integration tests
├── .env.example                # API keys template
├── requirements.txt
├── Modulkatalog-Master-Informatik.pdf
└── README.md
```

---

*Last updated: 2026-10-10*  
*Current phase: 1 — Data Foundation*
