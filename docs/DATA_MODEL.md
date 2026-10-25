# Data Model

## Input Schemas

### deletion_requests.csv (518 rows)

| Column | Type | Description |
|---|---|---|
| `case_id` | string | Unique case identifier (e.g., `case_33`) |
| `email` | string | Identity supplied with request (current or historical) |
| `requested_at` | ISO-8601 | When the request was submitted |
| `reported_status` | enum | Workflow claim: `COMPLETE`, `PARTIALLY_COMPLETE`, `NOT_STARTED` |
| `reported_at` | ISO-8601 | When the claim was reported |
| `audit_at` | ISO-8601 | Cutoff time — answer must reflect state at this point |
| `request_text` | string | Free-text request, may be in various languages |

### user_identities.csv (850 users)

| Column | Type | Description |
|---|---|---|
| `user_id` | string | Stable internal reference (e.g., `user_01`) |
| `name` | string | Current display name |
| `email` | string | Current email address |
| `phone` | string | Current phone number |
| `email_hash` | string | SHA-256 hash of current email |
| `updated_at` | ISO-8601 | When this snapshot was last updated |

### user_audit_log.csv (306 entries)

| Column | Type | Description |
|---|---|---|
| `audit_id` | string | Unique audit entry ID (e.g., `audit_01`) |
| `user_id` | string | User whose field changed |
| `event_time` | ISO-8601 | When the change occurred |
| `field_name` | enum | Changed field: `email`, `phone`, or `email_hash` |
| `old_value` | string | Previous value |
| `new_value` | string | New value |

### system_activity.csv (4,011 events)

| Column | Type | Description |
|---|---|---|
| `activity_id` | string | Unique activity ID (e.g., `activity_01`) |
| `event_time` | ISO-8601 | When the event occurred |
| `event_type` | enum | See event types below |
| `source_system` | string | System that initiated the event |
| `target_system` | string | System that received the event |
| `resource_id` | string | Affected resource |
| `reported_result` | string | Claimed result (e.g., `SUCCESS`) |
| `details` | string | Human-readable description |

**Event Types**: `ANONYMIZE_RECORD`, `BLOCK_RESTORE`, `CHECK_DATA_FLOW`, `CHECK_RESTORE_ACCESS`, `CLASSIFY_REQUEST`, `CREATE_EXPORT`, `DELETE_RECORD`, `DISABLE_DATA_FLOW`, `INDEX_RECORD`, `LINK_RESOURCE_IDENTITY`, `REDACT_RECORD`, `REFRESH_CACHE`, `RESTORE_BACKUP`, `RETAIN_RECORD`, `SEND_EMAIL`, `SYNC_RECORD`, `UPDATE_RECORD`

**System Pairs**: deletion_worker→(account_service, analytics_platform, backup_service, export_service, identity_service, integration_service, legal_service, search_service, support_platform), account_service→(search_service, cache_service, account_failover_replica, account_replication_cluster, analytics_platform), data_catalog→(various), integration_service→search_service, export_service→object_store, notification_service→email_delivery_service, privacy_intake→privacy_case_management, backup_service→search_service

### deletion_rules.csv (15 rules)

| rule_id | data_category | condition | required_action |
|---|---|---|---|
| rule_01 | USER_PROFILE | Always | DELETE |
| rule_02 | SECONDARY_IDENTIFIER | Always | DELETE |
| rule_03 | SEARCH_INDEX_ENTRY | Always | DELETE |
| rule_04 | CACHE_ENTRY | Always | DELETE |
| rule_05 | SUPPORT_MESSAGE | Contains shared context | REDACT |
| rule_06 | SUPPORT_ATTACHMENT | Belongs only to subject | DELETE |
| rule_07 | ANALYTICS_PROFILE | Still attributable | ANONYMIZE |
| rule_08 | PRODUCT_TELEMETRY | Still attributable | ANONYMIZE |
| rule_09 | USER_EXPORT | Always | DELETE |
| rule_10 | MARKETING_PROFILE | Always | DELETE |
| rule_11 | EMAIL_DELIVERY_LOG | Contains user email | REDACT |
| rule_12 | SECURITY_AUDIT_LOG | Within retention period | RETAIN |
| rule_13 | LEGAL_HOLD_RECORD | Active legal hold | RETAIN |
| rule_14 | BACKUP_ARCHIVE | Restore access can be blocked | RETAIN |
| rule_15 | ACCOUNT_TOMBSTONE | Deleted account, stable user_id needed | REDACT |

### evidence_files.csv (94 files)

| Column | Type | Description |
|---|---|---|
| `file_id` | string | Evidence identifier (e.g., `evidence_01`) |
| `file_path` | string | Relative path under `dataset/` |
| `origin` | string | Source system that captured the evidence |
| `captured_at` | ISO-8601 | When the evidence was captured |

## Evidence File Categories

### SQL Snapshots (24 files)

**Tables**: `customer_profiles`, `customer_search_documents`, `customer_analytics_profiles`, `support_records`, `customer_exports`, `connector_subscriptions`, `backup_restore_entries`, `security_audit_records`, `snapshot_scope`

**Replica Types**: `customer_data_inventory` (11 snapshots), `customer_data_read_replica` (5), `customer_data_regional_replicas` (3), `customer_data_reporting_replica` (2), `customer_data_failover_replica` (1), `customer_accounts_failover_replica` (1), `customer_search_primary` (1)

**Key Schema Details**:
- `customer_profiles.account_status` can be `ACTIVE`, `DELETION_PENDING`, or absent (deleted)
- `connector_subscriptions.enabled` is 0 or 1; `restore_allowed` is 0 or 1
- Records may reference users by `customer_reference` (user_id) or by email/phone/hash
- Null fields indicate redaction or anonymization

### JSON Records (28 files)

- **Service resource exports** (11 files): nested `{service_exports: {service_name: {resource_type: [records]}}}`
- **Customer data snapshot bundles** (12 files): structured snapshots of customer state
- **Other** (5 files): connector configs, analytics report, export jobs, export manifest, security audit ledger

### Log Files (26 files)

- **Resource lookup traces** (11 files): per-service readbacks showing `result=hit`/`rows=0`/`http_status=404`
- **Service events** (6 files): operational logs with resource-level events
- **Other** (9 files): application traces, cloud runtime exports, operations streams, search diagnostics, notification delivery, support replica, syslog archives

### PDFs (4 files)

Account history report, delivery correction attachment, legal retention register, security retention extract

### Images (11 PNG files)

Admin consoles, analytics views, backup console, connector management, export console, deleted account reference, marketing profile, object storage browser, search index inspector, security audit explorer, support ticket console

### Text (1 file)

Customer account handover document (shift handover with account/downstream checks)

## Resource-to-Category Mapping

| resource_id pattern | system_id | data_category | required_action |
|---|---|---|---|
| `account_*` | `account_service` | USER_PROFILE | DELETE |
| `search_*` | `search_service` | SEARCH_INDEX_ENTRY | DELETE |
| `analytics_*` | `analytics_platform` | ANALYTICS_PROFILE | ANONYMIZE |
| `support_*` | `support_platform` | SUPPORT_MESSAGE | REDACT |
| `export_*` | `export_service` | USER_EXPORT | DELETE |
| `data_flow_*` | `integration_service` | (active sync) | DISABLE |
| `backup_*` | `backup_service` | BACKUP_ARCHIVE | RETAIN (block restore) |
| `audit_record_*` | `security_service` | SECURITY_AUDIT_LOG | RETAIN |
| `tombstone_*` | `identity_service` | ACCOUNT_TOMBSTONE | REDACT |
| `marketing_*` | `marketing_platform` | MARKETING_PROFILE | DELETE |

## Output Schema

### output.csv

| Column | Type | Description |
|---|---|---|
| `case_id` | string | Matches input `case_id` |
| `deletion_status` | enum | `COMPLETE`, `INCOMPLETE`, `NOT_APPLICABLE` |
| `steps_json` | JSON array | Ordered steps (see step schema below) |

### Step Object

```json
{
  "step_no": 1,
  "phase": "FINDING",
  "system_id": "account_service",
  "resource_id": "account_005",
  "operation": "REPORT_REMAINING_RECORD",
  "state": "PRESENT",
  "evidence_id": "evidence_01"
}
```

All 7 fields are required. `evidence_id` is `""` for remediation steps and
verification steps in INCOMPLETE cases.
