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
                                     │
                                     ▼
+--------------------------------------------------------------------------+
|                       APPLICATION & SERVICE LAYER                        |
|  +--------------------+  +--------------------+  +--------------------+  |
|  |  Security / Auth   |  | Ingestion Pipeline |  |  Retrieval Engine  |  |
|  |  - RBAC & Sessions |  |  - Parsers (PDF/..) |  |  - Dense Embeddings|  |
|  |  - Audit Logger    |  |  - Chunking Engine |  |  - Top-K Ranker    |  |
|  +--------------------+  +--------------------+  +--------------------+  |
|                                     │                      │             |
|                                     ▼                      ▼             |
|                          +--------------------+  +--------------------+  |
|                          | Generation Engine  |  | Evaluation Engine  |  |
|                          |  - Grounded RAG    |  |  - P@K, MRR, nDCG  |  |
|                          |  - Local Ollama    |  |  - Faithfulness    |  |
|                          +--------------------+  +--------------------+  |
+--------------------------------------------------------------------------+
                                     │
                                     ▼
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

## 3. Relational Schema Architecture (SQLite)

The database layer consists of 15 normalized tables structured to enforce data integrity:

1. **`users`**: Unique usernames, emails, bcrypt-hashed passwords, and activation flags.
2. **`roles`**: Initial roles (`administrator`, `instructor`, `trainee`, `authorised_user`).
3. **`permissions`**: Granular capability codes (`user:manage`, `doc:upload`, `doc:approve`, `doc:view`, `doc:delete`, `app:configure`, `audit:view`).
4. **`user_roles`**: Many-to-many junction linking users to roles with cascade deletions.
5. **`role_permissions`**: Many-to-many junction mapping roles to authorized permissions.
6. **`sessions`**: Cryptographic session tokens stored as SHA-256 digests with explicit expiration timestamps.
7. **`documents`**: Document metadata, SHA-256 file fingerprints, vault paths, MIME types, and approval lifecycle states.
8. **`document_pages`**: Page-level extraction boundaries.
9. **`document_chunks`**: Stable UUIDs for chunked passages linked to vector embeddings.
10. **`document_permissions`**: Document-level access control lists.
11. **`conversations` & `messages`**: Multi-turn dialog persistence with citation payloads.
12. **`audit_logs`**: Tamper-evident logging of security, authentication, and administrative actions.
13. **`application_settings`**: Key-value JSON application preferences.
14. **`schema_version`**: Controlled schema evolution tracking.

---

## 4. Authentication & Security Flow

```
[Operator Input]
       │
       ▼
[Sanitization & Validation: regex, min 8 chars]
       │
       ▼
[User Retrieval: SQLite Indexed Query]
       │
       ▼
[Bcrypt Constant-Time Verification: bcrypt.checkpw(plain, hash)]
       │
       ▼
[Cryptographic Session Creation: secrets.token_urlsafe(32)]
       │
       ▼
[Token Hashing: SHA-256 stored in sessions table]
       │
       ▼
[Role & Permission Assembly: Distinct permissions compiled into session]
       │
       ▼
[Audit Logging: AUTH_LOGIN_SUCCESS recorded without passwords/tokens]
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
