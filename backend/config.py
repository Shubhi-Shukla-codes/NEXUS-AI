"""
NEXUS Configuration Engine
Provides centralized, strongly typed, environment-driven configuration
optimized for low-resource offline deployments.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any


def load_env_file(dotenv_path: Path) -> None:
    """Lightweight .env loader without requiring external python-dotenv."""
    if not dotenv_path.is_file():
        return
    with open(dotenv_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            key = key.strip()
            val = val.strip().strip("\"'").strip()
            if key not in os.environ:
                os.environ[key] = val


# Load .env if present
ROOT_DIR = Path(__file__).resolve().parent.parent
load_env_file(ROOT_DIR / ".env")


@dataclass(frozen=True)
class PathConfig:
    """System directory and storage path configurations."""
    root_dir: Path = ROOT_DIR
    data_dir: Path = ROOT_DIR / "data"
    db_dir: Path = ROOT_DIR / "data" / "database"
    sqlite_db_path: Path = ROOT_DIR / "data" / "database" / "nexus.db"
    vector_store_dir: Path = ROOT_DIR / "data" / "vector_store"
    vault_dir: Path = ROOT_DIR / "data" / "vault"
    sample_docs_dir: Path = ROOT_DIR / "data" / "sample_documents"
    eval_dir: Path = ROOT_DIR / "data" / "evaluation"
    export_dir: Path = ROOT_DIR / "data" / "exports"


@dataclass(frozen=True)
class SecurityConfig:
    """Authentication, authorization, and cryptographic settings."""
    secret_key: str = field(
        default_factory=lambda: os.getenv("NEXUS_SECRET_KEY", "nexus-offline-secure-default-key-change-me")
    )
    password_hash_algorithm: str = "bcrypt"
    session_expire_hours: int = 12
    max_login_attempts: int = 5
    lockout_duration_minutes: int = 15


@dataclass(frozen=True)
class ModelConfig:
    """Local LLM and Embedding Model configurations."""
    # LLM Settings (Ollama)
    ollama_base_url: str = field(
        default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    )
    llm_model: str = field(
        default_factory=lambda: os.getenv("NEXUS_LLM_MODEL", "qwen2.5:1.5b")
    )
    llm_temperature: float = 0.1
    llm_max_tokens: int = 1024
    llm_timeout_seconds: int = 60

    # Embedding Settings (Sentence Transformers)
    # Default is lightweight 384-dim all-MiniLM-L6-v2 (ideal for 8GB RAM laptops)
    embedding_model_name: str = field(
        default_factory=lambda: os.getenv("NEXUS_EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    )
    embedding_dimension: int = 384
    embedding_device: str = "cpu"
    embedding_batch_size: int = 16


@dataclass(frozen=True)
class IngestionConfig:
    """Document Ingestion and Chunking settings."""
    max_upload_size_bytes: int = 50 * 1024 * 1024  # 50 MB
    supported_extensions: tuple = (
        ".pdf", ".txt", ".docx", ".md", ".csv", ".json", ".xlsx"
    )
    chunk_size: int = 512
    chunk_overlap: int = 64
    max_chunks_per_doc: int = 5000


@dataclass(frozen=True)
class NexusConfig:
    """Master Application Configuration."""
    app_name: str = "NEXUS"
    app_version: str = "1.0.0-alpha"
    app_tagline: str = "Offline-First Knowledge Intelligence Platform"
    debug: bool = field(
        default_factory=lambda: os.getenv("NEXUS_DEBUG", "false").lower() in ("true", "1", "yes")
    )
    low_resource_mode: bool = True  # Optimizations for <= 8GB RAM

    paths: PathConfig = field(default_factory=PathConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    models: ModelConfig = field(default_factory=ModelConfig)
    ingestion: IngestionConfig = field(default_factory=IngestionConfig)

    # Pre-defined domain categories
    domains: tuple = (
        "technical_maintenance",
        "training_education",
        "safety_emergency",
        "defensive_cybersecurity",
        "humanitarian_geospatial",
        "hazard_environmental"
    )


# Singleton instance
settings = NexusConfig()
