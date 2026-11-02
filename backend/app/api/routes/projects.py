from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.database import get_db
from app.db.models.project import ImportProject, ProjectExtraction, ProjectKeyword
from app.db.models.user import User
from app.schemas.extraction import FieldProvenance
from app.schemas.keyword import KeywordIn, KeywordOut, KeywordUpdate
from app.schemas.project import ProjectDetail, ProjectUpdate

router = APIRouter(prefix="/api/projects", tags=["projects"])

EDITABLE_FIELDS = {
    "project_name", "short_form", "contract_value_crore", "country", "state_ut", "client_type",
    "project_status", "client_name", "client_address", "contact_person", "designation", "telephone",
    "email", "start_date", "completion_date", "duration_months", "total_staff_months",
    "professional_staff_months", "associated_consultants", "senior_professional_staff",
    "project_description", "actual_services", "ai_search_summary",
}


def _to_detail(project: ImportProject, db: Session) -> ProjectDetail:
    keywords = db.query(ProjectKeyword).filter(ProjectKeyword.project_id == project.id).all()
    provenance = db.query(ProjectExtraction).filter(ProjectExtraction.project_id == project.id).all()

    project_dict = {k: v for k, v in project.__dict__.items() if not k.startswith("_")}
    project_dict["validation_warnings"] = json.loads(project.validation_warnings) if project.validation_warnings else []
    data = ProjectDetail.model_validate(project_dict)
    data.keywords = [
        KeywordOut(
            id=k.id, keyword=k.keyword, category=k.category, description=k.description,
            aliases=json.loads(k.aliases) if k.aliases else [], source_supported=k.source_supported,
        )
        for k in keywords
    ]
    data.field_provenance = [
        FieldProvenance(
            field=p.field_name,
            value=p.value,
            source_text=p.source_text,
            source_location=p.source_location,
            confidence=p.confidence,
            extraction_type=p.extraction_type,
            edited_by_human=p.edited_by_human,
        )
        for p in provenance
    ]
    return data


@router.get("/{project_id}", response_model=ProjectDetail)
def get_project(project_id: str, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    project = db.query(ImportProject).filter(ImportProject.id == project_id).first()
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    return _to_detail(project, db)


@router.get("/{project_id}/source")
def view_source(project_id: str, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    project = db.query(ImportProject).filter(ImportProject.id == project_id).first()
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    return {
        "source_filename": project.source_filename,
        "source_assignment_number": project.source_assignment_number,
        "source_location": project.source_location,
        "source_page": project.source_page,
        "source_text": project.source_text,
    }


@router.patch("/{project_id}", response_model=ProjectDetail)
def update_project(
    project_id: str, payload: ProjectUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    project = db.query(ImportProject).filter(ImportProject.id == project_id).first()
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")

    for edit in payload.edits:
        if edit.field not in EDITABLE_FIELDS:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Field '{edit.field}' is not editable")

        # Preserve the original AI value: only create a new provenance record
        # for the human edit, never overwrite the original extraction row.
        existing = (
            db.query(ProjectExtraction)
            .filter(ProjectExtraction.project_id == project_id, ProjectExtraction.field_name == edit.field)
            .first()
        )
        db.add(
            ProjectExtraction(
                project_id=project_id,
                field_name=edit.field,
                value=edit.value,
                source_text=existing.source_text if existing else None,
                source_location=existing.source_location if existing else None,
                confidence=existing.confidence if existing else None,
                extraction_type=existing.extraction_type if existing else None,
                is_original_ai_value=False,
                edited_by_human=True,
                edited_by_user_id=user.id,
            )
        )
        value = edit.value
        if edit.field in ("contract_value_crore", "total_staff_months", "professional_staff_months"):
            value = float(edit.value) if edit.value not in (None, "") else None
        elif edit.field == "duration_months":
            value = int(edit.value) if edit.value not in (None, "") else None
        setattr(project, edit.field, value)

    project.edited_by_human = True
    db.commit()
    db.refresh(project)
    return _to_detail(project, db)


@router.post("/{project_id}/keywords", response_model=KeywordOut)
def add_keyword(project_id: str, payload: KeywordIn, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    project = db.query(ImportProject).filter(ImportProject.id == project_id).first()
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    kw = ProjectKeyword(
        project_id=project_id, keyword=payload.keyword, category=payload.category,
        description=payload.description, aliases=json.dumps(payload.aliases), source_supported=False,
    )
    db.add(kw)
    db.commit()
    db.refresh(kw)
    return KeywordOut(
        id=kw.id, keyword=kw.keyword, category=kw.category, description=kw.description,
        aliases=payload.aliases, source_supported=kw.source_supported,
    )


@router.patch("/{project_id}/keywords/{keyword_id}", response_model=KeywordOut)
def update_keyword(
    project_id: str, keyword_id: str, payload: KeywordUpdate,
    db: Session = Depends(get_db), _user: User = Depends(get_current_user),
):
    kw = db.query(ProjectKeyword).filter(ProjectKeyword.id == keyword_id, ProjectKeyword.project_id == project_id).first()
    if kw is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Keyword not found")
    if payload.keyword is not None:
        kw.keyword = payload.keyword
    if payload.category is not None:
        kw.category = payload.category
    if payload.description is not None:
        kw.description = payload.description
    if payload.aliases is not None:
        kw.aliases = json.dumps(payload.aliases)
    db.commit()
    db.refresh(kw)
    return KeywordOut(
        id=kw.id, keyword=kw.keyword, category=kw.category, description=kw.description,
        aliases=json.loads(kw.aliases) if kw.aliases else [], source_supported=kw.source_supported,
    )


@router.delete("/{project_id}/keywords/{keyword_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_keyword(project_id: str, keyword_id: str, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    kw = db.query(ProjectKeyword).filter(ProjectKeyword.id == keyword_id, ProjectKeyword.project_id == project_id).first()
    if kw is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Keyword not found")
    db.delete(kw)
    db.commit()
