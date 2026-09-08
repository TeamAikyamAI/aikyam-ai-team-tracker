from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_feature
from app.models.user import User
from app.models.update import Update
from app.models.project import Project
from app.schemas.update import UpdateCreate, UpdateOut, QuickFillRequest, QuickFillResponse
from app.services.audit import log_action
from app.services.ai import quick_fill_update

router = APIRouter(prefix="/updates", tags=["updates"])


@router.get("/project/{project_id}", response_model=list[UpdateOut])
def list_updates(project_id: int, db: Session = Depends(get_db), _: User = Depends(require_feature("dashboard"))):
    return (
        db.query(Update)
        .filter(Update.project_id == project_id)
        .order_by(Update.created_at.desc())
        .all()
    )


@router.post("", response_model=UpdateOut, status_code=201)
def create_update(payload: UpdateCreate, db: Session = Depends(get_db), user: User = Depends(require_feature("projects_manage"))):
    project = db.get(Project, payload.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    entry = Update(
        project_id=payload.project_id,
        author_id=user.id,
        plan=payload.plan,
        progress=payload.progress,
        problem=payload.problem,
        raw_bullets=payload.raw_bullets,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    log_action(db, user.id, "create_update", "update", entry.id, details=f"project_id={project.id}")
    return entry


@router.post("/quick-fill", response_model=QuickFillResponse)
def quick_fill(payload: QuickFillRequest, db: Session = Depends(get_db), _: User = Depends(require_feature("projects_manage"))):
    """AI Quick-Fill: turn a few raw bullets into a polished Plan/Progress/Problem entry."""
    return quick_fill_update(db, payload.bullets)
