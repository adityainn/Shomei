"""Tests for Shomei Stage 4: Product Quality, Audit Traceability, and Report Exports.

Verifies:
- Bidirectional traceability between findings and supporting evidence artifacts
- Report export metadata, synthetic disclosure, and schema fidelity
- Honest attestation behavior: certificates issued ONLY when COMPLETE, withheld when INCOMPLETE
- Statutory 4-way distinction guarantees (Requested, Observed, Recommended, Independently Verified)
- Robust input validation and error rejection (HTTP 422 for malformed email or empty text)
- Outstanding uncertainties reporting
"""

import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "code"))

import server

client = TestClient(server.app)


def test_finding_to_evidence_bidirectional_traceability():
    """Verify that every finding points to an existing evidence item and vice versa."""
    # Run audit on demo_02 (an INCOMPLETE case with residual data in read replicas and search index)
    payload = {
        "case_id": "demo_02",
        "email": "marcus.vance@example.com",
        "requested_at": "2026-08-14T09:30:00Z",
        "reported_status": "COMPLETE",
        "audit_at": "2026-08-16T11:00:00Z",
        "request_text": "Please delete all my account data and personal records under GDPR.",
    }
    res = client.post("/api/audit", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["deletion_status"] == "INCOMPLETE"
    findings = data["findings"]
    evidence_items = data["evidence_items"]

    assert len(findings) > 0, "INCOMPLETE audit must generate findings"
    assert len(evidence_items) > 0, "Evidence explorer must contain collected evidence artifacts"

    evidence_ids = {e["evidence_id"] for e in evidence_items}

    # Verify that every finding has a valid, existing supporting evidence ID
    for f in findings:
        assert "finding_id" in f and f["finding_id"]
        assert "evidence_id" in f and f["evidence_id"]
        assert f["evidence_id"] in evidence_ids, f"Finding {f['finding_id']} references missing evidence {f['evidence_id']}"
        assert "severity" in f
        assert "system" in f
        assert "resource" in f
        assert "description" in f
        assert "verification_status" in f
        assert "recommended_action" in f

    # Verify bidirectional link: evidence linked_finding_id matches a finding
    finding_ids = {f["finding_id"] for f in findings}
    linked_evidence_count = 0
    for e in evidence_items:
        if e.get("linked_finding_id"):
            assert e["linked_finding_id"] in finding_ids, f"Evidence {e['evidence_id']} links to non-existent finding {e['linked_finding_id']}"
            linked_evidence_count += 1

    assert linked_evidence_count > 0, "At least one evidence item must be linked to a finding"


def test_complete_audit_has_no_residual_findings_and_issues_certificate():
    """Verify that a COMPLETE audit contains 0 residual findings and issues a tamper-evident certificate."""
    payload = {
        "case_id": "demo_01",
        "email": "sarah.connor@example.com",
        "requested_at": "2026-08-10T14:00:00Z",
        "reported_status": "COMPLETE",
        "audit_at": "2026-08-12T10:00:00Z",
        "request_text": "I want my account permanently deleted.",
    }
    res = client.post("/api/audit", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["deletion_status"] == "COMPLETE"
    report = data["final_report"]
    distinctions = report["distinctions"]

    # Deletion independently verified must be True
    assert distinctions["deletion_independently_verified"] is True
    assert report["audit_certificate"] is not None
    assert report["audit_certificate"].startswith("SHOMEI-CERT-")

    # Residual findings count must be 0
    residual_findings = [f for f in data["findings"] if f.get("remediation_required", False)]
    assert len(residual_findings) == 0

    # Outstanding uncertainties should indicate zero residual
    assert "None" in report["outstanding_uncertainties"] or "Zero" in report["outstanding_uncertainties"]


def test_incomplete_audit_withholds_certificate_and_reports_uncertainties():
    """Verify that an INCOMPLETE audit strictly withholds compliance certificates."""
    payload = {
        "case_id": "demo_02",
        "email": "marcus.vance@example.com",
        "requested_at": "2026-08-14T09:30:00Z",
        "reported_status": "COMPLETE",
        "audit_at": "2026-08-16T11:00:00Z",
        "request_text": "Please delete all my account data.",
    }
    res = client.post("/api/audit", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["deletion_status"] == "INCOMPLETE"
    report = data["final_report"]
    distinctions = report["distinctions"]

    # Must NOT claim independent verification
    assert distinctions["deletion_independently_verified"] is False
    assert report["audit_certificate"] is None, "Incomplete audit must never issue a certificate"
    assert "UNVERIFIED" in report["verification_outcome"] or "INCOMPLETE" in report["verification_outcome"]
    assert "Residual" in report["outstanding_uncertainties"] or "withheld" in report["outstanding_uncertainties"]


def test_report_export_metadata_and_disclosure():
    """Verify that the final report contains required export metadata and synthetic disclosure."""
    payload = {
        "case_id": "demo_01",
        "email": "sarah.connor@example.com",
        "requested_at": "2026-08-10T14:00:00Z",
        "reported_status": "COMPLETE",
        "audit_at": "2026-08-12T10:00:00Z",
        "request_text": "Please erase my account.",
    }
    res = client.post("/api/audit", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["is_synthetic"] is True
    assert "disclosure" in data
    assert "Synthetic demonstration data" in data["disclosure"]

    report = data["final_report"]
    assert "export_metadata" in report
    meta = report["export_metadata"]
    assert meta["schema_version"] == "1.0"
    assert "Shomei" in meta["generator"]
    assert meta["tamper_evident"] is True


def test_input_validation_rejection():
    """Verify that missing or malformed inputs return HTTP 422 with actionable errors."""
    # 1. Invalid email without domain
    bad_email_payload = {
        "case_id": "custom",
        "email": "not-an-email",
        "requested_at": "2026-08-10T14:00:00Z",
        "reported_status": "COMPLETE",
        "audit_at": "2026-08-12T10:00:00Z",
        "request_text": "Delete my data please.",
    }
    res1 = client.post("/api/audit", json=bad_email_payload)
    assert res1.status_code == 422
    assert "valid subject email" in res1.json()["detail"].lower()

    # 2. Empty request text
    empty_text_payload = {
        "case_id": "custom",
        "email": "valid@example.com",
        "requested_at": "2026-08-10T14:00:00Z",
        "reported_status": "COMPLETE",
        "audit_at": "2026-08-12T10:00:00Z",
        "request_text": "   ",
    }
    res2 = client.post("/api/audit", json=empty_text_payload)
    assert res2.status_code == 422
    assert "request text" in res2.json()["detail"].lower()


def test_rerun_idempotency_and_state_isolation():
    """Verify that multiple consecutive runs (reruns) remain deterministic without state contamination."""
    payload = {
        "case_id": "demo_02",
        "email": "marcus.vance@example.com",
        "requested_at": "2026-08-14T09:30:00Z",
        "reported_status": "COMPLETE",
        "audit_at": "2026-08-16T11:00:00Z",
        "request_text": "Please delete all my account data.",
    }

    res_1 = client.post("/api/audit", json=payload)
    assert res_1.status_code == 200
    data_1 = res_1.json()

    res_2 = client.post("/api/audit", json=payload)
    assert res_2.status_code == 200
    data_2 = res_2.json()

    # Reruns must yield identical findings and outcomes
    assert data_1["deletion_status"] == data_2["deletion_status"] == "INCOMPLETE"
    assert len(data_1["findings"]) == len(data_2["findings"])
    assert data_1["final_report"]["distinctions"] == data_2["final_report"]["distinctions"]
    assert data_1["final_report"]["audit_certificate"] == data_2["final_report"]["audit_certificate"] is None


def test_concurrent_asynchronous_run_isolation():
    """Verify that distinct consecutive case audits do not contaminate or bleed state into each other."""
    payload_clean = {
        "case_id": "demo_01",
        "email": "sarah.connor@example.com",
        "requested_at": "2026-08-10T14:00:00Z",
        "reported_status": "COMPLETE",
        "audit_at": "2026-08-12T10:00:00Z",
        "request_text": "Permanently delete my account records.",
    }
    payload_residual = {
        "case_id": "demo_02",
        "email": "marcus.vance@example.com",
        "requested_at": "2026-08-14T09:30:00Z",
        "reported_status": "COMPLETE",
        "audit_at": "2026-08-16T11:00:00Z",
        "request_text": "Please delete all my account data.",
    }

    # Run clean then residual
    res_clean = client.post("/api/audit", json=payload_clean)
    res_residual = client.post("/api/audit", json=payload_residual)

    assert res_clean.status_code == 200
    assert res_residual.status_code == 200

    clean_data = res_clean.json()
    residual_data = res_residual.json()

    assert clean_data["case_id"] == "demo_01"
    assert clean_data["deletion_status"] == "COMPLETE"
    assert clean_data["final_report"]["audit_certificate"] is not None

    assert residual_data["case_id"] == "demo_02"
    assert residual_data["deletion_status"] == "INCOMPLETE"
    assert residual_data["final_report"]["audit_certificate"] is None


def test_client_run_state_invalidation_logic():
    """Simulate client state machine invariants: run IDs, aborts, resets, and export rejection."""
    class ClientAuditStateMachine:
        def __init__(self):
            self.current_step = 1
            self.audit_state = "UNRUN"  # UNRUN | RUNNING | COMPLETED
            self.current_run_id = 0
            self.authoritative_audit_result = None
            self.printable_report_html = ""
            self.is_inputs_stale = False

        def trigger_audit_start(self):
            if self.audit_state == "RUNNING":
                return False  # Prevent duplicate submission
            self.current_run_id += 1
            this_run_id = self.current_run_id
            self.audit_state = "RUNNING"
            self.authoritative_audit_result = None  # Invalidate previous result
            self.is_inputs_stale = False
            return this_run_id

        def complete_audit(self, run_id, data):
            if run_id != self.current_run_id:
                return False  # Stale run, discard!
            self.authoritative_audit_result = data
            self.audit_state = "COMPLETED"
            self.printable_report_html = f"Report for {data['case_id']}"
            return True

        def reset_workflow(self):
            self.current_run_id += 1  # Invalidate ongoing runs
            self.audit_state = "UNRUN"
            self.authoritative_audit_result = None
            self.printable_report_html = ""
            self.current_step = 1
            self.is_inputs_stale = False

        def export_json(self):
            if self.audit_state == "RUNNING":
                raise ValueError("Audit currently running")
            if self.audit_state != "COMPLETED" or not self.authoritative_audit_result:
                raise ValueError("No completed audit result available")
            return self.authoritative_audit_result

    sm = ClientAuditStateMachine()

    # 1. In UNRUN state, export must be rejected
    with pytest.raises(ValueError, match="No completed audit"):
        sm.export_json()

    # 2. Start Run 1
    run_1_id = sm.trigger_audit_start()
    assert sm.audit_state == "RUNNING"
    assert sm.authoritative_audit_result is None

    # Duplicate run blocked while RUNNING
    assert sm.trigger_audit_start() is False

    # While RUNNING, export must be rejected
    with pytest.raises(ValueError, match="currently running"):
        sm.export_json()

    # 3. User clicks Reset while Run 1 is in-flight
    sm.reset_workflow()
    assert sm.audit_state == "UNRUN"
    assert sm.authoritative_audit_result is None
    assert sm.printable_report_html == ""

    # Late response from Run 1 arrives after reset: must be discarded!
    assert sm.complete_audit(run_1_id, {"case_id": "demo_01"}) is False
    assert sm.audit_state == "UNRUN"
    assert sm.authoritative_audit_result is None

    # 4. Start Run 2, followed immediately by Run 3 before Run 2 finishes
    sm.audit_state = "UNRUN"
    run_2_id = sm.trigger_audit_start()
    sm.audit_state = "UNRUN"  # simulate cancellation
    run_3_id = sm.trigger_audit_start()

    # Older Run 2 completes late: must be discarded
    assert sm.complete_audit(run_2_id, {"case_id": "demo_01"}) is False
    assert sm.authoritative_audit_result is None

    # Newer Run 3 completes: must be accepted!
    assert sm.complete_audit(run_3_id, {"case_id": "demo_02"}) is True
    assert sm.authoritative_audit_result["case_id"] == "demo_02"
    assert sm.audit_state == "COMPLETED"

    # Export now succeeds
    exp = sm.export_json()
    assert exp["case_id"] == "demo_02"


def test_audit_bundle_generation_across_all_scenarios():
    """Verify audit bundle generation across all representative demonstration scenarios."""
    scenarios = [
        ("demo_01", "COMPLETE"),
        ("demo_02", "INCOMPLETE"),
        ("demo_03", "INCOMPLETE"),
        ("demo_04", "NOT_APPLICABLE"),
        ("demo_05", "NOT_APPLICABLE"),
    ]

    for cid, expected_status in scenarios:
        res_case = client.get("/api/cases")
        cases = res_case.json()["cases"]
        cinfo = cases[cid]

        payload = {
            "case_id": cid,
            "email": cinfo["email"],
            "requested_at": cinfo.get("requested_at", "2026-08-10T14:00:00Z"),
            "reported_status": cinfo.get("reported_status", "COMPLETE"),
            "audit_at": cinfo.get("reported_at", "2026-08-12T10:00:00Z"),
            "request_text": cinfo.get("request_text", "Please delete my records."),
        }
        res = client.post("/api/audit", json=payload)
        assert res.status_code == 200, f"Audit failed for scenario {cid}"
        data = res.json()

        assert data["deletion_status"] == expected_status
        assert len(data["systems_map"]) == 8  # All 8 platform systems in catalog
        assert len(data["evidence_items"]) > 0
        assert len(data["verification_conditions"]) >= 6
        assert "final_report" in data
        assert data["is_synthetic"] is True

        report = data["final_report"]
        assert "distinctions" in report
        assert "outstanding_uncertainties" in report
        assert "disclosure" in report

        if expected_status == "COMPLETE":
            assert report["audit_certificate"] is not None
            assert report["distinctions"]["deletion_independently_verified"] is True
        elif expected_status == "INCOMPLETE":
            assert report["audit_certificate"] is None
            assert report["distinctions"]["deletion_independently_verified"] is False
            assert "UNVERIFIED" in report["verification_outcome"] or "INCOMPLETE" in report["verification_outcome"]
        else:
            assert report["distinctions"]["deletion_independently_verified"] is False


def test_statutory_distinctions_and_disclosure_integrity():
    """Verify that every audit report preserves strict separation of the 4 statutory categories."""
    payload = {
        "case_id": "demo_02",
        "email": "marcus.vance@example.com",
        "requested_at": "2026-08-14T09:30:00Z",
        "reported_status": "COMPLETE",
        "audit_at": "2026-08-16T11:00:00Z",
        "request_text": "Please delete all my account data.",
    }
    res = client.post("/api/audit", json=payload)
    assert res.status_code == 200
    data = res.json()
    distinctions = data["final_report"]["distinctions"]

    # 1. Deletion Requested (Intake)
    assert "deletion_requested" in distinctions
    assert len(distinctions["deletion_requested"]) > 10

    # 2. Deletion Evidence Observed (Discovery)
    assert "deletion_evidence_observed" in distinctions
    assert len(distinctions["deletion_evidence_observed"]) > 10

    # 3. Remediation Recommended (Synthesis)
    assert "remediation_recommended" in distinctions
    assert len(distinctions["remediation_recommended"]) > 10

    # 4. Deletion Independently Verified (Statutory Outcome)
    assert "deletion_independently_verified" in distinctions
    assert distinctions["deletion_independently_verified"] is False  # Must be False for INCOMPLETE


