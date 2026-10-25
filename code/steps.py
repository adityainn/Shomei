"""Challenge-compliant step generator and sequence builder for Shomei.

Builds ordered, traceable Step arrays following the official challenge contract:
- Consecutive step numbering starting at 1
- Canonical Phase ordering: FINDING -> REMEDIATION -> VERIFICATION
- Canonical Operation ordering within each phase
- Deterministic tie-breaking: system_id ascending, resource_id ascending
- COMPLETE cases contain only verification steps citing verified evidence
- INCOMPLETE cases contain findings (citing evidence), remediations (empty evidence),
  and verifications (empty evidence)
- NOT_APPLICABLE cases contain empty step array
"""

from __future__ import annotations

from typing import List

from decision import DecisionResult
from models import CaseOutput, DeletionStatus, Operation, Phase, State, Step


class StepBuilder:
    """Constructs and validates challenge-compliant Step sequences from DecisionResults."""

    def build_case_output(self, decision: DecisionResult) -> CaseOutput:
        """Construct a validated CaseOutput from a DecisionResult."""
        if decision.deletion_status == DeletionStatus.NOT_APPLICABLE:
            out = CaseOutput(
                case_id=decision.case_id,
                deletion_status=DeletionStatus.NOT_APPLICABLE,
                steps=[],
            )
            out.validate()
            return out

        raw_steps: List[Step] = []

        if decision.deletion_status == DeletionStatus.COMPLETE:
            # COMPLETE cases: Verification steps only, citing verified evidence_id
            for ev in decision.compliant:
                res = decision.discovered_resources.get(ev.resource_id)
                ev_id = res.evidence_id if res else ""
                raw_steps.append(
                    Step(
                        step_no=0,
                        phase=Phase.VERIFICATION.value,
                        system_id=ev.system_id,
                        resource_id=ev.resource_id,
                        operation=ev.verification_op.value,
                        state=ev.expected_state.value,
                        evidence_id=ev_id,
                    )
                )

        elif decision.deletion_status == DeletionStatus.INCOMPLETE:
            # INCOMPLETE cases:
            # 1. Findings (citing evidence_id)
            for v in decision.violations:
                res = decision.discovered_resources.get(v.resource_id)
                ev_id = res.evidence_id if res else ""
                # Observed state for finding: PRESENT for records/PII, ACTIVE for flows/restore
                obs_state = res.observed_state.value if res else State.PRESENT.value
                raw_steps.append(
                    Step(
                        step_no=0,
                        phase=Phase.FINDING.value,
                        system_id=v.system_id,
                        resource_id=v.resource_id,
                        operation=v.finding_op.value if v.finding_op else Operation.REPORT_REMAINING_RECORD.value,
                        state=obs_state,
                        evidence_id=ev_id,
                    )
                )

            # 2. Remediations (evidence_id must be "")
            for v in decision.violations:
                raw_steps.append(
                    Step(
                        step_no=0,
                        phase=Phase.REMEDIATION.value,
                        system_id=v.system_id,
                        resource_id=v.resource_id,
                        operation=v.remediation_op.value if v.remediation_op else Operation.DELETE_RECORD.value,
                        state=v.expected_state.value,
                        evidence_id="",
                    )
                )

            # 3. Verifications for ALL resources (violations remediated + already compliant)
            # evidence_id must be "" for future post-remediation verifications
            seen_verif_resources = set()

            for v in decision.violations:
                if v.resource_id in seen_verif_resources:
                    continue
                seen_verif_resources.add(v.resource_id)
                raw_steps.append(
                    Step(
                        step_no=0,
                        phase=Phase.VERIFICATION.value,
                        system_id=v.system_id,
                        resource_id=v.resource_id,
                        operation=v.verification_op.value,
                        state=v.expected_state.value,
                        evidence_id="",
                    )
                )

            for c in decision.compliant:
                if c.resource_id in seen_verif_resources:
                    continue
                seen_verif_resources.add(c.resource_id)
                raw_steps.append(
                    Step(
                        step_no=0,
                        phase=Phase.VERIFICATION.value,
                        system_id=c.system_id,
                        resource_id=c.resource_id,
                        operation=c.verification_op.value,
                        state=c.expected_state.value,
                        evidence_id="",
                    )
                )

        # Canonical sort: Phase -> Operation order -> system_id -> resource_id
        sorted_steps = sorted(raw_steps, key=lambda s: s.sort_tuple())

        # Assign consecutive step_no starting at 1
        final_steps: List[Step] = []
        for idx, s in enumerate(sorted_steps, start=1):
            renumbered = Step(
                step_no=idx,
                phase=s.phase,
                system_id=s.system_id,
                resource_id=s.resource_id,
                operation=s.operation,
                state=s.state,
                evidence_id=s.evidence_id,
            )
            renumbered.validate()
            final_steps.append(renumbered)

        case_out = CaseOutput(
            case_id=decision.case_id,
            deletion_status=decision.deletion_status,
            steps=final_steps,
        )
        case_out.validate()
        return case_out
