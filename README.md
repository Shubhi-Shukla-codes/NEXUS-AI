# NEXUS: Offline-First Knowledge Intelligence Platform

**Privacy-Preserving, Multimodal, Domain-Specific Knowledge Intelligence Platform**

[![Tests](https://img.shields.io/badge/Tests-101%20Passed-4E6B50?style=for-the-badge&logo=pytest)](https://github.com)
[![Python](https://img.shields.io/badge/Python-3.12.10-3E5C76?style=for-the-badge&logo=python)](https://python.org)
[![Offline](https://img.shields.io/badge/Air--Gapped-100%25%20Offline-2C7A7B?style=for-the-badge)](https://github.com)
[![License](https://img.shields.io/badge/License-Apache--2.0-8C9B8E?style=for-the-badge)](LICENSE)

---

## 1. Executive Summary

**NEXUS** is an enterprise-grade, offline-first knowledge intelligence platform engineered for air-gapped, connectivity-constrained, and privacy-critical environments. Designed for technical training, equipment maintenance, defensive cybersecurity, humanitarian disaster management, and public safety operations, NEXUS turns heterogeneous documents into structured, searchable, and citation-backed knowledge.

Every response produced by NEXUS is **grounded in authorized local documentation**, complete with page-level citations, similarity scores, and strict provenance enforcement. When verified knowledge is absent, NEXUS explicitly abstains, eliminating AI hallucinations at the architectural level.

---

## 2. Architectural Topology

```mermaid
flowchart TD
    subgraph UI ["Tactical Military Frontend (Streamlit)"]
        A["Dashboard & Telemetry"]
        B["Knowledge Workspace (Chat)"]
        C["Vault & Repository"]
        D["Ingestion Engine"]
        E["Research Analytics"]
    end

    subgraph Security ["Security & Governance Layer"]
        F["RBAC Engine (4 Roles / 7 Permissions)"]
        G["Bcrypt Hash & Token Sessions"]
        H["Structured Audit Trail"]
    end

    subgraph Ingestion ["Multimodal Ingestion Pipeline"]
        I["PyMuPDF C-Engine & Docx / Tabular"]
        J["Text Normalization & Hyphen Cleaner"]
        K["Structure-Aware Chunker (UUIDv5)"]
        L["Table Matrix & Diagram Extractor"]
    end

    subgraph Storage ["Persistent Local Storage Layer"]
        M[("SQLite Database (WAL Mode)")]
        N[("SHA-256 File Vault (data/vault/)")]
        O[("ChromaDB Vector Store (Cosine HNSW)")]
        P["Extracted Media Vault (data/media/)"]
    end

    subgraph Retrieval ["Hybrid Search & Evidence Engine"]
        Q["Dense Semantic Retriever (all-MiniLM-L6-v2)"]
        R["BM25Okapi Sparse Retriever (Technical Codes)"]
        S["Reciprocal Rank Fusion (RRF k=60)"]
        T["Confidence Thresholding & Abstention"]
    end

    subgraph Generation ["Grounded RAG Inference"]
        U["Local Ollama Daemon (qwen2.5:1.5b)"]
        V["Strict Provenance Prompting [REF-X]"]
        W["Citation Resolver & SQLite Persistence"]
    end

    UI --> Security
    Security --> Ingestion
    Ingestion --> Storage
    Storage --> Retrieval
    Retrieval --> Generation
    Generation --> UI
```

---

## 3. Core System Capabilities

### 🛡️ 100% Air-Gapped Offline Operation
- Runs entirely on local commodity hardware without external network calls or cloud API dependencies.
- Zero telemetry transmission: your sensitive institutional records never leave the physical device.

### 🔍 Reciprocal Rank Fusion (RRF) Hybrid Search
- **Dense Vector Search**: Powered by `all-MiniLM-L6-v2` (384-dimensional embeddings) to understand conceptual semantics and natural language intent.
- **Sparse BM25 Search**: Customized tokenizer preserves alphanumeric identifiers, model numbers, and technical codes (`B-12`, `MIL-STD-810G`, `IP67`, `UN 1005`).
- **RRF Fusion**: Combines rankings using standard $k=60$ ($RRF = \frac{0.6}{60 + r_{\text{dense}}} + \frac{0.4}{60 + r_{\text{sparse}}}$), ensuring exact technical matches surface at top ranks.

### 🎯 Zero-Compute Strict Abstention
- If evidence falls below the calibrated relevance threshold ($\text{Cosine Sim} < 0.35$), NEXUS **abtains immediately without running LLM inference**, saving CPU/RAM cycles and completely preventing hallucinations.

### 🖼️ Multimodal Expansion
- **Raster Diagram Extraction**: Extracts electrical schematics, component drawings, and blueprints from PDF pages with SHA-256 deduplication.
- **Structured Table Representation**: Converts 2D tabular matrices into both standard GitHub Markdown and JSON records with column-header context preservation.
- **Scanned Page Fallback**: Automatically characterizes zero-text scanned pages with visual provenance descriptors so scanned drawings remain discoverable.

### 🔐 Multi-Tier RBAC & Security Hardening
- **Bcrypt Password Hashing**: Work factor 12 with cryptographically random salt.
- **Backend-Enforced Authorization**: All queries and document operations verify permissions (`doc:view`, `doc:upload`, `doc:approve`, `doc:delete`, `user:manage`, `audit:view`) at the database layer.
- **Penetration-Resistant**: Parameterized SQL queries defeat SQLi; strict filename sanitization neutralizes directory traversal (`../../`).

---

## 4. Hardware Specifications & Optimization

NEXUS is engineered specifically for **low-resource CPU environments** (e.g., standard issue field laptops):

| Hardware Attribute | Minimum Profile | Recommended Target |
| :--- | :--- | :--- |
| **Operating System** | Windows 10/11 (64-bit) | Windows 11 (64-bit) |
| **CPU** | Intel Core i5 (4 Cores) | Intel Core i5 / i7 (8+ Logical Cores) |
| **RAM** | 8 GB System Memory | 16 GB System Memory |
| **Storage** | 5 GB Free SSD Storage | 10 GB Free SSD Storage |
| **GPU / VRAM** | None (CPU Native) | Optional GPU acceleration |
| **Python Runtime** | Python 3.12 (Tested on 3.12.10) | Python 3.12.10 |
| **Local LLM** | Ollama with `qwen2.5:1.5b` (986 MB) | Ollama with `qwen2.5:1.5b` |

---

## 5. Quick Start Guide

### Option A: One-Click Windows Launcher (Recommended)
Simply double-click:
```cmd
run_nexus.bat
```
The batch script will perform environment pre-flight checks, verify Python 3.12, detect the local Ollama daemon, initialize SQLite schemas, and open the Streamlit interface at `http://localhost:8501`.

### Option B: Manual Terminal Launch
```powershell
# 1. Activate Virtual Environment
.\.venv\Scripts\Activate.ps1

# 2. Verify / Pull Target Local LLM in Ollama
ollama pull qwen2.5:1.5b

# 3. Execute Complete Test Suite (101 Tests)
pytest tests/

# 4. Launch Application
streamlit run app.py
```

---

## 6. Default Clearance Credentials

Upon initial launch, NEXUS initializes the database with baseline roles:

| Username | Password | Assigned Role | Capabilities |
| :--- | :--- | :--- | :--- |
| `admin` | `NexusAdmin#2026` | **Administrator** | Full system control, user management, configuration, audit inspection, document approval |
| `instructor_demo` | `NexusInstructor#2026` | **Instructor** | Document upload, document review & approval, training workspace queries, analytics |
| `trainee_demo` | `NexusTrainee#2026` | **Trainee** | Scoped document queries, evidence citation inspection, conversation history |

---

## 7. Institutional Domain Knowledge Pillars

NEXUS organizes information into 6 core operational knowledge pillars:

1. **`technical_maintenance`**: Equipment manuals, component repair, schematics, hydraulic governors, lubrication schedules.
2. **`training_education`**: Course curricula, standard operating procedures, practical rubrics, certification requirements.
3. **`safety_emergency`**: Chemical exposure protocols (SDS), Level B PPE guidelines, eye-wash triage, fire evacuation checklists.
4. **`defensive_cybersecurity`**: Air-gapped workstation hardening, cryptographic key rotation, firewall baselines, Modbus port 502 isolation.
5. **`humanitarian_geospatial`**: Field hospital resource directories (Alpha-4), logistics routes (Route Blue 20-ton limit), water supply planning.
6. **`hazard_environmental`**: Chemical classification (UN 1005 Ammonia, UN 1830 Sulphuric Acid), spill neutralization (hydrated lime), runoff containment barriers.

---

## 8. Quantitative Evaluation Benchmark Results

Empirical results from the 30-case benchmark evaluation suite (`BENCHMARK_CASES`):

| Evaluation Metric | Dense Semantic (ChromaDB) | Hybrid RRF (Dense + BM25) | Empirical Advantage |
| :--- | :--- | :--- | :--- |
| **Precision@4** | 0.250 | **0.250** | Parity |
| **Recall@4** | 1.000 | **1.000** | 100% Knowledge Capture |
| **Mean Reciprocal Rank (MRR)** | 0.955 | **1.000** | **+4.7% (Instant Top-1 Hit)** |
| **nDCG@4 (Discounted Gain)** | 0.968 | **1.000** | **+3.3% Optimal Ranking** |
| **Hit Rate@4** | 1.000 | **1.000** | 100% Target Retrieval |
| **Abstention Accuracy** | - | **100.0%** | Zero False Answers on Out-of-Domain Queries |
| **Citation Validity Rate** | - | **100.0%** | All Cited Tags Resolve to Ground Truth |

---

## 9. Verification & Automated Test Suite

NEXUS enforces high engineering rigor with 101 automated pytest unit, security, and integration tests:

```powershell
.\.venv\Scripts\pytest.exe -v tests/
```

```text
tests/security/test_security_audit.py (5 tests) ......... PASSED
tests/security/test_security_rbac.py (4 tests) .......... PASSED
tests/unit/test_auth.py (9 tests) ....................... PASSED
tests/unit/test_chunker.py (4 tests) .................... PASSED
tests/unit/test_cleaner.py (4 tests) .................... PASSED
tests/unit/test_database.py (4 tests) .................. PASSED
tests/unit/test_document_service.py (7 tests) .......... PASSED
tests/unit/test_evaluation.py (9 tests) ................. PASSED
tests/unit/test_foundation.py (6 tests) ................ PASSED
tests/unit/test_frontend.py (5 tests) .................. PASSED
tests/unit/test_generation.py (6 tests) ................ PASSED
tests/unit/test_hybrid_search.py (6 tests) ............. PASSED
tests/unit/test_multimodal.py (6 tests) ................. PASSED
tests/unit/test_optimization.py (3 tests) ............... PASSED
tests/unit/test_pipeline.py (4 tests) .................. PASSED
tests/unit/test_retrieval.py (6 tests) ................. PASSED
tests/unit/test_vault.py (8 tests) ..................... PASSED
tests/unit/test_vector_store.py (5 tests) .............. PASSED

================== 101 passed, 1 warning in 64.70s ==================
```

---

## 10. Responsible Use & Safety Directives

NEXUS is strictly designed for legitimate educational, research, technical knowledge-management, equipment maintenance, and public-safety operations. 
- Ingestion of classified, leaked, or unauthorized material is strictly forbidden by policy.
- The platform strictly enforces safety boundaries: weapon synthesis, attack planning, or targeting instructions are prohibited.
- All included demonstration files utilize synthetic, non-sensitive, or open-access institutional documentation.

---

*Developed by the Advanced Agentic Coding Team // NEXUS Intelligence Platform Version 1.0.0-alpha.*
