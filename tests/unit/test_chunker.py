"""
NEXUS Structure-Aware Chunker Unit Tests
Validates sliding window splitting, page-boundary tracking, and UUID consistency.
"""

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.ingestion.chunker import (
    generate_chunk_id,
    estimate_token_count,
    split_text_into_chunks,
    chunk_document_pages
)


class TestChunker(unittest.TestCase):
    """Test suite for structure-aware document chunking."""

    def test_generate_chunk_id_deterministic(self):
        """Verify chunk UUIDs are deterministic and consistent."""
        id1 = generate_chunk_id(document_id=42, page_number=3, chunk_index=1)
        id2 = generate_chunk_id(document_id=42, page_number=3, chunk_index=1)
        id3 = generate_chunk_id(document_id=42, page_number=3, chunk_index=2)

        self.assertEqual(id1, id2)
        self.assertNotEqual(id1, id3)
        self.assertEqual(len(id1), 36)  # Standard UUID string length

    def test_split_text_small_content(self):
        """Verify text smaller than chunk_size produces a single chunk."""
        text = "Short equipment note."
        chunks = split_text_into_chunks(text, chunk_size=200, chunk_overlap=30)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0]["content"], text)

    def test_split_text_multi_chunk_with_overlap(self):
        """Verify long text produces multiple chunks respecting size."""
        long_text = ("This is a detailed technical paragraph about turbine power calibration. " * 15).strip()
        chunks = split_text_into_chunks(long_text, chunk_size=250, chunk_overlap=50)

        self.assertGreater(len(chunks), 1)
        for c in chunks:
            self.assertLessEqual(c["char_length"], 350)  # Reasonable bounds around paragraph breaks
            self.assertGreater(c["token_count"], 0)

    def test_chunk_document_pages_boundary_preservation(self):
        """Verify page boundaries are strictly preserved across chunks."""
        pages = [
            {"page_number": 1, "text": "Page one first paragraph.\n\nPage one second paragraph."},
            {"page_number": 2, "text": "Page two standalone procedure."},
        ]
        chunks = chunk_document_pages(document_id=10, pages=pages, chunk_size=100)

        page_1_chunks = [c for c in chunks if c["page_number"] == 1]
        page_2_chunks = [c for c in chunks if c["page_number"] == 2]

        self.assertGreaterEqual(len(page_1_chunks), 1)
        self.assertEqual(len(page_2_chunks), 1)
        self.assertIn("Page two", page_2_chunks[0]["content"])


if __name__ == "__main__":
    unittest.main()
