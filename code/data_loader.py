"""Data ingestion and validation module for Shomei Deletion Audit Engine.

Loads, validates, and parses all participant-facing CSV files in dataset/
into strongly typed domain models.
"""

from __future__ import annotations

import csv
import os
from pathlib import Path
from typing import Dict, List, Optional

from models import (
    AuditLogEntry,
    CaseOutput,
    DeletionRequest,
    DeletionRule,
    DeletionStatus,
    EvidenceFileMeta,
    Step,
    SystemActivity,
    UserIdentity,
)


class DatasetLoader:
    """Deterministic loader and validator for dataset CSV artifacts."""

    def __init__(self, dataset_dir: str | Path = "dataset"):
        self.dataset_dir = Path(dataset_dir)

    def _resolve(self, filename: str) -> Path:
        """Resolve path to a dataset file and ensure it exists."""
        path = self.dataset_dir / filename
        if not path.is_file():
            raise FileNotFoundError(f"Required dataset file not found: {path}")
        return path

    def load_deletion_requests(self, filename: str = "deletion_requests.csv") -> List[DeletionRequest]:
        """Load and validate deletion requests."""
        path = self._resolve(filename)
        expected_header = ["case_id", "email", "requested_at", "reported_status", "reported_at", "audit_at", "request_text"]
        requests: List[DeletionRequest] = []

        with open(path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            if header != expected_header:
                raise ValueError(f"Invalid header in {filename}: expected {expected_header}, got {header}")

            for line_no, row in enumerate(reader, start=2):
                if len(row) != 7:
                    raise ValueError(f"Malformed row at line {line_no} in {filename}: expected 7 columns, got {len(row)}")
                requests.append(
                    DeletionRequest(
                        case_id=row[0].strip(),
                        email=row[1].strip(),
                        requested_at=row[2].strip(),
                        reported_status=row[3].strip(),
                        reported_at=row[4].strip(),
                        audit_at=row[5].strip(),
                        request_text=row[6].strip(),
                    )
                )

        return requests

    def load_user_identities(self, filename: str = "user_identities.csv") -> List[UserIdentity]:
        """Load and validate user current identity snapshots."""
        path = self._resolve(filename)
        expected_header = ["user_id", "name", "email", "phone", "email_hash", "updated_at"]
        identities: List[UserIdentity] = []

        with open(path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            if header != expected_header:
                raise ValueError(f"Invalid header in {filename}: expected {expected_header}, got {header}")

            for line_no, row in enumerate(reader, start=2):
                if len(row) != 6:
                    raise ValueError(f"Malformed row at line {line_no} in {filename}: expected 6 columns, got {len(row)}")
                identities.append(
                    UserIdentity(
                        user_id=row[0].strip(),
                        name=row[1].strip(),
                        email=row[2].strip(),
                        phone=row[3].strip(),
                        email_hash=row[4].strip(),
                        updated_at=row[5].strip(),
                    )
                )

        return identities

    def load_user_audit_log(self, filename: str = "user_audit_log.csv") -> List[AuditLogEntry]:
        """Load and validate historical identity changes."""
        path = self._resolve(filename)
        expected_header = ["audit_id", "user_id", "event_time", "field_name", "old_value", "new_value"]
        entries: List[AuditLogEntry] = []

        with open(path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            if header != expected_header:
                raise ValueError(f"Invalid header in {filename}: expected {expected_header}, got {header}")

            for line_no, row in enumerate(reader, start=2):
                if len(row) != 6:
                    raise ValueError(f"Malformed row at line {line_no} in {filename}: expected 6 columns, got {len(row)}")
                entries.append(
                    AuditLogEntry(
                        audit_id=row[0].strip(),
                        user_id=row[1].strip(),
                        event_time=row[2].strip(),
                        field_name=row[3].strip(),
                        old_value=row[4].strip(),
                        new_value=row[5].strip(),
                    )
                )

        return entries

    def load_system_activity(self, filename: str = "system_activity.csv") -> List[SystemActivity]:
        """Load and validate global system activity event stream."""
        path = self._resolve(filename)
        expected_header = ["activity_id", "event_time", "event_type", "source_system", "target_system", "resource_id", "reported_result", "details"]
        activities: List[SystemActivity] = []

        with open(path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            if header != expected_header:
                raise ValueError(f"Invalid header in {filename}: expected {expected_header}, got {header}")

            for line_no, row in enumerate(reader, start=2):
                if len(row) != 8:
                    raise ValueError(f"Malformed row at line {line_no} in {filename}: expected 8 columns, got {len(row)}")
                activities.append(
                    SystemActivity(
                        activity_id=row[0].strip(),
                        event_time=row[1].strip(),
                        event_type=row[2].strip(),
                        source_system=row[3].strip(),
                        target_system=row[4].strip(),
                        resource_id=row[5].strip(),
                        reported_result=row[6].strip(),
                        details=row[7].strip(),
                    )
                )

        return activities

    def load_deletion_rules(self, filename: str = "deletion_rules.csv") -> List[DeletionRule]:
        """Load and validate deletion policy rules."""
        path = self._resolve(filename)
        expected_header = ["rule_id", "data_category", "condition", "required_action"]
        rules: List[DeletionRule] = []

        with open(path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            if header != expected_header:
                raise ValueError(f"Invalid header in {filename}: expected {expected_header}, got {header}")

            for line_no, row in enumerate(reader, start=2):
                if len(row) != 4:
                    raise ValueError(f"Malformed row at line {line_no} in {filename}: expected 4 columns, got {len(row)}")
                rules.append(
                    DeletionRule(
                        rule_id=row[0].strip(),
                        data_category=row[1].strip(),
                        condition=row[2].strip(),
                        required_action=row[3].strip(),
                    )
                )

        return rules

    def load_evidence_manifest(self, filename: str = "evidence_files.csv") -> List[EvidenceFileMeta]:
        """Load and validate evidence file manifest."""
        path = self._resolve(filename)
        expected_header = ["file_id", "file_path", "origin", "captured_at"]
        evidence_metas: List[EvidenceFileMeta] = []

        with open(path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            if header != expected_header:
                raise ValueError(f"Invalid header in {filename}: expected {expected_header}, got {header}")

            for line_no, row in enumerate(reader, start=2):
                if len(row) != 4:
                    raise ValueError(f"Malformed row at line {line_no} in {filename}: expected 4 columns, got {len(row)}")
                evidence_metas.append(
                    EvidenceFileMeta(
                        file_id=row[0].strip(),
                        file_path=row[1].strip(),
                        origin=row[2].strip(),
                        captured_at=row[3].strip(),
                    )
                )

        return evidence_metas

    def load_sample_output(self, filename: str = "sample_output.csv") -> Dict[str, CaseOutput]:
        """Load and parse sample output for validation and evaluation."""
        import json
        path = self._resolve(filename)
        expected_header = ["case_id", "deletion_status", "steps_json"]
        outputs: Dict[str, CaseOutput] = {}

        with open(path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            if header != expected_header:
                raise ValueError(f"Invalid header in {filename}: expected {expected_header}, got {header}")

            for line_no, row in enumerate(reader, start=2):
                if len(row) != 3:
                    raise ValueError(f"Malformed row at line {line_no} in {filename}: expected 3 columns, got {len(row)}")
                case_id, status_str, steps_raw = row[0].strip(), row[1].strip(), row[2].strip()
                status = DeletionStatus(status_str)
                raw_steps = json.loads(steps_raw)
                steps = [Step.from_dict(s) for s in raw_steps]
                case_out = CaseOutput(case_id=case_id, deletion_status=status, steps=steps)
                case_out.validate()
                outputs[case_id] = case_out

        return outputs
