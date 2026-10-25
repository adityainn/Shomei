# Implementation Roadmap

## Phase 0: Foundation (Current — Complete)
**Duration**: 1 session
**Status**: ✅ COMPLETE

- [x] Clone repository
- [x] Read all instructions (AGENTS.md, README, problem_statement)
- [x] Inspect dataset structure and schemas
- [x] Analyze sample output format
- [x] Understand evidence file types and structures
- [x] Create documentation suite
- [x] Create architecture diagrams
- [x] Session logging established

**Acceptance**: Documentation reviewed, no implementation started.

---

## Phase 1: Core Infrastructure
**Duration**: 1 session
**Dependencies**: Phase 0
**Status**: 🔲 NOT STARTED

### Tasks
1. **Data Loader** — Load all CSVs, parse into typed data structures
2. **Identity Resolver** — Email → user_id lookup + historical audit trail
3. **Evidence Index** — Pre-parse all text-based evidence files, build inverted index
4. **SQL Evidence Engine** — Execute SQL snapshots with SQLite, query for user records
5. **Output Serializer** — Generate valid CSV with correct quoting and schema
6. **Output Validator** — Validate 518 rows, JSON, ordering, step numbering

### Files to Create/Modify
- `code/main.py` — Entry point, pipeline orchestration
- `code/data_loader.py` — CSV and evidence file loading
- `code/identity.py` — Identity resolution
- `code/evidence.py` — Evidence index and retrieval
- `code/sql_engine.py` — SQLite-based SQL evidence queries
- `code/output.py` — CSV output generation and validation
- `code/models.py` — Data classes for Case, Identity, Step, etc.

### Acceptance Criteria
- [ ] All CSVs load without error
- [ ] Identity resolver finds user_id for all 518 case emails
- [ ] Evidence index returns results for sample identifiers
- [ ] SQL queries return records from all 24 SQL evidence files
- [ ] Output validator accepts sample_output.csv
- [ ] Empty pipeline produces valid (but wrong) output.csv with 518 rows

### Test Gate
```bash
python3 code/main.py  # Produces output.csv with 518 rows
python3 -c "import csv; rows=list(csv.reader(open('output.csv')))[1:]; print(len(rows))"  # 518
```

---

## Phase 2: Deterministic Analysis Engine
**Duration**: 1 session
**Dependencies**: Phase 1

### Tasks
1. **Resource Discovery** — For each user, find all resources across evidence
2. **State Reconstruction** — Determine resource state at `audit_at` from evidence
3. **Deletion Rule Engine** — Apply `deletion_rules.csv` to each resource
4. **Violation Detection** — Compare actual vs required state
5. **Step Builder** — Generate correctly ordered steps for each case
6. **Sample Accuracy Test** — Score against 32 sample cases

### Files to Create/Modify
- `code/discovery.py` — Resource discovery across evidence sources
- `code/policy.py` — Deletion rule application
- `code/decision.py` — State comparison and violation detection
- `code/steps.py` — Step generation with correct ordering
- `code/evaluation/main.py` — Evaluation scoring against sample

### Acceptance Criteria
- [ ] Resource discovery finds records in SQL, JSON, logs for sample users
- [ ] State reconstruction correctly identifies PRESENT/ABSENT/REDACTED/ANONYMIZED
- [ ] Deletion rules correctly applied (DELETE/REDACT/ANONYMIZE/RETAIN)
- [ ] Step ordering matches sample_output.csv patterns
- [ ] ≥80% status accuracy on 32 sample cases
- [ ] Deterministic: same input → same output

### Test Gate
```bash
python3 code/evaluation/main.py  # Reports accuracy on sample cases
```

---

## Phase 3: AI-Assisted Components
**Duration**: 1 session
**Dependencies**: Phase 2

### Tasks
1. **Request Intent Classifier** — LLM-based deletion vs non-deletion classification
2. **Multimodal Evidence Analyzer** — Extract info from 11 images + 4 PDFs
3. **Integration** — Wire AI components into pipeline with validation + fallbacks
4. **Usage Tracking** — Track model calls, tokens, and cost
5. **Batching** — Batch intent classification for efficiency

### Files to Create/Modify
- `code/llm.py` — LLM client wrapper with retry logic
- `code/classifier.py` — Request intent classification
- `code/multimodal.py` — Image and PDF analysis
- `code/usage.py` — Token and cost tracking

### Acceptance Criteria
- [ ] Intent classifier correctly identifies 5 known non-deletion requests
- [ ] Image analysis extracts resource IDs and identifiers from screenshots
- [ ] PDF analysis extracts retention periods and legal hold information
- [ ] Usage tracker reports accurate token counts
- [ ] ≥85% status accuracy on 32 sample cases
- [ ] All 518 cases process without error

### Test Gate
```bash
python3 code/main.py  # Full run on 518 cases
python3 code/evaluation/main.py  # Reports accuracy
```

---

## Phase 4: Accuracy Optimization and Edge Cases
**Duration**: 1 session
**Dependencies**: Phase 3

### Tasks
1. **Error Analysis** — Analyze mismatches on sample cases
2. **Evidence Coverage** — Ensure all 94 evidence files are properly indexed
3. **Identity Edge Cases** — Handle email case sensitivity, historical lookups
4. **Temporal Boundary Handling** — Correctly filter by `audit_at`
5. **Tombstone Handling** — Correct REDACT behavior for account tombstones
6. **Replica Drift Detection** — Compare primary vs replica SQL states

### Acceptance Criteria
- [ ] ≥90% status accuracy on 32 sample cases
- [ ] All step fields correct for correctly-statused cases
- [ ] Evidence citations are valid file_ids for findings
- [ ] Temporal filtering correctly excludes post-audit_at evidence
- [ ] Tombstone cases correctly handled (REDACT, not DELETE)

---

## Phase 5: Evaluation, Reports, and Submission
**Duration**: 1 session
**Dependencies**: Phase 4

### Tasks
1. **Create 3+ synthetic evaluation cases** with expected outputs
2. **Write evaluation_report.md** with accuracy metrics
3. **Final full-dataset run** with usage tracking
4. **Write usage_report.md** with token/cost breakdown
5. **Update README.md** with setup and run instructions
6. **Package code.zip** without dataset or secrets
7. **Final validation** of output.csv

### Deliverables
- [ ] `output.csv` at repo root (518 rows, valid)
- [ ] `code/evaluation/evaluation_report.md`
- [ ] `code/evaluation/usage_report.md`
- [ ] Updated `README.md` with instructions
- [ ] `code.zip` ready for submission
- [ ] `log.txt` complete with all session entries

### Submission Checklist
- [ ] `output.csv` has header + 518 data rows sorted by case_id
- [ ] Every `steps_json` is valid JSON with consecutive step numbers
- [ ] COMPLETE cases have evidence-cited verification steps
- [ ] INCOMPLETE cases have findings + remediation + verification
- [ ] NOT_APPLICABLE cases have `[]`
- [ ] No secrets in any file
- [ ] No dataset files in code.zip
- [ ] No nested archives in code.zip

---

## Risk Mitigations

| Risk | Mitigation |
|---|---|
| LLM API rate limits | Implement batching and retry with backoff |
| High token costs | Use Gemini Flash (cheapest), batch classifications |
| Accuracy plateau below target | Focus on deterministic improvements first |
| Evidence parsing failures | Robust error handling, skip unparseable files |
| Temporal logic errors | Unit test `audit_at` filtering with known cases |
| Output format errors | Validator runs before every write |
| Time pressure | Phases are independent; can ship after Phase 3 |
