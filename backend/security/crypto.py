"""
NEXUS Cryptographic & Security Utilities
Provides bcrypt password hashing, constant-time verification,
and secure session token generation.
"""

import re
import secrets
import hashlib
from typing import Tuple, Optional
import bcrypt


def hash_password(password: str) -> str:
    """
    Hash plaintext password using bcrypt with automatic salt generation.
    Returns decoded UTF-8 string representation of bcrypt hash.
    """
    if not password or len(password.strip()) == 0:
        raise ValueError("Password cannot be empty.")
    
    salt = bcrypt.gensalt(rounds=12)
    pwd_bytes = password.encode("utf-8")
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify plaintext password against bcrypt hash in constant time.
    """
    if not plain_password or not hashed_password:
        return False
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8")
        )
    except Exception:
        return False


def generate_session_token() -> str:
    """
    Generate cryptographically strong URL-safe session token (32 bytes entropy).
    """
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    """
    Hash session token using SHA-256 before database storage.
    Ensures database compromises cannot hijack active user sessions.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def validate_username(username: str) -> Tuple[bool, Optional[str]]:
    """Validate username according to alphanumeric and length policies."""
    username = (username or "").strip()
    if not username:
        return False, "Username cannot be empty."
    if len(username) < 3 or len(username) > 32:
        return False, "Username must be between 3 and 32 characters."
    if not re.match(r"^[a-zA-Z0-9_\-\.]+$", username):
        return False, "Username may only contain letters, numbers, underscores, dashes, and periods."
    return True, None


def validate_password_strength(password: str) -> Tuple[bool, Optional[str]]:
    """Validate minimum password length and complexity."""
    if not password or len(password) < 8:
        return False, "Password must be at least 8 characters long."
    return True, None
