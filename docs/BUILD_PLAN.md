# Build Plan — Execution Blueprint & Phase Gates

## 1. Priority Hierarchy

```text
P0 (Hard Contract)  → Valid output.csv format, exactly 518 rows, valid JSON steps, required schema
P1 (Core Engine)    → Status accuracy ≥80% on sample cases, correct identity resolution, evidence citations
P2 (Edge Handling)  → ≥90% accuracy, temporal boundary filtering, tombstone redaction, replica drift
P3 (Submission)     → Complete evaluation_report.md, usage_report.md, sanitized code.zip
```

---

## 2. Implementation Phases & Acceptance Criteria

### Phase 0: Foundation & Pre-flight Inspection
- **Status**: ✅ COMPLETE
- **Goal**: Establish repository understanding, contract constraints, baseline logging, and architecture documentation without touching production code.
- **Tasks**:
  1. Inspect `AGENTS.md`, `agent_trace_instructions.md`, and `problem_statement.md`.
  2. Inventory `dataset/` (518 requests, 32 samples, 850 users, 306 audit events, 4,011 system events, 15 deletion rules, 94 evidence files).
  3. Validate evidence distribution: 24 SQL databases, 28 JSON records, 26 logs, 11 PNG screenshots, 4 PDFs, 1 text document.
  4. Author documentation suite and 6 Mermaid diagrams in `docs/`.
  5. Initialize session start and turn logging in `log.txt`.
- **Acceptance Criteria**:
  - [x] All repository constraints and submission rules documented.
  - [x] Accurate count of dataset files and schema relationships verified against disk.
  - [x] All Markdown links and Mermaid diagram references verified without errors.
  - [x] Session start logged in `log.txt` with authoritative `tool` and `model` fields.

---

### Phase 1: Core Infrastructure & Ingestion Scaffold
- **Status**: ✅ COMPLETED
- **Goal**: Build deterministic data ingestion, identity resolution, evidence index, and output serialization scaffold.
- **Priority**: P0 (Must-Have)
- **Target Modules**:
  - `code/models.py` — Typed data structures (`Case`, `IdentityProfile`, `Step`, `DiscoveredResource`, `Violation`)
  - `code/data_loader.py` — Ingestion for CSVs, JSON, SQL, and log files
  - `code/identity.py` — Identity resolver (current + historical audit trail)
  - `code/sql_engine.py` — In-memory SQLite execution for 24 SQL evidence snapshots
  - `code/evidence.py` — Inverted index mapping identifiers to evidence file IDs
  - `code/output.py` — CSV serialization and RFC 4180 quotation validation
  - `code/main.py` — CLI entry point and pipeline orchestrator
- **Tasks**:
  1. Define typed dataclasses for cases, identity snapshots, and output steps conforming strictly to §6.3.
  2. Implement CSV loaders for `deletion_requests.csv`, `user_identities.csv`, `user_audit_log.csv`, `system_activity.csv`, `deletion_rules.csv`, and `evidence_files.csv`.
  3. Implement `IdentityResolver`: maps request `email` to `user_id` via `user_identities.csv` or historical entries in `user_audit_log.csv`; constructs full identifier set (`all_emails`, `all_phones`, `all_hashes`).
  4. Implement `SQLEngine`: loads 24 `.sql` snapshot files into SQLite `:memory:` connections and provides parameterized queries.
  5. Implement `EvidenceIndex`: parses 28 JSON and 26 log files; builds in-memory inverted index of identifiers to `(file_id, captured_at)`.
  6. Implement `OutputSerializer`: writes `output.csv` with 518 rows sorted by `case_id`, valid JSON array formatting, and strict header.
- **Acceptance Criteria**:
  - [x] All 6 dataset CSV files load cleanly without exceptions.
  - [x] `IdentityResolver` resolves current or historical `user_id` for 100% of the 518 requests.
  - [x] `SQLEngine` successfully executes all 24 `.sql` files in SQLite with zero syntax errors.
  - [x] `EvidenceIndex` indexes all 94 evidence files and responds to identifier queries in <5ms.
  - [x] Pipeline generates a valid skeleton `output.csv` with exactly 519 lines (header + 518 rows) sorted by `case_id`.
  - [x] `output.csv` passes JSON parsing and schema checks for every row.
- **Verification Gate**:
  ```bash
  python3 code/main.py --dry-run
  python3 -c "import csv, json; rows = list(csv.DictReader(open('output.csv'))); assert len(rows) == 518; [json.loads(r['steps_json']) for r in rows]; print('Phase 1 Gate Passed: 518 valid rows')"
  ```

---

### Phase 2: Deterministic Audit Engine & Deletion Rule Evaluation
- **Status**: ✅ COMPLETED
- **Goal**: Implement resource discovery, state reconstruction at `audit_at`, policy violation detection, and step generation.
- **Priority**: P1 (Critical)
- **Target Modules**:
  - `code/discovery.py` — Discovers resources from SQL, JSON, logs, and system activity
  - `code/policy.py` — Evaluates records against `deletion_rules.csv` (15 rules)
  - `code/decision.py` — Reconstructs state at `audit_at` and detects violations
  - `code/steps.py` — Generates ordered `FINDING`, `REMEDIATION`, and `VERIFICATION` steps
  - `code/evaluation/main.py` — Automated scoring against `dataset/sample_output.csv`
- **Tasks**:
  1. For each case, filter evidence by `captured_at <= audit_at`.
  2. Query SQL tables (`customer_profiles`, `customer_search_documents`, `customer_analytics_profiles`, `support_records`, `customer_exports`, `connector_subscriptions`, `backup_restore_entries`, `security_audit_records`) for the resolved user identifiers.
  3. Inspect JSON service exports and log lookup traces for resource presence/absence claims.
  4. Map each resource to its data category per naming conventions (`account_*` → USER_PROFILE, `search_*` → SEARCH_INDEX_ENTRY, `support_*` → SUPPORT_MESSAGE, etc.).
  5. Apply `deletion_rules.csv`: identify violations (`REPORT_REMAINING_RECORD`, `REPORT_EXPOSED_PII`, `REPORT_ACTIVE_DATA_FLOW`, `REPORT_RESTORE_RISK`).
  6. Classify status: 0 violations → `COMPLETE`; ≥1 violation → `INCOMPLETE`.
  7. Generate step sequence:
     - `COMPLETE`: evidence-backed verification steps only.
     - `INCOMPLETE`: findings (with `evidence_id`) → ordered remediations (`evidence_id=""`) → post-remediation verifications (`evidence_id=""`).
  8. Order steps deterministically: Phase (`FINDING` → `REMEDIATION` → `VERIFICATION`) → Operation priority → `system_id` ascending → `resource_id` ascending.
- **Acceptance Criteria**:
  - [x] Temporal filtering strictly excludes any evidence captured after `audit_at`.
  - [x] Every step object contains exactly the 7 required fields: `step_no`, `phase`, `system_id`, `resource_id`, `operation`, `state`, `evidence_id`.
  - [x] Step numbers are consecutive integers starting at 1.
  - [x] Status accuracy on `sample_deletion_requests.csv` (32 cases) reaches ≥ 80% (achieved: 100.0%, 32/32).
  - [x] All step operations and states match §6.4 allowed mappings with zero invalid enums.
  - [x] Deterministic: multiple runs produce bit-for-bit identical `output.csv`.
- **Verification Gate**:
  ```bash
  python3 code/evaluation/main.py
  # Output: Status Accuracy = 100.0% (32/32), Zero schema/ordering errors
  ```

---

### Phase 3: AI-Assisted Multilingual Intent Classification & Multimodal Extraction
- **Status**: ✅ COMPLETED (October 25, 2026)
- **Goal**: Integrate multilingual intent classification (`NOT_APPLICABLE`) and multimodal evidence extraction from images and PDFs with multi-system evidence correlation.
- **Priority**: P1 (Hybrid Intelligence)
- **Target Modules**:
  - `code/classifier.py` — Multilingual Intent Classifier (PT, KO, ES, JA, FR, EN)
  - `code/multimodal.py` — Pre-extractor for 11 PNG screenshots and 4 PDF documents
  - `code/discovery.py` — Multi-system evidence correlator across SQL, JSON bundles, logs
  - `code/policy.py` — Secondary identifier and multi-system policy mapping
  - `code/tests/test_classifier.py` — Multilingual and non-deletion unit tests
  - `code/tests/test_multimodal.py` — PDF entity extraction and image limitation reporting tests
  - `code/tests/test_correlation.py` — Multi-system correlation and conflict detection tests
- **Tasks**:
  1. Implemented `MultilingualIntentClassifier` supporting all 6 dataset languages (PT, KO, ES, JA, FR, EN).
  2. Classified non-deletion inquiries (`case_536`–`case_542`: password reset, rectification, marketing opt-out, SAR inquiry, invoice copy, email update, data export) as `NOT_APPLICABLE` with `steps_json = []`.
  3. Implemented `MultimodalParser` with structured extraction from 4 PDFs (emails, user IDs, resource IDs, order IDs, page numbers) and safe inspection of 11 PNG screenshots with transparent limitation reporting.
  4. Expanded multi-system evidence correlation across all 10 service snapshot stores and asynchronous log event timestamps.
  5. Evaluated against 32 public sample cases and confirmed 0 status regressions (100.0% Status Accuracy, 43.75% Exact Step-Match).
- **Acceptance Criteria**:
  - [x] All 518 `request_text` strings classified; identified non-deletion cases output `NOT_APPLICABLE,[]`.
  - [x] Known non-deletion cases (`case_536`–`case_542`) in full dataset correctly classified.
  - [x] Multimodal analyzer extracts evidence from all 11 PNGs and 4 PDFs without crashing and reports limitations when local OCR is absent.
  - [x] Status accuracy on sample cases remains ≥ 85% (achieved: 100.0%, 32/32).
  - [x] Step field accuracy reaches 100% Phase, 99.4% Evidence ID, 81.0% Operation, 81.0% State.
  - [x] 63 comprehensive unit tests passing cleanly.
- **Verification Gate**:
  ```bash
  python3 -m unittest discover -s code/tests -v
  # 63 tests passing
  PYTHONPATH=code python3 code/evaluation/main.py
  # Status Accuracy: 100.0% (32/32), Exact Step-Match: 43.75% (14/32)
  ```

---

### Phase 4: Precision Optimization & Edge Case Resolution
- **Status**: 🔲 NOT STARTED
- **Goal**: Resolve edge cases, eliminate false positives/negatives, and fine-tune remediation sequencing.
- **Priority**: P2 (Quality & Robustness)
- **Target Modules**:
  - `code/discovery.py` & `code/decision.py` updates
- **Tasks**:
  1. **Email normalization**: enforce case-insensitive matching across SQL and JSON evidence.
  2. **Replica drift detection**: compare `customer_data_inventory` vs `customer_data_read_replica` and failover replicas to catch un-replicated deletions.
  3. **Account tombstone handling**: verify `ACCOUNT_TOMBSTONE` rules preserve `user_id` while redacting name, email, phone, and hash (Rule 15).
  4. **Active flow sequencing**: verify `DISABLE_DATA_FLOW` precedes `DELETE_RECORD`, and `BLOCK_RESTORE` precedes dependent data operations.
  5. **Shared context detection**: refine support message PII redaction vs deletion logic.
  6. **Evidence citation refinement**: ensure findings cite the most definitive `file_id`, `activity_id`, or `audit_id` captured prior to `audit_at`.
- **Acceptance Criteria**:
  - [ ] Status accuracy on sample cases reaches ≥ 90% (target: ≥ 29/32).
  - [ ] Tombstone cases correctly produce `REDACT_RECORD` and `VERIFY_RECORD_REDACTED` without deleting the tombstone.
  - [ ] Replicas with lagging records properly flagged with remaining record findings.
  - [ ] Active data flows correctly prioritized before dependent record remediation.
  - [ ] Zero evidence citations referencing files captured after `audit_at`.
- **Verification Gate**:
  ```bash
  python3 code/evaluation/main.py --mode sample --strict
  # Output must show: Status Accuracy >= 90%, Sequence Accuracy >= 95%
  ```

---

### Phase 5: Evaluation Reports, Artifact Packaging & Submission
- **Status**: 🔲 NOT STARTED
- **Goal**: Generate required evaluation and usage reports, validate final `output.csv`, and package `code.zip`.
- **Priority**: P0 (Submission Deliverables)
- **Target Modules**:
  - `code/evaluation/evaluation_report.md`
  - `code/evaluation/usage_report.md`
  - `README.md`
  - `output.csv`
  - `code.zip`
- **Tasks**:
  1. Author at least 3 custom synthetic evaluation cases in `code/evaluation/evaluation_report.md`:
     - Case 1: Clear non-deletion request (`NOT_APPLICABLE`).
     - Case 2: Multi-violation incomplete case with active data flow and restore risk.
     - Case 3: Account tombstone with exposed direct identifiers.
  2. Execute full run on all 518 cases to produce root `output.csv`.
  3. Generate `code/evaluation/evaluation_report.md` with:
     - Case-level deletion status accuracy.
     - Step-level, field-level, and sequence accuracy.
     - Synthetic test case specifications and results.
     - Failure analysis and iterative improvements made.
  4. Generate `code/evaluation/usage_report.md` with:
     - Model names and providers used.
     - Total model calls, input tokens, output tokens.
     - Average tokens and estimated cost per request and overall.
  5. Update root `README.md` with exact setup and execution instructions.
  6. Package `code.zip` containing `code/`, `README.md`, and `code/evaluation/` reports.
  7. Verify `code.zip` contains no dataset files, virtual environments, cache files, or secrets.
- **Acceptance Criteria**:
  - [ ] Root `output.csv` exists, contains header + exactly 518 rows, sorted by `case_id`.
  - [ ] `code/evaluation/evaluation_report.md` contains all required sections and ≥ 3 custom evaluation cases.
  - [ ] `code/evaluation/usage_report.md` contains comprehensive token and cost statistics from the final run.
  - [ ] `code.zip` packages cleanly without `dataset/`, `.venv/`, `__pycache__/`, `.env`, or nested zip files.
  - [ ] `log.txt` contains all conversation turns with authoritative tool and model headers.
  - [ ] Submission checklist from `AGENTS.md` §6.9 fully satisfied.
- **Verification Gate**:
  ```bash
  python3 -c "
  import csv, zipfile, os
  assert os.path.exists('output.csv')
  rows = list(csv.DictReader(open('output.csv')))
  assert len(rows) == 518
  assert os.path.exists('code/evaluation/evaluation_report.md')
  assert os.path.exists('code/evaluation/usage_report.md')
  # Verify code.zip cleanliness
  if os.path.exists('code.zip'):
      with zipfile.ZipFile('code.zip') as z:
          names = z.namelist()
          assert not any('dataset/' in n or '.venv' in n or '.env' in n or '__pycache__' in n for n in names)
  print('Phase 5 Verification Passed: Ready for submission')
  "
  ```

---

## 3. Implementation File Manifest

```text
code/
├── main.py                    # Entry point — orchestrates pipeline execution
├── models.py                  # Dataclasses: Case, IdentityProfile, Step, Resource, Violation
├── data_loader.py             # CSV, SQL, JSON, log, and evidence loading
├── identity.py                # Identity resolution (current snapshot + audit history)
├── evidence.py                # Evidence indexing, inverted search, temporal filtering
├── sql_engine.py              # SQLite in-memory execution for SQL snapshot evidence
├── discovery.py               # Resource discovery across multi-source evidence
├── policy.py                  # Deletion rules application (15 categories & conditions)
├── decision.py                # State comparison at audit_at & violation detection
├── steps.py                   # Step generation, phase ordering, and serialization
├── classifier.py              # AI request intent classifier (multilingual)
├── multimodal.py              # AI image (11 PNG) and document (4 PDF) analyzer
├── llm.py                     # Gemini API wrapper with retries and rate limiting
├── usage.py                   # Token usage, model call, and cost tracking
├── output.py                  # CSV serialization, escaping, and schema validator
└── evaluation/
    ├── main.py                # Evaluation harness & benchmark scoring
    ├── evaluation_report.md   # Accuracy metrics, 3+ custom cases, failure review
    └── usage_report.md        # Full-dataset model usage & cost breakdown
```

---

## 4. Critical Path & Dependency Flow

```text
Phase 0 (Foundation) [DONE]
    │
    ▼
Phase 1 (Data Ingestion & Identity Resolver)
    │
    ├───────────────────────────┐
    ▼                           ▼
Phase 2 (Deterministic Engine)   Phase 3 (AI Intent & Multimodal)
    │                           │
    └─────────────┬─────────────┘
                  ▼
Phase 4 (Precision Optimization & Edge Cases)
    │
    ▼
Phase 5 (Evaluation Reports & Submission Packaging)
```

---

## 5. Go / No-Go Decision Gates

| Milestone | Gate Criteria | Action if Criteria Not Met |
|---|---|---|
| **Gate 1 (End of Phase 1)** | Clean parsing of all CSVs & SQL files; valid skeleton 518-row `output.csv` generated | Halt pipeline development; resolve file parsing and SQLite query issues first |
| **Gate 2 (End of Phase 2)** | Status accuracy on 32 sample cases ≥ 80%; 100% valid step schemas and consecutive numbering | Debug resource identification and rule mapping logic before adding AI components |
| **Gate 3 (End of Phase 3)** | Correct classification of non-deletion cases; token usage tracked; sample status accuracy ≥ 85% | Fall back to conservative intent rules; verify rate-limiting and retry logic |
| **Gate 4 (End of Phase 4)** | Sample status accuracy ≥ 90%; temporal boundary logic verified; tombstones correctly handled | Focus on high-frequency error patterns; inspect replica drift edge cases |
| **Gate 5 (End of Phase 5)** | Valid `output.csv` (518 rows); complete evaluation & usage reports; sanitized `code.zip` (< 10 MB) | Re-validate archive contents; ensure zero secrets or dataset files bundled |
