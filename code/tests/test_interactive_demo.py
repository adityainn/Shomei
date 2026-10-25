"""Tests for Shomei Stage 2: Functional Interactive Audit Demo.

Verifies:
- Scenario selection and catalog discovery
- 8-stage audit workflow payload generation
- Status consistency across systems map, evidence explorer, findings, and final report
- Prevention of impossible states and honest verification attestation
- Mandatory synthetic data disclosure
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


def test_scenario_catalog():
    """Verify that the cases catalog contains both benchmark and synthetic demo scenarios."""
    res = client.get("/api/cases")
    assert res.status_code == 200
    data = res.json()
    assert "cases" in data
    cases = data["cases"]
    assert len(cases) >= 5

    # Check for core demonstration cases
    assert "demo_01" in cases
    assert "demo_02" in cases
    assert "demo_03" in cases
    assert "demo_04" in cases
    assert "demo_05" in cases

    # Check that required fields are present
    for cid in ["demo_01", "demo_02", "demo_04"]:
        c = cases[cid]
        assert "title" in c
        assert "email" in c
        assert "status" in c
        assert "is_synthetic" in c


def test_complete_audit_workflow():
    """Verify that a COMPLETE scenario is verified without residual findings."""
    res = client.post("/api/audit", json={
        "case_id": "demo_01",
        "email": "sarah.connor@example.com",
        "requested_at": "2026-08-10T14:00:00Z",
        "reported_status": "COMPLETE",
        "audit_at": "2026-08-15T10:00:00Z",
        "request_text": "Please permanently delete my user account and profile data."
    })
    assert res.status_code == 200
    data = res.json()

    assert data["deletion_status"] == "COMPLETE"
    assert len(data["systems_map"]) == 8
    assert len(data["evidence_items"]) == 8

    # All systems must be COMPLETE
    for s in data["systems_map"]:
        assert s["status"] == "COMPLETE"

    # All evidence must be VERIFIED_ABSENT or PSEUDONYMIZED
    for ev in data["evidence_items"]:
        assert ev["verification_status"] in ["VERIFIED_ABSENT", "PSEUDONYMIZED"]

    # 0 outstanding findings
    report = data["final_report"]
    assert report["summary_counts"]["outstanding_findings_count"] == 0
    assert report["distinctions"]["deletion_independently_verified"] is True
    assert report["audit_certificate"] is not None
    assert "SHOMEI-CERT" in report["audit_certificate"]
    assert "Synthetic demonstration data" in data["disclosure"]


def test_incomplete_audit_workflow_with_ghost_data():
    """Verify that an INCOMPLETE scenario detects residual ghost data and DOES NOT certify."""
    res = client.post("/api/audit", json={
        "case_id": "demo_02",
        "email": "leila.haddad@example.com",
        "requested_at": "2026-08-12T09:30:00Z",
        "reported_status": "COMPLETE",
        "audit_at": "2026-08-15T10:00:00Z",
        "request_text": "I closed my account 3 days ago. Ensure my autocomplete entries are erased."
    })
    assert res.status_code == 200
    data = res.json()

    assert data["deletion_status"] == "INCOMPLETE"
    assert len(data["systems_map"]) == 8

    # Systems with residual data must be marked INCOMPLETE
    systems_by_id = {s["id"]: s for s in data["systems_map"]}
    assert systems_by_id["replicas"]["status"] == "INCOMPLETE"
    assert systems_by_id["search_index"]["status"] == "INCOMPLETE"

    # Evidence items must include RESIDUAL_DETECTED
    evidence_by_sys = {e["system_id"]: e for e in data["evidence_items"]}
    assert evidence_by_sys["replicas"]["verification_status"] == "RESIDUAL_DETECTED"
    assert evidence_by_sys["search_index"]["verification_status"] == "RESIDUAL_DETECTED"

    # Outstanding findings must be present
    report = data["final_report"]
    assert report["summary_counts"]["outstanding_findings_count"] > 0

    # HONEST REPORT: Cannot mark as verified while unresolved findings remain
    assert report["distinctions"]["deletion_independently_verified"] is False
    assert report["audit_certificate"] is None
    assert "Synthetic demonstration data" in data["disclosure"]


def test_not_applicable_audit_workflow():
    """Verify that a legal hold or non-erasure inquiry is classified as NOT_APPLICABLE."""
    res = client.post("/api/audit", json={
        "case_id": "demo_04",
        "email": "alexandra.dupont@example.fr",
        "requested_at": "2026-08-15T15:20:00Z",
        "reported_status": "NOT_STARTED",
        "audit_at": "2026-08-17T10:00:00Z",
        "request_text": "I want all my banking records deleted immediately."
    })
    assert res.status_code == 200
    data = res.json()

    assert data["deletion_status"] == "NOT_APPLICABLE"
    for s in data["systems_map"]:
        assert s["status"] == "NOT_APPLICABLE"

    for ev in data["evidence_items"]:
        assert ev["verification_status"] == "EXEMPT"

    report = data["final_report"]
    assert report["overall_audit_status"] == "NOT_APPLICABLE"
    assert report["distinctions"]["deletion_independently_verified"] is False
    assert "Synthetic demonstration data" in data["disclosure"]


def test_statutory_verification_rules():
    """Verify that all 6 statutory invariant rules are evaluated."""
    res = client.post("/api/audit", json={
        "case_id": "demo_01",
        "email": "sarah.connor@example.com",
        "requested_at": "2026-08-10T14:00:00Z",
        "reported_status": "COMPLETE",
        "audit_at": "2026-08-15T10:00:00Z",
        "request_text": "Delete everything."
    })
    data = res.json()
    conditions = data["verification_conditions"]
    assert len(conditions) == 6

    rule_names = [c["rule_name"] for c in conditions]
    assert "Primary Entity Erasure" in rule_names
    assert "Asynchronous Replica Propagation" in rule_names
    assert "Inverted Index Document Purge" in rule_names
    assert "Audit Log Pseudonymization" in rule_names
    assert "Integration Sync Connector Lockdown" in rule_names
    assert "Disaster Recovery Restore Block" in rule_names

    for c in conditions:
        assert "statutory_citation" in c
        assert "passed" in c


def test_custom_user_edited_request_evaluation():
    """Verify that user-edited custom request parameters are evaluated honestly."""
    # 1. Custom edited input with AML/Legal hold keyword -> NOT_APPLICABLE
    res = client.post("/api/audit", json={
        "case_id": "custom_edited_case",
        "email": "custom.user@example.org",
        "requested_at": "2026-08-16T12:00:00Z",
        "reported_status": "NOT_STARTED",
        "audit_at": "2026-08-17T12:00:00Z",
        "request_text": "Please delete my account, but note I am subject to ongoing FinCEN AML legal hold."
    })
    assert res.status_code == 200
    data = res.json()
    assert data["deletion_status"] == "NOT_APPLICABLE"
    assert data["final_report"]["overall_audit_status"] == "NOT_APPLICABLE"
    assert data["final_report"]["distinctions"]["deletion_independently_verified"] is False

    # 2. Custom edited input with INCOMPLETE claim
    res2 = client.post("/api/audit", json={
        "case_id": "custom_drift_case",
        "email": "drift.user@example.org",
        "requested_at": "2026-08-16T12:00:00Z",
        "reported_status": "INCOMPLETE",
        "audit_at": "2026-08-17T12:00:00Z",
        "request_text": "I requested deletion but replicas still show data."
    })
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["deletion_status"] == "INCOMPLETE"
    assert data2["final_report"]["distinctions"]["deletion_independently_verified"] is False
    assert data2["final_report"]["audit_certificate"] is None

