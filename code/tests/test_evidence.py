"""Unit tests for evidence.py verifying inverted index search across multiple evidence formats."""

import sys
import unittest
from pathlib import Path

# Ensure code/ is on python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data_loader import DatasetLoader
from evidence import EvidenceIndex
from identity import IdentityResolver
from sql_engine import SQLEngine


class TestEvidenceIndex(unittest.TestCase):
    """Test suite for EvidenceIndex verifying indexing and cross-format queries."""

    @classmethod
    def setUpClass(cls):
        cls.repo_root = Path(__file__).parent.parent.parent
        cls.dataset_dir = cls.repo_root / "dataset"
        loader = DatasetLoader(cls.dataset_dir)
        cls.manifest = loader.load_evidence_manifest()
        identities = loader.load_user_identities()
        audit_log = loader.load_user_audit_log()
        cls.resolver = IdentityResolver(identities, audit_log)
        cls.sql_engine = SQLEngine(cls.dataset_dir, cls.manifest)
        cls.index = EvidenceIndex(cls.dataset_dir, cls.manifest, cls.sql_engine)

    def test_search_known_log_identifier(self):
        """Test finding an identifier that appears in structured resource lookup logs."""
        # eamponsah5039@fastmail.com appears in resource_lookup_trace log
        results = self.index.search_identifiers({"eamponsah5039@fastmail.com"})
        self.assertTrue(len(results) > 0)
        types = {r.evidence_type for r in results}
        self.assertIn("log", types)

        # Check resource_id extracted
        res_ids = {r.resource_id for r in results}
        self.assertIn("analytics_1575", res_ids)

    def test_search_sql_record_through_evidence_index(self):
        """Test finding an SQL record via the unified EvidenceIndex."""
        results = self.index.search_identifiers({"leila.haddad@yahoo.com"})
        self.assertTrue(len(results) > 0)
        types = {r.evidence_type for r in results}
        self.assertIn("sql", types)
        res_ids = {r.resource_id for r in results}
        self.assertIn("account_005", res_ids)

    def test_search_resource_id_index(self):
        """Test finding occurrences directly by resource_id."""
        results = self.index.search_resource_id("analytics_1575")
        self.assertTrue(len(results) > 0)
        self.assertEqual(results[0].resource_id, "analytics_1575")

    def test_temporal_cutoff_in_evidence_index(self):
        """Test that evidence after cutoff_time is excluded."""
        # Query with cutoff in 2025 (before any 2026 evidence was captured)
        results = self.index.search_identifiers(
            {"eamponsah5039@fastmail.com"},
            cutoff_time="2025-01-01T00:00:00Z"
        )
        self.assertEqual(len(results), 0)


if __name__ == "__main__":
    unittest.main()
