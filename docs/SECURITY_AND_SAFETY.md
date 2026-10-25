# Security and Safety

## Secret Management

| Requirement | Implementation |
|---|---|
| API keys never committed | Read from `GEMINI_API_KEY` environment variable |
| `.env` file for local dev | Add `.env` to `.gitignore`; document in README |
| No secrets in `log.txt` | Redact before writing; validate log entries post-write |
| No secrets in `code.zip` | Pre-submission checklist; exclude `.env` in packaging |
| No secrets in `output.csv` | Output contains only case_ids, statuses, and step JSON |

## Privacy Considerations

- All data in the challenge is **fictional** (confirmed by AGENTS.md §7)
- Never include real personal data in logs, code, or outputs
- The solution processes fictional PII (names, emails, phones) from the dataset —
  treat these with the same care as real data for good practice
- Do not store intermediate results containing PII outside the working directory

## Evidence Trust Model

The challenge explicitly states that **reported statuses and operation results are claims**.

### Trust Hierarchy

1. **High trust**: Direct evidence (SQL snapshots, JSON records, log readback traces)
   showing actual record state at a specific time
2. **Medium trust**: Structured log entries showing system behavior
   (index queries, profile lookups with HTTP status codes)
3. **Low trust**: `system_activity.csv` entries with `reported_result` —
   these are workflow claims, not proof of state
4. **No trust**: `reported_status` field in `deletion_requests.csv` —
   this is the value being audited, not evidence

### Evidence Validation Rules

- A finding must cite a participant-visible `file_id`, `activity_id`, or `audit_id`
- Evidence `captured_at` must be ≤ case's `audit_at`
- Cross-check multiple evidence sources when available
- Prefer the most recent evidence captured before `audit_at`
- SQL replicas may drift from primary — this is expected and relevant to findings

## Safe Policy Handling

### Deletion Rule Application Safety

1. **RETAIN rules take priority** — never delete data that policy requires to be retained
   (security audit logs within retention period, active legal holds, backup archives)
2. **REDACT preserves the record** — only removes prohibited identifiers
   (name, email, phone, email_hash) from SUPPORT_MESSAGE, EMAIL_DELIVERY_LOG,
   ACCOUNT_TOMBSTONE records
3. **ANONYMIZE preserves the record** — irreversibly unlinks from user
   (ANALYTICS_PROFILE, PRODUCT_TELEMETRY)
4. **DELETE removes entirely** — USER_PROFILE, SECONDARY_IDENTIFIER,
   SEARCH_INDEX_ENTRY, CACHE_ENTRY, SUPPORT_ATTACHMENT, USER_EXPORT, MARKETING_PROFILE
5. **ACCOUNT_TOMBSTONE special case** — preserve `user_id`, remove all direct identifiers

### Safe Ordering in Remediation

1. DISABLE_DATA_FLOW first — stop processes that can recreate data
2. BLOCK_RESTORE second — prevent backups from restoring deleted data
3. Then DELETE, REDACT, ANONYMIZE records — safe after flows are stopped

### Conservative Defaults

- If evidence is ambiguous → report as INCOMPLETE (err on the side of caution)
- If a record's category is unclear → treat as requiring deletion
- If `request_text` intent is unclear → treat as deletion request
  (false-positive on deletion is safer than missing a real deletion request)

## Logging Safety

Per AGENTS.md §5.4, never log:
- API keys, tokens, session cookies, OAuth codes, credentials, private keys
- Sensitive configuration or real personal data
- Full contents of large files or binary blobs (reference by path)
