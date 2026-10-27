# NEXUS: Engineering & Research Project Report

**Author**: Principal Software Architect & AI Engineering Team  
**System**: NEXUS (Offline-First Multimodal Domain-Specific Knowledge Intelligence Platform)  
**Date**: October 2026  
**Status**: Phase 0 Complete — Environment Inspection & Project Foundation Verified

---

## 1. Executive Summary

This report documents the architectural design, engineering decisions, performance benchmarks, and evaluation outcomes of the **NEXUS** platform. NEXUS is engineered from first principles to solve the challenge of operating secure, evidence-backed knowledge intelligence in low-resource, disconnected environments (such as field operations, training academies, and isolated facilities).

---

## 2. Environment & Resource Baseline

| Metric | Measured Baseline Value | Architectural Implication |
| :--- | :--- | :--- |
| **Operating System** | Windows 11 Home/Pro (Build 26200) | Native Windows process execution, path handling (`Pathlib`), PowerShell/Batch launcher scripts. |
| **CPU Architecture** | Intel Core i5 (12 Logical Cores) | Multi-threaded CPU execution for vector operations; batch parallelization. |
| **Total Physical RAM** | 15.64 GB | Meets the target laptop hardware profile. |
| **Available RAM** | 4.01 GB | Active constraint: heavy models (e.g. 7B+ parameters) will induce swap thrashing; runtime model footprint must remain $\le 2.0$ GB. |
| **Disk Storage** | 198.98 GB (23.11 GB Free) | Compact storage envelope; vector indices and cached embeddings must be kept pruned and compact. |
| **Python Runtime** | Python 3.12.10 (AMD64) | Full compatibility with PyMuPDF, ChromaDB, and modern async libraries. |
| **Local LLM Server** | Ollama CLI 0.40.11 | Embedded local runtime; standard REST endpoint (`http://127.0.0.1:11434`). |

---

## 3. Foundational Architectural Decisions

### Decision 1: Pure Offline Execution Guarantee
To guarantee strict privacy and eliminate reliance on external cloud APIs, all core subsystems (document parsing, embedding generation, semantic retrieval, and generative inference) are hosted locally. Network isolation is built into the architecture.

### Decision 2: Model Selection for Commodity Hardware
- **Language Model**: `Qwen2.5 1.5B (Instruct)`  
  *Justification*: At 1.5 billion parameters with 4-bit/8-bit quantization in Ollama, RAM footprint is approximately 1.1–1.4 GB. It demonstrates state-of-the-art reasoning, structured instruction following, and multilingual grounding at small scales.
- **Embedding Model**: `all-MiniLM-L6-v2`  
  *Justification*: 384-dimensional dense vectors with a model size of ~90 MB. It runs on CPU in milliseconds per chunk, preventing memory pressure.

### Decision 3: Relational Metadata & Vector Decoupling
- Relational metadata, access logs, users, and permissions are stored in **SQLite 3** with foreign key constraints and WAL logging.
- Dense embeddings are indexed in **ChromaDB**.
- The two stores are synchronized via stable Chunk UUIDs, ensuring that vector searches strictly validate relational permissions before returning candidate passages to the context assembler.

---

## 4. Milestone Log

### Milestone 0: Environment Inspection & Project Foundation
- **Date**: 2026-10-28
- **Deliverables**: Directory tree, `.gitignore`, `backend/config.py`, documentation, environment audit, unit test verification.
- **Validation**: All foundation tests passed with zero external dependencies.

### Milestone 1: UI and Application Foundation Shell
- **Date**: 2026-10-28
- **Deliverables**: 
  - Tactical camouflage CSS design system (`frontend/styles/theme.css`) with exact specified color tokens (#556B2F, #4B5320, #26382B, #C3B091, #D6C6A5, #F4F2E9, #202820, #B49A5A).
  - Scalable vector wordmark (`frontend/components/logo.py`) implementing symmetrical crossed-axis 'X' motif for full wordmark, sidebar, icon, and favicon.
  - Tactical navigation sidebar (`frontend/components/sidebar.py`) with domain scoping filter and live telemetry display.
  - Provenance citation cards (`frontend/components/citation_card.py`) and document cards (`frontend/components/document_card.py`).
  - Operational views: `dashboard` (database-backed real metrics), `chat` (conversational workspace with evidence cards), `repository` (vault management), `ingest` (upload pipeline), `analytics` (empirical telemetry), `settings` (model & air-gap controls), `login` (operator clearance gateway).
  - Master entrypoint `app.py` with session state initialization and view dispatcher.
- **Validation**:
  - Virtual environment `.venv` with `streamlit-1.66.1`.
  - 11 unit tests passed across foundation and frontend test suites.
  - Zero syntax/byte-compilation errors.
