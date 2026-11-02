from app.services.document_parser.base import ExtractedBlock, ParsedDocument
from app.services.project_splitter.splitter import split_into_projects


def _blocks(lines: list[str]) -> ParsedDocument:
    return ParsedDocument(blocks=[ExtractedBlock(text=l, block_type="paragraph", location=f"paragraph {i+1}") for i, l in enumerate(lines)])


def test_split_with_explicit_assignment_markers():
    doc = _blocks(
        [
            "Company Experience Profile",
            "Assignment-1",
            "Name of Project: GIS Platform",
            "Name of Client: State Government",
            "Assignment-2",
            "Name of Project: ERP Rollout",
            "Name of Client: NABARD",
        ]
    )
    segments = split_into_projects(doc)
    assert len(segments) == 2
    assert segments[0].source_assignment_number == "Assignment-1"
    assert "GIS Platform" in segments[0].text
    assert segments[1].source_assignment_number == "Assignment-2"
    assert "ERP Rollout" in segments[1].text
    # Preamble before the first boundary is discarded
    assert "Company Experience Profile" not in segments[0].text


def test_split_fallback_on_recurring_labels_when_no_assignment_markers():
    doc = _blocks(
        [
            "Name of Applicant: AFC India",
            "Description of the project.",
            "Name of Applicant: AFC India",
            "Another project description.",
        ]
    )
    segments = split_into_projects(doc)
    assert len(segments) == 2


def test_split_single_project_document_with_no_markers():
    doc = _blocks(["Just one project with no recurring headers.", "More detail about it."])
    segments = split_into_projects(doc)
    assert len(segments) == 1


def test_split_empty_document():
    assert split_into_projects(ParsedDocument(blocks=[])) == []
