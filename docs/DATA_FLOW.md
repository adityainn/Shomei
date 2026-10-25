# Data Flow — End-to-End Investigation Process

> See [data_flow.mmd](./diagrams/data_flow.mmd) for the visual diagram.

## Pipeline Stages

### Stage 1: Initialization (one-time, deterministic)

```
Load CSVs → Build identity lookup → Build evidence index → Load deletion rules
```

1. **Load CSV files** into memory: `deletion_requests.csv` (518 rows),
   `user_identities.csv` (850 users), `user_audit_log.csv` (306 entries),
   `system_activity.csv` (4,011 events), `deletion_rules.csv` (15 rules),
   `evidence_files.csv` (94 files)
2. **Build identity lookup**: email → user_id → full identity profile
3. **Build audit trail**: user_id → list of historical field changes (email, phone, email_hash)
4. **Parse evidence files**:
   - SQL files (24 files): read as text, optionally execute with SQLite for structured queries
   - JSON records (28 files): parse into Python dicts with nested service exports
   - Log files (26 files): read as text, extract structured events per line
   - PDFs (4 files): queue for AI-assisted extraction
   - Images (11 files): queue for AI-assisted extraction
   - Text records (1 file): read as text
5. **Build inverted index**: for text-based evidence, extract all identifiers
   (emails, phones, user_ids, resource_ids) → map to (file_id, line/record context)

### Stage 2: Per-Case Processing

For each of the 518 cases:

#### 2a. Request Intent Classification (AI-assisted)

```
request_text → LLM classifier → DELETION | NON_DELETION
```

- If NON_DELETION: emit `(case_id, NOT_APPLICABLE, [])` and continue to next case
- If DELETION: proceed to identity resolution

#### 2b. Identity Resolution (deterministic with fallback)

```
case.email → identity lookup → user_id + all historical identifiers
```

1. Look up `email` in `user_identities.csv` (current email field)
2. If not found: search `user_audit_log.csv` for historical email changes where
   `old_value` matches the request email → find `user_id` → get current identity
3. Build complete identifier set:
   - Current: email, phone, email_hash, user_id, name
   - Historical: all previous emails, phones, email_hashes from audit log

#### 2c. Evidence Gathering (deterministic + AI-assisted)

```
identifier set → evidence index search → filter by audit_at → case evidence bundle
```

1. **Text evidence search**: Query inverted index with all identifiers (current + historical).
   Collect matching `(file_id, context snippet)` pairs.
2. **SQL evidence query**: For each SQL snapshot captured at ≤ `audit_at`, query:
   - `customer_profiles` for email/user_id/account records
   - `customer_search_documents` for search index entries
   - `customer_analytics_profiles` for analytics records
   - `support_records` for support ticket data
   - `customer_exports` for export entries
   - `connector_subscriptions` for active data flows
   - `backup_restore_entries` for restore risks
   - `security_audit_records` for retained audit records
3. **JSON record search**: Match service resource exports and snapshot bundles
   for records referencing user identifiers
4. **Log evidence scan**: Parse structured log entries for resource lookups
   showing presence/absence of user records
5. **Multimodal evidence (AI-assisted)**: Send relevant images/PDFs to LLM for
   extraction of visible identifiers, resource states, and system information

#### 2d. State Reconstruction at audit_at (deterministic + AI-assisted)

For each discovered resource:
1. Determine latest evidence captured at ≤ `audit_at`
2. Determine resource state from evidence:
   - SQL: record present → PRESENT; no row → ABSENT; nullified PII fields → REDACTED; anonymized → ANONYMIZED
   - Logs: lookup result=hit → PRESENT; 404 → ABSENT
   - JSON snapshots: resource listed → PRESENT; absent → ABSENT
3. Cross-reference `system_activity.csv` events for the resource (claims, not proof)
4. AI-assisted state interpretation for ambiguous evidence

#### 2e. Policy Application (deterministic)

For each resource in state at `audit_at`:
1. Categorize the resource (map system_id/resource_id pattern to data category)
2. Look up `deletion_rules.csv` for the matching `data_category`
3. Determine required action: DELETE, REDACT, ANONYMIZE, RETAIN
4. Compare actual state vs required state
5. Identify violations:
   - Record present that should be deleted → `REPORT_REMAINING_RECORD`
   - PII exposed that should be redacted/anonymized → `REPORT_EXPOSED_PII`
   - Active data flow → `REPORT_ACTIVE_DATA_FLOW`
   - Restore access not blocked → `REPORT_RESTORE_RISK`

#### 2f. Decision (deterministic)

```
violations == 0 → COMPLETE
violations > 0  → INCOMPLETE
```

#### 2g. Step Generation (deterministic)

**For COMPLETE cases:**
- Generate VERIFICATION steps for each relevant resource with evidence citations
- Order: VERIFY_RECORD_ABSENT → VERIFY_RECORD_PRESENT → VERIFY_RECORD_REDACTED →
  VERIFY_RECORD_ANONYMIZED → VERIFY_DATA_FLOW_DISABLED → VERIFY_RESTORE_BLOCKED

**For INCOMPLETE cases:**
- FINDING phase: one step per violation (evidence-cited)
- REMEDIATION phase: one step per violation (evidence_id = "")
  - Order: DISABLE_DATA_FLOW → BLOCK_RESTORE → DELETE_RECORD → REDACT_RECORD → ANONYMIZE_RECORD
- VERIFICATION phase: one step per resource that needs final state confirmation (evidence_id = "")
- Number steps consecutively starting at 1

### Stage 3: Output Assembly (deterministic)

```
all case results → sort by case_id → serialize to CSV → validate → write output.csv
```

1. Collect all 518 case results
2. Sort by `case_id` (ascending)
3. Serialize each row: `case_id,deletion_status,"[{...}]"`
4. Validate: 518 data rows, valid JSON, consecutive step numbers, correct phases
5. Write to `output.csv` at repository root
