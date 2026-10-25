"""Domain models and schema definitions for Shomei Deletion Audit Engine.

Defines all data types, enums, constraints, and validation rules specified in
the HackerRank Orchestrate (October 2026) Ghost Data Still Exists challenge contract.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class DeletionStatus(str, Enum):
    """Allowed top-level deletion statuses."""
    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class Phase(str, Enum):
    """Allowed step phases in strict order."""
    FINDING = "FINDING"
    REMEDIATION = "REMEDIATION"
    VERIFICATION = "VERIFICATION"


class Operation(str, Enum):
    """Allowed operations grouped by phase."""
    # FINDING phase
    REPORT_REMAINING_RECORD = "REPORT_REMAINING_RECORD"
    REPORT_EXPOSED_PII = "REPORT_EXPOSED_PII"
    REPORT_ACTIVE_DATA_FLOW = "REPORT_ACTIVE_DATA_FLOW"
    REPORT_RESTORE_RISK = "REPORT_RESTORE_RISK"

    # REMEDIATION phase
    DISABLE_DATA_FLOW = "DISABLE_DATA_FLOW"
    BLOCK_RESTORE = "BLOCK_RESTORE"
    DELETE_RECORD = "DELETE_RECORD"
    REDACT_RECORD = "REDACT_RECORD"
    ANONYMIZE_RECORD = "ANONYMIZE_RECORD"

    # VERIFICATION phase
    VERIFY_RECORD_ABSENT = "VERIFY_RECORD_ABSENT"
    VERIFY_RECORD_PRESENT = "VERIFY_RECORD_PRESENT"
    VERIFY_RECORD_REDACTED = "VERIFY_RECORD_REDACTED"
    VERIFY_RECORD_ANONYMIZED = "VERIFY_RECORD_ANONYMIZED"
    VERIFY_DATA_FLOW_DISABLED = "VERIFY_DATA_FLOW_DISABLED"
    VERIFY_RESTORE_BLOCKED = "VERIFY_RESTORE_BLOCKED"


class State(str, Enum):
    """Allowed record/resource states."""
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    REDACTED = "REDACTED"
    ANONYMIZED = "ANONYMIZED"
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"
    BLOCKED = "BLOCKED"


# Canonical phase ordering (R1.8)
PHASE_ORDER: Dict[Phase, int] = {
    Phase.FINDING: 0,
    Phase.REMEDIATION: 1,
    Phase.VERIFICATION: 2,
}

# Canonical operation ordering within each phase (R7.1, AGENTS.md §6.4)
OPERATION_ORDER: Dict[Operation, int] = {
    # FINDING
    Operation.REPORT_REMAINING_RECORD: 0,
    Operation.REPORT_EXPOSED_PII: 1,
    Operation.REPORT_ACTIVE_DATA_FLOW: 2,
    Operation.REPORT_RESTORE_RISK: 3,

    # REMEDIATION
    Operation.DISABLE_DATA_FLOW: 0,
    Operation.BLOCK_RESTORE: 1,
    Operation.DELETE_RECORD: 2,
    Operation.REDACT_RECORD: 3,
    Operation.ANONYMIZE_RECORD: 4,

    # VERIFICATION
    Operation.VERIFY_RECORD_ABSENT: 0,
    Operation.VERIFY_RECORD_PRESENT: 1,
    Operation.VERIFY_RECORD_REDACTED: 2,
    Operation.VERIFY_RECORD_ANONYMIZED: 3,
    Operation.VERIFY_DATA_FLOW_DISABLED: 4,
    Operation.VERIFY_RESTORE_BLOCKED: 5,
}

# Allowed operations for each phase (AGENTS.md §6.4)
ALLOWED_PHASE_OPERATIONS: Dict[Phase, Set[Operation]] = {
    Phase.FINDING: {
        Operation.REPORT_REMAINING_RECORD,
        Operation.REPORT_EXPOSED_PII,
        Operation.REPORT_ACTIVE_DATA_FLOW,
        Operation.REPORT_RESTORE_RISK,
    },
    Phase.REMEDIATION: {
        Operation.DISABLE_DATA_FLOW,
        Operation.BLOCK_RESTORE,
        Operation.DELETE_RECORD,
        Operation.REDACT_RECORD,
        Operation.ANONYMIZE_RECORD,
    },
    Phase.VERIFICATION: {
        Operation.VERIFY_RECORD_ABSENT,
        Operation.VERIFY_RECORD_PRESENT,
        Operation.VERIFY_RECORD_REDACTED,
        Operation.VERIFY_RECORD_ANONYMIZED,
        Operation.VERIFY_DATA_FLOW_DISABLED,
        Operation.VERIFY_RESTORE_BLOCKED,
    },
}

# Allowed states for each operation (AGENTS.md §6.4)
ALLOWED_OPERATION_STATES: Dict[Operation, Set[State]] = {
    # FINDING
    Operation.REPORT_REMAINING_RECORD: {State.PRESENT},
    Operation.REPORT_EXPOSED_PII: {State.PRESENT},
    Operation.REPORT_ACTIVE_DATA_FLOW: {State.ACTIVE},
    Operation.REPORT_RESTORE_RISK: {State.ACTIVE},

    # REMEDIATION
    Operation.DISABLE_DATA_FLOW: {State.DISABLED},
    Operation.BLOCK_RESTORE: {State.BLOCKED},
    Operation.DELETE_RECORD: {State.ABSENT},
    Operation.REDACT_RECORD: {State.REDACTED},
    Operation.ANONYMIZE_RECORD: {State.ANONYMIZED},

    # VERIFICATION
    Operation.VERIFY_RECORD_ABSENT: {State.ABSENT},
    Operation.VERIFY_RECORD_PRESENT: {State.PRESENT},
    Operation.VERIFY_RECORD_REDACTED: {State.REDACTED},
    Operation.VERIFY_RECORD_ANONYMIZED: {State.ANONYMIZED},
    Operation.VERIFY_DATA_FLOW_DISABLED: {State.DISABLED},
    Operation.VERIFY_RESTORE_BLOCKED: {State.BLOCKED},
}


@dataclass(frozen=True)
class Step:
    """Represents a single step in steps_json adhering strictly to schema (R2.1)."""
    step_no: int
    phase: str
    system_id: str
    resource_id: str
    operation: str
    state: str
    evidence_id: str = ""

    def validate(self) -> None:
        """Validate step fields against official contract rules."""
        if not isinstance(self.step_no, int) or self.step_no <= 0:
            raise ValueError(f"step_no must be positive integer, got: {self.step_no}")
        if not self.system_id:
            raise ValueError("system_id must not be empty")
        if not self.resource_id:
            raise ValueError("resource_id must not be empty")

        try:
            phase_enum = Phase(self.phase)
        except ValueError:
            raise ValueError(f"Invalid phase: {self.phase}. Must be one of {[p.value for p in Phase]}")

        try:
            op_enum = Operation(self.operation)
        except ValueError:
            raise ValueError(f"Invalid operation: {self.operation}")

        try:
            state_enum = State(self.state)
        except ValueError:
            raise ValueError(f"Invalid state: {self.state}")

        if op_enum not in ALLOWED_PHASE_OPERATIONS[phase_enum]:
            raise ValueError(f"Operation {self.operation} is not permitted in phase {self.phase}")

        if state_enum not in ALLOWED_OPERATION_STATES[op_enum]:
            raise ValueError(f"State {self.state} is not permitted for operation {self.operation}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict matching exact JSON representation."""
        return {
            "step_no": self.step_no,
            "phase": self.phase,
            "system_id": self.system_id,
            "resource_id": self.resource_id,
            "operation": self.operation,
            "state": self.state,
            "evidence_id": self.evidence_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Step:
        """Instantiate and validate Step from dictionary."""
        required = {"step_no", "phase", "system_id", "resource_id", "operation", "state", "evidence_id"}
        missing = required - set(data.keys())
        if missing:
            raise ValueError(f"Step missing required fields: {missing}")
        step = cls(
            step_no=int(data["step_no"]),
            phase=str(data["phase"]),
            system_id=str(data["system_id"]),
            resource_id=str(data["resource_id"]),
            operation=str(data["operation"]),
            state=str(data["state"]),
            evidence_id=str(data.get("evidence_id", "")),
        )
        step.validate()
        return step

    def sort_tuple(self) -> Tuple[int, int, str, str]:
        """Return sorting key for deterministic ordering: Phase -> Op -> system_id -> resource_id."""
        p_idx = PHASE_ORDER.get(Phase(self.phase), 99)
        op_idx = OPERATION_ORDER.get(Operation(self.operation), 99)
        return (p_idx, op_idx, self.system_id, self.resource_id)


@dataclass
class DeletionRequest:
    """Represents a row in deletion_requests.csv."""
    case_id: str
    email: str
    requested_at: str
    reported_status: str
    reported_at: str
    audit_at: str
    request_text: str


@dataclass
class UserIdentity:
    """Represents a row in user_identities.csv."""
    user_id: str
    name: str
    email: str
    phone: str
    email_hash: str
    updated_at: str


@dataclass
class AuditLogEntry:
    """Represents a row in user_audit_log.csv."""
    audit_id: str
    user_id: str
    event_time: str
    field_name: str
    old_value: str
    new_value: str


@dataclass
class IdentityProfile:
    """Consolidated identity representation with current and historical identifiers."""
    user_id: str
    current_name: str
    current_email: str
    current_phone: str
    current_email_hash: str
    all_emails: Set[str] = field(default_factory=set)
    all_phones: Set[str] = field(default_factory=set)
    all_hashes: Set[str] = field(default_factory=set)
    all_names: Set[str] = field(default_factory=set)
    audit_history: List[AuditLogEntry] = field(default_factory=list)

    def identifiers_at(self, cutoff_time: Optional[str] = None) -> Set[str]:
        """Return all lowercase strings that identify this user at or before cutoff_time."""
        ids: Set[str] = {self.user_id.lower()}
        if self.current_email:
            ids.add(self.current_email.lower())
        if self.current_phone:
            ids.add(self.current_phone.lower())
        if self.current_email_hash:
            ids.add(self.current_email_hash.lower())

        for entry in self.audit_history:
            if cutoff_time is None or entry.event_time <= cutoff_time:
                if entry.old_value:
                    ids.add(entry.old_value.lower())
                if entry.new_value:
                    ids.add(entry.new_value.lower())

        return ids


@dataclass
class SystemActivity:
    """Represents a row in system_activity.csv."""
    activity_id: str
    event_time: str
    event_type: str
    source_system: str
    target_system: str
    resource_id: str
    reported_result: str
    details: str


@dataclass
class DeletionRule:
    """Represents a policy rule in deletion_rules.csv."""
    rule_id: str
    data_category: str
    condition: str
    required_action: str


@dataclass
class EvidenceFileMeta:
    """Represents a manifest entry in evidence_files.csv."""
    file_id: str
    file_path: str
    origin: str
    captured_at: str


@dataclass
class CaseOutput:
    """Represents a single evaluated case ready for output.csv."""
    case_id: str
    deletion_status: DeletionStatus
    steps: List[Step] = field(default_factory=list)

    def validate(self) -> None:
        """Validate case output semantics."""
        if not self.case_id:
            raise ValueError("case_id must not be empty")

        if self.deletion_status == DeletionStatus.NOT_APPLICABLE:
            if self.steps:
                raise ValueError(f"NOT_APPLICABLE case {self.case_id} must have empty steps_json, got {len(self.steps)} steps")
            return

        # Consecutive step number verification
        for idx, step in enumerate(self.steps, start=1):
            if step.step_no != idx:
                raise ValueError(f"Step numbers must be consecutive from 1, step {idx} had step_no={step.step_no}")
            step.validate()

        # Phase order verification
        current_phase_idx = -1
        for step in self.steps:
            p_idx = PHASE_ORDER[Phase(step.phase)]
            if p_idx < current_phase_idx:
                raise ValueError(f"Step out of phase order in case {self.case_id}: {step.phase} after phase index {current_phase_idx}")
            current_phase_idx = p_idx

        # COMPLETE vs INCOMPLETE constraints (AGENTS.md §6.3)
        if self.deletion_status == DeletionStatus.COMPLETE:
            for step in self.steps:
                if step.phase != Phase.VERIFICATION.value:
                    raise ValueError(f"COMPLETE case {self.case_id} can only contain VERIFICATION steps, found {step.phase}")
                if not step.evidence_id:
                    raise ValueError(f"COMPLETE case {self.case_id} verification step {step.step_no} must cite evidence_id")
        elif self.deletion_status == DeletionStatus.INCOMPLETE:
            # Remediation steps and post-remediation verification steps must have empty evidence_id
            for step in self.steps:
                if step.phase in (Phase.REMEDIATION.value, Phase.VERIFICATION.value) and step.evidence_id != "":
                    raise ValueError(f"INCOMPLETE case {self.case_id} future step {step.step_no} ({step.phase}) must have empty evidence_id")

    def steps_json(self) -> str:
        """Serialize steps as compact JSON array."""
        return json.dumps([s.to_dict() for s in self.steps], separators=(",", ":"))
