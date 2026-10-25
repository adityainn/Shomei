"""Unit tests for MultilingualIntentClassifier and intent-based routing.

Validates:
- Detection of languages: EN, PT, KO, ES, JA, FR
- Detection of standard erasure requests across all supported languages
- Classification of non-deletion inquiries (case_536 through case_542)
- Safe handling of ambiguous or non-erasure requests routing to NOT_APPLICABLE
"""

import sys
import unittest
from pathlib import Path

# Add code directory to sys.path
code_dir = Path(__file__).resolve().parent.parent
if str(code_dir) not in sys.path:
    sys.path.insert(0, str(code_dir))

from classifier import MultilingualIntentClassifier, RequestIntent
from data_loader import DatasetLoader
from decision import DecisionEngine
from discovery import DiscoveredResource
from models import DeletionRequest, DeletionStatus, IdentityProfile
from policy import PolicyEngine
from steps import StepBuilder


class TestMultilingualIntentClassifier(unittest.TestCase):
    """Test suite for MultilingualIntentClassifier."""

    @classmethod
    def setUpClass(cls):
        cls.repo_root = Path(__file__).resolve().parent.parent.parent
        cls.dataset_dir = cls.repo_root / "dataset"
        cls.loader = DatasetLoader(cls.dataset_dir)
        cls.classifier = MultilingualIntentClassifier()
        rules = cls.loader.load_deletion_rules()
        cls.policy = PolicyEngine(rules)
        cls.decision_engine = DecisionEngine(cls.policy, cls.classifier)
        cls.step_builder = StepBuilder()

    def test_language_detection(self):
        """Test language detection across all 6 challenge languages."""
        samples = [
            ("Please permanently delete my personal data and account.", "en"),
            ("Solicito a exclusão permanente da minha conta e de todos os dados associados.", "pt"),
            ("귀하의 시스템에서 제 모든 개인정보와 계정을 영구적으로 삭제해 주시기 바랍니다.", "ko"),
            ("Solicito la eliminación permanente de mi cuenta y todos mis datos personales.", "es"),
            ("私の個人データおよびアカウントを完全に削除してください。", "ja"),
            ("Veuillez procéder à la suppression définitive de mon compte et de mes données.", "fr"),
        ]
        for text, expected_lang in samples:
            with self.subTest(lang=expected_lang):
                detected = self.classifier.detect_language(text)
                self.assertEqual(detected, expected_lang)

    def test_multilingual_erasure_classification(self):
        """Test that erasure requests in all languages are classified as ERASURE."""
        samples = [
            ("Please permanently delete my personal data and account.", "en"),
            ("Solicito a exclusão permanente da minha conta e de todos os dados associados.", "pt"),
            ("귀하의 시스템에서 제 모든 개인정보와 계정을 영구적으로 삭제해 주시기 바랍니다.", "ko"),
            ("Solicito la eliminación permanente de mi cuenta y todos mis datos personales.", "es"),
            ("私の個人データおよびアカウントを完全に削除してください。", "ja"),
            ("Veuillez procéder à la suppression définitive de mon compte et de mes données.", "fr"),
        ]
        for idx, (text, lang) in enumerate(samples):
            req = DeletionRequest(
                case_id=f"test_erasure_{lang}",
                email=f"user_{lang}@example.com",
                requested_at="2026-09-01T00:00:00Z",
                reported_status="PENDING",
                reported_at="2026-09-01T12:00:00Z",
                audit_at="2026-09-02T00:00:00Z",
                request_text=text,
            )
            res = self.classifier.classify_request(req)
            self.assertTrue(res.is_deletion_request)
            self.assertEqual(res.intent, RequestIntent.ERASURE)
            self.assertEqual(res.detected_language, lang)

    def test_non_deletion_cases_536_to_542(self):
        """Test that explicit non-deletion cases in deletion_requests.csv are classified as non-erasure."""
        all_requests = self.loader.load_deletion_requests("deletion_requests.csv")
        req_map = {r.case_id: r for r in all_requests}

        expected_intents = {
            "case_536": RequestIntent.LOGIN_ASSISTANCE,
            "case_537": RequestIntent.RECTIFICATION,
            "case_538": RequestIntent.MARKETING_OPT_OUT,
            "case_539": RequestIntent.SUBJECT_ACCESS,
            "case_540": RequestIntent.INVOICE_COPY,
            "case_541": RequestIntent.EMAIL_UPDATE,
            "case_542": RequestIntent.DATA_EXPORT,
        }

        dummy_profile = IdentityProfile(
            user_id="user_test",
            current_name="Test User",
            current_email="test@example.com",
            current_phone="",
            current_email_hash="",
            all_emails={"test@example.com"},
            all_phones=set(),
            audit_history=[],
        )

        for case_id, exp_intent in expected_intents.items():
            req = req_map.get(case_id)
            self.assertIsNotNone(req, f"{case_id} must be in deletion_requests.csv")

            # 1. Test classifier result
            res = self.classifier.classify_request(req)
            self.assertFalse(res.is_deletion_request, f"{case_id} must NOT be a deletion request")
            self.assertEqual(res.intent, exp_intent)
            self.assertEqual(res.recommended_status, DeletionStatus.NOT_APPLICABLE)
            self.assertTrue(len(res.rationale) > 10)

            # 2. Test decision engine integration
            decision = self.decision_engine.evaluate(req, dummy_profile, [])
            self.assertEqual(decision.deletion_status, DeletionStatus.NOT_APPLICABLE)
            self.assertIn("not a deletion request", decision.rationale)

            # 3. Test step builder generates empty step array
            case_out = self.step_builder.build_case_output(decision)
            self.assertEqual(case_out.deletion_status, DeletionStatus.NOT_APPLICABLE)
            self.assertEqual(len(case_out.steps), 0)


if __name__ == "__main__":
    unittest.main()
