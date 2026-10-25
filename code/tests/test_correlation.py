"""Unit tests for Multi-System Evidence Correlation and Advanced Reasoning.

Validates:
- Multi-system correlation across SQL databases, JSON snapshots, and log streams
- System ID canonicalization across replica nodes and service tiers
- Conflict detection between reported status and residual personal data
- Secondary identifier index categorization (Rule 2)
- Preservation of evidence provenance and evidence_ids across correlated systems
- Temporal filtering respecting audit_at across asynchronous log exports
"""

import sys
import unittest
from pathlib import Path

# Add code directory to sys.path
code_dir = Path(__file__).resolve().parent.parent
if str(code_dir) not in sys.path:
    sys.path.insert(0, str(code_dir))

from data_loader import DatasetLoader
from decision import DecisionEngine
from discovery import DiscoveredResource, ResourceDiscoverer
from evidence import EvidenceIndex
from identity import IdentityResolver
from models import DeletionRequest, DeletionStatus, Operation, Phase, State
from policy import PolicyEngine
from sql_engine import SQLEngine
from steps import StepBuilder


class TestMultiSystemCorrelation(unittest.TestCase):
    """Test suite for multi-system correlation engine."""

    @classmethod
    def setUpClass(cls):
        cls.repo_root = Path(__file__).resolve().parent.parent.parent
        cls.dataset_dir = cls.repo_root / "dataset"
        cls.loader = DatasetLoader(cls.dataset_dir)

        cls.identities = cls.loader.load_user_identities()
        cls.audit_log = cls.loader.load_user_audit_log()
        cls.manifest = cls.loader.load_evidence_manifest()
        cls.activities = cls.loader.load_system_activity()
        cls.rules = cls.loader.load_deletion_rules()

        cls.resolver = IdentityResolver(cls.identities, cls.audit_log)
        cls.sql_engine = SQLEngine(cls.dataset_dir, cls.manifest)
        cls.evidence_index = EvidenceIndex(cls.dataset_dir, cls.manifest, cls.sql_engine)
        cls.discoverer = ResourceDiscoverer(
            cls.dataset_dir, cls.manifest, cls.sql_engine, cls.evidence_index, cls.activities
        )
        cls.policy = PolicyEngine(cls.rules)
        cls.decision_engine = DecisionEngine(cls.policy)
        cls.step_builder = StepBuilder()

    def test_conflicting_evidence_detection(self):
        """Test that reported status COMPLETE is rejected when a replica retains residual PII.

        Case: case_05 (Leila Haddad) was reported COMPLETE, but failover replica
        in account_service still contains account_005 in state PRESENT.
        Audit engine must detect the conflict and decide INCOMPLETE.
        """
        sample_requests = self.loader.load_deletion_requests("sample_deletion_requests.csv")
        req_05 = next(r for r in sample_requests if r.case_id == "case_05")
        self.assertEqual(req_05.reported_status, "COMPLETE")

        profile_05 = self.resolver.resolve_request(req_05)
        discovered = self.discoverer.discover_for_request(req_05, profile_05)

        # Confirm account_005 was found in account_service
        account_res = next((r for r in discovered if r.resource_id == "account_005"), None)
        self.assertIsNotNone(account_res)
        self.assertEqual(account_res.system_id, "account_service")
        self.assertEqual(account_res.observed_state, State.PRESENT)

        # Evaluate decision
        decision = self.decision_engine.evaluate(req_05, profile_05, discovered)
        self.assertEqual(decision.deletion_status, DeletionStatus.INCOMPLETE)
        self.assertTrue(any(v.resource_id == "account_005" for v in decision.violations))

    def test_canonical_system_id_resolution(self):
        """Test canonicalization of replica names into core service identifiers."""
        discoverer = self.discoverer
        self.assertEqual(discoverer._canonicalize_system_id("support_replica"), "support_platform")
        self.assertEqual(
            discoverer._canonicalize_system_id("customer_profiles_failover_replica"),
            "account_service",
        )
        self.assertEqual(
            discoverer._canonicalize_system_id("analytics_read_replica"),
            "analytics_platform",
        )
        self.assertEqual(discoverer._canonicalize_system_id("unknown_service"), "unknown_service")

    def test_secondary_identifier_categorization(self):
        """Test Rule 2 secondary identifier categorization for contact lookups and legacy indices."""
        res = DiscoveredResource(
            resource_id="contact_query_123",
            system_id="support_platform",
            observed_state=State.PRESENT,
            evidence_id="evidence_06",
            evidence_type="log",
            captured_at="2026-09-16T08:52:49Z",
        )
        eval_support = self.policy.evaluate_resource(res)
        # Should match Rule 2 SECONDARY_IDENTIFIER -> DELETE -> VIOLATION
        self.assertTrue(eval_support.is_violation)
        self.assertEqual(eval_support.rule_id, "rule_02")
        self.assertEqual(eval_support.remediation_op, Operation.DELETE_RECORD)
        self.assertEqual(eval_support.finding_op, Operation.REPORT_REMAINING_RECORD)

    def test_source_provenance_preservation(self):
        """Test that every discovered resource retains valid evidence provenance and file ID."""
        sample_requests = self.loader.load_deletion_requests("sample_deletion_requests.csv")
        req_01 = next(r for r in sample_requests if r.case_id == "case_01")
        profile_01 = self.resolver.resolve_request(req_01)
        discovered = self.discoverer.discover_for_request(req_01, profile_01)

        self.assertTrue(len(discovered) > 0)
        for res in discovered:
            self.assertTrue(res.resource_id != "")
            self.assertTrue(res.system_id != "")
            self.assertTrue(res.evidence_id.startswith("evidence_"))
            self.assertTrue(res.source_provenance != "")

    def test_temporal_cutoff_across_async_logs(self):
        """Test that asynchronous logs respect audit_at cutoff even when log files were archived later."""
        # Case 09 has audit_at="2026-09-16T09:00:00Z"
        # evidence_06 was archived 2026-09-18, but contains log events from 2026-09-16T08:52:49Z
        sample_requests = self.loader.load_deletion_requests("sample_deletion_requests.csv")
        req_09 = next(r for r in sample_requests if r.case_id == "case_09")
        profile_09 = self.resolver.resolve_request(req_09)
        discovered = self.discoverer.discover_for_request(req_09, profile_09)

        # Events before 09:00:00Z on Sept 16 must be found
        found_before_cutoff = any(
            r.evidence_id == "evidence_06"
            for r in discovered
        )
        self.assertTrue(found_before_cutoff)
        for r in discovered:
            event_time = r.details.get("event_time")
            if event_time:
                self.assertLessEqual(event_time, req_09.audit_at)


if __name__ == "__main__":
    unittest.main()
