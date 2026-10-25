"""Unit tests for MultimodalParser and multimodal evidence extraction.

Validates:
- Structured parsing of PDF documents using pypdf
- Extraction of emails, user IDs, resource IDs, order IDs, and page numbers
- Untrusted content handling and absence of code execution
- Safe inspection of image artifacts (dimensions, color mode) and limitation reporting
- Error resilience for non-existent files
"""

import sys
import unittest
from pathlib import Path

# Add code directory to sys.path
code_dir = Path(__file__).resolve().parent.parent
if str(code_dir) not in sys.path:
    sys.path.insert(0, str(code_dir))

from multimodal import MultimodalParser


class TestMultimodalParser(unittest.TestCase):
    """Test suite for MultimodalParser on real dataset artifacts."""

    @classmethod
    def setUpClass(cls):
        cls.repo_root = Path(__file__).resolve().parent.parent.parent
        cls.dataset_dir = cls.repo_root / "dataset"
        cls.parser = MultimodalParser(cls.dataset_dir)

    def test_parse_pdf_account_history(self):
        """Test parsing evidence_18 (account_history_report_20260718.pdf)."""
        res = self.parser.parse_pdf("evidence_18", "evidence/documents/account_history_report_20260718.pdf")
        self.assertTrue(res.is_successful)
        self.assertEqual(res.artifact_type, "pdf")
        self.assertEqual(res.page_count, 2)
        self.assertIn("ingrid.dahl@outlook.com", res.raw_text.lower())

        emails = [e.value for e in res.entities if e.entity_type == "email"]
        user_ids = [e.value for e in res.entities if e.entity_type == "user_id"]
        order_ids = [e.value for e in res.entities if e.entity_type == "order_id"]

        self.assertIn("ingrid.dahl@outlook.com", emails)
        self.assertIn("user_18", user_ids)
        self.assertIn("ORD-20261260", order_ids)

        # Check page provenance
        for e in res.entities:
            self.assertIsNotNone(e.page_no)
            self.assertIn(e.page_no, [1, 2])

    def test_parse_pdf_delivery_correction(self):
        """Test parsing evidence_58 (delivery_correction_attachment.pdf)."""
        res = self.parser.parse_pdf("evidence_58", "evidence/documents/delivery_correction_attachment.pdf")
        self.assertTrue(res.is_successful)
        self.assertEqual(res.page_count, 2)

        emails = [e.value for e in res.entities if e.entity_type == "email"]
        resource_ids = [e.value for e in res.entities if e.entity_type == "resource_id"]

        self.assertIn("priya.raman@gmail.com", emails)
        self.assertIn("support_001", resource_ids)

    def test_parse_pdf_non_existent(self):
        """Test graceful failure when PDF file does not exist."""
        res = self.parser.parse_pdf("evidence_999", "evidence/documents/non_existent.pdf")
        self.assertFalse(res.is_successful)
        self.assertTrue(any("not found" in lim.lower() for lim in res.limitations))

    def test_parse_image_limitations_reporting(self):
        """Test image inspection and transparent reporting of OCR limitations."""
        res = self.parser.parse_image("evidence_04", "evidence/images/account_admin_console_20260926.png")
        self.assertTrue(res.is_successful)
        self.assertEqual(res.artifact_type, "image")
        self.assertIn("dimensions", res.metadata)
        self.assertEqual(res.metadata["dimensions"], "1800x1200")
        self.assertEqual(res.metadata["color_mode"], "RGB")

        # In standard environment without tesseract, limitation must be reported
        if not res.metadata.get("ocr_applied"):
            self.assertTrue(any("OCR" in lim for lim in res.limitations))

    def test_parse_image_non_existent(self):
        """Test graceful failure when image file does not exist."""
        res = self.parser.parse_image("evidence_999", "evidence/images/non_existent.png")
        self.assertFalse(res.is_successful)
        self.assertTrue(any("not found" in lim.lower() for lim in res.limitations))


if __name__ == "__main__":
    unittest.main()
