# NEXUS System Architecture

This document describes the high-level architecture, subsystem boundaries, data flow pipelines, and design decisions of the NEXUS platform.

---

## 1. Architectural Principles

1. **Strict Offline Execution**: Zero telemetry, zero external API calls. All retrieval and generation loops execute locally.
2. **Separation of Concerns**: Modular layering between Presentation (Streamlit), Domain Logic (Ingestion/Retrieval/Generation), Storage (SQLite + ChromaDB), and Security (RBAC + Audit).
3. **Defense in Depth**: Access control enforced strictly in the backend service layer, never solely at the UI layer.
4. **Low-Resource Adaptability**: Lazy loading of neural networks, small batch sizes, and selective in-memory caching to function smoothly within 8–16 GB RAM envelopes on integrated graphics.
5. **Traceability & Groundedness**: Every chunk preserves parent document identifiers, page boundaries, headings, and character offsets. Responses with insufficient evidence strictly trigger abstention.

---

## 2. High-Level Subsystem Diagram

```
+--------------------------------------------------------------------------+
|                     PRESENTATION LAYER (Streamlit)                       |
|   [Dashboard]  [Conversational Workspace]  [Repository]  [Ingestion]      |
|   [Analytics & Evaluation]                 [Settings & User Admin]       |
+--------------------------------------------------------------------------+
                                     |
                                     v
+--------------------------------------------------------------------------+
|                       APPLICATION & SERVICE LAYER                        |
|  +--------------------+  +--------------------+  +--------------------+  |
|  |  Security / Auth   |  | Ingestion Pipeline |  |  Retrieval Engine  |  |
|  |  - RBAC & Sessions |  |  - Parsers (PDF/..) |  |  - Dense Embeddings|  |
|  |  - Audit Logger    |  |  - Chunking Engine |  |  - Top-K Ranker    |  |
|  +--------------------+  +--------------------+  +--------------------+  |
|                                     |                      |             |
|                                     v                      v             |
|                          +--------------------+  +--------------------+  |
|                          | Generation Engine  |  | Evaluation Engine  |  |
|                          |  - Grounded RAG    |  |  - P@K, MRR, nDCG  |  |
|                          |  - Local Ollama    |  |  - Faithfulness    |  |
|                          +--------------------+  +--------------------+  |
+--------------------------------------------------------------------------+
                                     |
                                     v
+--------------------------------------------------------------------------+
|                          PERSISTENCE LAYER                               |
|   +------------------------------------+   +--------------------------+  |
|   |         SQLite Database            |   |       ChromaDB           |  |
|   | - Users, Roles, Permissions        |   | - 384-d Dense Embeddings |  |
|   | - Document Metadata, Lifecycle     |   | - Metadata filtering     |  |
|   | - Chunks, Audit Logs, History      |   | - Cosine similarity      |  |
|   +------------------------------------+   +--------------------------+  |
|   +------------------------------------------------------------------+   |
|   |                      Document Vault (Local Disk)                 |   |
|   | - SHA-256 hashed storage, path sanitization, read-only vaults    |   |
|   +------------------------------------------------------------------+   |
+--------------------------------------------------------------------------+
```

---

## 3. Data Flow Pipelines

### 3.1 Document Ingestion Lifecycle
```
[Uploaded File]
       │
       ▼
[Validation: Extension, MIME, Magic Bytes, Max Size, Path Sanitization]
       │
       ▼
[Safe Storage: data/vault/<sha256>.<ext>]
       │
       ▼
[Extraction: PyMuPDF / docx / openpyxl / csv / json]
  -> Extracts: Plain text, Page numbers, Headings, Structural tables
       │
       ▼
[Text Cleaning: Normalization, Artifact removal, whitespace normalization]
       │
       ▼
[Structure-Aware Chunking: 512 tokens / 64 overlap + Page Boundary preservation]
       │
       ▼
[Review & Approval Gate: Role-based status (Pending -> Approved)]
       │
       ▼
[Embedding Generation: SentenceTransformers all-MiniLM-L6-v2]
       │
       ▼
[Vector Store Indexing: ChromaDB collection indexing + SQLite relational sync]
```

### 3.2 Retrieval-Augmented Generation (RAG) Lifecycle
```
[User Question]
       │
       ▼
[Authentication & RBAC Scope Check: Extract permitted Document IDs]
       │
       ▼
[Query Embedding: all-MiniLM-L6-v2]
       │
       ▼
[ChromaDB Similarity Retrieval: Cosine Distance, Top-K, Metadata Filter]
       │
       ▼
[Evidence Assembly: Deduplication, Page preservation, Context Window budget]
       │
       ▼
[Sufficiency Evaluation: If similarity score < threshold -> Abstain cleanly]
       │
       ▼
[Local LLM Prompt Formulation: System prompt + strict ground-truth context]
       │
       ▼
[Ollama Inference: Qwen2.5 1.5B (Local CPU/GPU)]
       │
       ▼
[Post-Processing: Citation Verification, Grounding check, Audit log entry]
       │
       ▼
[Final Evidence-Backed Response to User]
```

---

## 4. Hardware Optimization Strategy (8–16 GB RAM Profile)

1. **Lightweight Embeddings**: `all-MiniLM-L6-v2` consumes under 120 MB VRAM/RAM with high retrieval precision.
2. **Compact Foundation LLM**: `Qwen2.5 1.5B` requires ~1.2 GB RAM (4-bit/8-bit quantized in Ollama), leaving ample headroom for the operating system and ChromaDB.
3. **Lazy Subsystem Initialization**: Embedding models and vector database clients are loaded only upon the first ingestion or search request.
4. **Batch Processing**: Document chunk embeddings are generated in batches of 16 to avoid memory spikes.
5. **Connection Pooling**: SQLite transactions utilize WAL (Write-Ahead Logging) mode for concurrent reader isolation.
