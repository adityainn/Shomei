# AI Agent Design

> See [decision_flow.mmd](./diagrams/decision_flow.mmd) for the visual diagram.

## Responsibility Split: AI vs Deterministic

| Task | Approach | Rationale |
|---|---|---|
| CSV loading and parsing | Deterministic | Structured data, no interpretation needed |
| SQL evidence querying | Deterministic | Execute SQL, compare rows |
| JSON/log evidence parsing | Deterministic | Structured formats, regex/key extraction |
| Identity resolution (primary) | Deterministic | Exact email/user_id lookup |
| Identity resolution (historical) | Deterministic | Audit log search for old_value match |
| Request intent classification | **AI-assisted** | Multilingual free-text interpretation |
| Image/PDF evidence extraction | **AI-assisted** | Multimodal understanding required |
| Ambiguous evidence interpretation | **AI-assisted** | Context-dependent state determination |
| Evidence-to-case correlation | Hybrid | Deterministic ID matching + AI for ambiguous links |
| Deletion rule application | Deterministic | Category → action lookup |
| State comparison (actual vs required) | Deterministic | Enum comparison |
| Step ordering and numbering | Deterministic | Fixed ordering rules |
| CSV output serialization | Deterministic | Schema enforcement |
| Output validation | Deterministic | JSON parsing, row counting, field checking |

## AI-Assisted Components

### 1. Request Intent Classifier

**Purpose**: Determine if `request_text` authorizes deletion.

**Input**: `request_text` (free-text, multilingual)

**Output**: `DELETION` or `NON_DELETION`

**Prompt Strategy**:
```
You are classifying a customer's data privacy request.

Determine whether the request authorizes DELETION of personal data, or is a
different type of request (data access, export, correction, marketing opt-out,
account recovery, etc.)

Respond with exactly one word: DELETION or NON_DELETION

Request text: {request_text}
```

**Non-deletion signals** (from dataset analysis):
- "download my account information" / "copy of"
- "resetting the login" / "can't access"
- "remove me from marketing lists only"
- "copy of last year's invoices"
- "send me a copy" / "don't delete"

**Validation**: Structured output, single-word response, deterministic fallback if invalid.

**Optimization**: This classification is simple enough that it can be batched across
multiple cases in a single LLM call.

### 2. Multimodal Evidence Analyzer

**Purpose**: Extract factual information from images and PDFs.

**Input**: Image or PDF file + context about what to look for (user identifiers)

**Output**: Structured extraction of:
- Resource IDs visible
- User identifiers visible (emails, names, phones, hashes)
- Resource states shown
- System/service names
- Timestamps

**Prompt Strategy**:
```
Analyze this business document/screenshot from a commerce platform.

Extract all of the following if visible:
1. Resource IDs (format: type_NNNN, e.g., account_005, search_1234)
2. Email addresses
3. Phone numbers
4. Names
5. User IDs (format: user_NN)
6. Resource states (ACTIVE, DELETED, REDACTED, etc.)
7. System/service names
8. Timestamps

Return a JSON object with these fields. Use null for fields not found.
```

**Scope**: 11 images + 4 PDFs = 15 multimodal calls maximum.
These can be pre-processed once and cached.

### 3. Complex Evidence Correlator (optional)

**Purpose**: For cases where deterministic correlation produces ambiguous results,
use AI to synthesize evidence from multiple sources.

**Decision**: Only invoke if deterministic analysis is insufficient. Most cases
should be solvable with deterministic evidence correlation.

## Prompt Architecture

### Principles
1. **Single responsibility per prompt** — each AI call does one thing
2. **Structured output** — always request JSON or single-word responses
3. **Validation layer** — parse and validate every LLM response before using it
4. **Retry with backoff** — if response is invalid, retry up to 3 times
5. **Deterministic fallback** — if AI fails, use conservative default (INCOMPLETE)

### Token Budget Estimates

| Component | Calls | Input tokens/call | Output tokens/call | Total tokens |
|---|---|---|---|---|
| Intent classifier | ~52 batches of 10 | ~500 | ~100 | ~31,200 |
| Image analysis | 11 | ~1,000 | ~500 | ~16,500 |
| PDF analysis | 4 | ~2,000 | ~500 | ~10,000 |
| Complex correlation (if needed) | ~50 | ~2,000 | ~1,000 | ~150,000 |
| **Total estimate** | | | | **~207,700** |

**Estimated cost**: ~$0.50–$2.00 depending on model (Gemini 2.0 Flash is cost-effective).

## Retrieval Strategy

### Evidence Retrieval for a Case

1. **Identifier extraction**: Build set of all user identifiers (current + historical)
2. **Inverted index lookup**: Find all evidence files containing any identifier
3. **Temporal filter**: Exclude evidence with `captured_at > audit_at`
4. **SQL targeted queries**: For each relevant SQL snapshot, run targeted SELECT queries
5. **Log targeted scan**: For each relevant log file, grep for identifier matches
6. **JSON targeted search**: Walk JSON structures matching identifiers
7. **Multimodal cache**: Look up pre-extracted data from images/PDFs

### Caching Strategy

- **Pre-compute once**: Parse all SQL, JSON, and log files at startup
- **Identity index**: Map email/phone/hash/user_id → set of evidence file_ids
- **Resource index**: Map resource_id → set of evidence file_ids
- **Multimodal cache**: Extract image/PDF content once, store structured results
- **No cross-case caching needed**: each case is independent

## Failure Handling

| Failure Mode | Response |
|---|---|
| LLM API timeout | Retry with exponential backoff (3 attempts) |
| Invalid LLM response format | Retry with clarified prompt |
| LLM unavailable | Log error, mark case for manual review |
| Ambiguous evidence | Default to INCOMPLETE (conservative) |
| No evidence found for user | If deletion requested, check if user exists first |
| Rate limiting | Implement request queue with rate limiting |
