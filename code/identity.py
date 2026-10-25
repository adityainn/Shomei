"""Identity resolution module for Shomei Deletion Audit Engine.

Correlates current snapshots (user_identities.csv) and historical identity
modifications (user_audit_log.csv) into unified temporal-aware IdentityProfiles.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set

from models import AuditLogEntry, DeletionRequest, IdentityProfile, UserIdentity


class IdentityResolver:
    """Resolves and reconstructs full identity sets from current and historical data."""

    def __init__(self, identities: List[UserIdentity], audit_log: List[AuditLogEntry]):
        self._profiles_by_user_id: Dict[str, IdentityProfile] = {}
        self._email_to_user_id: Dict[str, str] = {}
        self._phone_to_user_id: Dict[str, str] = {}
        self._hash_to_user_id: Dict[str, str] = {}
        self._historical_email_to_user_id: Dict[str, str] = {}

        self._build_profiles(identities, audit_log)

    def _build_profiles(self, identities: List[UserIdentity], audit_log: List[AuditLogEntry]) -> None:
        """Construct unified IdentityProfile objects and reverse-lookup indexes."""
        # 1. Initialize profiles with current snapshot
        for u in identities:
            profile = IdentityProfile(
                user_id=u.user_id,
                current_name=u.name,
                current_email=u.email,
                current_phone=u.phone,
                current_email_hash=u.email_hash,
                all_emails={u.email.lower()} if u.email else set(),
                all_phones={u.phone.lower()} if u.phone else set(),
                all_hashes={u.email_hash.lower()} if u.email_hash else set(),
                all_names={u.name.lower()} if u.name else set(),
                audit_history=[],
            )
            self._profiles_by_user_id[u.user_id] = profile

            if u.email:
                self._email_to_user_id[u.email.lower()] = u.user_id
            if u.phone:
                self._phone_to_user_id[u.phone.lower()] = u.user_id
            if u.email_hash:
                self._hash_to_user_id[u.email_hash.lower()] = u.user_id

        # 2. Attach historical audit entries and enrich identifier sets
        # Sort audit entries chronologically
        sorted_audit = sorted(audit_log, key=lambda a: a.event_time)
        for a in sorted_audit:
            profile = self._profiles_by_user_id.get(a.user_id)
            if not profile:
                # If a user exists in audit log but not current snapshot (e.g. deleted account)
                profile = IdentityProfile(
                    user_id=a.user_id,
                    current_name="",
                    current_email="",
                    current_phone="",
                    current_email_hash="",
                    all_emails=set(),
                    all_phones=set(),
                    all_hashes=set(),
                    all_names=set(),
                    audit_history=[],
                )
                self._profiles_by_user_id[a.user_id] = profile

            profile.audit_history.append(a)

            if a.field_name == "email":
                if a.old_value:
                    val = a.old_value.lower()
                    profile.all_emails.add(val)
                    self._historical_email_to_user_id[val] = a.user_id
                if a.new_value:
                    val = a.new_value.lower()
                    profile.all_emails.add(val)
            elif a.field_name == "phone":
                if a.old_value:
                    profile.all_phones.add(a.old_value.lower())
                    self._phone_to_user_id[a.old_value.lower()] = a.user_id
                if a.new_value:
                    profile.all_phones.add(a.new_value.lower())
            elif a.field_name == "email_hash":
                if a.old_value:
                    profile.all_hashes.add(a.old_value.lower())
                    self._hash_to_user_id[a.old_value.lower()] = a.user_id
                if a.new_value:
                    profile.all_hashes.add(a.new_value.lower())

    def resolve_email(self, email: str) -> Optional[IdentityProfile]:
        """Resolve a case email (current or historical) to its IdentityProfile."""
        clean = email.strip().lower()
        # Direct current lookup
        user_id = self._email_to_user_id.get(clean)
        if user_id:
            return self._profiles_by_user_id.get(user_id)

        # Historical audit log lookup
        user_id = self._historical_email_to_user_id.get(clean)
        if user_id:
            return self._profiles_by_user_id.get(user_id)

        return None

    def resolve_user_id(self, user_id: str) -> Optional[IdentityProfile]:
        """Resolve directly by internal user_id."""
        return self._profiles_by_user_id.get(user_id.strip())

    def resolve_any(self, identifier: str) -> Optional[IdentityProfile]:
        """Attempt resolution across email, historical email, phone, hash, or user_id."""
        clean = identifier.strip().lower()
        profile = self.resolve_email(clean)
        if profile:
            return profile

        user_id = self._profiles_by_user_id.get(identifier.strip())
        if user_id:
            return user_id

        user_id = self._phone_to_user_id.get(clean)
        if user_id:
            return self._profiles_by_user_id.get(user_id)

        user_id = self._hash_to_user_id.get(clean)
        if user_id:
            return self._profiles_by_user_id.get(user_id)

        return None

    def resolve_request(self, req: DeletionRequest) -> Optional[IdentityProfile]:
        """Resolve identity for a deletion request row."""
        return self.resolve_email(req.email)

    def all_profiles(self) -> List[IdentityProfile]:
        """Return list of all registered user identity profiles."""
        return list(self._profiles_by_user_id.values())
