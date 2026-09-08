from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_feature
from app.models.user import User
from app.services import permissions as perms
from app.services.audit import log_action

router = APIRouter(prefix="/permissions", tags=["permissions"])


class PermissionUpdate(BaseModel):
    # {feature_key: {role: allowed}}
    changes: dict[str, dict[str, bool]]


@router.get("/me")
def my_features(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """What the signed-in user may use - the frontend builds its menu from this."""
    return {"role": user.role, "features": perms.allowed_features(db, user.role)}


@router.get("")
def get_matrix(db: Session = Depends(get_db), _: User = Depends(require_feature("admin_panel"))):
    return {
        "roles": [{"key": r, "label": perms.ROLE_LABELS[r]} for r in perms.ROLES],
        "features": perms.matrix(db),
    }


@router.put("")
def update_matrix(
    payload: PermissionUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_feature("admin_panel")),
):
    try:
        changed = perms.set_many(db, payload.changes, admin.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if changed:
        log_action(db, admin.id, "update_permissions", details=", ".join(sorted(changed)))
    return {"changed": changed, "features": perms.matrix(db)}
