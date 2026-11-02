from sqlalchemy.orm import Session

from app.db.models.project import ImportProject


def get_project(db: Session, project_id: str) -> ImportProject | None:
    return db.query(ImportProject).filter(ImportProject.id == project_id).first()


def list_projects_for_batch(db: Session, batch_id: str) -> list[ImportProject]:
    return db.query(ImportProject).filter(ImportProject.import_batch_id == batch_id).all()


def list_review_queue(db: Session, states: list[str]) -> list[ImportProject]:
    return db.query(ImportProject).filter(ImportProject.workflow_state.in_(states)).order_by(
        ImportProject.created_at.desc()
    ).all()
