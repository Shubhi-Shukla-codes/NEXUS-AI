"""
NEXUS Multimodal & Structured Table Unit Tests
Validates table extraction, Markdown/JSON table structuring, diagram extraction,
scanned page detection, and multimodal media persistence.
"""

import sys
import unittest
import tempfile
import fitz
from pathlib import Path
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.storage.db import init_database
from backend.security.auth import register_user
from backend.services.document_service import upload_document
from backend.ingestion.table_parser import (
    format_table_as_markdown,
    format_table_as_json_records,
    extract_tables_from_pdf_page,
    save_table_asset
)
from backend.ingestion.multimodal import (
    extract_images_from_pdf_page,
    is_scanned_page,
    list_document_media,
    FallbackVisualDescriptor
)


class TestMultimodalExtraction(unittest.TestCase):
    """Test suite for multimodal visual assets and tabular structuring."""

    def setUp(self):
        """Create isolated temporary database and media directory."""
        self.temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db_path = Path(self.temp_dir.name) / "test_multimodal.db"
        self.vault_path = Path(self.temp_dir.name) / "vault"
        self.media_path = Path(self.temp_dir.name) / "media"
        init_database(custom_path=self.db_path)

        self.user = register_user(
            username="multimodal_operator",
            password="Password@123",
            role="administrator",
            custom_path=self.db_path
        )

    def tearDown(self):
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_format_table_as_markdown(self):
        """Verify 2D matrix converts into standard GitHub Flavored Markdown table."""
        headers = ["Component", "Part Number", "Tolerance"]
        rows = [
            ["Alternator", "ALT-4500", "+/- 0.5%"],
            ["Governor", "GOV-12", "+/- 1.0%"],
        ]
        md = format_table_as_markdown(headers, rows)

        self.assertIn("| Component | Part Number | Tolerance |", md)
        self.assertIn("| --- | --- | --- |", md)
        self.assertIn("| Alternator | ALT-4500 | +/- 0.5% |", md)
        self.assertIn("| Governor | GOV-12 | +/- 1.0% |", md)

    def test_format_table_as_json_records(self):
        """Verify tabular matrix converts into key-value JSON records."""
        headers = ["Asset", "Rating"]
        rows = [
            ["Turbine A", "500 kW"],
            ["Turbine B", "750 kW"],
        ]
        records = format_table_as_json_records(headers, rows)

        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["Asset"], "Turbine A")
        self.assertEqual(records[0]["Rating"], "500 kW")
        self.assertEqual(records[1]["Asset"], "Turbine B")

    def test_save_and_list_table_assets(self):
        """Verify structured table records persist in 'document_media' table."""
        doc = upload_document(
            file_bytes=b"Sample document text",
            filename="spec_sheet.txt",
            domain="technical_maintenance",
            user_id=self.user["id"],
            vault_dir=self.vault_path,
            custom_path=self.db_path
        )

        headers = ["Pin", "Signal", "Voltage"]
        rows = [["1", "VCC", "5.0V"], ["2", "GND", "0.0V"]]

        saved = save_table_asset(
            document_id=doc["id"],
            page_number=1,
            table_index=1,
            headers=headers,
            rows=rows,
            custom_path=self.db_path
        )

        self.assertIsNotNone(saved["id"])
        self.assertEqual(saved["records_count"], 2)

        # Retrieve media
        media_list = list_document_media(doc["id"], media_type="table", custom_path=self.db_path)
        self.assertEqual(len(media_list), 1)
        self.assertEqual(media_list[0]["dimensions"], "2x3")
        self.assertIn("Table #1", media_list[0]["caption"])

    def test_fallback_visual_descriptor(self):
        """Verify synthetic visual asset descriptor calculates dimensions and aspect ratio."""
        # Create small test image
        img = Image.new("RGB", (200, 100), color=(70, 90, 80))
        img_byte_arr = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        img.save(img_byte_arr.name)
        img_byte_arr.close()

        with open(img_byte_arr.name, "rb") as f:
            raw_bytes = f.read()

        desc_engine = FallbackVisualDescriptor()
        desc = desc_engine.extract_text_from_image(raw_bytes)

        self.assertIn("200x100", desc)
        self.assertIn("Landscape", desc)
        self.assertIn("RGB", desc)

        try:
            Path(img_byte_arr.name).unlink()
        except Exception:
            pass

    def test_is_scanned_page_detection(self):
        """Verify accurate identification of scanned pages vs searchable text."""
        # Page with 0 text and 1 diagram -> Scanned/Diagram Page
        self.assertTrue(is_scanned_page(text_content="", embedded_images_count=1))
        # Page with plenty of text and an image -> Standard Text Page with image
        self.assertFalse(is_scanned_page(text_content="This is standard multi-page text content describing component assembly procedures.", embedded_images_count=1))
        # Empty text and 0 images -> Not a scanned image page
        self.assertFalse(is_scanned_page(text_content="", embedded_images_count=0))

    def test_pdf_embedded_image_extraction(self):
        """Verify extraction and persistence of raster diagrams embedded in PDF pages."""
        # 1. Create a PDF document with an embedded image
        pdf_doc = fitz.open()
        page = pdf_doc.new_page()

        # Insert a sample image into the page
        sample_img = Image.new("RGB", (150, 150), color=(100, 120, 140))
        temp_img = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        sample_img.save(temp_img.name)
        temp_img.close()

        rect = fitz.Rect(50, 50, 200, 200)
        page.insert_image(rect, filename=temp_img.name)

        pdf_path = Path(self.temp_dir.name) / "test_doc.pdf"
        pdf_doc.save(str(pdf_path))
        pdf_doc.close()

        # 2. Upload document to repository
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        doc_record = upload_document(
            file_bytes=pdf_bytes,
            filename="schematic_doc.pdf",
            domain="technical_maintenance",
            user_id=self.user["id"],
            vault_dir=self.vault_path,
            custom_path=self.db_path
        )

        # 3. Extract images from page
        reopened = fitz.open(str(pdf_path))
        extracted = extract_images_from_pdf_page(
            doc=reopened,
            page=reopened[0],
            document_id=doc_record["id"],
            page_number=1,
            media_dir=self.media_path,
            custom_path=self.db_path
        )
        reopened.close()

        self.assertGreaterEqual(len(extracted), 1)
        self.assertEqual(extracted[0]["width"], 150)
        self.assertEqual(extracted[0]["height"], 150)
        self.assertTrue(Path(extracted[0]["file_path"]).is_file())

        # Cleanup temp files
        try:
            Path(temp_img.name).unlink()
        except Exception:
            pass


if __name__ == "__main__":
    unittest.main()
