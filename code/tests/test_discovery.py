"""Unit tests for Phase 2 Resource Discovery."""

from __future__ import annotations

import unittest
from pathlib import Path

from data_loader import DatasetLoader
from discovery import DiscoveredResource, ResourceDiscoverer
from evidence import EvidenceIndex
from identity import IdentityResolver
from models import State
from sql_engine import SQLEngine


class TestResourceDiscovery(unittest.TestCase):
    """Test multi-source resource discovery and temporal cutoff handling."""

    @classmethod
    def setUpClass(cls):
        dataset_dir = Path(__file__).resolve().parent.parent.parent / "dataset"
        cls.loader = DatasetLoader(dataset_dir)
        cls.identities = cls.loader.load_user_identities()
        cls.audit_log = cls.loader.load_user_audit_log()
        cls.resolver = IdentityResolver(cls.identities, cls.audit_log)
        cls.manifest = cls.loader.load_evidence_manifest()
        cls.sql_engine = SQLEngine(dataset_dir, cls.manifest)
        cls.index = EvidenceIndex(dataset_dir, cls.manifest, cls.sql_engine)
        cls.activities = cls.loader.load_system_activity()
        cls.discoverer = ResourceDiscoverer(dataset_dir, cls.manifest, cls.sql_engine, cls.index, cls.activities)
        cls.sample_reqs = cls.loader.load_deletion_requests("sample_deletion_requests.csv")

    def test_discovery_for_case_01(self):
        """Verify discovery finds account_001 in account_service for case_01."""
        req_01 = [r for r in self.sample_reqs if r.case_id == "case_01"][0]
        profile = self.resolver.resolve_request(req_01)
        self.assertIsNotNone(profile)

        discovered = self.discoverer.discover_for_request(req_01, profile)
        res_ids = [d.resource_id for d in discovered]
        self.assertIn("account_001", res_ids)

        acc_res = [d for d in discovered if d.resource_id == "account_001"][0]
        self.assertEqual(acc_res.system_id, "account_service")
        self.assertEqual(acc_res.observed_state, State.ABSENT)
        self.assertEqual(acc_res.evidence_id, "evidence_54")

    def test_discovery_for_case_05_finding(self):
        """Verify discovery detects account_005 still PRESENT in replica for case_05."""
        req_05 = [r for r in self.sample_reqs if r.case_id == "case_05"][0]
        profile = self.resolver.resolve_request(req_05)
        self.assertIsNotNone(profile)

        discovered = self.discoverer.discover_for_request(req_05, profile)
        res_ids = [d.resource_id for d in discovered]
        self.assertIn("account_005", res_ids)

        acc_res = [d for d in discovered if d.resource_id == "account_005"][0]
        self.assertEqual(acc_res.observed_state, State.PRESENT)
        self.assertTrue(acc_res.has_pii)
        self.assertEqual(acc_res.evidence_id, "evidence_54")

    def test_temporal_cutoff_applied(self):
        """Verify resources captured after audit_at are excluded."""
        req_01 = [r for r in self.sample_reqs if r.case_id == "case_01"][0]
        profile = self.resolver.resolve_request(req_01)

        discovered = self.discoverer.discover_for_request(req_01, profile)
        for d in discovered:
            if d.evidence_type in ("sql", "json", "log", "text") and d.captured_at:
                self.assertLessEqual(d.captured_at, req_01.audit_at)


if __name__ == "__main__":
    unittest.main()
