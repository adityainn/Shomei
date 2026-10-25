# Evaluation Plan

## Metrics

### Primary Metrics

| Metric | Description | How to Measure |
|---|---|---|
| **Status Accuracy** | % of cases with correct `deletion_status` | Compare against sample_output.csv (32 cases) |
| **Step Completeness** | % of required steps present | Compare step sets per case |
| **Step Correctness** | % of steps with all 7 fields correct | Field-by-field comparison |
| **Sequence Accuracy** | % of cases with correctly ordered steps | Array order comparison |
| **Evidence Accuracy** | % of evidence_id citations that are correct | Compare cited evidence |

### Secondary Metrics

| Metric | Description |
|---|---|
| Identity resolution recall | % of historical identifiers correctly resolved |
| Finding precision | % of reported findings that are true violations |
| Finding recall | % of true violations that are reported |
| Retention compliance | % of RETAIN-required records correctly preserved |
| False-complete rate | % of INCOMPLETE cases incorrectly marked COMPLETE |
| False-incomplete rate | % of COMPLETE cases incorrectly marked INCOMPLETE |
| NOT_APPLICABLE accuracy | % of non-deletion requests correctly identified |

### Operational Metrics

| Metric | Description |
|---|---|
| Runtime (total) | Wall-clock time to process all 518 cases |
| Runtime (per case) | Average time per case |
| Model calls | Total LLM API calls |
| Token usage (input) | Total input tokens |
| Token usage (output) | Total output tokens |
| Estimated cost | Total API cost |
| Cost per case | Average API cost per case |

## Test Methodology

### Phase 1: Sample Validation (32 cases)

Use `sample_output.csv` (32 known-correct answers) as ground truth:

1. Run pipeline on `sample_deletion_requests.csv`
2. Compare output row-by-row against `sample_output.csv`
3. Score:
   - Status match: 32/32 target
   - Step-by-step comparison for all 32 cases
   - JSON array order comparison

### Phase 2: Synthetic Test Cases (minimum 3 required)

#### Synthetic Case 1: Clear Non-Deletion Request (NOT_APPLICABLE)

**Scenario**: Request text says "I'd like a copy of my data for my records"
- Expected status: `NOT_APPLICABLE`
- Expected steps: `[]`
- Tests: intent classification accuracy

**Design**: Create a case with deletion-like email, reported_status=COMPLETE,
but request_text clearly asks for data export, not deletion.

#### Synthetic Case 2: Multi-Violation INCOMPLETE Case

**Scenario**: User with historical email change, data found in:
- Search index (should be deleted)
- Analytics (should be anonymized, still has PII)
- Active data flow connector
- Backup with restore enabled

Expected:
- Status: `INCOMPLETE`
- 4 findings, 4 remediation steps, 6+ verification steps
- Correct remediation ordering (disable → block → delete → anonymize)

#### Synthetic Case 3: Account Tombstone with Exposed PII

**Scenario**: Account deleted, tombstone exists with `user_id` preserved,
but name and email still visible in tombstone record.

Expected:
- Status: `INCOMPLETE`
- Finding: `REPORT_EXPOSED_PII` on tombstone
- Remediation: `REDACT_RECORD` on tombstone
- Verification: `VERIFY_RECORD_REDACTED` on tombstone

#### Additional Synthetic Cases (stretch)

4. **COMPLETE case with multiple verification types** (absent, present, redacted, anonymized, disabled, blocked)
5. **Historical email match case** — request email matches old email from audit log
6. **Temporal boundary case** — evidence exists both before and after `audit_at`

### Phase 3: Full Dataset Run (518 cases)

1. Run pipeline on full `deletion_requests.csv`
2. Validate output format:
   - Exactly 518 data rows
   - Header: `case_id,deletion_status,steps_json`
   - Sorted by `case_id`
   - Valid JSON in every `steps_json`
   - Consecutive step numbers in every row
   - No empty `case_id` or `deletion_status`
3. Statistical analysis:
   - Status distribution (expect mix of COMPLETE, INCOMPLETE, NOT_APPLICABLE)
   - Average steps per case by status
   - Evidence utilization (% of evidence files referenced)

## Edge Cases to Test

| Edge Case | Test Strategy |
|---|---|
| Request in Japanese (case_14 pattern) | Verify intent classification handles CJK text |
| Request in Spanish (case_02 pattern) | Verify non-English deletion requests detected |
| Request in French (case_03 pattern) | Verify non-English deletion requests detected |
| Email case mismatch | Evidence may have uppercase email (e.g., `JULES-LAURENT@PROTON.ME`) |
| Historical email lookup | Request email matches `old_value` in audit log, not current |
| Multiple evidence sources for same resource | Choose most recent before `audit_at` |
| SQL replica drift | Different replicas show different states |
| Tombstone with PII | Account tombstone still has name/email visible |
| Active data flow with disabled connector | `enabled=0` vs `enabled=1` check |
| Backup with `restore_allowed=0` vs `restore_allowed=1` | State determines BLOCK_RESTORE need |
| Security audit within retention period | Must be RETAINED, not deleted |
| Evidence captured after `audit_at` | Must be excluded from consideration |
| User with no evidence at all | Likely COMPLETE if deletion worker processed |
| `reported_status=COMPLETE` but data remains | Core challenge scenario |
| `reported_status=NOT_STARTED` but data gone | Check if deletion happened anyway |

## Validation Pipeline

```python
def validate_output(output_path):
    """Deterministic validation of output.csv"""
    # 1. Check file exists at repo root
    # 2. Parse CSV, verify header
    # 3. Count rows (must be 518)
    # 4. Check case_ids match deletion_requests.csv exactly
    # 5. Verify sorting by case_id
    # 6. For each row:
    #    a. deletion_status in {COMPLETE, INCOMPLETE, NOT_APPLICABLE}
    #    b. steps_json parses as valid JSON array
    #    c. Step numbers consecutive from 1
    #    d. Phases in order: FINDING → REMEDIATION → VERIFICATION
    #    e. NOT_APPLICABLE → steps_json == []
    #    f. All 7 fields present in each step
    #    g. Operations match allowed set for their phase
    #    h. States match allowed set for their operation
    # 7. Report validation results
```
