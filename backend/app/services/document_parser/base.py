from dataclasses import dataclass, field


@dataclass
class ExtractedBlock:
    """One structural unit of extracted text (paragraph, heading, table row, list item)."""

    text: str
    block_type: str  # paragraph | heading | table_row | list_item
    location: str  # e.g. "page 8" or "paragraph 42" or "section 3 / table 1 / row 2"
    page: int | None = None


@dataclass
class ParsedDocument:
    blocks: list[ExtractedBlock] = field(default_factory=list)
    page_count: int | None = None
    extraction_method: str = "unknown"
    extraction_status: str = "SUCCESS"  # SUCCESS | PARTIAL | FAILED
    warnings: list[str] = field(default_factory=list)

    @property
    def full_text(self) -> str:
        return "\n".join(b.text for b in self.blocks if b.text.strip())


class DocumentParser:
    def can_parse(self, filename: str, mime_type: str) -> bool:
        raise NotImplementedError

    def parse(self, file_path: str) -> ParsedDocument:
        raise NotImplementedError
