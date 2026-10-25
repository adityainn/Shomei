# Shomei Phase 4 Precision Optimization & Edge Case Resolution Evaluation Report

**Generated:** `2026-10-25T04:28:09.174156+00:00`  
**Evaluation Corpus:** `dataset/sample_deletion_requests.csv` (32 sample cases)  
**Ground Truth:** `dataset/sample_output.csv`  

## 1. Executive Summary

- **Top-Level Status Accuracy:** **100.0%** (32/32) — **PASSED (>=80%)**
- **Exact Step-Sequence Match:** **100.0%** (32/32)
- **Step Count Alignment:** **100.0%** (32/32)
- **Total Steps Evaluated:** Predicted 193 vs Expected 193

## 2. Per-Status Performance

| Status | Support | Precision | Recall | F1 Score | TP | FP | FN |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `COMPLETE` | 10 | 1.000 | 1.000 | 1.000 | 10 | 0 | 0 |
| `INCOMPLETE` | 22 | 1.000 | 1.000 | 1.000 | 22 | 0 | 0 |

## 3. Step Field Accuracies (Aligned Steps)

| Field | Match Rate |
|:---|:---:|
| `phase` | 100.0% |
| `system_id` | 100.0% |
| `resource_id` | 100.0% |
| `operation` | 100.0% |
| `state` | 100.0% |
| `evidence_id` | 100.0% |

## 4. Case-by-Case Breakdown

| Case ID | Expected Status | Predicted Status | Status Match | Expected Steps | Predicted Steps | Exact Steps Match |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| `case_01` | `COMPLETE` | `COMPLETE` | PASS | 1 | 1 | EXACT |
| `case_02` | `COMPLETE` | `COMPLETE` | PASS | 1 | 1 | EXACT |
| `case_03` | `COMPLETE` | `COMPLETE` | PASS | 3 | 3 | EXACT |
| `case_04` | `COMPLETE` | `COMPLETE` | PASS | 2 | 2 | EXACT |
| `case_05` | `INCOMPLETE` | `INCOMPLETE` | PASS | 3 | 3 | EXACT |
| `case_06` | `INCOMPLETE` | `INCOMPLETE` | PASS | 4 | 4 | EXACT |
| `case_07` | `INCOMPLETE` | `INCOMPLETE` | PASS | 4 | 4 | EXACT |
| `case_08` | `INCOMPLETE` | `INCOMPLETE` | PASS | 4 | 4 | EXACT |
| `case_09` | `INCOMPLETE` | `INCOMPLETE` | PASS | 5 | 5 | EXACT |
| `case_10` | `INCOMPLETE` | `INCOMPLETE` | PASS | 4 | 4 | EXACT |
| `case_11` | `INCOMPLETE` | `INCOMPLETE` | PASS | 14 | 14 | EXACT |
| `case_12` | `INCOMPLETE` | `INCOMPLETE` | PASS | 5 | 5 | EXACT |
| `case_13` | `INCOMPLETE` | `INCOMPLETE` | PASS | 8 | 8 | EXACT |
| `case_14` | `INCOMPLETE` | `INCOMPLETE` | PASS | 5 | 5 | EXACT |
| `case_15` | `INCOMPLETE` | `INCOMPLETE` | PASS | 5 | 5 | EXACT |
| `case_16` | `INCOMPLETE` | `INCOMPLETE` | PASS | 7 | 7 | EXACT |
| `case_17` | `INCOMPLETE` | `INCOMPLETE` | PASS | 5 | 5 | EXACT |
| `case_18` | `INCOMPLETE` | `INCOMPLETE` | PASS | 14 | 14 | EXACT |
| `case_19` | `INCOMPLETE` | `INCOMPLETE` | PASS | 8 | 8 | EXACT |
| `case_20` | `INCOMPLETE` | `INCOMPLETE` | PASS | 8 | 8 | EXACT |
| `case_21` | `COMPLETE` | `COMPLETE` | PASS | 3 | 3 | EXACT |
| `case_22` | `INCOMPLETE` | `INCOMPLETE` | PASS | 8 | 8 | EXACT |
| `case_23` | `INCOMPLETE` | `INCOMPLETE` | PASS | 8 | 8 | EXACT |
| `case_24` | `INCOMPLETE` | `INCOMPLETE` | PASS | 7 | 7 | EXACT |
| `case_25` | `COMPLETE` | `COMPLETE` | PASS | 3 | 3 | EXACT |
| `case_26` | `COMPLETE` | `COMPLETE` | PASS | 6 | 6 | EXACT |
| `case_27` | `COMPLETE` | `COMPLETE` | PASS | 6 | 6 | EXACT |
| `case_28` | `COMPLETE` | `COMPLETE` | PASS | 6 | 6 | EXACT |
| `case_29` | `INCOMPLETE` | `INCOMPLETE` | PASS | 14 | 14 | EXACT |
| `case_30` | `INCOMPLETE` | `INCOMPLETE` | PASS | 14 | 14 | EXACT |
| `case_31` | `COMPLETE` | `COMPLETE` | PASS | 3 | 3 | EXACT |
| `case_32` | `INCOMPLETE` | `INCOMPLETE` | PASS | 5 | 5 | EXACT |

## 5. Mismatched Cases Analysis

None! 100% of the sample cases matched expected deletion status.
