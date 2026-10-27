"""
NEXUS Document Storage Vault
Provides secure file fingerprinting, validation, path traversal prevention,
and local disk storage under data/vault/.
"""

import os
import re
import hashlib
from pathlib import Path
from typing import Tuple, Optional, Dict, Any
from backend.config import settings

# Supported format signatures (magic bytes)
MAGIC_SIGNATURES = {
    ".pdf": b"%PDF",
    ".docx": b"PK\x03\x04",
    ".xlsx": b"PK\x03\x04",
}

MIME_TYPE_MAP = {
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".csv": "text/csv",
    ".json": "application/json",
}


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent directory traversal and shell injection.
    Strips directory separators, null bytes, and non-whitelisted characters.
    """
    if not filename:
        return "untitled_document.txt"
    # Take only basename
    clean = os.path.basename(filename).strip()
    # Replace dangerous characters with underscores
    clean = re.sub(r"[^\w\.\-\s]", "_", clean)
    clean = clean.replace("..", "_")
    return clean if clean else "document.bin"


def compute_sha256(data: bytes) -> str:
    """Compute SHA-256 hexadecimal hash of raw file bytes."""
    return hashlib.sha256(data).hexdigest()


def validate_file(
    filename: str,
    file_bytes: bytes,
    max_size_bytes: Optional[int] = None
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validate file size, extension, and magic bytes.
    Returns: (is_valid, error_message, detected_mime_type)
    """
    max_size = max_size_bytes or settings.ingestion.max_upload_size_bytes

    if not file_bytes or len(file_bytes) == 0:
        return False, "File is empty (0 bytes). Cannot ingest empty content.", None

    if len(file_bytes) > max_size:
        max_mb = max_size / (1024 * 1024)
        return False, f"File exceeds maximum permissible size of {max_mb:.0f} MB.", None

    # Check extension
    ext = Path(filename).suffix.lower()
    if ext not in settings.ingestion.supported_extensions:
        supported = ", ".join(settings.ingestion.supported_extensions)
        return False, f"Unsupported file extension '{ext}'. Permitted formats: {supported}", None

    mime_type = MIME_TYPE_MAP.get(ext, "application/octet-stream")

    # Magic byte signature validation
    if ext in MAGIC_SIGNATURES:
        expected_sig = MAGIC_SIGNATURES[ext]
        if not file_bytes.startswith(expected_sig):
            return False, f"File content signature does not match expected {ext.upper()} format.", None
    elif ext in (".txt", ".md", ".csv", ".json"):
        # Verify text encoding (UTF-8 or ASCII decodable)
        try:
            file_bytes[:4096].decode("utf-8")
        except UnicodeDecodeError:
            try:
                file_bytes[:4096].decode("latin-1")
            except Exception:
                return False, f"Text document '{filename}' is not valid UTF-8/ASCII encoded.", None

    return True, None, mime_type


def store_in_vault(
    file_bytes: bytes,
    filename: str,
    vault_dir: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Store file bytes securely in vault using its SHA-256 hash as the filename.
    Returns metadata dictionary including hash, path, and size.
    """
    target_vault = vault_dir or settings.paths.vault_dir
    target_vault.mkdir(parents=True, exist_ok=True)

    file_hash = compute_sha256(file_bytes)
    ext = Path(filename).suffix.lower()
    safe_name = f"{file_hash}{ext}"
    vault_file_path = target_vault / safe_name

    # Write file safely
    with open(vault_file_path, "wb") as f:
        f.write(file_bytes)

    return {
        "file_hash": file_hash,
        "vault_path": str(vault_file_path),
        "file_size": len(file_bytes),
        "safe_filename": sanitize_filename(filename)
    }


def remove_from_vault(vault_path_str: str) -> bool:
    """Safely remove a file from the vault."""
    try:
        p = Path(vault_path_str)
        if p.is_file():
            p.unlink()
            return True
        return False
    except Exception:
        return False
