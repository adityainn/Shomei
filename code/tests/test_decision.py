"""Unit tests for Phase 2 Decision Engine."""

from __future__ import annotations

import unittest
from pathlib import Path

from data_loader import DatasetLoader
from decision import DecisionEngine
from discovery import DiscoveredResource
from models import DeletionRequest, DeletionStatus, IdentityProfile, State
from policy import PolicyEngine


class TestDecisionEngine(unittest.TestCase):
    """Test deterministic audit decision evaluation."""

    @classmethod
    def setUpClass(cls):
        dataset_dir = Path(__file__).resolve().parent.parent.parent / "dataset"
        loader = DatasetLoader(dataset_dir)
        rules = loader.load_deletion_rules()
        cls.policy = PolicyEngine(rules)
        cls.engine = DecisionEngine(cls.policy)

    def test_complete_when_all_resources_compliant(self):
        """Case with all compliant resources and verification evidence produces COMPLETE."""
        req = DeletionRequest(
            case_id="case_t1",
            email="user@test.com",
            requested_at="2026-08-01T10:00:00Z",
            reported_status="COMPLETE",
            reported_at="2026-08-03T10:00:00Z",
            audit_at="2026-08-10T10:00:00Z",
            request_text="Delete my data",
        )
        profile = IdentityProfile(user_id="user_t1", current_name="Test", current_email="user@test.com", current_phone="", current_email_hash="")
        resources = [
            DiscoveredResource("account_001", "account_service", State.ABSENT, "evidence_54", "sql", "2026-08-05T10:00:00Z"),
            DiscoveredResource("audit_record_001", "security_service", State.PRESENT, "evidence_94", "log", "2026-08-05T10:00:00Z"),
        ]
        decision = self.engine.evaluate(req, profile, resources)
        self.assertEqual(decision.deletion_status, DeletionStatus.COMPLETE)
        self.assertEqual(len(decision.violations), 0)
        self.assertEqual(len(decision.compliant), 2)

    def test_incomplete_when_violation_present(self):
        """Case with any un-remediated violation produces INCOMPLETE."""
        req = DeletionRequest(
            case_id="case_t2",
            email="user@test.com",
            requested_at="2026-08-01T10:00:00Z",
            reported_status="COMPLETE",
            reported_at="2026-08-03T10:00:00Z",
            audit_at="2026-08-10T10:00:00Z",
            request_text="Delete my data",
        )
        profile = IdentityProfile(user_id="user_t2", current_name="Test", current_email="user@test.com", current_phone="", current_email_hash="")
        resources = [
            DiscoveredResource("account_002", "account_service", State.PRESENT, "evidence_54", "sql", "2026-08-05T10:00:00Z", has_pii=True),
        ]
        decision = self.engine.evaluate(req, profile, resources)
        self.assertEqual(decision.deletion_status, DeletionStatus.INCOMPLETE)
        self.assertEqual(len(decision.violations), 1)

    def test_not_applicable_when_legal_hold_active(self):
        """Case with active legal hold produces NOT_APPLICABLE."""
        req = DeletionRequest(
            case_id="case_t3",
            email="user@test.com",
            requested_at="2026-08-01T10:00:00Z",
            reported_status="COMPLETE",
            reported_at="2026-08-03T10:00:00Z",
            audit_at="2026-08-10T10:00:00Z",
            request_text="Delete my data",
        )
        profile = IdentityProfile(user_id="user_t3", current_name="Test", current_email="user@test.com", current_phone="", current_email_hash="")
        resources = [
            DiscoveredResource("legal_hold_999", "legal_service", State.PRESENT, "evidence_05", "sql", "2026-08-05T10:00:00Z"),
        ]
        decision = self.engine.evaluate(req, profile, resources)
        self.assertEqual(decision.deletion_status, DeletionStatus.NOT_APPLICABLE)

    def test_do_not_infer_complete_from_reported_status_alone(self):
        """Reported status NOT_STARTED without evidence cannot produce COMPLETE."""
        req = DeletionRequest(
            case_id="case_t4",
            email="user@test.com",
            requested_at="2026-08-01T10:00:00Z",
            reported_status="NOT_STARTED",
            reported_at="2026-08-03T10:00:00Z",
            audit_at="2026-08-10T10:00:00Z",
            request_text="Delete my data",
        )
        profile = IdentityProfile(user_id="user_t4", current_name="Test", current_email="user@test.com", current_phone="", current_email_hash="")
        decision = self.engine.evaluate(req, profile, [])
        self.assertEqual(decision.deletion_status, DeletionStatus.INCOMPLETE)


if __name__ == "__main__":
    unittest.main()
