"""
NEXUS Document Service
Coordinates file validation, vault persistence, relational metadata tracking,
lifecycle status transitions, and backend authorization.
"""

from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
from backend.storage.db import get_db_connection
from backend.storage.vault import (
    validate_file,
    store_in_vault,
    remove_from_vault,
    compute_sha256,
    sanitize_filename
)
from backend.security.rbac import has_permission, enforce_permission, AuthorizationError
from backend.security.audit import (
    log_audit_event,
    EVENT_DOC_UPLOAD,
    EVENT_DOC_APPROVE,
    EVENT_DOC_REJECT,
    EVENT_DOC_DELETE
)


class DocumentError(Exception):
    """Raised on document processing or business logic failures."""
    pass


def upload_document(
    file_bytes: bytes,
    filename: str,
    domain: str,
    user_id: int,
    username: str = "OPERATOR",
    title: Optional[str] = None,
    auto_approve: bool = False,
    vault_dir: Optional[Path] = None,
    custom_path: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Ingest, validate, and store a technical document.
    Enforces 'doc:upload' permission and detects duplicates by SHA-256 fingerprint.
    """
    # 1. Enforce RBAC permission
    enforce_permission(user_id, "doc:upload", actor_username=username, custom_path=custom_path)

    # 2. Validate file
    clean_filename = sanitize_filename(filename)
    is_valid, err, mime_type = validate_file(clean_filename, file_bytes)
    if not is_valid:
        raise DocumentError(err)

    # 3. Check for duplicates in SQLite by SHA-256 hash
    file_hash = compute_sha256(file_bytes)
    with get_db_connection(custom_path) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, filename, title, domain, status, file_size, created_at
            FROM documents WHERE file_hash = ?
            """,
            (file_hash,)
        )
        existing = cur.fetchone()
        if existing:
            # Duplicate document found
            return {
                "id": existing["id"],
                "filename": existing["filename"],
                "title": existing["title"],
                "domain": existing["domain"],
                "status": existing["status"],
                "file_size": existing["file_size"],
                "is_duplicate": True,
                "message": f"Document '{clean_filename}' matches existing vault document ID #{existing['id']}."
            }

        # 4. Store safely in disk vault
        vault_info = store_in_vault(file_bytes, clean_filename, vault_dir=vault_dir)

        # 5. Determine initial lifecycle status
        doc_title = (title or clean_filename).strip()
        status = "pending"
        approved_by = None
        approved_at = None

        if auto_approve and has_permission(user_id, "doc:approve", custom_path=custom_path):
            status = "approved"
            approved_by = user_id
            approved_at = datetime.now().isoformat()

        # 6. Insert metadata into SQLite
        cur.execute(
            """
            INSERT INTO documents (
                filename, file_hash, vault_path, file_size,
                mime_type, title, domain, status, chunk_count,
                created_by, approved_by, approved_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?)
            """,
            (
                clean_filename,
                file_hash,
                vault_info["vault_path"],
                vault_info["file_size"],
                mime_type,
                doc_title,
                domain.lower(),
                status,
                user_id,
                approved_by,
                approved_at
            )
        )
        doc_id = cur.lastrowid

    # 7. Record Audit Log
    log_audit_event(
        event_type=EVENT_DOC_UPLOAD,
        actor_username=username,
        actor_user_id=user_id,
        description=f"Uploaded document '{clean_filename}' (ID #{doc_id}, Domain: {domain}, Status: {status})",
        metadata={
            "document_id": doc_id,
            "filename": clean_filename,
            "file_hash": file_hash,
            "file_size": vault_info["file_size"],
            "domain": domain,
            "status": status
        },
        custom_path=custom_path
    )

    return {
        "id": doc_id,
        "filename": clean_filename,
        "title": doc_title,
        "domain": domain,
        "status": status,
        "file_size": vault_info["file_size"],
        "file_hash": file_hash,
        "vault_path": vault_info["vault_path"],
        "is_duplicate": False,
        "message": f"Successfully ingested '{clean_filename}' into vault with status '{status.upper()}'."
    }


def list_documents(
    domain: Optional[str] = None,
    status: Optional[str] = None,
    search_query: Optional[str] = None,
    user_id: Optional[int] = None,
    custom_path: Optional[Path] = None
) -> List[Dict[str, Any]]:
    """Retrieve document metadata list with optional domain, status, and query filtering."""
    if user_id:
        enforce_permission(user_id, "doc:view", custom_path=custom_path)

    query_parts = [
        """
        SELECT d.id, d.filename, d.title, d.domain, d.status,
               d.file_size, d.chunk_count, d.created_at, d.approved_at,
               u_cr.username as creator_name,
               u_ap.username as approver_name
        FROM documents d
        LEFT JOIN users u_cr ON u_cr.id = d.created_by
        LEFT JOIN users u_ap ON u_ap.id = d.approved_by
        WHERE 1=1
        """
    ]
    params: List[Any] = []

    if domain and domain != "all":
        query_parts.append("AND d.domain = ?")
        params.append(domain.lower())

    if status and status != "all":
        query_parts.append("AND d.status = ?")
        params.append(status.lower())

    if search_query:
        query_parts.append("AND (d.title LIKE ? OR d.filename LIKE ?)")
        sq = f"%{search_query.strip()}%"
        params.extend([sq, sq])

    query_parts.append("ORDER BY d.id DESC")
    final_sql = " ".join(query_parts)

    with get_db_connection(custom_path) as conn:
        cur = conn.cursor()
        cur.execute(final_sql, tuple(params))
        rows = cur.fetchall()
        return [dict(r) for r in rows]


def get_document_by_id(
    document_id: int,
    user_id: Optional[int] = None,
    custom_path: Optional[Path] = None
) -> Optional[Dict[str, Any]]:
    """Retrieve full document details by ID."""
    if user_id:
        enforce_permission(user_id, "doc:view", custom_path=custom_path)

    with get_db_connection(custom_path) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT d.*, 
                   u_cr.username as creator_name,
                   u_ap.username as approver_name
            FROM documents d
            LEFT JOIN users u_cr ON u_cr.id = d.created_by
            LEFT JOIN users u_ap ON u_ap.id = d.approved_by
            WHERE d.id = ?
            """,
            (document_id,)
        )
        row = cur.fetchone()
        return dict(row) if row else None


def approve_document(
    document_id: int,
    user_id: int,
    username: str = "OPERATOR",
    custom_path: Optional[Path] = None
) -> bool:
    """Approve a document for RAG indexing and knowledge retrieval."""
    enforce_permission(user_id, "doc:approve", actor_username=username, custom_path=custom_path)

    now_iso = datetime.now().isoformat()
    with get_db_connection(custom_path) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE documents
            SET status = 'approved', approved_by = ?, approved_at = ?, updated_at = ?
            WHERE id = ?
            """,
            (user_id, now_iso, now_iso, document_id)
        )
        if cur.rowcount == 0:
            raise DocumentError(f"Document ID #{document_id} not found.")

    log_audit_event(
        event_type=EVENT_DOC_APPROVE,
        actor_username=username,
        actor_user_id=user_id,
        description=f"Approved document ID #{document_id} for retrieval",
        metadata={"document_id": document_id},
        custom_path=custom_path
    )
    return True


def reject_document(
    document_id: int,
    user_id: int,
    username: str = "OPERATOR",
    reason: str = "Clearance denied",
    custom_path: Optional[Path] = None
) -> bool:
    """Reject a document from knowledge retrieval."""
    enforce_permission(user_id, "doc:approve", actor_username=username, custom_path=custom_path)

    now_iso = datetime.now().isoformat()
    with get_db_connection(custom_path) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE documents
            SET status = 'rejected', updated_at = ?
            WHERE id = ?
            """,
            (now_iso, document_id)
        )
        if cur.rowcount == 0:
            raise DocumentError(f"Document ID #{document_id} not found.")

    log_audit_event(
        event_type=EVENT_DOC_REJECT,
        actor_username=username,
        actor_user_id=user_id,
        description=f"Rejected document ID #{document_id}: {reason}",
        metadata={"document_id": document_id, "reason": reason},
        custom_path=custom_path
    )
    return True


def delete_document(
    document_id: int,
    user_id: int,
    username: str = "OPERATOR",
    custom_path: Optional[Path] = None
) -> bool:
    """Permanently delete a document from both SQLite and vault disk storage."""
    enforce_permission(user_id, "doc:delete", actor_username=username, custom_path=custom_path)

    with get_db_connection(custom_path) as conn:
        cur = conn.cursor()
        cur.execute("SELECT filename, vault_path FROM documents WHERE id = ?", (document_id,))
        doc = cur.fetchone()
        if not doc:
            raise DocumentError(f"Document ID #{document_id} not found.")

        filename = doc["filename"]
        vault_path = doc["vault_path"]

        # Delete database row (cascades chunks and document permissions)
        cur.execute("DELETE FROM documents WHERE id = ?", (document_id,))

    # Remove physical file from vault
    if vault_path:
        remove_from_vault(vault_path)

    log_audit_event(
        event_type=EVENT_DOC_DELETE,
        actor_username=username,
        actor_user_id=user_id,
        description=f"Deleted document ID #{document_id} ('{filename}') from vault",
        metadata={"document_id": document_id, "filename": filename},
        custom_path=custom_path
    )
    return True
