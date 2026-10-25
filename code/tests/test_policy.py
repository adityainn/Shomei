"""Unit tests for Phase 2 Policy Engine."""

from __future__ import annotations

import unittest
from pathlib import Path

from data_loader import DatasetLoader
from discovery import DiscoveredResource
from models import Operation, State
from policy import PolicyEngine


class TestPolicyEngine(unittest.TestCase):
    """Test policy rule mapping and evaluation logic."""

    @classmethod
    def setUpClass(cls):
        dataset_dir = Path(__file__).resolve().parent.parent.parent / "dataset"
        loader = DatasetLoader(dataset_dir)
        cls.rules = loader.load_deletion_rules()
        cls.policy = PolicyEngine(cls.rules)

    def test_rules_loaded(self):
        """Verify all 15 deletion rules are loaded."""
        self.assertEqual(len(self.rules), 15)

    def test_user_profile_violation_and_compliance(self):
        """Rule 1: USER_PROFILE must be DELETE (ABSENT)."""
        res_present = DiscoveredResource(
            resource_id="account_101",
            system_id="account_service",
            observed_state=State.PRESENT,
            evidence_id="evidence_54",
            evidence_type="sql",
            captured_at="2026-09-01T12:00:00Z",
            has_pii=True,
        )
        eval_present = self.policy.evaluate_resource(res_present)
        self.assertTrue(eval_present.is_violation)
        self.assertEqual(eval_present.finding_op, Operation.REPORT_REMAINING_RECORD)
        self.assertEqual(eval_present.remediation_op, Operation.DELETE_RECORD)
        self.assertEqual(eval_present.verification_op, Operation.VERIFY_RECORD_ABSENT)
        self.assertEqual(eval_present.expected_state, State.ABSENT)

        res_absent = DiscoveredResource(
            resource_id="account_101",
            system_id="account_service",
            observed_state=State.ABSENT,
            evidence_id="evidence_54",
            evidence_type="sql",
            captured_at="2026-09-01T12:00:00Z",
            has_pii=False,
        )
        eval_absent = self.policy.evaluate_resource(res_absent)
        self.assertTrue(eval_absent.is_compliant)
        self.assertFalse(eval_absent.is_violation)
        self.assertIsNone(eval_absent.finding_op)

    def test_support_message_redact(self):
        """Rule 5: SUPPORT_MESSAGE must be REDACT."""
        res_pii = DiscoveredResource(
            resource_id="support_202",
            system_id="support_platform",
            observed_state=State.PRESENT,
            evidence_id="evidence_61",
            evidence_type="log",
            captured_at="2026-09-01T12:00:00Z",
            has_pii=True,
        )
        eval_pii = self.policy.evaluate_resource(res_pii)
        self.assertTrue(eval_pii.is_violation)
        self.assertEqual(eval_pii.finding_op, Operation.REPORT_EXPOSED_PII)
        self.assertEqual(eval_pii.remediation_op, Operation.REDACT_RECORD)
        self.assertEqual(eval_pii.verification_op, Operation.VERIFY_RECORD_REDACTED)

        res_redacted = DiscoveredResource(
            resource_id="support_202",
            system_id="support_platform",
            observed_state=State.REDACTED,
            evidence_id="evidence_92",
            evidence_type="json",
            captured_at="2026-09-01T12:00:00Z",
            has_pii=False,
        )
        eval_redacted = self.policy.evaluate_resource(res_redacted)
        self.assertTrue(eval_redacted.is_compliant)
        self.assertEqual(eval_redacted.verification_op, Operation.VERIFY_RECORD_REDACTED)

    def test_analytics_profile_anonymize(self):
        """Rule 7: ANALYTICS_PROFILE must be ANONYMIZE."""
        res_pii = DiscoveredResource(
            resource_id="analytics_303",
            system_id="analytics_platform",
            observed_state=State.PRESENT,
            evidence_id="evidence_92",
            evidence_type="json",
            captured_at="2026-09-01T12:00:00Z",
            has_pii=True,
        )
        eval_pii = self.policy.evaluate_resource(res_pii)
        self.assertTrue(eval_pii.is_violation)
        self.assertEqual(eval_pii.finding_op, Operation.REPORT_EXPOSED_PII)
        self.assertEqual(eval_pii.remediation_op, Operation.ANONYMIZE_RECORD)
        self.assertEqual(eval_pii.verification_op, Operation.VERIFY_RECORD_ANONYMIZED)

    def test_security_audit_log_mandatory_retention(self):
        """Rule 12: SECURITY_AUDIT_LOG must be RETAINED in PRESENT state."""
        res_audit = DiscoveredResource(
            resource_id="audit_record_404",
            system_id="security_service",
            observed_state=State.PRESENT,
            evidence_id="evidence_94",
            evidence_type="log",
            captured_at="2026-09-01T12:00:00Z",
            has_pii=False,
        )
        eval_audit = self.policy.evaluate_resource(res_audit)
        self.assertTrue(eval_audit.is_compliant)
        self.assertFalse(eval_audit.is_violation)
        self.assertEqual(eval_audit.verification_op, Operation.VERIFY_RECORD_PRESENT)
        self.assertEqual(eval_audit.expected_state, State.PRESENT)

    def test_backup_archive_restore_blocked(self):
        """Rule 14: BACKUP_ARCHIVE must have restore blocked."""
        res_active = DiscoveredResource(
            resource_id="backup_505",
            system_id="backup_service",
            observed_state=State.ACTIVE,
            evidence_id="evidence_93",
            evidence_type="sql",
            captured_at="2026-09-01T12:00:00Z",
        )
        eval_active = self.policy.evaluate_resource(res_active)
        self.assertTrue(eval_active.is_violation)
        self.assertEqual(eval_active.finding_op, Operation.REPORT_RESTORE_RISK)
        self.assertEqual(eval_active.remediation_op, Operation.BLOCK_RESTORE)
        self.assertEqual(eval_active.verification_op, Operation.VERIFY_RESTORE_BLOCKED)

    def test_data_flow_disable(self):
        """Integration connectors must be DISABLED."""
        res_flow = DiscoveredResource(
            resource_id="data_flow_606",
            system_id="integration_service",
            observed_state=State.ACTIVE,
            evidence_id="evidence_01",
            evidence_type="log",
            captured_at="2026-09-01T12:00:00Z",
        )
        eval_flow = self.policy.evaluate_resource(res_flow)
        self.assertTrue(eval_flow.is_violation)
        self.assertEqual(eval_flow.finding_op, Operation.REPORT_ACTIVE_DATA_FLOW)
        self.assertEqual(eval_flow.remediation_op, Operation.DISABLE_DATA_FLOW)
        self.assertEqual(eval_flow.verification_op, Operation.VERIFY_DATA_FLOW_DISABLED)


if __name__ == "__main__":
    unittest.main()
