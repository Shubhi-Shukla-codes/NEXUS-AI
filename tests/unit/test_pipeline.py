"""
NEXUS Document Ingestion Pipeline Unit Tests
Validates multi-format extraction (PDF, DOCX, XLSX, CSV, JSON, TXT)
and relational chunk synchronization.
"""

import sys
import unittest
import tempfile
import json
import csv
from pathlib import Path
import fitz
import docx
import openpyxl

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.storage.db import init_database
from backend.security.auth import register_user
from backend.services.document_service import upload_document
from backend.ingestion.pipeline import process_document, get_document_chunks


class TestIngestionPipeline(unittest.TestCase):
    """Test suite for document parsers and chunking pipeline."""

    def setUp(self):
        """Create isolated temporary database and vault directory."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_pipeline.db"
        self.vault_path = Path(self.temp_dir.name) / "vault"
        init_database(custom_path=self.db_path)

        # Seed operator
        self.operator = register_user(
            username="pipeline_op",
            password="Password@123",
            role="instructor",
            custom_path=self.db_path
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_pdf_extraction_pipeline(self):
        """Verify PDF page text and table extraction through the ingestion pipeline."""
        # Create synthetic PDF in memory
        doc = fitz.open()
        p1 = doc.new_page()
        p1.insert_text((50, 72), "NEXUS Technical Field Manual - Page 1\nSection 1.1 Maintenance Procedures.")
        p2 = doc.new_page()
        p2.insert_text((50, 72), "NEXUS Technical Field Manual - Page 2\nSection 1.2 Component Troubleshooting.")
        pdf_bytes = doc.write()
        doc.close()

        # Ingest
        up = upload_document(
            file_bytes=pdf_bytes,
            filename="field_manual.pdf",
            domain="technical_maintenance",
            user_id=self.operator["id"],
            username="pipeline_op",
            vault_dir=self.vault_path,
            custom_path=self.db_path
        )

        # Process pipeline
        res = process_document(up["id"], custom_path=self.db_path)
        self.assertEqual(res["pages_count"], 2)
        self.assertGreaterEqual(res["chunks_count"], 2)

        # Verify chunks in SQLite
        chunks = get_document_chunks(up["id"], custom_path=self.db_path)
        self.assertEqual(len(chunks), res["chunks_count"])
        page_numbers = {c["page_number"] for c in chunks}
        self.assertEqual(page_numbers, {1, 2})

    def test_docx_extraction_pipeline(self):
        """Verify Word DOCX heading and table extraction."""
        # Create synthetic DOCX
        doc = docx.Document()
        doc.add_heading("Emergency Response Directive", level=1)
        doc.add_paragraph("First response team must verify situational perimeter.")
        doc.add_heading("Safety Checklist", level=2)
        table = doc.add_table(rows=2, cols=2)
        table.cell(0, 0).text = "Item"
        table.cell(0, 1).text = "Status"
        table.cell(1, 0).text = "Generator"
        table.cell(1, 1).text = "Operational"

        docx_path = Path(self.temp_dir.name) / "directive.docx"
        doc.save(str(docx_path))
        with open(docx_path, "rb") as f:
            docx_bytes = f.read()

        up = upload_document(
            file_bytes=docx_bytes,
            filename="directive.docx",
            domain="safety_emergency",
            user_id=self.operator["id"],
            username="pipeline_op",
            vault_dir=self.vault_path,
            custom_path=self.db_path
        )

        res = process_document(up["id"], custom_path=self.db_path)
        self.assertGreaterEqual(res["chunks_count"], 1)

        chunks = get_document_chunks(up["id"], custom_path=self.db_path)
        combined = " ".join(c["content"] for c in chunks)
        self.assertIn("Emergency Response Directive", combined)
        self.assertIn("Generator", combined)

    def test_xlsx_extraction_pipeline(self):
        """Verify Excel tabular extraction."""
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "EquipmentInventory"
        ws.append(["ComponentID", "Name", "Location", "Status"])
        ws.append(["C-101", "Radio Transceiver", "Sector 4", "Active"])
        ws.append(["C-102", "Battery Module", "Sector 2", "Standby"])

        xlsx_path = Path(self.temp_dir.name) / "inventory.xlsx"
        wb.save(str(xlsx_path))
        with open(xlsx_path, "rb") as f:
            xlsx_bytes = f.read()

        up = upload_document(
            file_bytes=xlsx_bytes,
            filename="inventory.xlsx",
            domain="technical_maintenance",
            user_id=self.operator["id"],
            username="pipeline_op",
            vault_dir=self.vault_path,
            custom_path=self.db_path
        )

        res = process_document(up["id"], custom_path=self.db_path)
        self.assertEqual(res["pages_count"], 1)
        self.assertGreaterEqual(res["chunks_count"], 1)

        chunks = get_document_chunks(up["id"], custom_path=self.db_path)
        self.assertIn("Radio Transceiver", chunks[0]["content"])

    def test_csv_and_json_extraction_pipeline(self):
        """Verify CSV and JSON file extraction."""
        # 1. CSV
        csv_data = "Hospital,Beds,EmergencyContact\nGeneral Hospital,250,+1-555-0199\nCentral Clinic,60,+1-555-0144\n"
        up_csv = upload_document(
            file_bytes=csv_data.encode("utf-8"),
            filename="hospitals.csv",
            domain="humanitarian_geospatial",
            user_id=self.operator["id"],
            username="pipeline_op",
            vault_dir=self.vault_path,
            custom_path=self.db_path
        )
        res_csv = process_document(up_csv["id"], custom_path=self.db_path)
        self.assertGreaterEqual(res_csv["chunks_count"], 1)

        # 2. JSON
        json_obj = {
            "threat_actor": "DEFENSIVE_MONITORING_BASELINE",
            "indicators": ["192.168.1.10", "suspicious_service.exe"],
            "severity": "HIGH"
        }
        json_bytes = json.dumps(json_obj, indent=2).encode("utf-8")
        up_json = upload_document(
            file_bytes=json_bytes,
            filename="threat_intel.json",
            domain="defensive_cybersecurity",
            user_id=self.operator["id"],
            username="pipeline_op",
            vault_dir=self.vault_path,
            custom_path=self.db_path
        )
        res_json = process_document(up_json["id"], custom_path=self.db_path)
        self.assertGreaterEqual(res_json["chunks_count"], 1)


if __name__ == "__main__":
    unittest.main()
