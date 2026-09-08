from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_feature
from app.models.user import User
from app.models.vertical import Vertical
from app.schemas.vertical import VerticalCreate, VerticalUpdate, VerticalOut
from app.services.audit import log_action

router = APIRouter(prefix="/verticals", tags=["verticals"])


@router.get("", response_model=list[VerticalOut])
def list_verticals(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.query(Vertical).order_by(Vertical.name).all()


@router.post("", response_model=VerticalOut, status_code=201)
def create_vertical(payload: VerticalCreate, db: Session = Depends(get_db), admin: User = Depends(require_feature("admin_panel"))):
    if db.query(Vertical).filter(Vertical.name == payload.name).first():
        raise HTTPException(status_code=400, detail="A vertical with this name already exists")
    vertical = Vertical(**payload.model_dump())
    db.add(vertical)
    db.commit()
    db.refresh(vertical)
    log_action(db, admin.id, "create_vertical", "vertical", vertical.id)
    return vertical


@router.patch("/{vertical_id}", response_model=VerticalOut)
def update_vertical(vertical_id: int, payload: VerticalUpdate, db: Session = Depends(get_db), admin: User = Depends(require_feature("admin_panel"))):
    vertical = db.get(Vertical, vertical_id)
    if not vertical:
        raise HTTPException(status_code=404, detail="Vertical not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(vertical, field, value)
    db.commit()
    db.refresh(vertical)
    log_action(db, admin.id, "update_vertical", "vertical", vertical.id)
    return vertical
