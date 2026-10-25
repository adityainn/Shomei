"""Unit tests for sql_engine.py verifying SQLite execution of SQL evidence files."""

import sys
import unittest
from pathlib import Path

# Ensure code/ is on python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data_loader import DatasetLoader
from identity import IdentityResolver
from sql_engine import SQLEngine


class TestSQLEngine(unittest.TestCase):
    """Test suite for SQLEngine verifying loading and parameterized queries on 24 SQL files."""

    @classmethod
    def setUpClass(cls):
        cls.repo_root = Path(__file__).parent.parent.parent
        cls.dataset_dir = cls.repo_root / "dataset"
        loader = DatasetLoader(cls.dataset_dir)
        cls.manifest = loader.load_evidence_manifest()
        identities = loader.load_user_identities()
        audit_log = loader.load_user_audit_log()
        cls.resolver = IdentityResolver(identities, audit_log)
        cls.engine = SQLEngine(cls.dataset_dir, cls.manifest)

    def test_all_24_sql_databases_loaded(self):
        """Verify all 24 SQL databases were loaded into in-memory SQLite connections."""
        self.assertEqual(len(self.engine.loaded_databases), 24)

    def test_find_records_by_identifier(self):
        """Test finding a known record (Leila Haddad / account_005) in failover replica."""
        profile = self.resolver.resolve_email("leila.haddad@yahoo.com")
        self.assertIsNotNone(profile)

        # Leila Haddad is in customer_accounts_failover_replica (evidence_54)
        matches = self.engine.find_records_for_profile(profile)
        self.assertTrue(len(matches) > 0)

        # Check that account_005 is found
        res_ids = {m.resource_id for m in matches}
        self.assertIn("account_005", res_ids)

        # Verify evidence_id points to evidence_54
        ev_ids = {m.file_id for m in matches if m.resource_id == "account_005"}
        self.assertIn("evidence_54", ev_ids)

    def test_temporal_cutoff_filtering(self):
        """Test that evidence captured after cutoff_time is excluded."""
        profile = self.resolver.resolve_email("leila.haddad@yahoo.com")
        self.assertIsNotNone(profile)

        # evidence_54 captured at 2026-09-02T23:00:00Z
        # If cutoff is 2026-08-01, evidence_54 must not appear
        matches_early = self.engine.find_records_for_profile(profile, cutoff_time="2026-08-01T00:00:00Z")
        ev_ids_early = {m.file_id for m in matches_early}
        self.assertNotIn("evidence_54", ev_ids_early)

        # If cutoff is 2026-09-10, evidence_54 must appear
        matches_late = self.engine.find_records_for_profile(profile, cutoff_time="2026-09-10T00:00:00Z")
        ev_ids_late = {m.file_id for m in matches_late}
        self.assertIn("evidence_54", ev_ids_late)


if __name__ == "__main__":
    unittest.main()
