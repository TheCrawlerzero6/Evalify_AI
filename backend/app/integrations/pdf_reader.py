from __future__ import annotations

from io import BytesIO
import logging

from pypdf import PdfReader

logger = logging.getLogger(__name__)


def extract_pdf_text(file_bytes: bytes) -> str:
    logger.debug("Extrayendo texto de PDF bytes=%d", len(file_bytes))
    reader = PdfReader(BytesIO(file_bytes))
    pages = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    extracted = "\n".join(pages).strip()
    logger.info("Extraccion PDF completada pages=%d chars=%d", len(reader.pages), len(extracted))
    return extracted
