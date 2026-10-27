# NEXUS: Offline-First Knowledge Intelligence Platform

**Privacy-Preserving, Multimodal, Domain-Specific Knowledge System**

---

## 1. Overview

NEXUS is an offline-first intelligent knowledge management platform designed to operate in connectivity-constrained, privacy-sensitive, and resource-bounded environments. It enables institutional users, maintenance teams, technical trainers, and emergency preparedness personnel to ingest technical documentation, perform semantic searches across localized document stores, and generate grounded, evidence-backed answers using local language models (Ollama / Qwen2.5) without sending private data to external cloud services.

## 2. Key Architecture Pillars

- **100% Offline-First Operation**: Document processing, vector embedding, similarity retrieval, and inference execute entirely on the local machine.
- **Evidence-Grounded RAG**: Every generated answer must cite exact source documents and page numbers. The model explicitly abstains when evidence is insufficient.
- **Resource-Constrained Optimization**: Specifically tuned for commodity laptops (Intel i5, 8–16 GB RAM, CPU execution) using lightweight embedding vectors (`all-MiniLM-L6-v2`) and compact models (`qwen2.5:1.5b`).
- **Role-Based Access Control (RBAC)**: Backend-enforced permissions governing document visibility and administrative operations.
- **Comprehensive Audit Trail**: Real-time logging of authentication, ingestion, approval, and query actions in a local SQLite database.

## 3. Supported Knowledge Domains

1. **Technical Knowledge and Maintenance**: Equipment manuals, troubleshooting guides, maintenance schedules.
2. **Training and Education**: Educational curricula, standard operating procedures, training modules.
3. **Safety and Emergency Preparedness**: Hazard awareness, evacuation protocols, first-aid education.
4. **Defensive Cybersecurity**: Incident response playbooks, security hardening benchmarks, vulnerability mitigation.
5. **Humanitarian and Geospatial Knowledge**: Public infrastructure, hospital directories, disaster preparedness data.
6. **Hazard and Environmental Safety**: Safety Data Sheets (SDS), protective equipment guidelines, chemical safety.

## 4. Hardware & Software Requirements

- **Operating System**: Windows 10/11 (64-bit)
- **Processor**: Intel Core i5 (or equivalent)
- **RAM**: Minimum 8 GB (16 GB recommended)
- **Python**: 3.12 (Tested on 3.12.10)
- **Local Model Runtime**: Ollama (Client version 0.40+) with `qwen2.5:1.5b`
- **Database**: SQLite (Relational metadata) & ChromaDB (Vector store)

## 5. Quick Start Guide

### Step 1: Environment Setup
Ensure Python 3.12 is installed and on your PATH.

```bash
# Verify Python version
python --version  # Must be 3.12.x
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Configure Ollama Runtime
Start the Ollama daemon and pull the target model:
```bash
ollama pull qwen2.5:1.5b
```

### Step 4: Run Tests
```bash
pytest tests/
```

### Step 5: Launch NEXUS
```bash
streamlit run app.py
```

## 6. Project Structure

```text
NEXUS/
├── app.py                 # Streamlit entry point
├── requirements.txt       # Dependency definitions
├── backend/               # Core business logic, storage, retrieval, generation
├── frontend/              # UI components, views, military/tactical camouflage theme
├── data/                  # Local encrypted vault, SQLite database, Chroma vector store
├── tests/                 # Unit, integration, security, and performance test suites
└── docs/                  # Architectural documentation and evaluation reports
```

## 7. License & Compliance

NEXUS is strictly designed for legitimate educational, research, technical knowledge-management, and public safety applications. All demonstration datasets use publicly available, open-licensed, or synthetic non-sensitive records.
