"""Unit tests for Phase 2 Step Builder."""

from __future__ import annotations

import unittest
from pathlib import Path

from data_loader import DatasetLoader
from decision import DecisionResult
from discovery import DiscoveredResource
from models import DeletionStatus, Operation, Phase, State
from policy import PolicyEngine, PolicyEvaluationResult
from steps import StepBuilder


class TestStepBuilder(unittest.TestCase):
    """Test challenge-compliant step sequence construction and validation."""

    @classmethod
    def setUpClass(cls):
        dataset_dir = Path(__file__).resolve().parent.parent.parent / "dataset"
        loader = DatasetLoader(dataset_dir)
        rules = loader.load_deletion_rules()
        cls.policy = PolicyEngine(rules)
        cls.builder = StepBuilder()

    def test_complete_case_has_only_verification_with_evidence(self):
        """COMPLETE case contains only VERIFICATION steps citing evidence_id."""
        res_acc = DiscoveredResource("account_001", "account_service", State.ABSENT, "evidence_54", "sql", "2026-09-01T12:00:00Z")
        res_aud = DiscoveredResource("audit_record_001", "security_service", State.PRESENT, "evidence_94", "log", "2026-09-01T12:00:00Z")

        decision = DecisionResult(
            case_id="case_c1",
            deletion_status=DeletionStatus.COMPLETE,
            evaluations=[],
            violations=[],
            compliant=[
                self.policy.evaluate_resource(res_acc),
                self.policy.evaluate_resource(res_aud),
            ],
            discovered_resources={"account_001": res_acc, "audit_record_001": res_aud},
            rationale="All compliant",
        )

        case_out = self.builder.build_case_output(decision)
        self.assertEqual(case_out.deletion_status, DeletionStatus.COMPLETE)
        self.assertEqual(len(case_out.steps), 2)
        for s in case_out.steps:
            self.assertEqual(s.phase, Phase.VERIFICATION.value)
            self.assertTrue(len(s.evidence_id) > 0)
        self.assertEqual(case_out.steps[0].step_no, 1)
        self.assertEqual(case_out.steps[1].step_no, 2)

    def test_incomplete_case_ordering_and_empty_evidence(self):
        """INCOMPLETE case contains FINDING (with evidence) -> REMEDIATION (empty) -> VERIFICATION (empty)."""
        res_search = DiscoveredResource("search_001", "search_service", State.PRESENT, "evidence_57", "sql", "2026-09-01T12:00:00Z", has_pii=True)
        res_acc = DiscoveredResource("account_006", "account_service", State.ABSENT, "evidence_54", "sql", "2026-09-01T12:00:00Z")

        decision = DecisionResult(
            case_id="case_i1",
            deletion_status=DeletionStatus.INCOMPLETE,
            evaluations=[],
            violations=[self.policy.evaluate_resource(res_search)],
            compliant=[self.policy.evaluate_resource(res_acc)],
            discovered_resources={"search_001": res_search, "account_006": res_acc},
            rationale="Search index entry remaining",
        )

        case_out = self.builder.build_case_output(decision)
        self.assertEqual(case_out.deletion_status, DeletionStatus.INCOMPLETE)
        self.assertEqual(len(case_out.steps), 4)

        # Step 1: Finding
        self.assertEqual(case_out.steps[0].phase, Phase.FINDING.value)
        self.assertEqual(case_out.steps[0].resource_id, "search_001")
        self.assertEqual(case_out.steps[0].evidence_id, "evidence_57")

        # Step 2: Remediation
        self.assertEqual(case_out.steps[1].phase, Phase.REMEDIATION.value)
        self.assertEqual(case_out.steps[1].resource_id, "search_001")
        self.assertEqual(case_out.steps[1].evidence_id, "")

        # Steps 3 & 4: Verifications in canonical order (account_service before search_service)
        self.assertEqual(case_out.steps[2].phase, Phase.VERIFICATION.value)
        self.assertEqual(case_out.steps[2].system_id, "account_service")
        self.assertEqual(case_out.steps[2].resource_id, "account_006")
        self.assertEqual(case_out.steps[2].evidence_id, "")

        self.assertEqual(case_out.steps[3].phase, Phase.VERIFICATION.value)
        self.assertEqual(case_out.steps[3].system_id, "search_service")
        self.assertEqual(case_out.steps[3].resource_id, "search_001")
        self.assertEqual(case_out.steps[3].evidence_id, "")

    def test_not_applicable_case_empty_steps(self):
        """NOT_APPLICABLE case must have empty steps array."""
        decision = DecisionResult(
            case_id="case_na",
            deletion_status=DeletionStatus.NOT_APPLICABLE,
            evaluations=[],
            violations=[],
            compliant=[],
            discovered_resources={},
            rationale="Legal hold",
        )
        case_out = self.builder.build_case_output(decision)
        self.assertEqual(case_out.deletion_status, DeletionStatus.NOT_APPLICABLE)
        self.assertEqual(len(case_out.steps), 0)


if __name__ == "__main__":
    unittest.main()
