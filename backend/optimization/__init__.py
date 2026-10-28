"""
NEXUS Optimization Package
Exposes memory profiling, batch limits enforcement, and garbage collection utilities.
"""

from backend.optimization.memory_manager import (
    get_system_memory_profile,
    cleanup_system_memory,
    generate_batch_slices
)

__all__ = [
    "get_system_memory_profile",
    "cleanup_system_memory",
    "generate_batch_slices"
]
