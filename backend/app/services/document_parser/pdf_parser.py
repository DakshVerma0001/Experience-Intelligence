import re

import pymupdf as fitz  # PyMuPDF

from app.services.document_parser.base import DocumentParser, ExtractedBlock, ParsedDocument
from app.services.document_parser.ocr_parser import OcrParser

_GARBAGE_CHAR_RE = re.compile(r"[^\x20-\x7E -￿\n]")


def _quality_score(text: str) -> float:
    """Heuristic 0-1 score for whether extracted page text looks usable."""
    if not text.strip():
        return 0.0
    garbage = len(_GARBAGE_CHAR_RE.findall(text))
    ratio_garbage = garbage / max(len(text), 1)
    length_score = min(len(text.strip()) / 200.0, 1.0)
    return max(0.0, min(1.0, length_score - ratio_garbage))


class PdfParser(DocumentParser):
    """Extracts text page-by-page using PyMuPDF; falls back to OCR only for
    pages that look image-heavy or garbled, never for the whole document
    unnecessarily."""

    def __init__(self, ocr_parser: OcrParser | None = None):
        self.ocr_parser = ocr_parser or OcrParser()

    def can_parse(self, filename: str, mime_type: str) -> bool:
        return filename.lower().endswith(".pdf") or mime_type == "application/pdf"

    def parse(self, file_path: str) -> ParsedDocument:
        blocks: list[ExtractedBlock] = []
        warnings: list[str] = []
        ocr_pages = 0

        with fitz.open(file_path) as doc:
            page_count = doc.page_count
            for page_index in range(page_count):
                page = doc.load_page(page_index)
                text = page.get_text("text") or ""
                quality = _quality_score(text)

                if quality < 0.35:
                    ocr_text = self.ocr_parser.ocr_page(doc, page_index)
                    if ocr_text and len(ocr_text.strip()) > len(text.strip()):
                        text = ocr_text
                        ocr_pages += 1
                        warnings.append(f"Page {page_index + 1}: used OCR fallback (low native text quality).")

                for para in [p.strip() for p in text.split("\n") if p.strip()]:
                    blocks.append(
                        ExtractedBlock(
                            text=para,
                            block_type="paragraph",
                            location=f"page {page_index + 1}",
                            page=page_index + 1,
                        )
                    )

        method = "PyMuPDF" if ocr_pages == 0 else f"PyMuPDF+OCR({ocr_pages} pages)"
        status = "SUCCESS" if blocks else "FAILED"
        if not blocks:
            warnings.append("No extractable text found in PDF document.")
        return ParsedDocument(
            blocks=blocks,
            page_count=page_count,
            extraction_method=method,
            extraction_status=status,
            warnings=warnings,
        )
