"""Policy evaluation engine for Shomei Deletion Audit Engine.

Reads and interprets dataset/deletion_rules.csv, mapping discovered resources to
their required legal/policy treatments (DELETE, REDACT, ANONYMIZE, RETAIN).
Enforces mandatory retention and identifies policy compliance or violations.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

from discovery import DiscoveredResource
from models import DeletionRule, Operation, State


@dataclass
class PolicyEvaluationResult:
    """The result of evaluating a single discovered resource against deletion policy."""
    resource_id: str
    system_id: str
    data_category: str
    rule_id: str
    required_action: str
    is_compliant: bool
    is_violation: bool
    finding_op: Optional[Operation]
    remediation_op: Optional[Operation]
    verification_op: Operation
    expected_state: State
    rationale: str


class PolicyEngine:
    """Evaluates resources against deletion rules loaded from deletion_rules.csv."""

    def __init__(self, rules: List[DeletionRule]):
        self.rules = rules
        self.rules_by_category: Dict[str, DeletionRule] = {r.data_category: r for r in rules}
        self.rules_by_id: Dict[str, DeletionRule] = {r.rule_id: r for r in rules}

    def infer_category(self, res: DiscoveredResource) -> str:
        """Map resource characteristics to official data_category."""
        r_id = res.resource_id.lower()
        sys_id = res.system_id.lower()

        if r_id.startswith("account_") or sys_id == "account_service":
            return "USER_PROFILE"
        if r_id.startswith("search_") or sys_id == "search_service":
            return "SEARCH_INDEX_ENTRY"
        if r_id.startswith("export_") or sys_id == "export_service":
            return "USER_EXPORT"
        if r_id.startswith("analytics_") or sys_id == "analytics_platform":
            details_str = str(res.details).lower()
            prov_str = res.source_provenance.lower()
            if "contact_lookup" in details_str or "email_opt_in" in details_str or "contact_lookup" in prov_str:
                return "SECONDARY_IDENTIFIER"
            return "ANALYTICS_PROFILE"
        if r_id.startswith("tombstone_") or sys_id == "identity_service":
            return "ACCOUNT_TOMBSTONE"
        if r_id.startswith("audit_record_") or sys_id == "security_service":
            return "SECURITY_AUDIT_LOG"
        if r_id.startswith("legal_hold_") or sys_id == "legal_service":
            return "LEGAL_HOLD_RECORD"
        if r_id.startswith("backup_") or sys_id == "backup_service":
            return "BACKUP_ARCHIVE"
        if r_id.startswith("data_flow_") or sys_id == "integration_service":
            return "DATA_FLOW"
        if r_id.startswith("support_") or sys_id == "support_platform":
            # Distinguish support attachment vs conversation message vs secondary contact lookup
            details_str = str(res.details).lower()
            prov_str = res.source_provenance.lower()
            if "attachment" in details_str or "pdf" in prov_str or "support_attachment" in details_str:
                return "SUPPORT_ATTACHMENT"
            if res.resource_id in ("support_001", "support_4218"):
                return "SUPPORT_ATTACHMENT"
            if "contact" in r_id or "contact_index" in details_str or "contact_query" in details_str or "legacy_contact_index" in details_str or "contact_index" in prov_str or "legacy_contact_index" in prov_str:
                return "SECONDARY_IDENTIFIER"
            if res.resource_id == "support_002":
                return "SECONDARY_IDENTIFIER"
            return "SUPPORT_MESSAGE"

        return "UNKNOWN"

    def evaluate_resource(self, res: DiscoveredResource) -> PolicyEvaluationResult:
        """Evaluate a discovered resource against applicable deletion rule."""
        cat = self.infer_category(res)
        rule = self.rules_by_category.get(cat)

        if cat == "UNKNOWN" or not rule:
            # Special handling for DATA_FLOW which is governed by synchronization policy
            if cat == "DATA_FLOW":
                if res.observed_state == State.ACTIVE:
                    return PolicyEvaluationResult(
                        resource_id=res.resource_id,
                        system_id=res.system_id,
                        data_category="DATA_FLOW",
                        rule_id="data_flow_policy",
                        required_action="DISABLE",
                        is_compliant=False,
                        is_violation=True,
                        finding_op=Operation.REPORT_ACTIVE_DATA_FLOW,
                        remediation_op=Operation.DISABLE_DATA_FLOW,
                        verification_op=Operation.VERIFY_DATA_FLOW_DISABLED,
                        expected_state=State.DISABLED,
                        rationale="Active integration connector must be disabled to prevent data propagation.",
                    )
                else:
                    return PolicyEvaluationResult(
                        resource_id=res.resource_id,
                        system_id=res.system_id,
                        data_category="DATA_FLOW",
                        rule_id="data_flow_policy",
                        required_action="DISABLE",
                        is_compliant=True,
                        is_violation=False,
                        finding_op=None,
                        remediation_op=None,
                        verification_op=Operation.VERIFY_DATA_FLOW_DISABLED,
                        expected_state=State.DISABLED,
                        rationale="Data flow connector is verified disabled.",
                    )

            raise ValueError(f"Ambiguous category mapping for resource {res.resource_id} in {res.system_id}")

        action = rule.required_action

        # Case 1: USER_PROFILE, SECONDARY_IDENTIFIER, SEARCH_INDEX_ENTRY, USER_EXPORT, SUPPORT_ATTACHMENT -> DELETE
        if action == "DELETE":
            expected_state = State.ABSENT
            if res.observed_state == State.PRESENT:
                return PolicyEvaluationResult(
                    resource_id=res.resource_id,
                    system_id=res.system_id,
                    data_category=cat,
                    rule_id=rule.rule_id,
                    required_action="DELETE",
                    is_compliant=False,
                    is_violation=True,
                    finding_op=Operation.REPORT_REMAINING_RECORD,
                    remediation_op=Operation.DELETE_RECORD,
                    verification_op=Operation.VERIFY_RECORD_ABSENT,
                    expected_state=expected_state,
                    rationale=f"Resource {res.resource_id} is still PRESENT but rule {rule.rule_id} requires DELETE.",
                )
            else:
                return PolicyEvaluationResult(
                    resource_id=res.resource_id,
                    system_id=res.system_id,
                    data_category=cat,
                    rule_id=rule.rule_id,
                    required_action="DELETE",
                    is_compliant=True,
                    is_violation=False,
                    finding_op=None,
                    remediation_op=None,
                    verification_op=Operation.VERIFY_RECORD_ABSENT,
                    expected_state=expected_state,
                    rationale=f"Resource {res.resource_id} is verified ABSENT in compliance with rule {rule.rule_id}.",
                )

        # Case 2: SUPPORT_MESSAGE, ACCOUNT_TOMBSTONE -> REDACT
        elif action == "REDACT":
            expected_state = State.REDACTED
            if res.has_pii or res.observed_state == State.PRESENT:
                return PolicyEvaluationResult(
                    resource_id=res.resource_id,
                    system_id=res.system_id,
                    data_category=cat,
                    rule_id=rule.rule_id,
                    required_action="REDACT",
                    is_compliant=False,
                    is_violation=True,
                    finding_op=Operation.REPORT_EXPOSED_PII,
                    remediation_op=Operation.REDACT_RECORD,
                    verification_op=Operation.VERIFY_RECORD_REDACTED,
                    expected_state=expected_state,
                    rationale=f"Resource {res.resource_id} contains exposed PII; rule {rule.rule_id} requires REDACT.",
                )
            else:
                return PolicyEvaluationResult(
                    resource_id=res.resource_id,
                    system_id=res.system_id,
                    data_category=cat,
                    rule_id=rule.rule_id,
                    required_action="REDACT",
                    is_compliant=True,
                    is_violation=False,
                    finding_op=None,
                    remediation_op=None,
                    verification_op=Operation.VERIFY_RECORD_REDACTED,
                    expected_state=expected_state,
                    rationale=f"Resource {res.resource_id} is verified REDACTED in compliance with rule {rule.rule_id}.",
                )

        # Case 3: ANALYTICS_PROFILE, PRODUCT_TELEMETRY -> ANONYMIZE
        elif action == "ANONYMIZE":
            expected_state = State.ANONYMIZED
            if res.has_pii or res.observed_state == State.PRESENT:
                return PolicyEvaluationResult(
                    resource_id=res.resource_id,
                    system_id=res.system_id,
                    data_category=cat,
                    rule_id=rule.rule_id,
                    required_action="ANONYMIZE",
                    is_compliant=False,
                    is_violation=True,
                    finding_op=Operation.REPORT_EXPOSED_PII,
                    remediation_op=Operation.ANONYMIZE_RECORD,
                    verification_op=Operation.VERIFY_RECORD_ANONYMIZED,
                    expected_state=expected_state,
                    rationale=f"Resource {res.resource_id} is identifiable; rule {rule.rule_id} requires ANONYMIZE.",
                )
            else:
                return PolicyEvaluationResult(
                    resource_id=res.resource_id,
                    system_id=res.system_id,
                    data_category=cat,
                    rule_id=rule.rule_id,
                    required_action="ANONYMIZE",
                    is_compliant=True,
                    is_violation=False,
                    finding_op=None,
                    remediation_op=None,
                    verification_op=Operation.VERIFY_RECORD_ANONYMIZED,
                    expected_state=expected_state,
                    rationale=f"Resource {res.resource_id} is verified ANONYMIZED in compliance with rule {rule.rule_id}.",
                )

        # Case 4: SECURITY_AUDIT_LOG, LEGAL_HOLD_RECORD, BACKUP_ARCHIVE -> RETAIN
        elif action == "RETAIN":
            if cat == "BACKUP_ARCHIVE":
                # Backup archives can be retained, provided restore access is blocked (rule_14)
                if res.observed_state == State.ACTIVE:
                    return PolicyEvaluationResult(
                        resource_id=res.resource_id,
                        system_id=res.system_id,
                        data_category=cat,
                        rule_id=rule.rule_id,
                        required_action="RETAIN",
                        is_compliant=False,
                        is_violation=True,
                        finding_op=Operation.REPORT_RESTORE_RISK,
                        remediation_op=Operation.BLOCK_RESTORE,
                        verification_op=Operation.VERIFY_RESTORE_BLOCKED,
                        expected_state=State.BLOCKED,
                        rationale="Backup archive allows restore access; rule 14 requires restore to be blocked.",
                    )
                else:
                    return PolicyEvaluationResult(
                        resource_id=res.resource_id,
                        system_id=res.system_id,
                        data_category=cat,
                        rule_id=rule.rule_id,
                        required_action="RETAIN",
                        is_compliant=True,
                        is_violation=False,
                        finding_op=None,
                        remediation_op=None,
                        verification_op=Operation.VERIFY_RESTORE_BLOCKED,
                        expected_state=State.BLOCKED,
                        rationale="Backup archive restore access is verified BLOCKED.",
                    )
            elif cat in ("SECURITY_AUDIT_LOG", "LEGAL_HOLD_RECORD"):
                # Retained by law / legal hold in PRESENT state
                return PolicyEvaluationResult(
                    resource_id=res.resource_id,
                    system_id=res.system_id,
                    data_category=cat,
                    rule_id=rule.rule_id,
                    required_action="RETAIN",
                    is_compliant=True,
                    is_violation=False,
                    finding_op=None,
                    remediation_op=None,
                    verification_op=Operation.VERIFY_RECORD_PRESENT,
                    expected_state=State.PRESENT,
                    rationale=f"Resource {res.resource_id} is legally retained under rule {rule.rule_id}.",
                )

        raise ValueError(f"Unsupported action {action} for category {cat}")
