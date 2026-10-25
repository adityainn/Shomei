"""Unit tests for data_loader.py verifying dataset file ingestion and schema validation."""

import sys
import unittest
from pathlib import Path

# Ensure code/ is on python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data_loader import DatasetLoader
from models import DeletionStatus


class TestDataLoader(unittest.TestCase):
    """Test suite for DatasetLoader verifying CSV headers, row counts, and types."""

    @classmethod
    def setUpClass(cls):
        # Resolve dataset directory relative to repository root
        cls.repo_root = Path(__file__).parent.parent.parent
        cls.dataset_dir = cls.repo_root / "dataset"
        cls.loader = DatasetLoader(cls.dataset_dir)

    def test_load_deletion_requests(self):
        """Verify deletion_requests.csv loads exactly 518 cases with all 7 columns."""
        requests = self.loader.load_deletion_requests()
        self.assertEqual(len(requests), 518)
        first = requests[0]
        self.assertTrue(first.case_id.startswith("case_"))
        self.assertIn("@", first.email)
        self.assertTrue(first.requested_at)
        self.assertIn(first.reported_status, {"COMPLETE", "PARTIALLY_COMPLETE", "NOT_STARTED"})
        self.assertTrue(first.audit_at)
        self.assertTrue(first.request_text)

    def test_load_user_identities(self):
        """Verify user_identities.csv loads exactly 850 users."""
        identities = self.loader.load_user_identities()
        self.assertEqual(len(identities), 850)
        first = identities[0]
        self.assertTrue(first.user_id.startswith("user_"))
        self.assertTrue(first.name)
        self.assertIn("@", first.email)
        self.assertTrue(first.phone)
        self.assertEqual(len(first.email_hash), 64)  # SHA-256 hash length

    def test_load_user_audit_log(self):
        """Verify user_audit_log.csv loads exactly 306 change events."""
        audit = self.loader.load_user_audit_log()
        self.assertEqual(len(audit), 306)
        first = audit[0]
        self.assertTrue(first.audit_id.startswith("audit_"))
        self.assertTrue(first.user_id.startswith("user_"))
        self.assertIn(first.field_name, {"email", "phone", "email_hash"})

    def test_load_system_activity(self):
        """Verify system_activity.csv loads exactly 4011 events."""
        activity = self.loader.load_system_activity()
        self.assertEqual(len(activity), 4011)
        first = activity[0]
        self.assertTrue(first.activity_id.startswith("activity_"))
        self.assertTrue(first.event_time)
        self.assertTrue(first.event_type)

    def test_load_deletion_rules(self):
        """Verify deletion_rules.csv loads exactly 15 rules."""
        rules = self.loader.load_deletion_rules()
        self.assertEqual(len(rules), 15)
        actions = {r.required_action for r in rules}
        self.assertEqual(actions, {"DELETE", "REDACT", "ANONYMIZE", "RETAIN"})

    def test_load_evidence_manifest(self):
        """Verify evidence_files.csv loads exactly 94 evidence files."""
        manifest = self.loader.load_evidence_manifest()
        self.assertEqual(len(manifest), 94)
        for meta in manifest:
            self.assertTrue(meta.file_id.startswith("evidence_"))
            self.assertTrue(meta.file_path.startswith("evidence/"))
            # Confirm file exists on disk
            full_path = self.dataset_dir / meta.file_path
            self.assertTrue(full_path.is_file(), f"Manifest file missing on disk: {full_path}")

    def test_load_sample_output(self):
        """Verify sample_output.csv loads and validates all 32 sample cases."""
        sample_outputs = self.loader.load_sample_output()
        self.assertEqual(len(sample_outputs), 32)
        for case_id, case_out in sample_outputs.items():
            self.assertIn(case_out.deletion_status, {DeletionStatus.COMPLETE, DeletionStatus.INCOMPLETE})
            # Every sample case should pass validation
            case_out.validate()


if __name__ == "__main__":
    unittest.main()
