"""
NEXUS User & Authentication Data Models
Provides typed data structures for users, roles, permissions, and sessions.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class User:
    """Represents an authenticated or persisted user."""
    id: int
    username: str
    email: Optional[str] = None
    role: str = "trainee"
    roles: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)
    is_active: bool = True
    created_at: Optional[datetime] = None


@dataclass
class Session:
    """Represents an active cryptographic session."""
    token: str
    user_id: int
    expires_at: datetime
    is_active: bool = True
    ip_address: Optional[str] = None
