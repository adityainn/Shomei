"""SQLite-based execution engine for SQL snapshot evidence files.

Loads SQL evidence files into in-memory SQLite databases, indexes table schemas,
and executes parameterized queries to find records matching user identifiers
at or before a given audit cutoff time.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from models import EvidenceFileMeta, IdentityProfile


@dataclass
class SQLRecordMatch:
    """A matched record in an SQL evidence snapshot."""
    file_id: str
    file_path: str
    origin: str
    captured_at: str
    table_name: str
    resource_id: str
    matched_field: str
    matched_value: str
    row_data: Dict[str, Any]


class SQLEngine:
    """Manages SQLite in-memory databases for SQL evidence snapshots."""

    def __init__(self, dataset_dir: str | Path, manifest: List[EvidenceFileMeta]):
        self.dataset_dir = Path(dataset_dir)
        self._manifest_by_id: Dict[str, EvidenceFileMeta] = {m.file_id: m for m in manifest}
        self._manifest_by_path: Dict[str, EvidenceFileMeta] = {m.file_path: m for m in manifest}

        # Loaded databases: file_id -> (sqlite3.Connection, EvidenceFileMeta, Dict[table_name, List[col_names]])
        self._dbs: Dict[str, Tuple[sqlite3.Connection, EvidenceFileMeta, Dict[str, List[str]]]] = {}
        self._load_all_sql_files()

    def _load_all_sql_files(self) -> None:
        """Scan manifest for .sql files and load into in-memory SQLite connections."""
        for meta in self._manifest_by_id.values():
            if not meta.file_path.endswith(".sql"):
                continue

            full_path = self.dataset_dir / meta.file_path
            if not full_path.is_file():
                continue

            conn = sqlite3.connect(":memory:")
            with open(full_path, "r", encoding="utf-8") as f:
                sql_script = f.read()
            conn.executescript(sql_script)

            # Discover all user tables and columns
            tables_schema: Dict[str, List[str]] = {}
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            for (tbl_name,) in cursor.fetchall():
                cursor.execute(f"PRAGMA table_info('{tbl_name}');")
                cols = [row[1] for row in cursor.fetchall()]
                tables_schema[tbl_name] = cols

            self._dbs[meta.file_id] = (conn, meta, tables_schema)

    @property
    def loaded_databases(self) -> List[str]:
        """Return list of loaded database file_ids."""
        return list(self._dbs.keys())

    def get_database_meta(self, file_id: str) -> Optional[EvidenceFileMeta]:
        """Get manifest metadata for a database file_id."""
        item = self._dbs.get(file_id)
        return item[1] if item else None

    def find_records_by_identifiers(
        self,
        identifiers: Set[str],
        cutoff_time: Optional[str] = None,
    ) -> List[SQLRecordMatch]:
        """Search all loaded SQL databases for any record matching the supplied identifiers."""
        if not identifiers:
            return []

        clean_ids = {i.strip().lower() for i in identifiers if i and i.strip()}
        matches: List[SQLRecordMatch] = []

        for file_id, (conn, meta, tables_schema) in self._dbs.items():
            # Apply temporal cutoff: captured_at <= cutoff_time (R4.9, AGENTS.md §6.6)
            if cutoff_time is not None and meta.captured_at > cutoff_time:
                continue

            cur = conn.cursor()
            for tbl_name, cols in tables_schema.items():
                if tbl_name == "snapshot_scope":
                    continue

                # Case 1: Standard structured tables with identifier columns
                id_cols = [
                    c for c in cols
                    if any(key in c.lower() for key in [
                        "email", "user_id", "customer_reference",
                        "subject_reference", "phone", "hash", "display_name", "full_name"
                    ])
                ]

                if id_cols:
                    # Construct search conditions
                    conditions = []
                    params: List[str] = []
                    for c in id_cols:
                        for ident in clean_ids:
                            conditions.append(f"LOWER({c}) = ?")
                            params.append(ident)

                    if conditions:
                        query = f"SELECT * FROM \"{tbl_name}\" WHERE " + " OR ".join(conditions)
                        try:
                            cur.execute(query, params)
                            for row in cur.fetchall():
                                row_data = dict(zip(cols, row))
                                resource_id = str(row_data.get("resource_id", ""))

                                # Determine which field matched
                                matched_field = "unknown"
                                matched_val = ""
                                for c in id_cols:
                                    val = str(row_data.get(c, "")).strip().lower()
                                    if val in clean_ids:
                                        matched_field = c
                                        matched_val = val
                                        break

                                matches.append(
                                    SQLRecordMatch(
                                        file_id=file_id,
                                        file_path=meta.file_path,
                                        origin=meta.origin,
                                        captured_at=meta.captured_at,
                                        table_name=tbl_name,
                                        resource_id=resource_id,
                                        matched_field=matched_field,
                                        matched_value=matched_val,
                                        row_data=row_data,
                                    )
                                )
                        except Exception:
                            # Skip if query fails
                            pass

                # Case 2: Replica tables storing record_json
                if "record_json" in cols:
                    try:
                        cur.execute(f"SELECT * FROM \"{tbl_name}\";")
                        for row in cur.fetchall():
                            row_data = dict(zip(cols, row))
                            raw_json = str(row_data.get("record_json", ""))
                            # Check if any identifier appears in JSON with exact word boundaries
                            raw_lower = raw_json.lower()
                            matched_ident = None
                            for ident in clean_ids:
                                if re.search(r'\b' + re.escape(ident) + r'\b', raw_lower):
                                    matched_ident = ident
                                    break

                            if matched_ident:
                                resource_id = str(row_data.get("resource_id", ""))
                                matches.append(
                                    SQLRecordMatch(
                                        file_id=file_id,
                                        file_path=meta.file_path,
                                        origin=meta.origin,
                                        captured_at=meta.captured_at,
                                        table_name=tbl_name,
                                        resource_id=resource_id,
                                        matched_field="record_json",
                                        matched_value=matched_ident,
                                        row_data=row_data,
                                    )
                                )
                    except Exception:
                        pass

        return matches

    def find_records_for_profile(
        self,
        profile: IdentityProfile,
        cutoff_time: Optional[str] = None,
    ) -> List[SQLRecordMatch]:
        """Convenience method to query for all identifiers in an IdentityProfile."""
        identifiers = profile.identifiers_at(cutoff_time)
        return self.find_records_by_identifiers(identifiers, cutoff_time)
