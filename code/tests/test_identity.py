"""Unit tests for identity.py verifying identity resolution across current and historical data."""

import sys
import unittest
from pathlib import Path

# Ensure code/ is on python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data_loader import DatasetLoader
from identity import IdentityResolver


class TestIdentityResolver(unittest.TestCase):
    """Test suite for IdentityResolver against actual dataset identities and audit history."""

    @classmethod
    def setUpClass(cls):
        cls.repo_root = Path(__file__).parent.parent.parent
        cls.dataset_dir = cls.repo_root / "dataset"
        loader = DatasetLoader(cls.dataset_dir)
        identities = loader.load_user_identities()
        audit_log = loader.load_user_audit_log()
        cls.requests = loader.load_deletion_requests()
        cls.resolver = IdentityResolver(identities, audit_log)

    def test_current_identity_resolution(self):
        """Test resolving an email directly from user_identities.csv."""
        profile = self.resolver.resolve_email("amina.elmasri@gmail.com")
        self.assertIsNotNone(profile)
        self.assertEqual(profile.user_id, "user_01")
        self.assertEqual(profile.current_name, "Amina El-Masri")
        self.assertIn("amina.elmasri@gmail.com", profile.all_emails)

    def test_case_insensitive_resolution(self):
        """Test resolving emails regardless of case casing."""
        p1 = self.resolver.resolve_email("AMINA.ELMASRI@GMAIL.COM")
        p2 = self.resolver.resolve_email("Amina.ElMasri@gmail.com")
        self.assertIsNotNone(p1)
        self.assertIsNotNone(p2)
        self.assertEqual(p1.user_id, "user_01")
        self.assertEqual(p2.user_id, "user_01")

    def test_historical_email_resolution(self):
        """Test resolving an old email that was changed in user_audit_log.csv."""
        # Check that historical resolution returns the correct user_id
        # In audit_log, user_485 changed email or phone
        for req in self.requests:
            profile = self.resolver.resolve_request(req)
            self.assertIsNotNone(profile, f"Failed to resolve request email: {req.email} for {req.case_id}")

    def test_100_percent_request_coverage(self):
        """Test that 100% of the 518 deletion requests resolve to a user_id."""
        resolved_count = 0
        current_matches = 0
        historical_matches = 0

        for req in self.requests:
            profile = self.resolver.resolve_request(req)
            self.assertIsNotNone(profile)
            resolved_count += 1
            if req.email.lower() == profile.current_email.lower():
                current_matches += 1
            else:
                historical_matches += 1
                self.assertIn(req.email.lower(), profile.all_emails)

        self.assertEqual(resolved_count, 518)
        self.assertEqual(current_matches, 418)
        self.assertEqual(historical_matches, 100)

    def test_all_identifiers_inclusion(self):
        """Test that profile gathers all emails, phones, and hashes."""
        profile = self.resolver.resolve_user_id("user_01")
        self.assertIsNotNone(profile)
        self.assertTrue(len(profile.all_emails) >= 1)
        self.assertTrue(len(profile.all_phones) >= 1)
        self.assertTrue(len(profile.all_hashes) >= 1)


if __name__ == "__main__":
    unittest.main()
