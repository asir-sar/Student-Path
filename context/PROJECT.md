# Student-Path: Modulkatalog RAG System

## Purpose

A Retrieval-Augmented Generation system that answers student questions and recommends semester courses based on the University of Passau's Master Informatik Modulkatalog (course catalogue, ~600 pages, ~200-300 modules).

## Goals

1. **Primary:** Build a working RAG pipeline that students can query for course recommendations
2. **Learning:** Practice the exact same RAG patterns planned for an enterprise RAG project
3. **Transferable skills:** Ingestion pipeline, BGE-M3 embeddings, Qdrant hybrid search, reranking, LangGraph agent

## Scope

| In Scope | Out of Scope |
|---|---|
| Single PDF ingestion pipeline | Multi-source data (MySQL, employee knowledge) |
| Structured module extraction | Permission/access control |
| Hybrid search (semantic + keyword) | GDPR compliance |
| Metadata-filtered retrieval | Production deployment (Docker/K8s) |
| Course recommendation agent | Teams bot integration |
| Simple web UI | User authentication |
| Quality evaluation (Ragas) | Change detection (single static PDF) |

## Data Source

- **File:** `Modulkatalog-Master-Informatik.pdf` (~4.3 MB, 600+ pages)
- **Structure:** Bilingual (German + English) table-format course descriptions
- **Content per module:** ID, name, ECTS, semester, language, lecturer, prerequisites, workload, learning outcomes, content, assessment, literature

## Relationship to Enterprise Project

This project is a **stepping stone** for an enterprise RAG project (its technical guide is kept private, outside this repository). ~70% of the architecture transfers directly. See [ARCHITECTURE.md](ARCHITECTURE.md) for the mapping.

---

*Created: 2026-10-10*
*Status: Phase 1 — Data Foundation*
