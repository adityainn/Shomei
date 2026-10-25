# Known Limitations

## Verified Limitations

### L1: No Ground Truth for Full Dataset
- Only 32 of 518 cases have known-correct answers (`sample_output.csv`)
- Cannot measure full-dataset accuracy until submission
- **Mitigation**: Maximize sample accuracy, create synthetic cases, validate format rigorously

### L2: Multimodal Evidence May Be Lossy
- 11 PNG screenshots and 4 PDFs require AI-assisted extraction
- LLM vision may miss small text, misread identifiers, or hallucinate
- **Mitigation**: Cross-reference multimodal findings with structured evidence;
  use multimodal only as supplementary confirmation

### L3: Evidence Coverage Uncertainty
- Not every user will appear in every evidence file
- Some users may appear only in multimodal evidence (images/PDFs)
- Some evidence may contain information relevant to users not in the request set
- **Mitigation**: Cast a wide net (search all identifier forms), but only report
  findings backed by specific evidence

### L4: Temporal Reasoning Complexity
- `audit_at` filtering requires comparing ISO-8601 timestamps correctly
- Evidence files cover January 2026 through October 2026
- A resource may be present in one snapshot and absent in a later one
- **Mitigation**: Unit test timestamp comparison logic; use most recent evidence ≤ `audit_at`

### L5: Email Case Sensitivity
- Evidence may contain emails in different cases (e.g., `JULES-LAURENT@PROTON.ME` vs `jules-laurent@proton.me`)
- Email addresses should be compared case-insensitively per RFC 5321
- **Mitigation**: Normalize all emails to lowercase before comparison

### L6: Sample Output Has No NOT_APPLICABLE Cases
- All 32 sample cases are either COMPLETE or INCOMPLETE
- No ground truth for NOT_APPLICABLE classification
- Only 5 obvious non-deletion requests identified in full dataset
- **Mitigation**: Test intent classifier on known non-deletion phrases;
  err on side of treating ambiguous requests as deletion

## Unresolved Questions

### Q1: How Are `resource_id` Values Discovered?
The sample output references specific resource IDs (e.g., `account_005`, `search_1993`).
These must be found through:
- SQL snapshot queries matching user identifiers
- JSON snapshot bundles matching user identifiers
- Log readback traces showing resource lookups
- System activity entries referencing the resource

**Open**: Need to verify that our evidence search consistently finds the same resource IDs
as the golden answers.

### Q2: Which Evidence File to Cite?
When multiple evidence files confirm the same finding, which `file_id` should be cited?
- Sample output pattern: appears to cite the most comprehensive/recent evidence ≤ `audit_at`
- Some cases cite specific evidence types (e.g., `evidence_54` for account_service lookups,
  `evidence_92` for resource_lookup_trace snapshots)
- **Approach**: Use the evidence file that most directly shows the resource state

### Q3: What Constitutes "Shared Context" for SUPPORT_MESSAGE?
Rule 05 says REDACT when "Conversation contains shared customer, agent, or order context."
- Does every support message qualify? The sample output uses REDACT for support records
  that have PII, and DELETE when they belong only to the subject.
- **Approach**: If support record contains PII (requester_email, requester_phone, requester_name),
  apply REDACT. If no PII and belongs only to subject, it was likely already handled.

### Q4: How Are COMPLETE Cases Verified?
For COMPLETE cases, verification steps must cite evidence:
- Sample shows `evidence_54` (failover replica), `evidence_56` (analytics report),
  `evidence_92` (resource_lookup_trace), `evidence_94` (resource_lookup_trace),
  `evidence_51` (snapshot bundle)
- **Pattern**: Use the most recent evidence file ≤ `audit_at` that covers the relevant system

### Q5: Activity Log vs Evidence Priority
`system_activity.csv` shows deletion_worker performing DELETE_RECORD with SUCCESS.
If evidence confirms the record is gone, do we trust both? Or only evidence?
- **Approach**: Activity is a claim. Evidence confirms. If evidence contradicts activity, trust evidence.

### Q6: Marketing Platform and Email Delivery Log Resources
- `marketing_*` resources and `marketing_platform` appear in some evidence but not in sample output
- Email delivery logs appear in evidence but not in sample output
- **Question**: Under what circumstances do these appear as findings?
- **Approach**: Apply rules (DELETE for marketing, REDACT for email delivery) when evidence
  shows these resources exist with user data

## Uncertainties

### U1: Evidence File Assignment to Cases
The evidence manifest (`evidence_files.csv`) does not specify which case or user each
evidence file relates to. The solution must match evidence to cases through content analysis.
This is a core challenge requirement but introduces uncertainty about completeness.

### U2: PDF and Image Content Reliability
Without running the actual multimodal analysis, we cannot confirm what information
the PDFs and images contain. The pre-analysis (filenames and origins) suggests:
- PDFs: account history, delivery attachments, legal retention, security retention
- Images: admin consoles, analytics views, backup consoles, search inspectors

### U3: LLM Classification Accuracy on Multilingual Text
Intent classification must handle English, Spanish, French, Japanese, and potentially
other languages. Classification accuracy is uncertain until tested.

### U4: Evidence Exhaustiveness
We cannot confirm that all relevant resources for every user appear in the evidence.
The solution must handle cases where:
- A resource exists but appears in no evidence file
- A resource appears only in system_activity but not in evidence
- A resource appears in evidence but not in system_activity
