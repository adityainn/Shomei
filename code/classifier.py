"""Multilingual Intent Classifier for Shomei Deletion Audit Engine.

Analyzes request texts across multiple languages (English, Portuguese, Korean,
Spanish, Japanese, French) to identify whether a submission is a genuine
GDPR/privacy erasure request or a non-deletion inquiry (e.g., rectification,
marketing opt-out, data export, invoice copy, login assistance).

Conforms to HackerRank Orchestrate contract: non-deletion requests are
classified as NOT_APPLICABLE with empty steps array.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple

from models import DeletionRequest, DeletionStatus


class RequestIntent(str, Enum):
    """Categorized intent of a user submission."""
    ERASURE = "ERASURE"
    RECTIFICATION = "RECTIFICATION"
    MARKETING_OPT_OUT = "MARKETING_OPT_OUT"
    SUBJECT_ACCESS = "SUBJECT_ACCESS"
    INVOICE_COPY = "INVOICE_COPY"
    EMAIL_UPDATE = "EMAIL_UPDATE"
    DATA_EXPORT = "DATA_EXPORT"
    LOGIN_ASSISTANCE = "LOGIN_ASSISTANCE"
    UNKNOWN = "UNKNOWN"


@dataclass
class IntentClassificationResult:
    """Outcome of intent analysis for a deletion request."""
    case_id: str
    detected_language: str
    intent: RequestIntent
    is_deletion_request: bool
    confidence: float
    rationale: str
    recommended_status: Optional[DeletionStatus] = None


class MultilingualIntentClassifier:
    """Deterministic and multilingual intent classification engine."""

    # Explicit non-deletion pattern rules with high precision
    NON_DELETION_PATTERNS = [
        (
            RequestIntent.LOGIN_ASSISTANCE,
            [
                r"\bcan'?t access my profile\b",
                r"\bresetting the login\b",
                r"\bdo not close the account\b",
                r"\bpassword reset\b",
            ],
            "User requested login assistance or password reset while explicitly asking not to close the account.",
        ),
        (
            RequestIntent.RECTIFICATION,
            [
                r"\bmisspelled on the account\b",
                r"\bcorrect it without removing\b",
                r"\brectif",
                r"\bupdate my (?:name|surname|details)\b",
            ],
            "User requested rectification or spelling correction without record removal.",
        ),
        (
            RequestIntent.MARKETING_OPT_OUT,
            [
                r"\bmarketing lists only\b",
                r"\bopt-?out of marketing\b",
                r"\bunsubscribe from (?:marketing|promotions|newsletters)\b",
                r"\bstill want receipts and service messages\b",
            ],
            "User requested marketing communication opt-out only, retaining transactional service account.",
        ),
        (
            RequestIntent.SUBJECT_ACCESS,
            [
                r"\bwhat personal information you hold\b",
                r"\binformation request, not a request to erase\b",
                r"\bsubject access request\b",
                r"\bdata access inquiry\b",
            ],
            "User submitted a formal subject access/information request, explicitly stating it is not an erasure request.",
        ),
        (
            RequestIntent.INVOICE_COPY,
            [
                r"\bcopy of (?:last year's )?invoices\b",
                r"\bleave my profile and purchase history in place\b",
                r"\breceipt copy\b",
                r"\bbilling statement copy\b",
            ],
            "User requested invoice/billing copies while explicitly asking to retain profile and history.",
        ),
        (
            RequestIntent.EMAIL_UPDATE,
            [
                r"\bchange the email address\b",
                r"\bwant to continue using the service\b",
                r"\bupdate my login email\b",
            ],
            "User requested an email address change to continue using the service.",
        ),
        (
            RequestIntent.DATA_EXPORT,
            [
                r"\bsend me a copy of the information\b.*?\bdon'?t delete\b",
                r"\bexport my data\b.*?\bcontinue using\b",
                r"\bdownload my data\b.*?\bleave\b",
            ],
            "User requested a data portability export while explicitly instructing not to delete the account.",
        ),
    ]

    # Multilingual deletion markers
    LANGUAGE_DELETION_PATTERNS = {
        "pt": [r"\bexclusão permanente da conta\b", r"\bapagar meus dados\b", r"\beliminar conta\b"],
        "es": [r"\beliminación permanente de la cuenta\b", r"\bsuprimir mi cuenta\b", r"\bborrar mis datos\b"],
        "fr": [r"\bsuppression définitive du compte\b", r"\beffacer mes données\b", r"\bsupprimer mon compte\b"],
        "ja": [r"アカウントの完全な削除", r"データの消去", r"アカウントを削除"],
        "ko": [r"계정의 영구 삭제", r"개인정보 삭제", r"계정 삭제를 요청"],
        "en": [
            r"\bpermanently delete\b",
            r"\bdelet(?:e|ing) my account\b",
            r"\baccount-deletion request\b",
            r"\berase (?:my|all) personal data\b",
            r"\brequest to delete\b",
        ],
    }

    def detect_language(self, text: str) -> str:
        """Detect the dominant language of the request text."""
        # Check Asian scripts first
        if re.search(r"[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]", text):
            return "ja"
        if re.search(r"[\uAC00-\uD7AF\u1100-\u11FF]", text):
            return "ko"

        # Check Latin languages
        lower = text.lower()
        if any(w in lower for w in ["exclusão", "e-mail", "anteriores", "identificadores"]):
            if "exclusão" in lower or "verifiquem" in lower:
                return "pt"
        if any(w in lower for w in ["eliminación", "correo", "revisen"]):
            return "es"
        if any(w in lower for w in ["suppression", "définitive", "veuillez", "adresse e-mail"]):
            return "fr"

        return "en"

    def classify_request(self, request: DeletionRequest) -> IntentClassificationResult:
        """Classify the intent of a deletion request."""
        text = request.request_text.strip()
        lang = self.detect_language(text)
        lower_text = text.lower()

        # 1. Check for explicit non-deletion patterns
        for intent, patterns, rationale in self.NON_DELETION_PATTERNS:
            for pat in patterns:
                if re.search(pat, lower_text, re.IGNORECASE):
                    return IntentClassificationResult(
                        case_id=request.case_id,
                        detected_language=lang,
                        intent=intent,
                        is_deletion_request=False,
                        confidence=0.98,
                        rationale=rationale,
                        recommended_status=DeletionStatus.NOT_APPLICABLE,
                    )

        # 2. Check for explicit deletion patterns in detected language
        for lang_code, patterns in self.LANGUAGE_DELETION_PATTERNS.items():
            for pat in patterns:
                if re.search(pat, text, re.IGNORECASE):
                    return IntentClassificationResult(
                        case_id=request.case_id,
                        detected_language=lang_code,
                        intent=RequestIntent.ERASURE,
                        is_deletion_request=True,
                        confidence=0.99,
                        rationale=f"Explicit erasure request identified matching standard {lang_code.upper()} deletion template.",
                        recommended_status=None,
                    )

        # 3. Default fallback: treat as standard erasure request with moderate confidence
        return IntentClassificationResult(
            case_id=request.case_id,
            detected_language=lang,
            intent=RequestIntent.ERASURE,
            is_deletion_request=True,
            confidence=0.85,
            rationale="No explicit non-deletion exclusion found; default to standard erasure audit workflow.",
            recommended_status=None,
        )
