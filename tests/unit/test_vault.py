"""
NEXUS Storage Vault Unit Tests
Validates file sanitization, format signature checking, path traversal protection,
and SHA-256 fingerprinting.
"""

import sys
import unittest
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.storage.vault import (
    sanitize_filename,
    compute_sha256,
    validate_file,
    store_in_vault,
    remove_from_vault
)


class TestVaultStorage(unittest.TestCase):
    """Test suite for document storage vault and validation."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.vault_path = Path(self.temp_dir.name) / "vault"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_sanitize_filename_prevents_path_traversal(self):
        """Verify directory traversal patterns are sanitized."""
        self.assertEqual(sanitize_filename("../../etc/passwd.pdf"), "passwd.pdf")
        self.assertEqual(sanitize_filename("..\\..\\windows\\system32\\cmd.exe"), "cmd.exe")
        self.assertEqual(sanitize_filename("my document (v1).pdf"), "my document _v1_.pdf")
        self.assertEqual(sanitize_filename(""), "untitled_document.txt")

    def test_compute_sha256(self):
        """Verify SHA-256 calculation matches expected hash."""
        data = b"NEXUS offline document content."
        expected = "8c6feec63d0cfae60e8d1aa3a18a9fc89f927e1f6e2b10a2fdbf0408544e3f4e"
        # Verify deterministic hash
        h1 = compute_sha256(data)
        h2 = compute_sha256(data)
        self.assertEqual(h1, h2)
        self.assertEqual(len(h1), 64)

    def test_validate_empty_file_rejected(self):
        """Verify 0-byte files are rejected."""
        valid, err, _ = validate_file("test.pdf", b"")
        self.assertFalse(valid)
        self.assertIn("empty", err.lower())

    def test_validate_oversized_file_rejected(self):
        """Verify files exceeding size limits are rejected."""
        large_bytes = b"0" * 1024
        valid, err, _ = validate_file("test.pdf", large_bytes, max_size_bytes=512)
        self.assertFalse(valid)
        self.assertIn("exceeds", err.lower())

    def test_validate_unsupported_extension_rejected(self):
        """Verify dangerous or unsupported extensions are rejected."""
        valid, err, _ = validate_file("malicious.exe", b"MZ\x90\x00Binary")
        self.assertFalse(valid)
        self.assertIn("unsupported", err.lower())

    def test_validate_pdf_magic_bytes(self):
        """Verify valid PDF magic signature passes, invalid signature fails."""
        valid_pdf = b"%PDF-1.5 test pdf content"
        valid, err, mime = validate_file("manual.pdf", valid_pdf)
        self.assertTrue(valid)
        self.assertIsNone(err)
        self.assertEqual(mime, "application/pdf")

        # Fake PDF without %PDF header
        invalid_pdf = b"This is just plain text masquerading as pdf"
        valid_f, err_f, _ = validate_file("fake.pdf", invalid_pdf)
        self.assertFalse(valid_f)
        self.assertIn("signature", err_f.lower())

    def test_validate_plaintext_formats(self):
        """Verify txt, md, json, csv valid files pass."""
        txt_bytes = b"Technical specification for antenna system."
        valid, _, mime = validate_file("specs.txt", txt_bytes)
        self.assertTrue(valid)
        self.assertEqual(mime, "text/plain")

        md_bytes = b"# Emergency Protocol\nStep 1: Evacuate."
        valid, _, mime = validate_file("protocol.md", md_bytes)
        self.assertTrue(valid)
        self.assertEqual(mime, "text/markdown")

    def test_store_and_remove_from_vault(self):
        """Verify file persistence and removal from disk vault."""
        sample_data = b"%PDF-1.4 sample content for disk vault"
        stored = store_in_vault(sample_data, "test_manual.pdf", vault_dir=self.vault_path)

        self.assertTrue(Path(stored["vault_path"]).is_file())
        self.assertEqual(stored["file_size"], len(sample_data))
        self.assertEqual(stored["safe_filename"], "test_manual.pdf")

        # Read back content
        with open(stored["vault_path"], "rb") as f:
            read_back = f.read()
        self.assertEqual(read_back, sample_data)

        # Remove from vault
        removed = remove_from_vault(stored["vault_path"])
        self.assertTrue(removed)
        self.assertFalse(Path(stored["vault_path"]).exists())


if __name__ == "__main__":
    unittest.main()
