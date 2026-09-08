from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_feature
from app.models.user import User
from app.models.status import Status
from app.schemas.status import StatusCreate, StatusUpdate, StatusOut
from app.services.audit import log_action

router = APIRouter(prefix="/statuses", tags=["statuses"])


@router.get("", response_model=list[StatusOut])
def list_statuses(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.query(Status).order_by(Status.sort_order).all()


@router.post("", response_model=StatusOut, status_code=201)
def create_status(payload: StatusCreate, db: Session = Depends(get_db), admin: User = Depends(require_feature("admin_panel"))):
    if db.query(Status).filter(Status.name == payload.name).first():
        raise HTTPException(status_code=400, detail="A status with this name already exists")
    st = Status(**payload.model_dump())
    db.add(st)
    db.commit()
    db.refresh(st)
    log_action(db, admin.id, "create_status", "status", st.id)
    return st


@router.patch("/{status_id}", response_model=StatusOut)
def update_status_row(status_id: int, payload: StatusUpdate, db: Session = Depends(get_db), admin: User = Depends(require_feature("admin_panel"))):
    st = db.get(Status, status_id)
    if not st:
        raise HTTPException(status_code=404, detail="Status not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(st, field, value)
    db.commit()
    db.refresh(st)
    log_action(db, admin.id, "update_status", "status", st.id)
    return st
