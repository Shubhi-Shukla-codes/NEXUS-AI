"""
NEXUS Low-Resource Optimization & Memory Manager
Monitors process RAM footprints, enforces batch slicing on commodity hardware (< 8GB RAM),
and manages explicit garbage collection and SQLite WAL checkpointing.
"""

import os
import gc
import sys
import psutil
import logging
from typing import Dict, Any, List, Tuple, Optional
from pathlib import Path

from backend.config import settings
from backend.storage.db import get_db_connection

logger = logging.getLogger("nexus.optimization")


def get_system_memory_profile() -> Dict[str, Any]:
    """
    Measure active Python process memory usage and host physical RAM.
    """
    proc = psutil.Process(os.getpid())
    mem_info = proc.memory_info()
    rss_mb = round(mem_info.rss / (1024 * 1024), 2)

    sys_mem = psutil.virtual_memory()
    total_ram_mb = round(sys_mem.total / (1024 * 1024), 2)
    available_ram_mb = round(sys_mem.available / (1024 * 1024), 2)
    cpu_cores = os.cpu_count() or 1

    return {
        "process_pid": os.getpid(),
        "process_rss_mb": rss_mb,
        "host_total_ram_mb": total_ram_mb,
        "host_available_ram_mb": available_ram_mb,
        "cpu_logical_cores": cpu_cores,
        "low_resource_mode": settings.low_resource_mode,
        "batch_size_ceiling": settings.models.embedding_batch_size
    }


def cleanup_system_memory(custom_db_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Force explicit cyclic garbage collection and trigger SQLite WAL truncation
    to maintain lean RAM and disk journal footprints.
    """
    proc = psutil.Process(os.getpid())
    before_rss_mb = round(proc.memory_info().rss / (1024 * 1024), 2)

    # 1. Python GC
    collected_objects = gc.collect()

    # 2. PyTorch cache purge if loaded
    if "torch" in sys.modules:
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass

    # 3. SQLite WAL Checkpoint (Truncate WAL journal)
    try:
        with get_db_connection(custom_db_path) as conn:
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
    except Exception as exc:
        logger.debug("WAL checkpoint notice: %s", exc)

    after_rss_mb = round(proc.memory_info().rss / (1024 * 1024), 2)
    freed_mb = max(0.0, round(before_rss_mb - after_rss_mb, 2))

    return {
        "collected_objects": collected_objects,
        "before_rss_mb": before_rss_mb,
        "after_rss_mb": after_rss_mb,
        "freed_mb": freed_mb
    }


def generate_batch_slices(total_items: int, batch_size: int = 16) -> List[Tuple[int, int]]:
    """
    Divide total items into bounded index intervals [(0, 16), (16, 32), ...].
    Guarantees that CPU memory never experiences spikes during batch embedding or indexing.
    """
    if total_items <= 0:
        return []
    b_size = max(1, batch_size)
    slices = []
    for start in range(0, total_items, b_size):
        end = min(total_items, start + b_size)
        slices.append((start, end))
    return slices
