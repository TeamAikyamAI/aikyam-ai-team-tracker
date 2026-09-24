"""The API key register.

A record of which provider's key each project uses, what for, whose account it
sits on and when it lapses. Deliberately NOT a vault: there is no field for the
secret and no endpoint that could return one. The value of this screen is
knowing what exists and what is about to expire.

Behind the ``api_keys`` feature, which defaults to admin and team member. A
requestor has no reason to see the team's infrastructure.
"""
from datetime import date
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.deps import require_feature
from app.models.user import User
from app.models.project import Project
from app.models.api_key import ApiKeyEntry, ApiProvider
from app.schemas.api_key import (
    ApiKeyCreate, ApiKeyOut, ApiKeyUpdate,
    ApiProviderCreate, ApiProviderOut, ApiProviderUpdate,
)
from app.services.audit import log_action
from app.services import settings as cfg
from app.services.api_keys import EXPIRY_WINDOW_DAYS, describe_expiry
from app.services.api_key_excel import build_api_key_workbook

router = APIRouter(prefix="/api-keys", tags=["api-keys"])
providers_router = APIRouter(prefix="/api-providers", tags=["api-keys"])


def _out(entry: ApiKeyEntry, today: date) -> ApiKeyOut:
    row = ApiKeyOut.model_validate(entry)
    row.project_name = (
        entry.project.name if entry.project else (entry.project_label or "-")
    )
    # No provider means the key has not been taken out yet - the same word the
    # team's own sheet already uses in that column.
    row.provider_name = entry.provider.name if entry.provider else "Pending"
    row.days_left, row.expiry_state = describe_expiry(entry.expires_on, entry.status, today)
    return row


def _today(db: Session) -> date:
    from app.services import daily
    return daily.today_for(db)


# ---------------------------------------------------------------------------
# the register
# ---------------------------------------------------------------------------

@router.get("", response_model=list[ApiKeyOut])
def list_api_keys(db: Session = Depends(get_db), _: User = Depends(require_feature("api_keys"))):
    today = _today(db)
    rows = (
        db.query(ApiKeyEntry)
        .options(selectinload(ApiKeyEntry.project), selectinload(ApiKeyEntry.provider))
        .order_by(ApiKeyEntry.id.desc())
        .all()
    )
    return [_out(r, today) for r in rows]


@router.get("/expiring", response_model=list[ApiKeyOut])
def expiring_api_keys(db: Session = Depends(get_db), _: User = Depends(require_feature("api_keys"))):
    """Keys already lapsed or lapsing inside the warning window - what the
    dashboard card counts and the Monday digest lists."""
    today = _today(db)
    rows = (
        db.query(ApiKeyEntry)
        .options(selectinload(ApiKeyEntry.project), selectinload(ApiKeyEntry.provider))
        .filter(ApiKeyEntry.expires_on.isnot(None), ApiKeyEntry.status != "revoked")
        .order_by(ApiKeyEntry.expires_on)
        .all()
    )
    out = [_out(r, today) for r in rows]
    return [r for r in out if r.expiry_state in ("soon", "expired")]


def _check_refs(db: Session, project_id: int | None, provider_id: int | None) -> None:
    if project_id and not db.get(Project, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    if provider_id and not db.get(ApiProvider, provider_id):
        raise HTTPException(status_code=404, detail="Provider not found")


@router.post("", response_model=ApiKeyOut, status_code=201)
def create_api_key(payload: ApiKeyCreate, db: Session = Depends(get_db), user: User = Depends(require_feature("api_keys"))):
    _check_refs(db, payload.project_id, payload.provider_id)
    data = payload.model_dump()
    # A linked project is the name; a typed label alongside it would only drift.
    if data.get("project_id"):
        data["project_label"] = None
    entry = ApiKeyEntry(**data, created_by_id=user.id)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    log_action(db, user.id, "create_api_key", "api_key", entry.id,
               details=f"{entry.provider.name if entry.provider else '-'} / "
                       f"{entry.project.name if entry.project else entry.project_label}")
    return _out(entry, _today(db))


@router.patch("/{entry_id}", response_model=ApiKeyOut)
def update_api_key(entry_id: int, payload: ApiKeyUpdate, db: Session = Depends(get_db), user: User = Depends(require_feature("api_keys"))):
    entry = db.get(ApiKeyEntry, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    data = payload.model_dump(exclude_unset=True)
    _check_refs(db, data.get("project_id"), data.get("provider_id"))
    for field, value in data.items():
        setattr(entry, field, value)
    if entry.project_id:
        entry.project_label = None
    if not entry.project_id and not (entry.project_label or "").strip():
        raise HTTPException(status_code=400, detail="Pick a project, or type a name for the work this key belongs to")
    # An edit must not leave a live key with nobody behind it.
    if entry.provider_id is None and entry.status != "pending":
        raise HTTPException(
            status_code=400,
            detail="Pick a provider, or set the status to pending if it is not decided yet",
        )
    db.commit()
    db.refresh(entry)
    log_action(db, user.id, "update_api_key", "api_key", entry.id)
    return _out(entry, _today(db))


@router.delete("/{entry_id}", status_code=204)
def delete_api_key(entry_id: int, db: Session = Depends(get_db), user: User = Depends(require_feature("api_keys"))):
    entry = db.get(ApiKeyEntry, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    label = f"{entry.provider.name if entry.provider else '-'} / " \
            f"{entry.project.name if entry.project else entry.project_label}"
    db.delete(entry)
    db.commit()
    log_action(db, user.id, "delete_api_key", "api_key", entry_id, details=label)
    return None


@router.get("/export.xlsx")
def export_api_keys(db: Session = Depends(get_db), user: User = Depends(require_feature("api_keys"))):
    """The same register as a workbook, in the column order the team's own
    Api_Key.xlsx already uses."""
    today = _today(db)
    rows = (
        db.query(ApiKeyEntry)
        .options(selectinload(ApiKeyEntry.project), selectinload(ApiKeyEntry.provider))
        .order_by(ApiKeyEntry.id)
        .all()
    )
    wb = build_api_key_workbook([_out(r, today) for r in rows], cfg.get(db, "app_name"), today)
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    log_action(db, user.id, "export_api_keys", "api_key", None)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="API_Keys_{today.isoformat()}.xlsx"'},
    )


# ---------------------------------------------------------------------------
# the provider master list
# ---------------------------------------------------------------------------

@providers_router.get("", response_model=list[ApiProviderOut])
def list_providers(db: Session = Depends(get_db), _: User = Depends(require_feature("api_keys"))):
    return db.query(ApiProvider).order_by(ApiProvider.sort_order, ApiProvider.name).all()


@providers_router.post("", response_model=ApiProviderOut, status_code=201)
def create_provider(payload: ApiProviderCreate, db: Session = Depends(get_db), admin: User = Depends(require_feature("admin_panel"))):
    name = payload.name.strip()
    if db.query(ApiProvider).filter(ApiProvider.name.ilike(name)).first():
        raise HTTPException(status_code=400, detail=f'A provider called "{name}" already exists')
    row = ApiProvider(**{**payload.model_dump(), "name": name})
    db.add(row)
    db.commit()
    db.refresh(row)
    log_action(db, admin.id, "create_api_provider", "api_provider", row.id, details=row.name)
    return row


@providers_router.patch("/{provider_id}", response_model=ApiProviderOut)
def update_provider(provider_id: int, payload: ApiProviderUpdate, db: Session = Depends(get_db), admin: User = Depends(require_feature("admin_panel"))):
    row = db.get(ApiProvider, provider_id)
    if not row:
        raise HTTPException(status_code=404, detail="Provider not found")
    data = payload.model_dump(exclude_unset=True)
    if "name" in data and data["name"]:
        data["name"] = data["name"].strip()
        clash = db.query(ApiProvider).filter(
            ApiProvider.name.ilike(data["name"]), ApiProvider.id != provider_id
        ).first()
        if clash:
            raise HTTPException(status_code=400, detail=f'A provider called "{data["name"]}" already exists')
    for field, value in data.items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    log_action(db, admin.id, "update_api_provider", "api_provider", row.id, details=row.name)
    return row


@providers_router.delete("/{provider_id}", status_code=204)
def delete_provider(provider_id: int, db: Session = Depends(get_db), admin: User = Depends(require_feature("admin_panel"))):
    """Refused while any key still points at it - deactivate instead, which
    keeps the history readable."""
    row = db.get(ApiProvider, provider_id)
    if not row:
        raise HTTPException(status_code=404, detail="Provider not found")
    in_use = db.query(ApiKeyEntry).filter(ApiKeyEntry.provider_id == provider_id).count()
    if in_use:
        raise HTTPException(
            status_code=400,
            detail=f"{row.name} is used by {in_use} key(s). Deactivate it instead of deleting it.",
        )
    name = row.name
    db.delete(row)
    db.commit()
    log_action(db, admin.id, "delete_api_provider", "api_provider", provider_id, details=name)
    return None
