"""
Splits a parsed document's text into individual project/assignment segments.

Historical documents are not standardized (see project spec), so this splitter
does NOT depend on one exact template. It looks for structural boundary
markers such as "Assignment-1", "Assignment / Job name", "Name of Project",
etc. If no such markers exist anywhere in the document, it falls back to
inferring boundaries from recurring field-label patterns.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.services.document_parser.base import ExtractedBlock, ParsedDocument

# Primary boundary markers: explicit "Assignment" headings. These take
# priority - if any exist in the document, they are the ONLY boundaries used,
# so a "Name of Project: X" content line elsewhere is never mistaken for a
# new project boundary.
_PRIMARY_BOUNDARY_PATTERNS = [
    re.compile(r"^assignment\s*[-#:]?\s*(\d+)\b", re.IGNORECASE),
    re.compile(r"^assignment\s*/\s*job\s*name\s*[:\-]?\s*$", re.IGNORECASE),
    re.compile(r"^assignment\b\s*[:\-]?\s*$", re.IGNORECASE),
]

# Secondary boundary markers: only used when no primary "Assignment" markers
# exist anywhere in the document. Must be a bare label line (no value after
# the colon) to avoid matching a content line like "Name of Project: GIS".
_SECONDARY_BOUNDARY_PATTERNS = [
    re.compile(r"^name\s+of\s+(the\s+)?project\s*[:\-]?\s*$", re.IGNORECASE),
    re.compile(r"^project\s*[-#:]?\s*(\d+)\b", re.IGNORECASE),
    re.compile(r"^job\s*name\s*[:\-]?\s*$", re.IGNORECASE),
]

# Recurring field labels used as a fallback inference signal when no explicit
# assignment markers exist anywhere in the document.
_FALLBACK_LABELS = [
    re.compile(r"^name\s+of\s+(the\s+)?(applicant|client|employer|project)\b", re.IGNORECASE),
    re.compile(r"^firm'?s\s+name\b", re.IGNORECASE),
]

_ASSIGNMENT_NUMBER_RE = re.compile(r"assignment\s*[-#:]?\s*(\d+)", re.IGNORECASE)


@dataclass
class ProjectSegment:
    source_assignment_number: str | None
    blocks: list[ExtractedBlock] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n".join(b.text for b in self.blocks)

    @property
    def location_range(self) -> str:
        locs = [b.location for b in self.blocks if b.location]
        if not locs:
            return "unknown"
        return f"{locs[0]} - {locs[-1]}" if len(locs) > 1 else locs[0]

    @property
    def first_page(self) -> int | None:
        for b in self.blocks:
            if b.page is not None:
                return b.page
        return None


def _extract_assignment_number(text: str) -> str | None:
    m = _ASSIGNMENT_NUMBER_RE.search(text)
    return f"Assignment-{m.group(1)}" if m else None


def _is_primary_boundary(text: str) -> bool:
    stripped = text.strip()
    if len(stripped) > 120:
        return False  # boundary markers are short headings/labels, not prose
    return any(p.search(stripped) for p in _PRIMARY_BOUNDARY_PATTERNS)


def _is_secondary_boundary(text: str) -> bool:
    stripped = text.strip()
    if len(stripped) > 120:
        return False
    return any(p.search(stripped) for p in _SECONDARY_BOUNDARY_PATTERNS)


def _is_fallback_boundary(text: str) -> bool:
    stripped = text.strip()
    if len(stripped) > 120:
        return False
    return any(p.search(stripped) for p in _FALLBACK_LABELS)


def split_into_projects(document: ParsedDocument) -> list[ProjectSegment]:
    blocks = document.blocks
    if not blocks:
        return []

    boundary_indices = [i for i, b in enumerate(blocks) if _is_primary_boundary(b.text)]

    if not boundary_indices:
        secondary_indices = [i for i, b in enumerate(blocks) if _is_secondary_boundary(b.text)]
        if len(secondary_indices) >= 2:
            boundary_indices = secondary_indices

    if not boundary_indices:
        # Fallback: infer boundaries from recurring field-label patterns.
        fallback_indices = [i for i, b in enumerate(blocks) if _is_fallback_boundary(b.text)]
        # Only treat as boundaries if the pattern repeats (i.e. genuinely recurring).
        if len(fallback_indices) >= 2:
            boundary_indices = fallback_indices

    if not boundary_indices:
        # Single project document: treat the whole thing as one segment.
        return [ProjectSegment(source_assignment_number=None, blocks=list(blocks))]

    segments: list[ProjectSegment] = []
    for seg_start, seg_end in zip(boundary_indices, boundary_indices[1:] + [len(blocks)]):
        seg_blocks = blocks[seg_start:seg_end]
        if not seg_blocks:
            continue
        header_text = seg_blocks[0].text
        assignment_number = _extract_assignment_number(header_text)
        segments.append(ProjectSegment(source_assignment_number=assignment_number, blocks=seg_blocks))

    # Any leading content before the first boundary is discarded as document
    # preamble/cover-page content, not a project.
    return segments
