# Requirements — Challenge Contract Traceability

This document maps every requirement from `AGENTS.md` §6, `problem_statement.md`, and
`README.md` to a traceable identifier. Implementation must satisfy all of these.

## R1: Output Format

| ID | Requirement | Source |
|---|---|---|
| R1.1 | File: root-level `output.csv` | §6.3 |
| R1.2 | Header: `case_id,deletion_status,steps_json` | §6.3 |
| R1.3 | Exactly 518 data rows (one per `case_id` in `deletion_requests.csv`) | §6.3 |
| R1.4 | Rows sorted by `case_id` | §6.3 |
| R1.5 | `deletion_status` ∈ {`COMPLETE`, `INCOMPLETE`, `NOT_APPLICABLE`} | §6.3 |
| R1.6 | `steps_json` is a valid JSON array | §6.3 |
| R1.7 | Step numbers consecutive from 1 | §6.3 |
| R1.8 | Phase order: `FINDING` → `REMEDIATION` → `VERIFICATION` | §6.3 |
| R1.9 | `NOT_APPLICABLE` → `steps_json = []` | §6.3 |
| R1.10 | JSON key order and whitespace ignored; array order significant | §6.3 |

## R2: Step Schema

| ID | Requirement | Source |
|---|---|---|
| R2.1 | Each step has exactly: `step_no`, `phase`, `system_id`, `resource_id`, `operation`, `state`, `evidence_id` | §6.3 |
| R2.2 | Only allowed operations per phase (§6.4 tables) | §6.4 |
| R2.3 | No invented phases, operations, or states | §6.4 |

## R3: Deletion Decision Rules

| ID | Requirement | Source |
|---|---|---|
| R3.1 | Determine if `request_text` authorizes deletion (non-deletion → `NOT_APPLICABLE`) | §6.5 |
| R3.2 | Resolve current + historical identifiers for the subject | §6.5 |
| R3.3 | Reconstruct true state at `audit_at`; ignore later evidence | §6.5 |
| R3.4 | Apply `deletion_rules.csv` to every relevant record | §6.5 |
| R3.5 | `ACCOUNT_TOMBSTONE`: preserve stable `user_id`, remove name/email/phone/hash | §6.5 |
| R3.6 | `COMPLETE` only when all copies treated + no active recreate path + retained records available | §6.5 |
| R3.7 | For `INCOMPLETE`: report every policy violation + recreation risk with evidence | §6.5 |
| R3.8 | Remediation order: disable data flows + block restores → then downstream copies → source records | §6.5 |
| R3.9 | Verification must cover required final state for each remediated record/process | §6.5 |

## R4: Evidence Rules

| ID | Requirement | Source |
|---|---|---|
| R4.1 | Activity logs / workflow statuses / system messages are claims, not proof | §6.6 |
| R4.2 | Use `evidence_files.csv` to locate files; inspect contents, not just manifest | §6.6 |
| R4.3 | Match evidence via identifiers, hashes, resource IDs, timestamps, grounded links | §6.6 |
| R4.4 | Images + PDFs are ordinary business artifacts; extract facts, not verdicts | §6.6 |
| R4.5 | SQL evidence may be primary / regional / reporting / failover replicas | §6.6 |
| R4.6 | Findings cite `file_id`, `activity_id`, or `audit_id` | §6.6 |
| R4.7 | `COMPLETE` verification steps cite evidence proving current compliant state | §6.6 |
| R4.8 | Remediation + future verification for `INCOMPLETE` → `evidence_id = ""` | §6.6 |
| R4.9 | Never cite organizer-only truth or evidence captured after `audit_at` | §6.6 |

## R5: Submission Artifacts

| ID | Requirement | Source |
|---|---|---|
| R5.1 | `code.zip` with runnable solution, prompts, config, `README.md` | §6.9 |
| R5.2 | `code/evaluation/evaluation_report.md` | §6.8 |
| R5.3 | `code/evaluation/usage_report.md` | §6.8 |
| R5.4 | `output.csv` at repository root | §6.7 |
| R5.5 | `log.txt` as chat transcript | §6.9 |
| R5.6 | No secrets, dataset files, venvs, or nested archives in `code.zip` | §6.9 |
| R5.7 | No organizer-only files, hardcoded labels, or case-family shortcuts | §6.7 |

## R6: Evaluation Reports

| ID | Requirement | Source |
|---|---|---|
| R6.1 | Case-level deletion-status accuracy | §6.8 |
| R6.2 | Step-level and field-level accuracy | §6.8 |
| R6.3 | Sequence accuracy | §6.8 |
| R6.4 | At least 3 additional evaluation cases created by participant | §6.8 |
| R6.5 | Failures found and improvements made | §6.8 |
| R6.6 | Usage report: model providers, calls, tokens, cost | §6.8 |

## R7: Step Ordering (within each phase)

| ID | Requirement | Source |
|---|---|---|
| R7.1 | Within each phase, follow operation order from §6.4 table | README |
| R7.2 | Then sort by `system_id` ascending | README |
| R7.3 | Then sort by `resource_id` ascending | README |

### Operation Order Reference

**FINDING**: `REPORT_REMAINING_RECORD` → `REPORT_EXPOSED_PII` → `REPORT_ACTIVE_DATA_FLOW` → `REPORT_RESTORE_RISK`

**REMEDIATION**: `DISABLE_DATA_FLOW` → `BLOCK_RESTORE` → `DELETE_RECORD` → `REDACT_RECORD` → `ANONYMIZE_RECORD`

**VERIFICATION**: `VERIFY_RECORD_ABSENT` → `VERIFY_RECORD_PRESENT` → `VERIFY_RECORD_REDACTED` → `VERIFY_RECORD_ANONYMIZED` → `VERIFY_DATA_FLOW_DISABLED` → `VERIFY_RESTORE_BLOCKED`
