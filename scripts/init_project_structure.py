import os
from pathlib import Path

# Base directory is the project root (parent of scripts/)
BASE_DIR = Path(__file__).resolve().parent.parent

dirs_to_create = [
    "frontend/styles",
    "frontend/components",
    "frontend/views",
    "backend/models",
    "backend/services",
    "backend/storage",
    "backend/security",
    "backend/ingestion",
    "backend/retrieval",
    "backend/generation",
    "backend/evaluation",
    "backend/integrations",
    "data/database",
    "data/vector_store",
    "data/vault",
    "data/sample_documents",
    "data/evaluation",
    "data/exports",
    "scripts",
    "docs",
    "tests/unit",
    "tests/integration",
    "tests/security",
    "tests/performance",
]

for d in dirs_to_create:
    dir_path = BASE_DIR / d
    dir_path.mkdir(parents=True, exist_ok=True)
    # If python package, add __init__.py
    if d.startswith("backend") or d.startswith("frontend") or d.startswith("tests"):
        init_file = dir_path / "__init__.py"
        if not init_file.exists():
            init_file.write_text("# Auto-generated package init\n", encoding="utf-8")
    elif d.startswith("data"):
        gitkeep = dir_path / ".gitkeep"
        if not gitkeep.exists():
            gitkeep.write_text("", encoding="utf-8")

# Root package inits
for root_pkg in ["backend", "frontend", "tests"]:
    init_file = BASE_DIR / root_pkg / "__init__.py"
    if not init_file.exists():
        init_file.write_text("# Root package init\n", encoding="utf-8")

print("Directory structure created successfully at project root.")
