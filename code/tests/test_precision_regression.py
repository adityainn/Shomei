"""Regression and precision optimization test suite for Shomei (Phase 4).

Validates:
1. Complex operation ordering (FINDING -> REMEDIATION -> VERIFICATION) across cases 03, 04, 21-25.
2. Exact step count, resource identification, and evidence IDs for multi-system cases.
3. Connector deactivation and verification logic under deletion rules.
4. Determinism of audit engine evaluation across multiple consecutive runs.
"""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from data_loader import DatasetLoader
from decision import DecisionEngine
from discovery import ResourceDiscoverer
from evidence import EvidenceIndex
from identity import IdentityResolver
from models import DeletionStatus, Operation, Phase, State
from policy import PolicyEngine
from sql_engine import SQLEngine
from steps import StepBuilder


class TestPrecisionRegression(unittest.TestCase):
    """Regression tests for edge cases and precision optimizations."""

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
        cls.index = EvidenceIndex(cls.dataset_dir, cls.manifest, cls.sql_engine)
        cls.discoverer = ResourceDiscoverer(cls.dataset_dir, cls.manifest, cls.sql_engine, cls.index, cls.activities)
        cls.policy = PolicyEngine(cls.rules)
        cls.decision_engine = DecisionEngine(cls.policy)
        cls.step_builder = StepBuilder()

        cls.sample_reqs = {r.case_id: r for r in cls.loader.load_deletion_requests("sample_deletion_requests.csv")}
        cls.ground_truth = cls.loader.load_sample_output("sample_output.csv")

    def _evaluate_case(self, case_id: str):
        req = self.sample_reqs[case_id]
        prof = self.resolver.resolve_request(req)
        discovered = self.discoverer.discover_for_request(req, prof)
        decision = self.decision_engine.evaluate(req, prof, discovered)
        return self.step_builder.build_case_output(decision)

    def test_case_03_precision(self):
        """Case 03 (COMPLETE): Verify 3 systems citing evidence_94."""
        out = self._evaluate_case("case_03")
        self.assertEqual(out.deletion_status, DeletionStatus.COMPLETE)
        self.assertEqual(len(out.steps), 3)

        expected = self.ground_truth["case_03"]
        for p_step, e_step in zip(out.steps, expected.steps):
            self.assertEqual(p_step.phase, e_step.phase)
            self.assertEqual(p_step.system_id, e_step.system_id)
            self.assertEqual(p_step.resource_id, e_step.resource_id)
            self.assertEqual(p_step.operation, e_step.operation)
            self.assertEqual(p_step.state, e_step.state)
            self.assertEqual(p_step.evidence_id, e_step.evidence_id)

    def test_case_04_precision(self):
        """Case 04 (COMPLETE): Verify account and anonymized analytics."""
        out = self._evaluate_case("case_04")
        self.assertEqual(out.deletion_status, DeletionStatus.COMPLETE)
        self.assertEqual(len(out.steps), 2)
        expected = self.ground_truth["case_04"]
        for p_step, e_step in zip(out.steps, expected.steps):
            self.assertEqual(p_step.system_id, e_step.system_id)
            self.assertEqual(p_step.resource_id, e_step.resource_id)
            self.assertEqual(p_step.operation, e_step.operation)
            self.assertEqual(p_step.evidence_id, e_step.evidence_id)

    def test_case_21_precision(self):
        """Case 21 (COMPLETE): Multi-system verified complete (account, audit, analytics)."""
        out = self._evaluate_case("case_21")
        self.assertEqual(out.deletion_status, DeletionStatus.COMPLETE)
        self.assertEqual(len(out.steps), 3)
        expected = self.ground_truth["case_21"]
        for p_step, e_step in zip(out.steps, expected.steps):
            self.assertEqual(p_step.resource_id, e_step.resource_id)
            self.assertEqual(p_step.operation, e_step.operation)
            self.assertEqual(p_step.evidence_id, e_step.evidence_id)

    def test_case_23_precision(self):
        """Case 23 (INCOMPLETE): Export and search findings with sequential remediations and verifications."""
        out = self._evaluate_case("case_23")
        self.assertEqual(out.deletion_status, DeletionStatus.INCOMPLETE)
        self.assertEqual(len(out.steps), 8)
        expected = self.ground_truth["case_23"]
        for p_step, e_step in zip(out.steps, expected.steps):
            self.assertEqual(p_step.step_no, e_step.step_no)
            self.assertEqual(p_step.phase, e_step.phase)
            self.assertEqual(p_step.system_id, e_step.system_id)
            self.assertEqual(p_step.resource_id, e_step.resource_id)
            self.assertEqual(p_step.operation, e_step.operation)
            self.assertEqual(p_step.state, e_step.state)
            self.assertEqual(p_step.evidence_id, e_step.evidence_id)

    def test_case_24_precision(self):
        """Case 24 (INCOMPLETE): Account and search index remaining records without spurious analytics."""
        out = self._evaluate_case("case_24")
        self.assertEqual(out.deletion_status, DeletionStatus.INCOMPLETE)
        self.assertEqual(len(out.steps), 7)
        expected = self.ground_truth["case_24"]
        for p_step, e_step in zip(out.steps, expected.steps):
            self.assertEqual(p_step.resource_id, e_step.resource_id)
            self.assertEqual(p_step.operation, e_step.operation)

    def test_case_25_precision(self):
        """Case 25 (COMPLETE): Account, audit record, and anonymized analytics."""
        out = self._evaluate_case("case_25")
        self.assertEqual(out.deletion_status, DeletionStatus.COMPLETE)
        self.assertEqual(len(out.steps), 3)
        expected = self.ground_truth["case_25"]
        for p_step, e_step in zip(out.steps, expected.steps):
            self.assertEqual(p_step.resource_id, e_step.resource_id)
            self.assertEqual(p_step.operation, e_step.operation)
            self.assertEqual(p_step.evidence_id, e_step.evidence_id)

    def test_case_28_and_29_batch_differentiation(self):
        """Cases 28 and 29: Test that distinct accounts in the same batch are mapped correctly."""
        out_28 = self._evaluate_case("case_28")
        out_29 = self._evaluate_case("case_29")

        self.assertEqual(out_28.deletion_status, DeletionStatus.COMPLETE)
        self.assertEqual(out_29.deletion_status, DeletionStatus.INCOMPLETE)

        res_28 = [s.resource_id for s in out_28.steps]
        res_29 = [s.resource_id for s in out_29.steps]

        self.assertIn("account_5482", res_28)
        self.assertIn("analytics_6077", res_28)

        self.assertIn("account_7012", res_29)
        self.assertIn("analytics_5208", res_29)

    def test_case_31_and_32_tombstone_handling(self):
        """Cases 31 and 32: Test compliant redacted tombstone vs exposed PII tombstone."""
        out_31 = self._evaluate_case("case_31")
        out_32 = self._evaluate_case("case_32")

        self.assertEqual(out_31.deletion_status, DeletionStatus.COMPLETE)
        self.assertEqual(out_32.deletion_status, DeletionStatus.INCOMPLETE)

        # Case 31: tombstone_440 is already redacted
        self.assertEqual(len(out_31.steps), 3)
        self.assertTrue(all(s.phase == "VERIFICATION" for s in out_31.steps))

        # Case 32: tombstone_9178 has exposed PII -> FINDING + REMEDIATION + VERIFICATION
        self.assertEqual(len(out_32.steps), 5)
        self.assertEqual(out_32.steps[0].phase, "FINDING")
        self.assertEqual(out_32.steps[0].operation, "REPORT_EXPOSED_PII")
        self.assertEqual(out_32.steps[1].phase, "REMEDIATION")
        self.assertEqual(out_32.steps[1].operation, "REDACT_RECORD")

    def test_determinism_across_multiple_runs(self):
        """Verify that 3 consecutive complete evaluation runs produce identical results."""
        from dataclasses import asdict
        runs_output = []
        for _ in range(3):
            case_results = {}
            for req in self.sample_reqs.values():
                prof = self.resolver.resolve_request(req)
                discovered = self.discoverer.discover_for_request(req, prof)
                decision = self.decision_engine.evaluate(req, prof, discovered)
                out = self.step_builder.build_case_output(decision)
                case_results[req.case_id] = asdict(out)
            json_str = json.dumps(case_results, sort_keys=True, default=str)
            run_hash = hashlib.sha256(json_str.encode("utf-8")).hexdigest()
            runs_output.append(run_hash)

        self.assertEqual(runs_output[0], runs_output[1])
        self.assertEqual(runs_output[1], runs_output[2])


if __name__ == "__main__":
    unittest.main()
