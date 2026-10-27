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

### Milestone 2: Relational Database & Role-Based Authentication
- **Date**: 2026-10-28
- **Deliverables**:
  - SQLite relational schema (`backend/storage/schema.py`) with 15 normalized tables, foreign keys, cascade deletes, and B-Tree indexes.
  - Connection manager with context handling, WAL mode, and automatic rollback (`backend/storage/db.py`).
  - Cryptographic security engine (`backend/security/crypto.py`) using `bcrypt` (12 rounds) and `secrets.token_urlsafe(32)`.
  - Token hashing: Raw session tokens never stored; stored as SHA-256 digests in `sessions` table.
  - Role-Based Access Control (`backend/security/rbac.py`) with 4 baseline roles (Administrator, Instructor, Trainee, Authorised User) and 7 granular permissions.
  - Independent backend permission enforcement via `enforce_permission` (raising `AuthorizationError` on unauthorized attempts).
  - Structured audit trail engine (`backend/security/audit.py`) with sensitive payload stripping.
  - Streamlit UI integration: `login.py` connected to database authentication, automatic initial administrator bootstrap (`admin` / `Admin@Nexus2026!`), and permission-filtered navigation.
- **Validation**:
  - 28 unit and security tests passed in 11.65 seconds via `pytest`.
  - Isolated temporary SQLite test databases used for all assertions.

### Milestone 3: Secure Document Storage Vault & Repository Lifecycle
- **Date**: 2026-10-28
- **Deliverables**:
  - File security vault (`backend/storage/vault.py`) enforcing magic-byte format validation (%PDF, PK ZIP, UTF-8 text), path traversal sanitization, and 50MB file size ceiling.
  - SHA-256 content fingerprinting: Documents stored immutably as `<sha256>.<ext>`, eliminating filename collisions and automatically flagging exact duplicate uploads.
  - Document service (`backend/services/document_service.py`) governing multi-parameter listing (domain, status, keyword search), approval state machine (`pending` -> `approved` / `rejected`), and permanent deletion with vault file unlinking.
  - Streamlit UI integration: `ingest.py` connected to multi-file intake with real-time fingerprint feedback; `repository.py` connected to live search, expandable metadata preview, and permission-restricted approve/delete triggers.
- **Validation**:
  - 43 tests passed across foundation, frontend, database, auth, vault, and document service suites.
  - Zero test regressions.

### Milestone 4: Multi-Format Document Ingestion & Structure-Aware Chunking
- **Date**: 2026-10-28
- **Deliverables**:
  - C-based PyMuPDF (fitz) parser extracting page text and converting tabular layout grids into standard Markdown tables.
  - Parsers for Microsoft Word (.docx), Excel (.xlsx), CSV, JSON, Markdown, and TXT files.
  - Text cleaning engine (`backend/ingestion/cleaner.py`) fixing broken line-break hyphenations (`tele-\ncommunication` -> `telecommunication`), normalizing irregular whitespaces, and stripping recurring boilerplate running headers/footers across pages.
  - Structure-aware chunker (`backend/ingestion/chunker.py`) enforcing strict page-boundary preservation (chunks never cross page borders untracked), heading context propagation, and deterministic UUIDv5 generation (`uuid5(NAMESPACE_DNS, doc_page_chunk)`).
  - Master pipeline (`backend/ingestion/pipeline.py`) populating SQLite `document_pages` and `document_chunks` relational records and updating document chunk counts.
  - Streamlit ingestion UI updated to automatically trigger pipeline upon upload with instant page and chunk telemetry display.
- **Validation**:
  - 55 automated tests passed in 30.79s across unit, integration, and security suites.
  - Validated synthetic PDF, DOCX, XLSX, CSV, JSON extraction.

### Milestone 5: Local Embeddings & ChromaDB Vector Storage
- **Date**: 2026-10-28
- **Deliverables**:
  - Local embedding subsystem (`backend/retrieval/embeddings.py`) with abstract provider interface, lazy loading to avoid startup memory spikes on 8-16 GB laptop hardware, and L2 unit vector normalization.
  - Default model: `all-MiniLM-L6-v2` (384 dimensions) with 16-chunk batch processing on CPU; deterministic mock provider for testing and air-gapped CI.
  - ChromaDB integration (`backend/storage/vector_store.py`) operating in-process with SQLite/DuckDB persistence under `data/vector_store/`.
  - HNSW cosine distance indexing (`hnsw:space: cosine`) with metadata filtering by domain category and approval lifecycle state (`approved` / `indexed`).
  - Controlled full re-indexing engine (`backend/retrieval/reindex.py`) enabling administrators to safely re-sync all relational SQLite passages into ChromaDB if models change.
  - Dashboard telemetry updated to query real ChromaDB collection vector counts.
- **Validation**:
  - 60 automated tests passed in 39.30s via `pytest`.
  - Verified embedding normalization, Chroma upsert, metadata filtering, vector unlinking on document deletion, and controlled full re-indexing.

### Milestone 6: Semantic Retrieval Engine & Evidence Grounding
- **Date**: 2026-10-28
- **Deliverables**:
  - Semantic retrieval engine (`backend/retrieval/retriever.py`): Vectorizes incoming user queries using the local embedding model, issues cosine distance queries against ChromaDB, and converts distance to cosine similarity (`1.0 - distance`).
  - Permission-aware query gating: Enforces backend RBAC check (`doc:view`) before any vector search is executed, eliminating UI bypass risks.
  - Confidence thresholding & strict abstention: Configurable similarity threshold (default `0.35`). Queries matching candidates below the threshold return `is_sufficient=False` with a polite abstention signal, mitigating RAG hallucinations when knowledge is missing.
  - Context token budgeting & prompt assembly: Truncates retrieved chunks to a strict token ceiling (default 1500 tokens / 6000 chars) to prevent context window overflow on small models, and formats rich evidence headers (`[Document: <filename>, Page: <page>, Score: <similarity>]`).
  - Automatic vector synchronization: Updated `backend/services/document_service.py` to auto-index approved documents and auto-delete vectors when documents are removed.
  - Tactical Chat UI integration (`frontend/views/chat.py`): Operators can query the local knowledge repository with live similarity scores, expandable evidence references, and instant warning badges on abstention.
- **Validation**:
  - 66 automated tests passed in 48.74s across unit, security, and integration suites.
  - Tested query retrieval, abstention below threshold, Top-K limits, domain scoping, empty query handling, and unauthorized permission blocking.

### Milestone 7: Local LLM & Grounded RAG Synthesis
- **Date**: 2026-10-28
- **Deliverables**:
  - Local Ollama client (`backend/generation/ollama_client.py`): Supports local REST inference (`/api/generate` & `/api/chat`) for `qwen2.5:1.5b` with CPU parameter tuning (temperature=0.1, max_tokens=1024, context=2048). Provides deterministic `MockLLMClient` for air-gapped unit testing and CI.
  - Strict provenance prompting (`NEXUS_SYSTEM_PROMPT`): Directs model to act as a domain-specific intelligence terminal, basing answers exclusively on provided references, citing sources via `[REF-1]`, `[REF-2]`, and strictly abstaining without hallucination when information is lacking.
  - Grounded RAG engine (`backend/generation/rag_engine.py`): Integrates retriever and LLM. Implements zero-compute abstention (skips LLM entirely when evidence falls below threshold), builds formatted context blocks, and parses answer text to map citations back to chunk metadata.
  - SQLite Conversation & Message persistence (`backend/services/conversation_service.py`): Thread management with automatic title generation, multi-turn history tracking, and JSON citation persistence.
  - Tactical Chat UI integration (`frontend/views/chat.py`): Interactive briefing thread management (create, switch, delete), live LLM synthesis display, inline `[REF-X]` citations cards, and tactical abstention alerts.
- **Validation**:
  - 72 automated tests passed in 50.96s across unit, security, and integration suites.
  - Validated conversation thread lifecycle, mock LLM generation, grounded prompt assembly, citation mapping, threshold abstention, and empty query safety.

### Milestone 8: Advanced Hybrid Search & Domain Taxonomy Modules
- **Date**: 2026-10-28
- **Deliverables**:
  - In-memory BM25 sparse keyword index (`backend/retrieval/bm25.py`): BM25Okapi implementation with custom technical tokenization that preserves alphanumeric part numbers, codes, and hyphens (e.g. `B-12`, `MIL-STD-810G`, `IP67`). Dynamically synchronized with SQLite `document_chunks`.
  - Domain taxonomy engine (`backend/retrieval/domain_manager.py`): Complete profiles, metadata schemas, and keyword dictionaries for the 6 core institutional pillars (`technical_maintenance`, `training_education`, `safety_emergency`, `defensive_cybersecurity`, `humanitarian_geospatial`, `hazard_environmental`). Includes heuristic domain inference from natural language queries.
  - Reciprocal Rank Fusion (`backend/retrieval/hybrid_retriever.py`): Combines dense vector candidates and sparse BM25 candidates with standard constant $k=60$ ($RRF\_score = \frac{0.6}{60 + r_{dense}} + \frac{0.4}{60 + r_{sparse}}$), elevating documents that match both semantic concepts and exact technical codes.
  - Tactical Chat UI integration (`frontend/views/chat.py`): Search Mode selector allowing operators to toggle between "Hybrid (Dense + BM25 RRF)" and "Dense Semantic (ChromaDB)", with real-time domain profile telemetry display.
- **Validation**:
  - 78 automated tests passed in 59.29s across all unit, security, and integration suites.
  - Validated technical tokenization, BM25 exact code retrieval, domain taxonomy matching, RRF candidate rank fusion, hybrid retrieval pipeline, and hybrid RAG generation.
