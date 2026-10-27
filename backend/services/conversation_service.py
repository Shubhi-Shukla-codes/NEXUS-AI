"""
NEXUS Conversation Service
Manages multi-turn conversation threads, message histories, and citation attachments
persisted in SQLite.
"""

import json
import uuid
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from backend.storage.db import get_db_connection as get_connection

logger = logging.getLogger("nexus.conversation_service")


class ConversationError(Exception):
    """Base exception for conversation management errors."""
    pass


def create_conversation(
    user_id: int,
    title: str = "New Tactical Briefing",
    domain_scope: str = "all",
    custom_path: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Create a new conversation session for an authenticated user.
    """
    conv_id = str(uuid.uuid4())
    cleaned_title = title.strip()[:100] or "New Tactical Briefing"

    with get_connection(custom_path) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO conversations (id, title, user_id, domain_scope)
            VALUES (?, ?, ?, ?)
            """,
            (conv_id, cleaned_title, user_id, domain_scope)
        )
        cur.execute(
            "SELECT id, title, user_id, domain_scope, created_at, updated_at FROM conversations WHERE id = ?",
            (conv_id,)
        )
        row = cur.fetchone()

    return {
        "id": row["id"],
        "title": row["title"],
        "user_id": row["user_id"],
        "domain_scope": row["domain_scope"],
        "created_at": str(row["created_at"]),
        "updated_at": str(row["updated_at"])
    }


def list_conversations(
    user_id: int,
    limit: int = 50,
    custom_path: Optional[Path] = None
) -> List[Dict[str, Any]]:
    """
    Retrieve all conversation sessions belonging to a specific user, ordered by recent activity.
    """
    with get_connection(custom_path) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT c.id, c.title, c.domain_scope, c.created_at, c.updated_at,
                   COUNT(m.id) as message_count
            FROM conversations c
            LEFT JOIN messages m ON c.id = m.conversation_id
            WHERE c.user_id = ?
            GROUP BY c.id
            ORDER BY c.updated_at DESC
            LIMIT ?
            """,
            (user_id, limit)
        )
        rows = cur.fetchall()

    return [
        {
            "id": r["id"],
            "title": r["title"],
            "domain_scope": r["domain_scope"],
            "created_at": str(r["created_at"]),
            "updated_at": str(r["updated_at"]),
            "message_count": r["message_count"]
        }
        for r in rows
    ]


def get_conversation(
    conversation_id: str,
    user_id: Optional[int] = None,
    custom_path: Optional[Path] = None
) -> Optional[Dict[str, Any]]:
    """
    Retrieve single conversation by ID, optionally validating user ownership.
    """
    with get_connection(custom_path) as conn:
        cur = conn.cursor()
        if user_id is not None:
            cur.execute(
                "SELECT * FROM conversations WHERE id = ? AND user_id = ?",
                (conversation_id, user_id)
            )
        else:
            cur.execute("SELECT * FROM conversations WHERE id = ?", (conversation_id,))
        row = cur.fetchone()

    if not row:
        return None

    return {
        "id": row["id"],
        "title": row["title"],
        "user_id": row["user_id"],
        "domain_scope": row["domain_scope"],
        "created_at": str(row["created_at"]),
        "updated_at": str(row["updated_at"])
    }


def update_conversation_title(
    conversation_id: str,
    title: str,
    user_id: Optional[int] = None,
    custom_path: Optional[Path] = None
) -> bool:
    """
    Update the display title of a conversation.
    """
    clean_title = title.strip()[:100]
    if not clean_title:
        return False

    with get_connection(custom_path) as conn:
        cur = conn.cursor()
        if user_id is not None:
            cur.execute(
                """
                UPDATE conversations
                SET title = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND user_id = ?
                """,
                (clean_title, conversation_id, user_id)
            )
        else:
            cur.execute(
                """
                UPDATE conversations
                SET title = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (clean_title, conversation_id)
            )
        return cur.rowcount > 0


def delete_conversation(
    conversation_id: str,
    user_id: Optional[int] = None,
    custom_path: Optional[Path] = None
) -> bool:
    """
    Permanently delete a conversation and its messages via cascade.
    """
    with get_connection(custom_path) as conn:
        cur = conn.cursor()
        if user_id is not None:
            cur.execute(
                "DELETE FROM conversations WHERE id = ? AND user_id = ?",
                (conversation_id, user_id)
            )
        else:
            cur.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
        return cur.rowcount > 0


def add_message(
    conversation_id: str,
    role: str,
    content: str,
    citations: Optional[List[Dict[str, Any]]] = None,
    user_id: Optional[int] = None,
    custom_path: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Add a new message (user, assistant, or system) to the conversation.
    Updates the conversation's updated_at timestamp.
    """
    allowed_roles = {"user", "assistant", "system"}
    if role not in allowed_roles:
        raise ConversationError(f"Invalid message role '{role}'. Allowed: {allowed_roles}")

    if not content or not content.strip():
        raise ConversationError("Message content cannot be empty.")

    citations_json = json.dumps(citations or [])

    with get_connection(custom_path) as conn:
        cur = conn.cursor()
        # Verify conversation exists
        cur.execute("SELECT id, title FROM conversations WHERE id = ?", (conversation_id,))
        conv = cur.fetchone()
        if not conv:
            raise ConversationError(f"Conversation ID '{conversation_id}' does not exist.")

        cur.execute(
            """
            INSERT INTO messages (conversation_id, user_id, role, content, citations_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (conversation_id, user_id, role, content, citations_json)
        )
        msg_id = cur.lastrowid

        # If it's the first user message and title is default, auto-update title to query summary
        if role == "user" and conv["title"] == "New Tactical Briefing":
            auto_title = content.strip().split("\n")[0][:45]
            if len(content.strip()) > 45:
                auto_title += "..."
            cur.execute(
                """
                UPDATE conversations
                SET title = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (auto_title, conversation_id)
            )
        else:
            cur.execute(
                "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (conversation_id,)
            )

        cur.execute("SELECT * FROM messages WHERE id = ?", (msg_id,))
        row = cur.fetchone()

    return {
        "id": row["id"],
        "conversation_id": row["conversation_id"],
        "role": row["role"],
        "content": row["content"],
        "citations": json.loads(row["citations_json"] or "[]"),
        "created_at": str(row["created_at"])
    }


def get_conversation_messages(
    conversation_id: str,
    user_id: Optional[int] = None,
    custom_path: Optional[Path] = None
) -> List[Dict[str, Any]]:
    """
    Retrieve ordered message history for a conversation.
    """
    with get_connection(custom_path) as conn:
        cur = conn.cursor()
        # Check ownership if user_id given
        if user_id is not None:
            cur.execute(
                "SELECT id FROM conversations WHERE id = ? AND user_id = ?",
                (conversation_id, user_id)
            )
            if not cur.fetchone():
                return []

        cur.execute(
            """
            SELECT id, conversation_id, user_id, role, content, citations_json, created_at
            FROM messages
            WHERE conversation_id = ?
            ORDER BY created_at ASC, id ASC
            """,
            (conversation_id,)
        )
        rows = cur.fetchall()

    return [
        {
            "id": r["id"],
            "conversation_id": r["conversation_id"],
            "role": r["role"],
            "content": r["content"],
            "citations": json.loads(r["citations_json"] or "[]"),
            "created_at": str(r["created_at"])
        }
        for r in rows
    ]
