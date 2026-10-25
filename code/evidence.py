"""Evidence indexing and multi-source correlation engine for Shomei.

Indexes all 94 evidence files (SQL, JSON, logs, text, images, PDFs) from dataset/,
extracts structured identifiers, and provides temporal-aware query methods that link
user profiles directly to concrete evidence artifacts.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from models import EvidenceFileMeta, IdentityProfile
from multimodal import MultimodalParser, MultimodalDocumentResult
from sql_engine import SQLEngine, SQLRecordMatch


@dataclass
class EvidenceOccurrence:
    """A grounded occurrence of an identifier or resource within an evidence file."""
    file_id: str
    file_path: str
    origin: str
    captured_at: str
    evidence_type: str  # 'sql', 'json', 'log', 'text', 'binary', 'pdf', 'image'
    matched_identifier: str
    system_id: str = ""
    resource_id: str = ""
    context_snippet: str = ""
    raw_record: Optional[Dict[str, Any]] = None


class EvidenceIndex:
    """In-memory inverted index of identifiers and resources across all evidence files."""

    def __init__(
        self,
        dataset_dir: str | Path,
        manifest: List[EvidenceFileMeta],
        sql_engine: Optional[SQLEngine] = None,
    ):
        self.dataset_dir = Path(dataset_dir)
        self.manifest = manifest
        self._manifest_by_id: Dict[str, EvidenceFileMeta] = {m.file_id: m for m in manifest}
        self.sql_engine = sql_engine or SQLEngine(dataset_dir, manifest)
        self.multimodal_parser = MultimodalParser(self.dataset_dir)
        self.multimodal_results: Dict[str, MultimodalDocumentResult] = {}

        # Inverted index: identifier.lower() -> List[EvidenceOccurrence]
        self._index: Dict[str, List[EvidenceOccurrence]] = {}
        # Resource index: resource_id -> List[EvidenceOccurrence]
        self._resource_index: Dict[str, List[EvidenceOccurrence]] = {}

        self._build_index()

    def _add_occurrence(self, ident: str, occ: EvidenceOccurrence) -> None:
        """Register an occurrence in the inverted index."""
        clean_id = ident.strip().lower()
        if not clean_id:
            return
        if clean_id not in self._index:
            self._index[clean_id] = []
        self._index[clean_id].append(occ)

        if occ.resource_id:
            res_id = occ.resource_id.strip()
            if res_id not in self._resource_index:
                self._resource_index[res_id] = []
            self._resource_index[res_id].append(occ)

    def _build_index(self) -> None:
        """Parse all non-SQL evidence files and build the in-memory inverted index."""
        email_pattern = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
        user_id_pattern = re.compile(r"user_\d+")
        resource_id_pattern = re.compile(r"(account|search|analytics|support|export|data_flow|backup|audit_record|tombstone|marketing)_\d+")

        for meta in self.manifest:
            full_path = self.dataset_dir / meta.file_path
            if not full_path.is_file():
                continue

            rel_path = meta.file_path.lower()

            # 1. JSON records
            if rel_path.endswith(".json"):
                try:
                    with open(full_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    self._index_json_object(data, meta)
                except Exception:
                    pass

            # 2. Log files
            elif rel_path.endswith(".log"):
                try:
                    with open(full_path, "r", encoding="utf-8") as f:
                        for line_no, line in enumerate(f, start=1):
                            line_str = line.strip()
                            if not line_str:
                                continue
                            self._index_log_line(line_str, line_no, meta)
                except Exception:
                    pass

            # 3. Plain-text records
            elif rel_path.endswith(".txt"):
                try:
                    with open(full_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    self._index_text_content(content, meta)
                except Exception:
                    pass

            # 4. PDF documents
            elif rel_path.endswith(".pdf"):
                try:
                    res = self.multimodal_parser.parse_pdf(meta.file_id, meta.file_path)
                    self.multimodal_results[meta.file_id] = res
                    if res.is_successful:
                        self._index_text_content(res.raw_text, meta, evidence_type="pdf")
                except Exception:
                    pass

            # 5. Image documents (PNG)
            elif rel_path.endswith(".png"):
                try:
                    res = self.multimodal_parser.parse_image(meta.file_id, meta.file_path)
                    self.multimodal_results[meta.file_id] = res
                except Exception:
                    pass

    def _index_json_object(self, obj: Any, meta: EvidenceFileMeta, parent_system: str = "") -> None:
        """Recursively walk JSON objects to extract identifiers and resources."""
        if isinstance(obj, dict):
            # Check for service exports wrapper pattern
            if "service_exports" in obj and isinstance(obj["service_exports"], dict):
                for service_name, sub in obj["service_exports"].items():
                    self._index_json_object(sub, meta, parent_system=service_name)
                return

            # Extract resource_id and service if present
            res_id = str(obj.get("resource_id", ""))
            system_id = str(obj.get("service", parent_system))

            if res_id:
                occ_res = EvidenceOccurrence(
                    file_id=meta.file_id,
                    file_path=meta.file_path,
                    origin=meta.origin,
                    captured_at=meta.captured_at,
                    evidence_type="json",
                    matched_identifier="",
                    system_id=system_id,
                    resource_id=res_id,
                    context_snippet=f"resource_id={res_id}",
                    raw_record=obj,
                )
                if res_id not in self._resource_index:
                    self._resource_index[res_id] = []
                self._resource_index[res_id].append(occ_res)

            # Find identifiers in keys/values
            for k, v in obj.items():
                if isinstance(v, (dict, list)):
                    self._index_json_object(v, meta, parent_system=system_id)
                elif isinstance(v, str):
                    val_lower = v.strip().lower()
                    # Check if key implies identifier or value looks like email/user_id
                    if any(term in k.lower() for term in ["email", "user_id", "phone", "hash", "reference", "lookup_key"]):
                        occ = EvidenceOccurrence(
                            file_id=meta.file_id,
                            file_path=meta.file_path,
                            origin=meta.origin,
                            captured_at=meta.captured_at,
                            evidence_type="json",
                            matched_identifier=val_lower,
                            system_id=system_id,
                            resource_id=res_id,
                            context_snippet=f"{k}={v}",
                            raw_record=obj,
                        )
                        self._add_occurrence(val_lower, occ)

        elif isinstance(obj, list):
            for item in obj:
                self._index_json_object(item, meta, parent_system=parent_system)

    def _index_log_line(self, line: str, line_no: int, meta: EvidenceFileMeta) -> None:
        """Parse structured key=value tokens from log lines."""
        # Extract tokens like key=value
        tokens = dict(re.findall(r'(\w+)=([^\s]+)', line))
        res_id = tokens.get("resource_id", "")
        service = tokens.get("service", "")

        # Check if line starts with timestamp
        line_parts = line.split()
        log_time = meta.captured_at
        if line_parts and "T" in line_parts[0] and line_parts[0].endswith("Z"):
            log_time = line_parts[0]

        if res_id:
            occ_res = EvidenceOccurrence(
                file_id=meta.file_id,
                file_path=meta.file_path,
                origin=meta.origin,
                captured_at=log_time,
                evidence_type="log",
                matched_identifier=res_id.lower(),
                system_id=service or self._map_resource_prefix_to_system(res_id),
                resource_id=res_id,
                context_snippet=f"line {line_no}: {line[:120]}",
                raw_record=tokens,
            )
            self._add_occurrence(res_id.lower(), occ_res)

        for k, v in tokens.items():
            k_lower = k.lower()
            if any(term in k_lower for term in ["email", "user_id", "customer_reference", "lookup_key", "phone", "hash"]):
                val_clean = v.strip('"\'').lower()
                if val_clean != "null" and val_clean:
                    occ = EvidenceOccurrence(
                        file_id=meta.file_id,
                        file_path=meta.file_path,
                        origin=meta.origin,
                        captured_at=log_time,
                        evidence_type="log",
                        matched_identifier=val_clean,
                        system_id=service,
                        resource_id=res_id,
                        context_snippet=f"line {line_no}: {line[:120]}",
                        raw_record=tokens,
                    )
                    self._add_occurrence(val_clean, occ)

    def _index_text_content(self, text: str, meta: EvidenceFileMeta, evidence_type: str = "text") -> None:
        """Scan free-text documents for identifiable strings, handling both tabular lines and document contexts."""
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        has_pipe_table = sum(1 for l in lines if "|" in l) >= 2

        if has_pipe_table:
            # Tabular multi-record document (e.g., handover text or disputed order register)
            for line_str in lines:
                emails = re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", line_str)
                user_ids = re.findall(r"\buser_\d+\b", line_str)
                res_ids = re.findall(r"\b((?:account|search|analytics|support|export|data_flow|backup|audit_record|tombstone|marketing|legal_hold)_\d+)\b", line_str)

                line_res = res_ids[0] if res_ids else ""
                line_sys = self._map_resource_prefix_to_system(line_res) if line_res else ""

                for e in emails:
                    occ = EvidenceOccurrence(
                        file_id=meta.file_id,
                        file_path=meta.file_path,
                        origin=meta.origin,
                        captured_at=meta.captured_at,
                        evidence_type=evidence_type,
                        matched_identifier=e.lower(),
                        system_id=line_sys,
                        resource_id=line_res,
                        context_snippet=line_str[:120].strip(),
                    )
                    self._add_occurrence(e.lower(), occ)

                for u in user_ids:
                    occ = EvidenceOccurrence(
                        file_id=meta.file_id,
                        file_path=meta.file_path,
                        origin=meta.origin,
                        captured_at=meta.captured_at,
                        evidence_type=evidence_type,
                        matched_identifier=u.lower(),
                        system_id=line_sys,
                        resource_id=line_res,
                        context_snippet=line_str[:120].strip(),
                    )
                    self._add_occurrence(u.lower(), occ)

                for r in res_ids:
                    occ = EvidenceOccurrence(
                        file_id=meta.file_id,
                        file_path=meta.file_path,
                        origin=meta.origin,
                        captured_at=meta.captured_at,
                        evidence_type=evidence_type,
                        matched_identifier=r.lower(),
                        system_id=self._map_resource_prefix_to_system(r),
                        resource_id=r,
                        context_snippet=line_str[:120].strip(),
                    )
                    self._add_occurrence(r.lower(), occ)
        else:
            # Single-context page/document (e.g. delivery correction PDF or compliance journal)
            emails = re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text)
            user_ids = re.findall(r"\buser_\d+\b", text)
            res_ids = re.findall(r"\b((?:account|search|analytics|support|export|data_flow|backup|audit_record|tombstone|marketing|legal_hold)_\d+)\b", text)

            primary_res = res_ids[0] if res_ids else ""
            primary_sys = self._map_resource_prefix_to_system(primary_res) if primary_res else ""

            for e in emails:
                occ = EvidenceOccurrence(
                    file_id=meta.file_id,
                    file_path=meta.file_path,
                    origin=meta.origin,
                    captured_at=meta.captured_at,
                    evidence_type=evidence_type,
                    matched_identifier=e.lower(),
                    system_id=primary_sys,
                    resource_id=primary_res,
                    context_snippet=text[:120].strip(),
                )
                self._add_occurrence(e.lower(), occ)

            for u in user_ids:
                occ = EvidenceOccurrence(
                    file_id=meta.file_id,
                    file_path=meta.file_path,
                    origin=meta.origin,
                    captured_at=meta.captured_at,
                    evidence_type=evidence_type,
                    matched_identifier=u.lower(),
                    system_id=primary_sys,
                    resource_id=primary_res,
                    context_snippet=text[:120].strip(),
                )
                self._add_occurrence(u.lower(), occ)

            for r in res_ids:
                occ = EvidenceOccurrence(
                    file_id=meta.file_id,
                    file_path=meta.file_path,
                    origin=meta.origin,
                    captured_at=meta.captured_at,
                    evidence_type=evidence_type,
                    matched_identifier=r.lower(),
                    system_id=self._map_resource_prefix_to_system(r),
                    resource_id=r,
                    context_snippet=text[:120].strip(),
                )
                self._add_occurrence(r.lower(), occ)

    @staticmethod
    def _map_resource_prefix_to_system(resource_id: str) -> str:
        """Map resource prefix to system_id."""
        prefix = resource_id.split("_")[0] if "_" in resource_id else ""
        mapping = {
            "account": "account_service",
            "search": "search_service",
            "analytics": "analytics_platform",
            "support": "support_platform",
            "export": "export_service",
            "data": "integration_service",  # data_flow
            "backup": "backup_service",
            "audit": "security_service",    # audit_record
            "tombstone": "identity_service",
            "marketing": "marketing_platform",
        }
        return mapping.get(prefix, "unknown_service")

    def search_identifiers(
        self,
        identifiers: Set[str],
        cutoff_time: Optional[str] = None,
    ) -> List[EvidenceOccurrence]:
        """Search all evidence files (SQL + JSON + logs + text) matching any of the identifiers."""
        results: List[EvidenceOccurrence] = []
        clean_ids = {i.strip().lower() for i in identifiers if i and i.strip()}

        # 1. Search inverted index (JSON, logs, text)
        for ident in clean_ids:
            occurrences = self._index.get(ident, [])
            for occ in occurrences:
                if cutoff_time is None or occ.captured_at <= cutoff_time:
                    results.append(occ)

        # 2. Search SQL engine
        if self.sql_engine:
            sql_matches = self.sql_engine.find_records_by_identifiers(clean_ids, cutoff_time)
            for m in sql_matches:
                results.append(
                    EvidenceOccurrence(
                        file_id=m.file_id,
                        file_path=m.file_path,
                        origin=m.origin,
                        captured_at=m.captured_at,
                        evidence_type="sql",
                        matched_identifier=m.matched_value,
                        system_id=self._map_table_to_system(m.table_name),
                        resource_id=m.resource_id,
                        context_snippet=f"{m.table_name}: {m.matched_field}={m.matched_value}",
                        raw_record=m.row_data,
                    )
                )

        return results

    def search_profile(
        self,
        profile: IdentityProfile,
        cutoff_time: Optional[str] = None,
    ) -> List[EvidenceOccurrence]:
        """Convenience method searching all identifiers for a user profile."""
        identifiers = profile.identifiers_at(cutoff_time)
        return self.search_identifiers(identifiers, cutoff_time)

    def search_resource_id(
        self,
        resource_id: str,
        cutoff_time: Optional[str] = None,
    ) -> List[EvidenceOccurrence]:
        """Find occurrences of a specific resource_id."""
        clean_res = resource_id.strip()
        occurrences = self._resource_index.get(clean_res, [])
        filtered = [
            occ for occ in occurrences
            if cutoff_time is None or occ.captured_at <= cutoff_time
        ]
        filtered.sort(key=lambda o: o.captured_at, reverse=True)
        return filtered

    def get_file_meta(self, file_id: str) -> Optional[EvidenceFileMeta]:
        """Get file manifest metadata by file_id."""
        return self._manifest_by_id.get(file_id)

    @staticmethod
    def _map_table_to_system(table_name: str) -> str:
        """Infer system_id from SQL table name."""
        tbl = table_name.lower()
        if "customer_profiles" in tbl or "customer_data" in tbl or "customer_accounts" in tbl:
            return "account_service"
        if "search" in tbl:
            return "search_service"
        if "analytics" in tbl:
            return "analytics_platform"
        if "support" in tbl:
            return "support_platform"
        if "export" in tbl:
            return "export_service"
        if "connector" in tbl:
            return "integration_service"
        if "backup" in tbl:
            return "backup_service"
        if "audit" in tbl or "security" in tbl:
            return "security_service"
        return "unknown_service"
