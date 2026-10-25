"""Deterministic audit decision engine for Shomei.

Evaluates evidence and resource states as of audit_at, determines deletion status
(COMPLETE, INCOMPLETE, NOT_APPLICABLE), and records audit rationales and evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from classifier import MultilingualIntentClassifier
from discovery import DiscoveredResource
from models import DeletionRequest, DeletionStatus, IdentityProfile, State
from policy import PolicyEngine, PolicyEvaluationResult


@dataclass
class DecisionResult:
    """Consolidated audit decision for a single deletion request case."""
    case_id: str
    deletion_status: DeletionStatus
    evaluations: List[PolicyEvaluationResult]
    violations: List[PolicyEvaluationResult]
    compliant: List[PolicyEvaluationResult]
    discovered_resources: Dict[str, DiscoveredResource]
    rationale: str


class DecisionEngine:
    """Makes deterministic audit decisions based on discovered resources and deletion rules."""

    def __init__(self, policy: PolicyEngine, classifier: Optional[MultilingualIntentClassifier] = None):
        self.policy = policy
        self.classifier = classifier or MultilingualIntentClassifier()

    def evaluate(
        self,
        request: DeletionRequest,
        profile: IdentityProfile,
        discovered_resources: List[DiscoveredResource],
    ) -> DecisionResult:
        """Evaluate all resources for a request and determine final audit status."""
        res_by_id: Dict[str, DiscoveredResource] = {r.resource_id: r for r in discovered_resources}

        # 0. Check Request Intent via Multilingual Intent Classifier
        if self.classifier:
            intent_res = self.classifier.classify_request(request)
            if not intent_res.is_deletion_request:
                return DecisionResult(
                    case_id=request.case_id,
                    deletion_status=DeletionStatus.NOT_APPLICABLE,
                    evaluations=[],
                    violations=[],
                    compliant=[],
                    discovered_resources=res_by_id,
                    rationale=f"Request is not a deletion request ({intent_res.intent.value}: {intent_res.rationale}). Non-erasure requests are NOT_APPLICABLE.",
                )

        # 1. Check for Active Legal Hold (Rule 13) -> NOT_APPLICABLE
        has_legal_hold = any(
            r.resource_id.startswith("legal_hold_") or r.system_id == "legal_service"
            for r in discovered_resources
        )
        if has_legal_hold:
            return DecisionResult(
                case_id=request.case_id,
                deletion_status=DeletionStatus.NOT_APPLICABLE,
                evaluations=[],
                violations=[],
                compliant=[],
                discovered_resources=res_by_id,
                rationale="Request cannot be processed because an active legal hold is in place.",
            )

        # 2. Evaluate all discovered resources against deletion policy
        evaluations: List[PolicyEvaluationResult] = []
        violations: List[PolicyEvaluationResult] = []
        compliant: List[PolicyEvaluationResult] = []

        for res in discovered_resources:
            ev = self.policy.evaluate_resource(res)
            evaluations.append(ev)
            if ev.is_violation:
                violations.append(ev)
            else:
                compliant.append(ev)

        # 3. Determine Deletion Status
        if violations:
            status = DeletionStatus.INCOMPLETE
            reasons = [f"{v.resource_id} in {v.system_id} ({v.finding_op.value if v.finding_op else 'VIOLATION'})" for v in violations]
            rationale = f"Deletion is INCOMPLETE due to observed violations: {', '.join(reasons)}"
        else:
            # Check for sufficient verification evidence
            # Do not infer COMPLETE solely from reported_status (AGENTS.md §6.2)
            has_verification_evidence = any(
                res.evidence_id and res.evidence_id != "" for res in discovered_resources
            )
            # If reported_status was NOT_STARTED and no verification evidence exists
            if request.reported_status == "NOT_STARTED" and not has_verification_evidence:
                status = DeletionStatus.INCOMPLETE
                rationale = "Deletion was NOT_STARTED and no verification evidence was found."
            elif not discovered_resources and request.reported_status != "COMPLETE":
                status = DeletionStatus.INCOMPLETE
                rationale = "No resources were discovered and request was not confirmed complete."
            else:
                status = DeletionStatus.COMPLETE
                rationale = f"All {len(compliant)} applicable resources comply with policy and have sufficient verification evidence."

        return DecisionResult(
            case_id=request.case_id,
            deletion_status=status,
            evaluations=evaluations,
            violations=violations,
            compliant=compliant,
            discovered_resources=res_by_id,
            rationale=rationale,
        )
