# NEXUS Project Status & Execution Roadmap

**Project Version**: 1.0.0-alpha  
**Last Updated**: 2026-10-28  
**Operating Environment**: Windows 11, Intel Core i5 (12 Logical Cores), 15.6 GB RAM (4.0 GB free), Python 3.12.10, Ollama 0.40.11

---

## Phase Execution Checklist

- [x] **PHASE 0: Environment Inspection & Project Foundation**
  - [x] Hardware and platform resource audit (RAM, CPU, Disk, OS).
  - [x] Python 3.12 runtime verification.
  - [x] Ollama CLI and daemon status inspection.
  - [x] Directory structure creation with package initialization.
  - [x] Git repository initialization and `.gitignore` configuration.
  - [x] Centralized configuration engine (`backend/config.py`).
  - [x] Foundational documentation (`README.md`, `ARCHITECTURE.md`, `PROJECT_STATUS.md`, `PROJECT_REPORT.md`).
  - [x] Foundation unit tests verification.

- [ ] **PHASE 1: UI and Application Foundation**
  - [ ] Streamlit master entry point (`app.py`).
  - [ ] Military/tactical camouflage theme and custom CSS design system.
  - [ ] Responsive navigation and view routing.
  - [ ] Reusable components (`header`, `sidebar`, `citation_card`, `document_card`).
  - [ ] Empty and loading states.

- [ ] **PHASE 2: Database and Authentication**
  - [ ] SQLite schema design with foreign keys, indexes, and migrations.
  - [ ] Cryptographic password hashing (bcrypt / PBKDF2 fallback).
  - [ ] Session management and state persistence.
  - [ ] Role-Based Access Control (Admin, Instructor, Trainee, Authorised User).
  - [ ] Structured audit logging engine.

- [ ] **PHASE 3: Document Repository**
  - [ ] Upload handling with SHA-256 fingerprinting.
  - [ ] Secure vault storage with path traversal protection.
  - [ ] Document listing, search, filtering, and metadata inspection.
  - [ ] Approval workflow (Pending -> Approved -> Rejected).
  - [ ] Permission-scoped document actions and soft/hard deletion.

- [ ] **PHASE 4: Ingestion Engine**
  - [ ] PyMuPDF (fitz) text and table extraction with page tracking.
  - [ ] DOCX, TXT, MD, CSV, JSON, XLSX parsers.
  - [ ] Text cleaning and structural normalization.
  - [ ] Structure-aware chunking with stable IDs and boundary metadata.

- [ ] **PHASE 5: Embeddings and Vector Storage**
  - [ ] SentenceTransformers model wrapper (`all-MiniLM-L6-v2`).
  - [ ] Batched chunk embedding generation with normalization.
  - [ ] ChromaDB persistent client and collection management.
  - [ ] Re-indexing and sync between SQLite and ChromaDB.

- [ ] **PHASE 6: Semantic Retrieval**
  - [ ] Query vectorization and cosine similarity retrieval.
  - [ ] Metadata-filtered Top-K candidate extraction.
  - [ ] Strict permission-aware retrieval boundary enforcement.
  - [ ] Evidence deduplication and context budget assembly.

- [ ] **PHASE 7: Local LLM and RAG**
  - [ ] Ollama API client integration for `qwen2.5:1.5b`.
  - [ ] Grounded prompt templating with strict provenance enforcement.
  - [ ] Grounded answer synthesis with page-level citations.
  - [ ] Automated abstention when evidence is insufficient or irrelevant.
  - [ ] Multi-turn conversation persistence in SQLite.

- [ ] **PHASE 8: Advanced Search and Domain Modules**
  - [ ] Hybrid search (dense semantic + keyword BM25).
  - [ ] Domain-specific metadata schemas and specialized filters.
  - [ ] Domain knowledge management across 6 core pillars.

- [ ] **PHASE 9: Dataset and Evaluation Framework**
  - [ ] Curated demonstration dataset (public + synthetic).
  - [ ] Evaluation benchmark suite (30-50 questions with ground truth).
  - [ ] Retrieval metrics calculation (P@K, Recall@K, MRR, nDCG).
  - [ ] Answer faithfulness and hallucination evaluation.

- [ ] **PHASE 10: Multimodal Expansion**
  - [ ] OCR pipeline for scanned documents and diagrams.
  - [ ] Structured table representation and query interface.

- [ ] **PHASE 11: Optimization and Final Deployment**
  - [ ] Memory profiling and garbage collection tuning.
  - [ ] Security hardening audit and penetration tests.
  - [ ] Windows launcher script (`run_nexus.bat`).
  - [ ] Complete research report and demonstration package.

---

## Current Status Summary
Phase 0 foundation is complete and verified. Next step: Phase 1 UI and Application Foundation.
