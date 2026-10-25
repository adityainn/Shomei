# Technical Decisions

## TD-1: Python as Implementation Language

**Decision**: Use Python 3.x with `code/main.py` as entry point.

**Rationale**:
- Starter repo already provides `code/main.py` as suggested entry point
- Rich ecosystem for CSV, JSON, SQL (sqlite3 stdlib), and LLM APIs
- Excellent multimodal AI library support
- Fastest development velocity for a hackathon

**Alternatives Considered**:
- Node.js/TypeScript — would work but less mature AI libraries
- Go — faster runtime but slower development, weaker AI ecosystem

---

## TD-2: Gemini Flash as Primary LLM

**Decision**: Use Gemini 2.0 Flash via the `google-genai` Python SDK.

**Rationale**:
- Lowest cost per token among capable models
- Fast inference (important for 518 cases)
- Multimodal support (images + PDFs)
- Multilingual text understanding
- `google-genai` SDK is lightweight and well-documented

**Alternatives Considered**:
- Claude Opus — higher quality but 10-20x cost per token
- GPT-4o — good quality but higher cost than Gemini Flash
- Local models — no API cost but slower and less capable for multimodal

**Risk**: If Gemini Flash accuracy is insufficient for evidence analysis,
consider Gemini Pro for complex cases only (hybrid approach).

---

## TD-3: Single-Pass Pipeline (No Multi-Agent Orchestration)

**Decision**: Process cases in a simple sequential pipeline with deterministic
components and targeted AI calls. No multi-agent framework.

**Rationale**:
- 518 cases × simple pipeline = manageable complexity
- Most logic is deterministic (data loading, SQL queries, rule application, step ordering)
- AI is needed only for: intent classification (~52 batches), multimodal extraction (15 files)
- Multi-agent adds latency, debugging difficulty, and token overhead
- Hackathon constraint: simpler is faster to build and debug

**Alternatives Considered**:
- Google Antigravity SDK multi-agent — powerful but overkill for this task
- LangChain agent — adds unnecessary abstraction
- ReAct agent per case — too many LLM calls, unpredictable

---

## TD-4: Pre-Compute Evidence Index at Startup

**Decision**: Parse all 94 evidence files at startup and build an inverted index
of identifiers → file_ids. Do not re-parse evidence per case.

**Rationale**:
- 94 files, ~2.9 MB total — fits easily in memory
- Parsing once saves time across 518 cases
- SQL files can be loaded into SQLite once and queried many times
- JSON and log files are parsed once into structured data

**Trade-offs**:
- Higher startup time (~5-10 seconds)
- Higher memory usage (~50-100 MB for indexed evidence)
- Worthwhile for 518× speedup on per-case evidence lookups

---

## TD-5: SQLite for SQL Evidence Queries

**Decision**: Use Python's built-in `sqlite3` module to execute SQL evidence files.

**Rationale**:
- SQL files are explicitly "readable as text and executable with SQLite"
- Enables precise, structured queries for specific users/resources
- No external dependencies needed
- Each SQL file creates its own in-memory database

**Implementation**:
```python
import sqlite3
conn = sqlite3.connect(":memory:")
with open(sql_file_path) as f:
    conn.executescript(f.read())
# Now query: SELECT * FROM customer_profiles WHERE email = ?
```

---

## TD-6: Deterministic Step Ordering

**Decision**: Implement step ordering as a pure sort function, not AI-generated.

**Rationale**:
- Ordering rules are fully specified: phase order → operation order → system_id → resource_id
- This is a deterministic, testable function
- Sample output confirms the exact ordering convention
- AI would only add noise and inconsistency

**Implementation**:
```python
PHASE_ORDER = {"FINDING": 0, "REMEDIATION": 1, "VERIFICATION": 2}
OPERATION_ORDER = {
    "REPORT_REMAINING_RECORD": 0, "REPORT_EXPOSED_PII": 1,
    "REPORT_ACTIVE_DATA_FLOW": 2, "REPORT_RESTORE_RISK": 3,
    "DISABLE_DATA_FLOW": 0, "BLOCK_RESTORE": 1,
    "DELETE_RECORD": 2, "REDACT_RECORD": 3, "ANONYMIZE_RECORD": 4,
    "VERIFY_RECORD_ABSENT": 0, "VERIFY_RECORD_PRESENT": 1,
    "VERIFY_RECORD_REDACTED": 2, "VERIFY_RECORD_ANONYMIZED": 3,
    "VERIFY_DATA_FLOW_DISABLED": 4, "VERIFY_RESTORE_BLOCKED": 5,
}

def sort_key(step):
    return (PHASE_ORDER[step["phase"]],
            OPERATION_ORDER[step["operation"]],
            step["system_id"],
            step["resource_id"])
```

---

## TD-7: Batch Intent Classification

**Decision**: Batch multiple `request_text` values into a single LLM call
(up to 10 per batch) for intent classification.

**Rationale**:
- Reduces API calls from ~518 to ~52
- Intent classification is simple enough for batching
- Each classification is independent (no cross-case context needed)
- Reduces latency and cost

**Risk**: Batch errors could affect multiple cases. Mitigation: validate each
classification independently, retry individual failures.

---

## TD-8: Conservative Defaults for Ambiguous Cases

**Decision**: When evidence is ambiguous or insufficient, default to `INCOMPLETE`.

**Rationale**:
- The challenge's core insight is that `COMPLETE` requires proof
- False-complete (marking incomplete as complete) is worse than false-incomplete
- Participants are expected to prove completion with evidence
- A false-negative finding (missing a violation) is better than a false-positive
  completion

---

## TD-9: Resource-to-Category Mapping via Naming Convention

**Decision**: Map `resource_id` prefixes and `system_id` to data categories
deterministically.

**Rationale**:
- Clear naming patterns: `account_*` → USER_PROFILE, `search_*` → SEARCH_INDEX_ENTRY, etc.
- Sample output confirms these mappings
- Deterministic and fast — no AI needed

**Verified mappings from sample_output.csv**:
- `account_service` / `account_*` → rule_01 (DELETE)
- `search_service` / `search_*` → rule_03 (DELETE)
- `analytics_platform` / `analytics_*` → rule_07 (ANONYMIZE)
- `support_platform` / `support_*` → rule_05 (REDACT)
- `export_service` / `export_*` → rule_09 (DELETE)
- `integration_service` / `data_flow_*` → data flow (DISABLE)
- `backup_service` / `backup_*` → rule_14 (RETAIN/BLOCK_RESTORE)
- `security_service` / `audit_record_*` → rule_12 (RETAIN)
- `identity_service` / `tombstone_*` → rule_15 (REDACT)
