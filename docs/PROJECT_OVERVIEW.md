# Project Overview

## Problem Statement

Northstar Shop's deletion workflow marks customer data removal as **"Complete"** while
personal data persists across secondary databases, replicas, logs, support attachments,
exports, search indexes, analytics records, archives, and backups. Synchronization and
restore processes can also recreate data that was deleted from its source.

**Shomei** must be an AI-powered deletion audit agent that:

1. Determines whether each request actually authorizes deletion.
2. Resolves the subject's current and historical identifiers.
3. Reconstructs the true data state at the case's `audit_at` time from evidence.
4. Applies the organization's deletion policy to every relevant record.
5. Reports whether the deletion is `COMPLETE`, `INCOMPLETE`, or `NOT_APPLICABLE`.
6. For incomplete deletions: reports remaining records, exposed PII, active data flows,
   restore risks, and produces ordered remediation + verification steps.
7. For complete deletions: produces evidence-backed verification steps proving compliance.

## Objectives

| Objective | Metric |
|---|---|
| Correct deletion status for all 518 cases | Status accuracy |
| Accurate identity resolution (current + historical) | Identity recall |
| Complete discovery of remaining data and recreation risks | Finding completeness |
| Correct evidence citations | Evidence precision |
| Proper policy application per `deletion_rules.csv` | Policy compliance |
| Correct, complete, ordered remediation and verification | Step sequence accuracy |
| Valid `output.csv` with 518 rows, sorted by `case_id` | Schema validity |

## Users

- **HackerRank evaluators**: automated grader + AI interviewer
- **Developer (participant)**: builds, tests, and submits the solution

## Scope

### In Scope
- Processing all 518 deletion requests in `dataset/deletion_requests.csv`
- All evidence types: SQL snapshots, JSON records, structured logs, PDFs, images, text
- 15 deletion rules across 15 data categories
- Identity resolution via `user_identities.csv` + `user_audit_log.csv`
- System activity correlation via `system_activity.csv` (4,011 events)
- Evidence correlation via `evidence_files.csv` (94 evidence files)
- Multimodal evidence: 11 PNG screenshots, 4 PDF documents
- Multi-language request text interpretation (EN, ES, FR, JP, and others)

### Out of Scope
- Building the actual Northstar Shop platform
- Real-time deletion execution
- Organizer-only files, golden answers, or generator internals
