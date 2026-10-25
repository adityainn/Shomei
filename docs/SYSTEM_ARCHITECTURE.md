# System Architecture

> See [component_architecture.mmd](./diagrams/component_architecture.mmd) for the visual diagram.
> See [system_context.mmd](./diagrams/system_context.mmd) for the system context diagram.

## Architecture Principles

1. **Deterministic where possible, AI-assisted where beneficial** — Status constraints,
   ordering, schema validation, and CSV serialization are deterministic. AI interprets
   request text, analyzes multimodal evidence, and correlates findings across sources.
2. **Single-pass pipeline** — Each case flows through a linear pipeline; no complex
   orchestration, no vector databases, no external services beyond the LLM API.
3. **Evidence-first decisions** — Every finding must be backed by participant-visible
   evidence. Claims from `system_activity.csv` are starting points, not conclusions.
4. **Fail-safe defaults** — When uncertain, prefer `INCOMPLETE` over `COMPLETE`.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Shomei Pipeline (code/main.py)             │
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────────┐  │
│  │ Data     │→ │ Case     │→ │ Case     │→ │ Output        │  │
│  │ Loader   │  │ Builder  │  │ Processor│  │ Serializer    │  │
│  └──────────┘  └──────────┘  └──────────┘  └───────────────┘  │
│       ↓             ↓             ↓                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                     │
│  │ Evidence │  │ Identity │  │ Decision │                      │
│  │ Index    │  │ Resolver │  │ Engine   │                      │
│  └──────────┘  └──────────┘  └──────────┘                     │
│                                    ↓                            │
│                             ┌──────────┐                       │
│                             │ Step     │                        │
│                             │ Builder  │                        │
│                             └──────────┘                       │
└─────────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

### 1. Data Loader (Deterministic) — `EXISTING: None`

- Loads all CSV files: `deletion_requests.csv`, `user_identities.csv`,
  `user_audit_log.csv`, `system_activity.csv`, `deletion_rules.csv`,
  `evidence_files.csv`
- Parses SQL evidence files into SQLite in-memory databases
- Parses JSON evidence records into structured dicts
- Reads text-based evidence (logs, handover docs) as strings
- Indexes evidence by `file_id` with metadata (path, origin, `captured_at`)

### 2. Evidence Index (Deterministic) — `PROPOSED`

- Pre-processes all 94 evidence files
- For text evidence (SQL, JSON, logs, text): extracts all identifiers (emails, phones,
  hashes, user IDs, resource IDs) into a searchable inverted index
- For binary evidence (images, PDFs): requires AI-assisted extraction at query time
- Provides `search(identifier) → [(file_id, context)]` lookups
- Filters results by `captured_at <= audit_at` at query time

### 3. Identity Resolver (Deterministic + AI-Assisted) — `PROPOSED`

- **Deterministic**: Looks up `email` from the deletion request in `user_identities.csv`
  to find the current `user_id`, then queries `user_audit_log.csv` to build the full
  identity history (previous emails, phones, email hashes)
- **AI-Assisted**: When the request email doesn't directly match `user_identities.csv`,
  checks `user_audit_log.csv` for historical emails that were later changed
- Outputs: `{user_id, current_email, current_phone, current_email_hash, all_emails, all_phones, all_hashes}`

### 4. Case Builder (Deterministic) — `PROPOSED`

- For each case: links the request to the resolved identity
- Filters `system_activity.csv` for relevant events (by resource IDs, user references)
- Gathers all evidence files whose contents mention any of the user's identifiers
- Assembles a "case context" bundle with: request, identity, relevant activity, relevant evidence

### 5. Request Intent Classifier (AI-Assisted) — `PROPOSED`

- Classifies `request_text` as DELETION vs NON_DELETION
- Must handle multiple languages (English, Spanish, French, Japanese, etc.)
- Non-deletion intents: data access, export, correction, marketing opt-out,
  account recovery, copy/download
- Returns `NOT_APPLICABLE` immediately for non-deletion requests

### 6. Decision Engine (AI-Assisted + Deterministic) — `PROPOSED`

- **AI-Assisted**: Analyzes evidence to determine resource states at `audit_at`
  - Queries SQL snapshots for user records across all replica types
  - Reads JSON snapshots for resource presence/absence
  - Parses log entries for lookup results (404 = absent, hit = present)
  - Analyzes images and PDFs for relevant information
- **Deterministic**: Applies `deletion_rules.csv` to each discovered resource
  - Maps resource type → data category → required action
  - Determines expected vs actual state
  - Identifies violations (remaining records, exposed PII, active flows, restore risks)

### 7. Step Builder (Deterministic) — `PROPOSED`

- Generates `steps_json` based on decision engine findings
- **COMPLETE cases**: verification steps only, with evidence citations
- **INCOMPLETE cases**: findings → remediation → verification, with correct ordering
- Enforces phase ordering: FINDING → REMEDIATION → VERIFICATION
- Within each phase: orders by operation priority → system_id → resource_id
- Remediation ordering: DISABLE_DATA_FLOW → BLOCK_RESTORE → DELETE → REDACT → ANONYMIZE
- Assigns consecutive step numbers starting at 1
- Sets `evidence_id` appropriately (cited for findings/COMPLETE verifications, empty for remediation/INCOMPLETE verifications)

### 8. Output Serializer (Deterministic) — `PROPOSED`

- Sorts all 518 rows by `case_id`
- Serializes `steps_json` as valid JSON
- Writes CSV with proper quoting (double-quote escaping for embedded JSON)
- Validates output against schema before writing
- Writes to `output.csv` at repository root

### 9. Usage Tracker (Deterministic) — `PROPOSED`

- Tracks all LLM API calls: model name, input tokens, output tokens
- Computes totals and per-request averages
- Generates `code/evaluation/usage_report.md`
