"""Unit tests for output.py verifying serialization and strict compliance validation."""

import csv
import os
import sys
import tempfile
import unittest
from pathlib import Path

# Ensure code/ is on python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data_loader import DatasetLoader
from models import CaseOutput, DeletionStatus, Step
from output import OutputSerializer


class TestOutput(unittest.TestCase):
    """Test suite for OutputSerializer verifying formatting and validation rules."""

    @classmethod
    def setUpClass(cls):
        cls.repo_root = Path(__file__).parent.parent.parent
        cls.dataset_dir = cls.repo_root / "dataset"
        cls.sample_output_path = cls.dataset_dir / "sample_output.csv"

    def test_validate_sample_output(self):
        """Test that the official sample_output.csv passes 32/32 rows without errors."""
        report = OutputSerializer.validate_file(
            self.sample_output_path,
            expected_row_count=32,
        )
        self.assertTrue(report.is_valid, f"Validation failed with errors:\n{report.summary()}")
        self.assertEqual(report.total_rows, 32)
        self.assertEqual(len(report.errors), 0)

    def test_skeleton_generation_and_validation(self):
        """Test generating a skeleton output file and running full validation on it."""
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            case_ids = [f"case_{i:03d}" for i in range(1, 11)]
            OutputSerializer.generate_skeleton(case_ids, tmp_path)

            report = OutputSerializer.validate_file(
                tmp_path,
                expected_case_ids=case_ids,
                expected_row_count=10,
            )
            self.assertTrue(report.is_valid)
            self.assertEqual(report.total_rows, 10)
            self.assertEqual(report.status_counts[DeletionStatus.NOT_APPLICABLE.value], 10)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def test_invalid_header_rejection(self):
        """Test that bad CSV header is caught by validator."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as tmp:
            tmp.write("case_id,wrong_status,wrong_steps\n")
            tmp_path = Path(tmp.name)

        try:
            report = OutputSerializer.validate_file(tmp_path, expected_row_count=0)
            self.assertFalse(report.is_valid)
            self.assertTrue(any("Header mismatch" in e for e in report.errors))
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def test_unsorted_case_ids_rejection(self):
        """Test that rows not sorted by case_id are flagged."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as tmp:
            tmp.write("case_id,deletion_status,steps_json\n")
            tmp.write("case_002,NOT_APPLICABLE,[]\n")
            tmp.write("case_001,NOT_APPLICABLE,[]\n")
            tmp_path = Path(tmp.name)

        try:
            report = OutputSerializer.validate_file(tmp_path, expected_row_count=2)
            self.assertFalse(report.is_valid)
            self.assertTrue(any("not sorted" in e for e in report.errors))
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def test_invalid_phase_order_in_steps_rejection(self):
        """Test that step array with FINDING after REMEDIATION is rejected."""
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as t:
            tmp_path = Path(t.name)

        with open(tmp_path, "w", encoding="utf-8", newline="") as tmp:
            writer = csv.writer(tmp)
            writer.writerow(["case_id", "deletion_status", "steps_json"])
            bad_steps = (
                '[{"step_no":1,"phase":"REMEDIATION","system_id":"account_service","resource_id":"acc_1","operation":"DELETE_RECORD","state":"ABSENT","evidence_id":""},'
                '{"step_no":2,"phase":"FINDING","system_id":"account_service","resource_id":"acc_1","operation":"REPORT_REMAINING_RECORD","state":"PRESENT","evidence_id":"ev_1"}]'
            )
            writer.writerow(["case_001", "INCOMPLETE", bad_steps])

        try:
            report = OutputSerializer.validate_file(tmp_path, expected_row_count=1)
            self.assertFalse(report.is_valid)
            self.assertTrue(any("phase order" in e for e in report.errors))
        finally:
            if tmp_path.exists():
                tmp_path.unlink()


if __name__ == "__main__":
    unittest.main()
