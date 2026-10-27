"""
NEXUS Text Cleaner Unit Tests
Validates text normalization, hyphenation recombining, and header/footer stripping.
"""

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.ingestion.cleaner import clean_text, remove_repetitive_headers_footers


class TestTextCleaner(unittest.TestCase):
    """Test suite for document cleaning and normalization."""

    def test_clean_text_normalizes_whitespace(self):
        """Verify irregular spaces and excessive blank lines are standardized."""
        raw = "Line 1   with   tabs\t\tand   spaces.\n\n\n\nLine 2.\r\nLine 3."
        cleaned = clean_text(raw)
        self.assertNotIn("   ", cleaned)
        self.assertNotIn("\r", cleaned)
        self.assertNotIn("\n\n\n", cleaned)
        self.assertIn("Line 1 with tabs and spaces.", cleaned)

    def test_clean_text_recombines_hyphenated_splits(self):
        """Verify broken hyphenated words at line breaks are re-joined."""
        raw = "This is a tele-\ncommunication component."
        cleaned = clean_text(raw)
        self.assertIn("telecommunication component", cleaned)

    def test_clean_text_removes_unprintable_chars(self):
        """Verify non-printable control characters are removed."""
        raw = "Secure\x00Device\x08Configuration\x0cReport"
        cleaned = clean_text(raw)
        self.assertEqual(cleaned, "SecureDeviceConfigurationReport")

    def test_remove_repetitive_headers_footers(self):
        """Verify repeated header boilerplate is removed across pages."""
        pages = [
            {"page_number": 1, "text": "CONFIDENTIAL // TECHNICAL MANUAL\nContent of page 1\nPage 1 of 3"},
            {"page_number": 2, "text": "CONFIDENTIAL // TECHNICAL MANUAL\nContent of page 2\nPage 2 of 3"},
            {"page_number": 3, "text": "CONFIDENTIAL // TECHNICAL MANUAL\nContent of page 3\nPage 3 of 3"},
        ]
        cleaned = remove_repetitive_headers_footers(pages, threshold_ratio=0.7)
        for p in cleaned:
            self.assertNotIn("CONFIDENTIAL // TECHNICAL MANUAL", p["text"])
            self.assertIn(f"Content of page {p['page_number']}", p["text"])


if __name__ == "__main__":
    unittest.main()
