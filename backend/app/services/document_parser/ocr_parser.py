from app.core.logging import get_logger

logger = get_logger(__name__)


class OcrParser:
    """OCR fallback for image-heavy/garbled PDF pages using pytesseract.
    Requires the Tesseract binary to be installed on the host; if it is
    unavailable, OCR is skipped gracefully (native text extraction still runs)."""

    def __init__(self):
        self._available: bool | None = None

    def _check_available(self) -> bool:
        if self._available is not None:
            return self._available
        try:
            import pytesseract

            pytesseract.get_tesseract_version()
            self._available = True
        except Exception:
            self._available = False
            logger.warning("Tesseract OCR binary not found; OCR fallback disabled.")
        return self._available

    def ocr_page(self, fitz_doc, page_index: int) -> str | None:
        if not self._check_available():
            return None
        try:
            import pytesseract
            from PIL import Image
            import io

            page = fitz_doc.load_page(page_index)
            pix = page.get_pixmap(dpi=200)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            return pytesseract.image_to_string(img)
        except Exception as exc:
            logger.warning("OCR failed for page %s: %s", page_index + 1, exc)
            return None
