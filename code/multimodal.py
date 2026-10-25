"""Multimodal Evidence Parser for Shomei Deletion Audit Engine.

Extracts structured text, entities, and metadata from non-text evidence artifacts:
- PDF documents (4 files: customer statements, disputed order registers, compliance extracts, delivery correction attachments)
- PNG images (11 files: admin console screenshots, storage browser views, UI inspectors)

Ensures untrusted evidence is safely sanitized and never executed.
Provides source traceability with file IDs, page numbers, and structured entity mappings.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ExtractedEntity:
    """A verified entity extracted from an artifact."""
    entity_type: str  # email, user_id, order_id, resource_id, ticket_id, timestamp
    value: str
    page_no: Optional[int] = None
    confidence: float = 1.0
    context_snippet: str = ""


@dataclass
class MultimodalDocumentResult:
    """Complete extraction result for a document artifact."""
    file_id: str
    file_path: str
    artifact_type: str  # pdf or image
    is_successful: bool
    page_count: int = 1
    raw_text: str = ""
    entities: List[ExtractedEntity] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    limitations: List[str] = field(default_factory=list)


class MultimodalParser:
    """Extracts facts from PDF documents and image screenshots."""

    def __init__(self, dataset_dir: Path):
        self.dataset_dir = dataset_dir

    def parse_pdf(self, file_id: str, relative_path: str) -> MultimodalDocumentResult:
        """Parse text and structured entities from a PDF document using pypdf."""
        full_path = self.dataset_dir / relative_path
        if not full_path.is_file():
            return MultimodalDocumentResult(
                file_id=file_id,
                file_path=relative_path,
                artifact_type="pdf",
                is_successful=False,
                limitations=[f"File not found: {relative_path}"],
            )

        try:
            import pypdf
        except ImportError:
            return MultimodalDocumentResult(
                file_id=file_id,
                file_path=relative_path,
                artifact_type="pdf",
                is_successful=False,
                limitations=["pypdf library not available in runtime environment"],
            )

        try:
            reader = pypdf.PdfReader(str(full_path))
            page_count = len(reader.pages)
            pages_text: List[str] = []
            entities: List[ExtractedEntity] = []

            for page_idx, page in enumerate(reader.pages, start=1):
                txt = page.extract_text() or ""
                pages_text.append(txt)

                # Extract emails
                for m in re.finditer(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", txt):
                    entities.append(ExtractedEntity(
                        entity_type="email",
                        value=m.group(0).lower(),
                        page_no=page_idx,
                        context_snippet=txt[max(0, m.start() - 30):min(len(txt), m.end() + 30)].strip(),
                    ))

                # Extract user IDs
                for m in re.finditer(r"\buser_\d+\b", txt):
                    entities.append(ExtractedEntity(
                        entity_type="user_id",
                        value=m.group(0).lower(),
                        page_no=page_idx,
                        context_snippet=txt[max(0, m.start() - 30):min(len(txt), m.end() + 30)].strip(),
                    ))

                # Extract resource IDs
                for m in re.finditer(r"\b((?:account|search|analytics|support|export|data_flow|backup|audit_record|tombstone|marketing|legal_hold)_\d+)\b", txt):
                    entities.append(ExtractedEntity(
                        entity_type="resource_id",
                        value=m.group(0),
                        page_no=page_idx,
                        context_snippet=txt[max(0, m.start() - 30):min(len(txt), m.end() + 30)].strip(),
                    ))

                # Extract order references
                for m in re.finditer(r"\bORD-\d+\b", txt):
                    entities.append(ExtractedEntity(
                        entity_type="order_id",
                        value=m.group(0),
                        page_no=page_idx,
                        context_snippet=txt[max(0, m.start() - 30):min(len(txt), m.end() + 30)].strip(),
                    ))

            full_text = "\n--- PAGE BREAK ---\n".join(pages_text)
            return MultimodalDocumentResult(
                file_id=file_id,
                file_path=relative_path,
                artifact_type="pdf",
                is_successful=True,
                page_count=page_count,
                raw_text=full_text,
                entities=entities,
                metadata={"num_pages": page_count, "size_bytes": full_path.stat().st_size},
            )
        except Exception as e:
            return MultimodalDocumentResult(
                file_id=file_id,
                file_path=relative_path,
                artifact_type="pdf",
                is_successful=False,
                limitations=[f"PDF parsing error: {e}"],
            )

    def parse_image(self, file_id: str, relative_path: str) -> MultimodalDocumentResult:
        """Inspect and parse facts from a PNG screenshot artifact."""
        full_path = self.dataset_dir / relative_path
        if not full_path.is_file():
            return MultimodalDocumentResult(
                file_id=file_id,
                file_path=relative_path,
                artifact_type="image",
                is_successful=False,
                limitations=[f"Image file not found: {relative_path}"],
            )

        try:
            from PIL import Image
        except ImportError:
            return MultimodalDocumentResult(
                file_id=file_id,
                file_path=relative_path,
                artifact_type="image",
                is_successful=False,
                limitations=["PIL library not available in runtime environment"],
            )

        try:
            with Image.open(full_path) as img:
                width, height = img.size
                mode = img.mode
                info_chunks = {k: str(v)[:200] for k, v in img.info.items() if isinstance(v, (str, bytes))}

            # Check if an OCR engine (e.g. pytesseract) is installed
            has_ocr = False
            ocr_text = ""
            try:
                import pytesseract
                has_ocr = True
                with Image.open(full_path) as img:
                    ocr_text = pytesseract.image_to_string(img)
            except Exception:
                has_ocr = False

            limitations = []
            if not has_ocr:
                limitations.append("Local OCR engine (pytesseract/tesseract-ocr) not installed on host.")

            entities: List[ExtractedEntity] = []
            if ocr_text:
                for m in re.finditer(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", ocr_text):
                    entities.append(ExtractedEntity(entity_type="email", value=m.group(0).lower()))
                for m in re.finditer(r"\buser_\d+\b", ocr_text):
                    entities.append(ExtractedEntity(entity_type="user_id", value=m.group(0).lower()))
                for m in re.finditer(r"\b((?:account|search|analytics|support|export|data_flow|backup|audit_record|tombstone|marketing)_\d+)\b", ocr_text):
                    entities.append(ExtractedEntity(entity_type="resource_id", value=m.group(0)))

            return MultimodalDocumentResult(
                file_id=file_id,
                file_path=relative_path,
                artifact_type="image",
                is_successful=True,
                page_count=1,
                raw_text=ocr_text,
                entities=entities,
                metadata={
                    "dimensions": f"{width}x{height}",
                    "color_mode": mode,
                    "info_chunks": info_chunks,
                    "ocr_applied": has_ocr,
                },
                limitations=limitations,
            )
        except Exception as e:
            return MultimodalDocumentResult(
                file_id=file_id,
                file_path=relative_path,
                artifact_type="image",
                is_successful=False,
                limitations=[f"Image inspection error: {e}"],
            )
