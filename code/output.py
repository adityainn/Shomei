"""Output serialization and strict validation module for Shomei.

Ensures generated output.csv strictly complies with the challenge contract (R1, R2, R7),
including header, row count, sorting, step numbering, phase ordering, and JSON formatting.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from models import (
    ALLOWED_OPERATION_STATES,
    ALLOWED_PHASE_OPERATIONS,
    CaseOutput,
    DeletionStatus,
    Operation,
    Phase,
    State,
    Step,
)


@dataclass
class ValidationReport:
    """Detailed summary of output validation results."""
    is_valid: bool
    total_rows: int
    status_counts: Dict[str, int] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def summary(self) -> str:
        """Formatted human-readable validation summary."""
        status_str = ", ".join(f"{k}: {v}" for k, v in self.status_counts.items())
        res = [
            f"Validation: {'PASSED' if self.is_valid else 'FAILED'}",
            f"Total data rows: {self.total_rows}",
            f"Status distribution: {status_str or 'none'}",
            f"Errors ({len(self.errors)}):",
        ]
        for e in self.errors[:10]:
            res.append(f"  - {e}")
        if len(self.errors) > 10:
            res.append(f"  ... and {len(self.errors) - 10} more errors")
        return "\n".join(res)


class OutputSerializer:
    """Serializes evaluated CaseOutput objects and validates compliance with challenge rules."""

    EXPECTED_HEADER = ["case_id", "deletion_status", "steps_json"]

    @classmethod
    def serialize_to_file(
        cls,
        case_outputs: Sequence[CaseOutput],
        target_path: str | Path,
        sort_by_case_id: bool = True,
    ) -> None:
        """Serialize a list of CaseOutputs to a CSV file."""
        target = Path(target_path)
        items = list(case_outputs)
        if sort_by_case_id:
            items.sort(key=lambda c: c.case_id)

        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
            writer.writerow(cls.EXPECTED_HEADER)
            for case_out in items:
                writer.writerow([
                    case_out.case_id,
                    case_out.deletion_status.value if isinstance(case_out.deletion_status, DeletionStatus) else str(case_out.deletion_status),
                    case_out.steps_json(),
                ])

    @classmethod
    def generate_skeleton(
        cls,
        case_ids: Sequence[str],
        target_path: str | Path,
        default_status: DeletionStatus = DeletionStatus.NOT_APPLICABLE,
    ) -> None:
        """Generate a valid skeleton CSV file for pre-flight testing."""
        outputs = [
            CaseOutput(case_id=cid, deletion_status=default_status, steps=[])
            for cid in case_ids
        ]
        cls.serialize_to_file(outputs, target_path)

    @classmethod
    def validate_file(
        cls,
        file_path: str | Path,
        expected_case_ids: Optional[Sequence[str]] = None,
        expected_row_count: int = 518,
        manifest: Optional[Dict[str, Any]] = None,
        requests_by_id: Optional[Dict[str, Any]] = None,
    ) -> ValidationReport:
        """Thoroughly validate an output.csv file against all official challenge constraints."""
        report = ValidationReport(is_valid=True, total_rows=0)
        path = Path(file_path)

        if not path.is_file():
            report.is_valid = False
            report.errors.append(f"Output file does not exist: {path}")
            return report

        seen_case_ids: List[str] = []
        status_counts: Dict[str, int] = {
            DeletionStatus.COMPLETE.value: 0,
            DeletionStatus.INCOMPLETE.value: 0,
            DeletionStatus.NOT_APPLICABLE.value: 0,
        }

        manifest_map = None
        if manifest is not None:
            if isinstance(manifest, list):
                manifest_map = {getattr(m, "file_id", str(m)): m for m in manifest}
            elif isinstance(manifest, dict):
                manifest_map = manifest

        with open(path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader, None)

            # R1.2: Exact header row
            if header != cls.EXPECTED_HEADER:
                report.is_valid = False
                report.errors.append(f"Header mismatch: expected {cls.EXPECTED_HEADER}, got {header}")

            for row_no, row in enumerate(reader, start=2):
                if len(row) != 3:
                    report.is_valid = False
                    report.errors.append(f"Row {row_no}: malformed column count (expected 3, got {len(row)})")
                    continue

                case_id, status_str, steps_raw = row[0].strip(), row[1].strip(), row[2].strip()
                seen_case_ids.append(case_id)

                # R1.5: Valid status enum
                if status_str in status_counts:
                    status_counts[status_str] += 1
                else:
                    report.is_valid = False
                    report.errors.append(f"Row {row_no} ({case_id}): invalid deletion_status '{status_str}'")

                # R1.6: Valid JSON array
                try:
                    steps_list = json.loads(steps_raw)
                except Exception as ex:
                    report.is_valid = False
                    report.errors.append(f"Row {row_no} ({case_id}): JSON parsing error in steps_json: {ex}")
                    continue

                if not isinstance(steps_list, list):
                    report.is_valid = False
                    report.errors.append(f"Row {row_no} ({case_id}): steps_json is not an array")
                    continue

                # R1.9: NOT_APPLICABLE must have empty array []
                if status_str == DeletionStatus.NOT_APPLICABLE.value and len(steps_list) > 0:
                    report.is_valid = False
                    report.errors.append(f"Row {row_no} ({case_id}): NOT_APPLICABLE must have steps_json=[], got {len(steps_list)} steps")

                # Validate steps within array
                current_phase_order = -1
                for idx, s in enumerate(steps_list, start=1):
                    if not isinstance(s, dict):
                        report.is_valid = False
                        report.errors.append(f"Row {row_no} ({case_id}): step {idx} is not a JSON object")
                        continue

                    # R2.1: Exactly 7 required fields
                    req_fields = {"step_no", "phase", "system_id", "resource_id", "operation", "state", "evidence_id"}
                    missing_fields = req_fields - set(s.keys())
                    if missing_fields:
                        report.is_valid = False
                        report.errors.append(f"Row {row_no} ({case_id}): step {idx} missing fields {missing_fields}")

                    # R1.7: Consecutive step numbers starting at 1
                    step_no = s.get("step_no")
                    if step_no != idx:
                        report.is_valid = False
                        report.errors.append(f"Row {row_no} ({case_id}): step number out of sequence (expected {idx}, got {step_no})")

                    phase_val = s.get("phase")
                    op_val = s.get("operation")
                    state_val = s.get("state")
                    ev_id = s.get("evidence_id", "")

                    # Phase check
                    try:
                        phase_enum = Phase(phase_val)
                    except ValueError:
                        report.is_valid = False
                        report.errors.append(f"Row {row_no} ({case_id}): invalid phase '{phase_val}'")
                        continue

                    # R1.8: Strict phase order (FINDING -> REMEDIATION -> VERIFICATION)
                    phase_order_idx = {"FINDING": 0, "REMEDIATION": 1, "VERIFICATION": 2}[phase_val]
                    if phase_order_idx < current_phase_order:
                        report.is_valid = False
                        report.errors.append(f"Row {row_no} ({case_id}): step {idx} phase {phase_val} violates phase order")
                    current_phase_order = phase_order_idx

                    # Operation check
                    try:
                        op_enum = Operation(op_val)
                    except ValueError:
                        report.is_valid = False
                        report.errors.append(f"Row {row_no} ({case_id}): invalid operation '{op_val}'")
                        continue

                    if op_enum not in ALLOWED_PHASE_OPERATIONS[phase_enum]:
                        report.is_valid = False
                        report.errors.append(f"Row {row_no} ({case_id}): operation {op_val} illegal in phase {phase_val}")

                    # State check
                    try:
                        state_enum = State(state_val)
                    except ValueError:
                        report.is_valid = False
                        report.errors.append(f"Row {row_no} ({case_id}): invalid state '{state_val}'")
                        continue

                    if state_enum not in ALLOWED_OPERATION_STATES[op_enum]:
                        report.is_valid = False
                        report.errors.append(f"Row {row_no} ({case_id}): state {state_val} illegal for operation {op_val}")

                    # Evidence citation rules (R4.7, R4.8)
                    if status_str == DeletionStatus.COMPLETE.value:
                        if phase_enum != Phase.VERIFICATION:
                            report.is_valid = False
                            report.errors.append(f"Row {row_no} ({case_id}): COMPLETE case has non-verification step ({phase_val})")
                        if not ev_id:
                            report.is_valid = False
                            report.errors.append(f"Row {row_no} ({case_id}): COMPLETE verification step {step_no} must cite evidence_id")
                    elif status_str == DeletionStatus.INCOMPLETE.value:
                        if phase_enum in (Phase.REMEDIATION, Phase.VERIFICATION) and ev_id != "":
                            report.is_valid = False
                            report.errors.append(f"Row {row_no} ({case_id}): INCOMPLETE future step {step_no} ({phase_val}) must have empty evidence_id, got '{ev_id}'")
                        elif phase_enum == Phase.FINDING and not ev_id:
                            report.is_valid = False
                            report.errors.append(f"Row {row_no} ({case_id}): INCOMPLETE finding step {step_no} must cite evidence_id")

                    # Check evidence manifest validity if provided
                    if ev_id and manifest_map is not None:
                        if ev_id not in manifest_map:
                            report.is_valid = False
                            report.errors.append(f"Row {row_no} ({case_id}): step {step_no} cites unknown evidence_id '{ev_id}'")

        report.total_rows = len(seen_case_ids)
        report.status_counts = status_counts

        # R1.3: Exactly 518 data rows
        if report.total_rows != expected_row_count:
            report.is_valid = False
            report.errors.append(f"Expected exactly {expected_row_count} data rows, found {report.total_rows}")

        # R1.4: Sorted by case_id
        if seen_case_ids != sorted(seen_case_ids):
            report.is_valid = False
            report.errors.append("Rows are not sorted in ascending order by case_id")

        # Compare with expected case IDs if supplied
        if expected_case_ids:
            expected_set = set(expected_case_ids)
            actual_set = set(seen_case_ids)
            missing_ids = expected_set - actual_set
            extra_ids = actual_set - expected_set
            if missing_ids:
                report.is_valid = False
                report.errors.append(f"Missing expected case_ids (first 5): {sorted(list(missing_ids))[:5]}")
            if extra_ids:
                report.is_valid = False
                report.errors.append(f"Found unexpected case_ids (first 5): {sorted(list(extra_ids))[:5]}")

        if report.errors:
            report.is_valid = False

        return report
