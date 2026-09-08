from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_feature
from app.models.user import User
from app.models.audit_log import AuditLog
from app.schemas.audit import AuditLogOut

router = APIRouter(prefix="/audit-logs", tags=["audit"])


@router.get("", response_model=list[AuditLogOut])
def list_audit_logs(
    user_id: int | None = Query(None),
    action: str | None = Query(None),
    entity_type: str | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    limit: int = Query(200, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(require_feature("audit_trail")),
):
    """Admin-only audit trail: every mutating action across every user, with
    full date/time detail - satisfies the 'admin has full visibility across
    all users' activity' requirement."""
    q = db.query(AuditLog)
    if user_id is not None:
        q = q.filter(AuditLog.user_id == user_id)
    if action:
        q = q.filter(AuditLog.action == action)
    if entity_type:
        q = q.filter(AuditLog.entity_type == entity_type)
    if date_from:
        q = q.filter(AuditLog.created_at >= date_from)
    if date_to:
        q = q.filter(AuditLog.created_at <= date_to)
    rows = q.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit).all()
    out = []
    for r in rows:
        out.append(AuditLogOut(
            id=r.id, user_id=r.user_id, user_name=r.user.name if r.user else None,
            action=r.action, entity_type=r.entity_type, entity_id=r.entity_id,
            details=r.details, created_at=r.created_at,
        ))
    return out
