from docx import Document as DocxDocument

from app.services.document_parser.base import DocumentParser, ExtractedBlock, ParsedDocument


class DocxParser(DocumentParser):
    """Extracts paragraphs, headings, tables and list items from a DOCX file.

    DOCX has no reliable page model, so we track paragraph/section references
    instead of fabricating page numbers (per project requirements)."""

    def can_parse(self, filename: str, mime_type: str) -> bool:
        return filename.lower().endswith(".docx") or "wordprocessingml" in (mime_type or "")

    def parse(self, file_path: str) -> ParsedDocument:
        doc = DocxDocument(file_path)
        blocks: list[ExtractedBlock] = []

        body_elements = list(doc.element.body)
        para_index = 0
        table_index = 0

        # Walk the document body in order so tables interleave correctly with paragraphs.
        paragraphs_by_id = {p._p: p for p in doc.paragraphs}
        tables_by_id = {t._tbl: t for t in doc.tables}

        for element in body_elements:
            if element in paragraphs_by_id:
                p = paragraphs_by_id[element]
                para_index += 1
                text = p.text.strip()
                if not text:
                    continue
                style_name = (p.style.name if p.style else "") or ""
                block_type = "heading" if "heading" in style_name.lower() or "title" in style_name.lower() else "paragraph"
                if p.style and p.style.name and "list" in p.style.name.lower():
                    block_type = "list_item"
                blocks.append(
                    ExtractedBlock(
                        text=text,
                        block_type=block_type,
                        location=f"paragraph {para_index}",
                    )
                )
            elif element in tables_by_id:
                table = tables_by_id[element]
                table_index += 1
                for row_idx, row in enumerate(table.rows, start=1):
                    cells = [c.text.strip() for c in row.cells]
                    row_text = " | ".join(c for c in cells if c)
                    if not row_text:
                        continue
                    blocks.append(
                        ExtractedBlock(
                            text=row_text,
                            block_type="table_row",
                            location=f"table {table_index} / row {row_idx}",
                        )
                    )

        status = "SUCCESS" if blocks else "FAILED"
        warnings = [] if blocks else ["No extractable text found in DOCX document."]
        return ParsedDocument(
            blocks=blocks,
            page_count=None,
            extraction_method="python-docx",
            extraction_status=status,
            warnings=warnings,
        )
