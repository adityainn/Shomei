"""Unit tests for models.py data structures and schema validators."""

import sys
import unittest
from pathlib import Path

# Ensure code/ is on python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models import (
    AuditLogEntry,
    CaseOutput,
    DeletionStatus,
    IdentityProfile,
    Operation,
    Phase,
    State,
    Step,
)


class TestModels(unittest.TestCase):
    """Test suite for Step, CaseOutput, and IdentityProfile domain models."""

    def test_valid_step_creation(self):
        """Test creating and validating a valid finding step."""
        step = Step(
            step_no=1,
            phase="FINDING",
            system_id="account_service",
            resource_id="account_005",
            operation="REPORT_REMAINING_RECORD",
            state="PRESENT",
            evidence_id="evidence_54",
        )
        step.validate()
        d = step.to_dict()
        self.assertEqual(d["step_no"], 1)
        self.assertEqual(d["phase"], "FINDING")
        self.assertEqual(d["operation"], "REPORT_REMAINING_RECORD")
        self.assertEqual(d["state"], "PRESENT")

    def test_step_deserialization(self):
        """Test reconstructing a Step from a dictionary."""
        raw = {
            "step_no": 2,
            "phase": "REMEDIATION",
            "system_id": "account_service",
            "resource_id": "account_005",
            "operation": "DELETE_RECORD",
            "state": "ABSENT",
            "evidence_id": "",
        }
        step = Step.from_dict(raw)
        self.assertEqual(step.step_no, 2)
        self.assertEqual(step.phase, "REMEDIATION")
        self.assertEqual(step.operation, "DELETE_RECORD")
        self.assertEqual(step.state, "ABSENT")

    def test_step_validation_invalid_phase(self):
        """Test that invalid phase raises ValueError."""
        step = Step(
            step_no=1,
            phase="INVALID_PHASE",
            system_id="account_service",
            resource_id="account_001",
            operation="REPORT_REMAINING_RECORD",
            state="PRESENT",
        )
        with self.assertRaises(ValueError):
            step.validate()

    def test_step_validation_illegal_operation_for_phase(self):
        """Test that remediation operation in finding phase raises ValueError."""
        step = Step(
            step_no=1,
            phase="FINDING",
            system_id="account_service",
            resource_id="account_001",
            operation="DELETE_RECORD",  # Remediation op in FINDING phase
            state="ABSENT",
        )
        with self.assertRaises(ValueError):
            step.validate()

    def test_step_validation_illegal_state_for_operation(self):
        """Test that illegal state for operation raises ValueError."""
        step = Step(
            step_no=1,
            phase="FINDING",
            system_id="account_service",
            resource_id="account_001",
            operation="REPORT_REMAINING_RECORD",
            state="ABSENT",  # REPORT_REMAINING_RECORD requires PRESENT
        )
        with self.assertRaises(ValueError):
            step.validate()

    def test_case_output_not_applicable_must_have_empty_steps(self):
        """Test that NOT_APPLICABLE status requires empty steps array."""
        valid_na = CaseOutput(
            case_id="case_100",
            deletion_status=DeletionStatus.NOT_APPLICABLE,
            steps=[],
        )
        valid_na.validate()
        self.assertEqual(valid_na.steps_json(), "[]")

        invalid_na = CaseOutput(
            case_id="case_100",
            deletion_status=DeletionStatus.NOT_APPLICABLE,
            steps=[
                Step(
                    step_no=1,
                    phase="VERIFICATION",
                    system_id="account_service",
                    resource_id="account_001",
                    operation="VERIFY_RECORD_ABSENT",
                    state="ABSENT",
                    evidence_id="evidence_01",
                )
            ],
        )
        with self.assertRaises(ValueError):
            invalid_na.validate()

    def test_case_output_consecutive_step_numbers(self):
        """Test that non-consecutive step numbers are rejected."""
        case_out = CaseOutput(
            case_id="case_05",
            deletion_status=DeletionStatus.INCOMPLETE,
            steps=[
                Step(
                    step_no=1,
                    phase="FINDING",
                    system_id="account_service",
                    resource_id="account_005",
                    operation="REPORT_REMAINING_RECORD",
                    state="PRESENT",
                    evidence_id="evidence_54",
                ),
                Step(
                    step_no=3,  # Skipped 2
                    phase="REMEDIATION",
                    system_id="account_service",
                    resource_id="account_005",
                    operation="DELETE_RECORD",
                    state="ABSENT",
                    evidence_id="",
                ),
            ],
        )
        with self.assertRaises(ValueError):
            case_out.validate()

    def test_case_output_phase_order(self):
        """Test that steps violating FINDING -> REMEDIATION -> VERIFICATION are rejected."""
        case_out = CaseOutput(
            case_id="case_05",
            deletion_status=DeletionStatus.INCOMPLETE,
            steps=[
                Step(
                    step_no=1,
                    phase="REMEDIATION",
                    system_id="account_service",
                    resource_id="account_005",
                    operation="DELETE_RECORD",
                    state="ABSENT",
                    evidence_id="",
                ),
                Step(
                    step_no=2,
                    phase="FINDING",  # FINDING after REMEDIATION violates phase order
                    system_id="account_service",
                    resource_id="account_005",
                    operation="REPORT_REMAINING_RECORD",
                    state="PRESENT",
                    evidence_id="evidence_54",
                ),
            ],
        )
        with self.assertRaises(ValueError):
            case_out.validate()

    def test_identity_profile_identifiers_at(self):
        """Test temporal identifier retrieval from IdentityProfile."""
        profile = IdentityProfile(
            user_id="user_485",
            current_name="Marie Dupont",
            current_email="marie.new@example.com",
            current_phone="+33 6 63 29 68 28",
            current_email_hash="hash123",
            audit_history=[
                AuditLogEntry(
                    audit_id="audit_01",
                    user_id="user_485",
                    event_time="2025-01-10T10:00:00Z",
                    field_name="email",
                    old_value="marie.old@example.com",
                    new_value="marie.new@example.com",
                ),
                AuditLogEntry(
                    audit_id="audit_02",
                    user_id="user_485",
                    event_time="2026-05-15T10:00:00Z",
                    field_name="phone",
                    old_value="+33 6 00 00 00 00",
                    new_value="+33 6 63 29 68 28",
                ),
            ],
        )

        # Before any changes
        early = profile.identifiers_at("2024-01-01T00:00:00Z")
        self.assertIn("user_485", early)
        self.assertNotIn("marie.old@example.com", early)

        # After email change but before phone change
        mid = profile.identifiers_at("2025-06-01T00:00:00Z")
        self.assertIn("marie.old@example.com", mid)
        self.assertNotIn("+33 6 00 00 00 00", mid)

        # After all changes
        late = profile.identifiers_at("2026-12-31T00:00:00Z")
        self.assertIn("marie.old@example.com", late)
        self.assertIn("+33 6 00 00 00 00", late)


if __name__ == "__main__":
    unittest.main()
