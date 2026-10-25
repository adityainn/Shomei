"""Evaluation runner for Shomei Deletion Audit Engine.

Evaluates audit predictions against dataset/sample_output.csv across 32 sample cases.
Reports:
- Status accuracy (numerator/denominator, percentage)
- Per-status precision, recall, F1
- Step-level metrics (exact step match, step count, operation match, resource match, evidence ID match)
- Analysis of any mismatched cases
- Exports machine-readable report (JSON) and concise human-readable Markdown report
"""

from __future__ import annotations

import json
import os
import sys
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

# Add parent code directory to path
repo_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(repo_root / "code"))

from data_loader import DatasetLoader
from decision import DecisionEngine
from discovery import ResourceDiscoverer
from evidence import EvidenceIndex
from identity import IdentityResolver
from models import CaseOutput, DeletionRequest, DeletionStatus, Step
from policy import PolicyEngine
from sql_engine import SQLEngine
from steps import StepBuilder


def compute_metrics(
    predictions: Dict[str, CaseOutput],
    ground_truth: Dict[str, CaseOutput],
    requests: Dict[str, DeletionRequest],
) -> Dict[str, Any]:
    """Compute detailed evaluation metrics comparing predictions against ground truth."""
    total_cases = len(ground_truth)
    status_matches = 0
    exact_step_matches = 0

    # Status confusion matrix: exp_status -> pred_status -> count
    confusion_matrix: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    mismatched_cases: List[Dict[str, Any]] = []

    # Step-level metrics
    total_exp_steps = 0
    total_pred_steps = 0
    matching_step_counts = 0
    step_field_matches = {"phase": 0, "system_id": 0, "resource_id": 0, "operation": 0, "state": 0, "evidence_id": 0}
    total_compared_steps = 0

    case_details: List[Dict[str, Any]] = []

    for case_id, exp_out in ground_truth.items():
        pred_out = predictions.get(case_id)
        req = requests.get(case_id)

        if not pred_out:
            mismatched_cases.append({
                "case_id": case_id,
                "reason": "Missing prediction",
                "expected_status": exp_out.deletion_status.value,
                "predicted_status": None,
            })
            continue

        exp_status = exp_out.deletion_status.value
        pred_status = pred_out.deletion_status.value
        confusion_matrix[exp_status][pred_status] += 1

        is_status_match = (exp_status == pred_status)
        if is_status_match:
            status_matches += 1
        else:
            mismatched_cases.append({
                "case_id": case_id,
                "email": req.email if req else "",
                "reported_status": req.reported_status if req else "",
                "expected_status": exp_status,
                "predicted_status": pred_status,
                "reason": f"Status mismatch: expected {exp_status}, predicted {pred_status}",
            })

        # Step comparison
        exp_steps = exp_out.steps
        pred_steps = pred_out.steps
        total_exp_steps += len(exp_steps)
        total_pred_steps += len(pred_steps)

        if len(exp_steps) == len(pred_steps):
            matching_step_counts += 1

        exp_step_tuples = [(s.phase, s.system_id, s.resource_id, s.operation, s.state, s.evidence_id) for s in exp_steps]
        pred_step_tuples = [(s.phase, s.system_id, s.resource_id, s.operation, s.state, s.evidence_id) for s in pred_steps]

        is_exact_steps_match = (exp_step_tuples == pred_step_tuples)
        if is_exact_steps_match:
            exact_step_matches += 1

        # Compare aligned steps up to min length
        min_len = min(len(exp_steps), len(pred_steps))
        for i in range(min_len):
            es = exp_steps[i]
            ps = pred_steps[i]
            total_compared_steps += 1
            if es.phase == ps.phase:
                step_field_matches["phase"] += 1
            if es.system_id == ps.system_id:
                step_field_matches["system_id"] += 1
            if es.resource_id == ps.resource_id:
                step_field_matches["resource_id"] += 1
            if es.operation == ps.operation:
                step_field_matches["operation"] += 1
            if es.state == ps.state:
                step_field_matches["state"] += 1
            if es.evidence_id == ps.evidence_id:
                step_field_matches["evidence_id"] += 1

        case_details.append({
            "case_id": case_id,
            "status_match": is_status_match,
            "exact_steps_match": is_exact_steps_match,
            "expected_status": exp_status,
            "predicted_status": pred_status,
            "expected_step_count": len(exp_steps),
            "predicted_step_count": len(pred_steps),
        })

    # Per-status Precision, Recall, F1
    all_statuses = [s.value for s in DeletionStatus]
    status_metrics: Dict[str, Dict[str, float]] = {}
    for st in all_statuses:
        tp = confusion_matrix[st][st]
        fp = sum(confusion_matrix[other][st] for other in all_statuses if other != st)
        fn = sum(confusion_matrix[st][other] for other in all_statuses if other != st)

        precision = (tp / (tp + fp)) if (tp + fp) > 0 else 0.0
        recall = (tp / (tp + fn)) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

        support = sum(confusion_matrix[st].values())
        if support > 0 or (tp + fp) > 0:
            status_metrics[st] = {
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "f1": round(f1, 4),
                "support": support,
                "true_positives": tp,
                "false_positives": fp,
                "false_negatives": fn,
            }

    status_accuracy = (status_matches / total_cases) if total_cases > 0 else 0.0
    exact_step_accuracy = (exact_step_matches / total_cases) if total_cases > 0 else 0.0
    step_count_accuracy = (matching_step_counts / total_cases) if total_cases > 0 else 0.0

    field_accuracies = {}
    for k, v in step_field_matches.items():
        field_accuracies[k] = round((v / total_compared_steps), 4) if total_compared_steps > 0 else 0.0

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_cases": total_cases,
        "status_accuracy": {
            "numerator": status_matches,
            "denominator": total_cases,
            "percentage": round(status_accuracy * 100, 2),
            "target_met": (status_accuracy >= 0.80),
        },
        "exact_step_match_accuracy": {
            "numerator": exact_step_matches,
            "denominator": total_cases,
            "percentage": round(exact_step_accuracy * 100, 2),
        },
        "step_count_accuracy": {
            "numerator": matching_step_counts,
            "denominator": total_cases,
            "percentage": round(step_count_accuracy * 100, 2),
        },
        "step_field_accuracy": field_accuracies,
        "total_expected_steps": total_exp_steps,
        "total_predicted_steps": total_pred_steps,
        "per_status_metrics": status_metrics,
        "confusion_matrix": {k: dict(v) for k, v in confusion_matrix.items()},
        "mismatched_cases": mismatched_cases,
        "case_details": case_details,
    }


def generate_markdown_report(report_data: Dict[str, Any]) -> str:
    """Generate concise, publication-grade Markdown evaluation summary."""
    acc = report_data["status_accuracy"]
    step_acc = report_data["exact_step_match_accuracy"]
    per_status = report_data["per_status_metrics"]

    md = []
    md.append("# Shomei Phase 4 Precision Optimization & Edge Case Resolution Evaluation Report")
    md.append("")
    md.append(f"**Generated:** `{report_data['timestamp']}`  ")
    md.append(f"**Evaluation Corpus:** `dataset/sample_deletion_requests.csv` (32 sample cases)  ")
    md.append(f"**Ground Truth:** `dataset/sample_output.csv`  ")
    md.append("")
    md.append("## 1. Executive Summary")
    md.append("")
    status_target_badge = "**PASSED (>=80%)**" if acc["target_met"] else "**BELOW TARGET (<80%)**"
    md.append(f"- **Top-Level Status Accuracy:** **{acc['percentage']}%** ({acc['numerator']}/{acc['denominator']}) — {status_target_badge}")
    md.append(f"- **Exact Step-Sequence Match:** **{step_acc['percentage']}%** ({step_acc['numerator']}/{step_acc['denominator']})")
    md.append(f"- **Step Count Alignment:** **{report_data['step_count_accuracy']['percentage']}%** ({report_data['step_count_accuracy']['numerator']}/{report_data['step_count_accuracy']['denominator']})")
    md.append(f"- **Total Steps Evaluated:** Predicted {report_data['total_predicted_steps']} vs Expected {report_data['total_expected_steps']}")
    md.append("")
    md.append("## 2. Per-Status Performance")
    md.append("")
    md.append("| Status | Support | Precision | Recall | F1 Score | TP | FP | FN |")
    md.append("|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|")
    for st, m in per_status.items():
        md.append(f"| `{st}` | {m['support']} | {m['precision']:.3f} | {m['recall']:.3f} | {m['f1']:.3f} | {m['true_positives']} | {m['false_positives']} | {m['false_negatives']} |")
    md.append("")
    md.append("## 3. Step Field Accuracies (Aligned Steps)")
    md.append("")
    md.append("| Field | Match Rate |")
    md.append("|:---|:---:|")
    for field, rate in report_data["step_field_accuracy"].items():
        md.append(f"| `{field}` | {rate * 100:.1f}% |")
    md.append("")
    md.append("## 4. Case-by-Case Breakdown")
    md.append("")
    md.append("| Case ID | Expected Status | Predicted Status | Status Match | Expected Steps | Predicted Steps | Exact Steps Match |")
    md.append("|:---|:---:|:---:|:---:|:---:|:---:|:---:|")
    for c in report_data["case_details"]:
        s_icon = "PASS" if c["status_match"] else "FAIL"
        st_icon = "EXACT" if c["exact_steps_match"] else "DIFF"
        md.append(f"| `{c['case_id']}` | `{c['expected_status']}` | `{c['predicted_status']}` | {s_icon} | {c['expected_step_count']} | {c['predicted_step_count']} | {st_icon} |")
    md.append("")

    if report_data["mismatched_cases"]:
        md.append("## 5. Mismatched Cases Analysis")
        md.append("")
        for m in report_data["mismatched_cases"]:
            md.append(f"- **`{m['case_id']}`**: Expected `{m['expected_status']}`, got `{m['predicted_status']}`. Reason: {m['reason']}")
        md.append("")
    else:
        md.append("## 5. Mismatched Cases Analysis")
        md.append("")
        md.append("None! 100% of the sample cases matched expected deletion status.")
        md.append("")

    return "\n".join(md)


def main() -> None:
    """Run full evaluation pipeline."""
    print("=" * 70)
    print("Shomei Deletion Audit Engine — Phase 2 Evaluation Runner")
    print("=" * 70)

    dataset_dir = repo_root / "dataset"
    loader = DatasetLoader(dataset_dir)

    print("[1/5] Loading datasets...")
    identities = loader.load_user_identities()
    audit_log = loader.load_user_audit_log()
    manifest = loader.load_evidence_manifest()
    activities = loader.load_system_activity()
    rules = loader.load_deletion_rules()

    sample_requests_list = loader.load_deletion_requests("sample_deletion_requests.csv")
    sample_requests = {r.case_id: r for r in sample_requests_list}
    ground_truth = loader.load_sample_output("sample_output.csv")
    print(f"      Loaded {len(sample_requests)} sample requests, {len(ground_truth)} expected outputs.")

    print("[2/5] Initializing engines...")
    resolver = IdentityResolver(identities, audit_log)
    sql_engine = SQLEngine(dataset_dir, manifest)
    index = EvidenceIndex(dataset_dir, manifest, sql_engine)
    discoverer = ResourceDiscoverer(dataset_dir, manifest, sql_engine, index, activities)
    policy = PolicyEngine(rules)
    decision_engine = DecisionEngine(policy)
    step_builder = StepBuilder()

    print("[3/5] Running audit engine on 32 sample cases...")
    predictions: Dict[str, CaseOutput] = {}
    for req in sample_requests_list:
        profile = resolver.resolve_request(req)
        discovered = discoverer.discover_for_request(req, profile)
        decision = decision_engine.evaluate(req, profile, discovered)
        case_out = step_builder.build_case_output(decision)
        predictions[req.case_id] = case_out

    print("[4/5] Computing metrics...")
    report_data = compute_metrics(predictions, ground_truth, sample_requests)

    print("[5/5] Saving reports...")
    eval_dir = repo_root / "code" / "evaluation"
    eval_dir.mkdir(parents=True, exist_ok=True)

    json_path = eval_dir / "evaluation_report.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2)

    md_report = generate_markdown_report(report_data)
    md_path = eval_dir / "EVALUATION_REPORT.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_report)

    print("\n" + "=" * 70)
    print("EVALUATION RESULTS SUMMARY")
    print("=" * 70)
    acc = report_data["status_accuracy"]
    step_acc = report_data["exact_step_match_accuracy"]
    print(f"Status Accuracy:         {acc['percentage']}% ({acc['numerator']}/{acc['denominator']})")
    print(f"Exact Step-Match Rate:   {step_acc['percentage']}% ({step_acc['numerator']}/{step_acc['denominator']})")
    print(f"Target (>=80%):          {'MET' if acc['target_met'] else 'NOT MET'}")
    print(f"Reports saved to:")
    print(f"  - JSON: {json_path}")
    print(f"  - MD:   {md_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()
