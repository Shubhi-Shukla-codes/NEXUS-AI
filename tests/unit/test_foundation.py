"""
NEXUS Foundation & Configuration Unit Tests
Validates directory integrity, settings loading, and environment assumptions.
"""

import sys
import unittest
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.config import settings, NexusConfig


class TestFoundation(unittest.TestCase):
    """Test suite for system foundation and configuration."""

    def test_python_version(self):
        """Verify Python runtime meets minimum requirement (>= 3.12)."""
        self.assertGreaterEqual(
            sys.version_info[:2],
            (3, 12),
            f"Python version must be >= 3.12, found: {sys.version}"
        )

    def test_settings_instance(self):
        """Verify settings is an instance of NexusConfig with appropriate defaults."""
        self.assertIsInstance(settings, NexusConfig)
        self.assertEqual(settings.app_name, "NEXUS")
        self.assertTrue(settings.low_resource_mode)

    def test_required_paths_exist(self):
        """Verify all critical system directories exist on disk."""
        required_dirs = [
            settings.paths.data_dir,
            settings.paths.db_dir,
            settings.paths.vector_store_dir,
            settings.paths.vault_dir,
            settings.paths.sample_docs_dir,
            settings.paths.eval_dir,
            settings.paths.export_dir,
        ]
        for directory in required_dirs:
            self.assertTrue(
                directory.exists(),
                f"Required directory does not exist: {directory}"
            )

    def test_supported_domains(self):
        """Verify standard domain modules are registered."""
        expected_domains = {
            "technical_maintenance",
            "training_education",
            "safety_emergency",
            "defensive_cybersecurity",
            "humanitarian_geospatial",
            "hazard_environmental"
        }
        self.assertEqual(set(settings.domains), expected_domains)

    def test_ingestion_supported_extensions(self):
        """Verify expected document file extensions are supported."""
        expected = {".pdf", ".txt", ".docx", ".md", ".csv", ".json", ".xlsx"}
        self.assertEqual(set(settings.ingestion.supported_extensions), expected)

    def test_model_config_defaults(self):
        """Verify model settings target low-resource offline profiles."""
        self.assertEqual(settings.models.llm_model, "qwen2.5:1.5b")
        self.assertEqual(settings.models.embedding_model_name, "all-MiniLM-L6-v2")
        self.assertEqual(settings.models.embedding_dimension, 384)
        self.assertEqual(settings.models.embedding_device, "cpu")


if __name__ == "__main__":
    unittest.main()
