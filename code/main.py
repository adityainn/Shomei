"""Main entry point for Shomei Deletion Audit Agent.

Orchestrates data ingestion, identity resolution, evidence index,
audit evaluation, and output serialization conforming to HackerRank Orchestrate contract.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

# Add current directory to python path
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from data_loader import DatasetLoader
from evidence import EvidenceIndex
from identity import IdentityResolver
from output import OutputSerializer
from sql_engine import SQLEngine


from decision import DecisionEngine
from discovery import ResourceDiscoverer
from policy import PolicyEngine
from steps import StepBuilder


def run_phase1_inspection(dataset_dir: Path, verbose: bool = False) -> int:
    """Run Phase 1 data ingestion, identity resolution, and index validation."""
    print("=" * 60)
    print(" Shomei Deletion Audit Engine — Phase 1 Scaffold Inspection")
    print("=" * 60)

    loader = DatasetLoader(dataset_dir)

    print("\n1. Loading dataset CSVs...")
    requests = loader.load_deletion_requests()
    identities = loader.load_user_identities()
    audit_log = loader.load_user_audit_log()
    activity = loader.load_system_activity()
    rules = loader.load_deletion_rules()
    manifest = loader.load_evidence_manifest()

    print(f"  - Deletion requests: {len(requests)} cases")
    print(f"  - User identities:   {len(identities)} profiles")
    print(f"  - User audit log:    {len(audit_log)} events")
    print(f"  - System activity:   {len(activity)} events")
    print(f"  - Deletion rules:    {len(rules)} policy rules")
    print(f"  - Evidence files:    {len(manifest)} manifest entries")

    print("\n2. Initializing IdentityResolver...")
    resolver = IdentityResolver(identities, audit_log)
    resolved_count = 0
    current_matches = 0
    historical_matches = 0

    for req in requests:
        profile = resolver.resolve_request(req)
        if profile:
            resolved_count += 1
            if req.email.lower() == profile.current_email.lower():
                current_matches += 1
            else:
                historical_matches += 1

    print(f"  - Resolved {resolved_count}/{len(requests)} requests ({resolved_count/len(requests)*100:.1f}%)")
    print(f"  - Matched current email:    {current_matches}")
    print(f"  - Matched historical audit: {historical_matches}")

    print("\n3. Loading SQL Engine...")
    sql_engine = SQLEngine(dataset_dir, manifest)
    print(f"  - In-memory SQLite databases loaded: {len(sql_engine.loaded_databases)}/24")

    print("\n4. Building Unified EvidenceIndex...")
    index = EvidenceIndex(dataset_dir, manifest, sql_engine)
    print("  - EvidenceIndex ready across SQL, JSON, logs, and text.")

    print("\n5. Testing Output Validation Scaffold (dry-run)...")
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        case_ids = [r.case_id for r in requests]
        OutputSerializer.generate_skeleton(case_ids, tmp_path)
        report = OutputSerializer.validate_file(
            tmp_path,
            expected_case_ids=case_ids,
            expected_row_count=518,
        )
        print(f"  - Skeleton generation and schema validation: {'PASSED' if report.is_valid else 'FAILED'}")
        if not report.is_valid:
            for err in report.errors:
                print(f"    ERROR: {err}")
            return 1
    finally:
        if tmp_path.exists():
            tmp_path.unlink()

    print("\n" + "=" * 60)
    print(" Phase 1 Scaffold Verification: ALL CHECKS PASSED")
    print("=" * 60)
    return 0


def run_full_audit(dataset_dir: Path, output_path: Path, verbose: bool = False) -> int:
    """Run full deletion audit across all 518 cases and write validated output.csv."""
    print("=" * 70)
    print("Shomei Deletion Audit Agent — Full 518-Case Execution")
    print("=" * 70)

    loader = DatasetLoader(dataset_dir)
    print("\n[1/5] Ingesting dataset files...")
    requests = loader.load_deletion_requests("deletion_requests.csv")
    identities = loader.load_user_identities()
    audit_log = loader.load_user_audit_log()
    manifest = loader.load_evidence_manifest()
    activity = loader.load_system_activity()
    rules = loader.load_deletion_rules()

    print(f"  - Deletion requests: {len(requests)} cases")
    print(f"  - User identities:   {len(identities)} profiles")
    print(f"  - User audit log:    {len(audit_log)} events")
    print(f"  - Evidence manifest: {len(manifest)} files")
    print(f"  - System activity:   {len(activity)} events")
    print(f"  - Deletion rules:    {len(rules)} policy rules")

    print("\n[2/5] Initializing engines...")
    resolver = IdentityResolver(identities, audit_log)
    sql_engine = SQLEngine(dataset_dir, manifest)
    index = EvidenceIndex(dataset_dir, manifest, sql_engine)
    discoverer = ResourceDiscoverer(dataset_dir, manifest, sql_engine, index, activity)
    policy = PolicyEngine(rules)
    decision_engine = DecisionEngine(policy)
    step_builder = StepBuilder()
    print("  - All engines successfully initialized.")

    print(f"\n[3/5] Auditing {len(requests)} deletion cases...")
    case_outputs = []
    status_counts = {"COMPLETE": 0, "INCOMPLETE": 0, "NOT_APPLICABLE": 0}

    for idx, req in enumerate(requests, start=1):
        profile = resolver.resolve_request(req)
        discovered = discoverer.discover_for_request(req, profile)
        decision = decision_engine.evaluate(req, profile, discovered)
        case_out = step_builder.build_case_output(decision)
        case_outputs.append(case_out)
        status_counts[case_out.deletion_status.value] += 1
        if idx % 100 == 0 or idx == len(requests):
            print(f"  - Audited {idx}/{len(requests)} cases...")

    print("\n[4/5] Serializing outputs...")
    OutputSerializer.serialize_to_file(case_outputs, output_path, sort_by_case_id=True)
    print(f"  - Written to: {output_path}")

    print("\n[5/5] Validating output CSV against strict challenge constraints...")
    expected_case_ids = [r.case_id for r in requests]
    requests_by_id = {r.case_id: r for r in requests}
    report = OutputSerializer.validate_file(
        output_path,
        expected_case_ids=expected_case_ids,
        expected_row_count=518,
        manifest=manifest,
        requests_by_id=requests_by_id,
    )

    print("\n" + "=" * 70)
    print("AUDIT EXECUTION SUMMARY")
    print("=" * 70)
    print(f"Target Output:     {output_path}")
    print(f"Total Rows:        {report.total_rows} (Expected: 518)")
    print(f"Validation Status: {'PASSED' if report.is_valid else 'FAILED'}")
    print(f"Status Breakdown:  COMPLETE={status_counts['COMPLETE']}, INCOMPLETE={status_counts['INCOMPLETE']}, NOT_APPLICABLE={status_counts['NOT_APPLICABLE']}")

    if not report.is_valid:
        print("\nVALIDATION ERRORS:")
        for err in report.errors:
            print(f"  ERROR: {err}")
        return 1

    print("All 518 rows strictly conform to the challenge contract.")
    print("=" * 70)
    return 0


def main() -> int:
    """CLI argument parser and dispatcher."""
    parser = argparse.ArgumentParser(description="Shomei Deletion Audit Agent")
    parser.add_argument(
        "--dataset",
        type=str,
        default="dataset",
        help="Path to dataset directory (default: dataset)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="output.csv",
        help="Path for generated output CSV (default: output.csv)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run Phase 1 scaffold verification without generating final outputs",
    )
    parser.add_argument(
        "--eval",
        action="store_true",
        help="Run Phase 2 evaluation runner on 32 public sample cases",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose logging",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    dataset_path = repo_root / args.dataset if not Path(args.dataset).is_absolute() else Path(args.dataset)
    output_path = repo_root / args.output if not Path(args.output).is_absolute() else Path(args.output)

    if args.eval:
        from evaluation.main import main as eval_main
        eval_main()
        return 0

    if args.dry_run:
        return run_phase1_inspection(dataset_path, verbose=args.verbose)

    return run_full_audit(dataset_path, output_path, verbose=args.verbose)


if __name__ == "__main__":
    sys.exit(main())
