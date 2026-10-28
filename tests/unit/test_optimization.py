"""
NEXUS Optimization & Memory Management Unit Tests
Validates process RAM profiling, batch limits generation,
and explicit garbage collection cleanup.
"""

import sys
import unittest
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.storage.db import init_database
from backend.optimization.memory_manager import (
    get_system_memory_profile,
    cleanup_system_memory,
    generate_batch_slices
)


class TestOptimizationManager(unittest.TestCase):
    """Test suite for memory management and batch slicing."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_opt.db"
        init_database(custom_path=self.db_path)

    def tearDown(self):
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_get_system_memory_profile(self):
        """Verify memory profiling returns valid positive readings."""
        profile = get_system_memory_profile()

        self.assertIn("process_rss_mb", profile)
        self.assertIn("host_available_ram_mb", profile)
        self.assertIn("cpu_logical_cores", profile)
        self.assertGreater(profile["process_rss_mb"], 0.0)
        self.assertGreater(profile["host_available_ram_mb"], 0.0)
        self.assertGreaterEqual(profile["cpu_logical_cores"], 1)

    def test_cleanup_system_memory(self):
        """Verify explicit GC and WAL truncation executes cleanly."""
        res = cleanup_system_memory(custom_db_path=self.db_path)

        self.assertIn("collected_objects", res)
        self.assertIn("before_rss_mb", res)
        self.assertIn("after_rss_mb", res)
        self.assertGreaterEqual(res["collected_objects"], 0)

    def test_generate_batch_slices(self):
        """Verify batch generation divides workload into bounded intervals."""
        # 35 items with batch size 16 -> [(0, 16), (16, 32), (32, 35)]
        slices = generate_batch_slices(35, batch_size=16)
        self.assertEqual(len(slices), 3)
        self.assertEqual(slices[0], (0, 16))
        self.assertEqual(slices[1], (16, 32))
        self.assertEqual(slices[2], (32, 35))

        # Edge cases
        self.assertEqual(generate_batch_slices(0), [])
        self.assertEqual(generate_batch_slices(10, batch_size=20), [(0, 10)])


if __name__ == "__main__":
    unittest.main()
