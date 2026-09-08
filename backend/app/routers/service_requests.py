import logging
import os
import re
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import require_feature
from app.models.user import User
from app.models.vertical import Vertical
from app.models.status import Status
from app.models.project import Project
from app.models.service_request import ServiceRequest
from app.schemas.service_request import ServiceRequestOut, ServiceRequestReview
from app.services.audit import log_action
from app.services.email import send_email
from app.services import settings as cfg
from jinja2 import Environment, FileSystemLoader

router = APIRouter(prefix="/requests", tags=["requests"])
_log = logging.getLogger("aikyam.requests")
_env = Environment(loader=FileSystemLoader("app/templates"))

_SAFE_CHARS = re.compile(r"[^A-Za-z0-9._-]+")

# How each decision reads in the subject line and the body of the email.
DECISION_LABELS = {
    "approved": "Approved",
    "rejected": "Not taken up",
    "on_hold": "On hold",
}


def safe_filename(name: str) -> str:
    """Reduce a client-supplied filename to a basename made of safe characters.

    Strips any directory component (so ``../../etc/passwd`` can never escape
    the upload directory), collapses everything outside [A-Za-z0-9._-] to an
    underscore, and caps the length so the stored path fits its column.
    """
    base = os.path.basename(name.replace("\\", "/"))
    base = _SAFE_CHARS.sub("_", base).strip("._") or "brd"
    return base[:120]


def original_filename(stored_path: str) -> str:
    """The name the requestor uploaded, recovered from ``<uuid>_<name>``."""
    base = os.path.basename(stored_path)
    return base.split("_", 1)[1] if "_" in base else base


def _visible_request(db: Session, request_id: int, user: User) -> ServiceRequest:
    req = db.get(ServiceRequest, request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if user.role == "requestor" and req.requestor_id != user.id:
        # Do not reveal that the request exists.
        raise HTTPException(status_code=404, detail="Request not found")
    return req


@router.get("", response_model=list[ServiceRequestOut])
def list_requests(db: Session = Depends(get_db), user: User = Depends(require_feature("my_requests", "requests_review"))):
    q = db.query(ServiceRequest)
    if user.role == "requestor":
        q = q.filter(ServiceRequest.requestor_id == user.id)
    return q.order_by(ServiceRequest.created_at.desc()).all()


@router.post("", response_model=ServiceRequestOut, status_code=201)
def submit_request(
    vertical_id: int = Form(...),
    title: str = Form(...),
    description: str | None = Form(None),
    brd_file: UploadFile = File(...),  # compulsory - request cannot be built without it
    db: Session = Depends(get_db),
    user: User = Depends(require_feature("apply")),
):
    vertical = db.get(Vertical, vertical_id)
    if not vertical:
        raise HTTPException(status_code=404, detail="Vertical not found")

    if not brd_file.filename:
        raise HTTPException(status_code=400, detail="A signed BRD file is required to submit a request")

    # Cap the upload (admin-configurable) - read one byte past the limit so an
    # oversized file is rejected without pulling all of it into memory.
    max_bytes = int(cfg.get(db, "max_brd_upload_mb")) * 1024 * 1024
    payload = brd_file.file.read(max_bytes + 1)
    if len(payload) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"The BRD must be {cfg.get(db, 'max_brd_upload_mb')} MB or smaller",
        )
    if not payload:
        raise HTTPException(status_code=400, detail="The uploaded BRD is empty")

    os.makedirs(settings.upload_dir, exist_ok=True)
    safe_name = f"{uuid.uuid4().hex}_{safe_filename(brd_file.filename)}"
    dest_path = os.path.join(settings.upload_dir, safe_name)
    with open(dest_path, "wb") as f:
        f.write(payload)

    req = ServiceRequest(
        vertical_id=vertical_id,
        requestor_id=user.id,
        title=title,
        description=description,
        brd_file_path=dest_path,
        status="submitted",
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    log_action(db, user.id, "submit_request", "service_request", req.id)

    # Notify the AI team, CC the vertical head and (if configured) management.
    # The row is already committed, so nothing in here may escape - a failure
    # here once turned a saved request into a 500, and the requestor filed it
    # a second time believing the first was lost.
    try:
        # Everyone on the team gets it, not only the admins: a request that only
        # reaches the shared mailbox is a request the engineer who will actually
        # build it never saw. Ordered by name so the To line reads the same every
        # time, and de-duplicated in case the requestor is on the team themselves.
        ai_team_emails = list(dict.fromkeys(
            u.email
            for u in db.query(User)
            .filter(User.role.in_(["admin", "member"]), User.is_active == True)  # noqa: E712
            .order_by(User.name)
            .all()
        ))
        # The requirement is that the vertical head AND management above the AI
        # team both see every incoming request. Management is whoever sits at the
        # top of the team's reporting chain but has no login - the same address
        # the weekly rollup goes to - so it stays admin-editable, not hardcoded.
        management_emails = [
            u.external_manager_email
            for u in db.query(User)
            .filter(
                User.role.in_(["admin", "member"]),
                User.is_active == True,  # noqa: E712
                User.reports_to_id.is_(None),
                User.external_manager_email.isnot(None),
            )
            .all()
            if u.external_manager_email
        ]
        cc = [vertical.head_email] + [e for e in dict.fromkeys(management_emails) if e != vertical.head_email]
        html = _env.get_template("request_submitted.html").render(
            request=req, vertical_name=vertical.name, vertical_head=vertical.head_name,
            requestor_name=user.name, app_name=cfg.get(db, "app_name"),
            signature=cfg.get(db, "email_signature"),
        )
        if ai_team_emails:
            send_email(db, to=ai_team_emails, subject=f"New project request: {title}",
                       html_body=html, cc=cc, reply_to=user.email, from_display_name=user.name)
    except Exception:
        _log.exception("could not send the submission notification for request %s", req.id)

    return req


@router.get("/{request_id}", response_model=ServiceRequestOut)
def get_request(request_id: int, db: Session = Depends(get_db), user: User = Depends(require_feature("my_requests", "requests_review"))):
    return _visible_request(db, request_id, user)


@router.get("/{request_id}/brd")
def download_brd(request_id: int, db: Session = Depends(get_db), user: User = Depends(require_feature("my_requests", "requests_review"))):
    """Serve the signed BRD to people allowed to see the request.

    Replaces the old unauthenticated static mount: admins and members can open
    any BRD, a requestor only their own. The file is sent as an attachment with
    ``nosniff`` so a crafted upload can never execute in the browser.
    """
    req = _visible_request(db, request_id, user)
    path = os.path.abspath(req.brd_file_path)
    root = os.path.abspath(settings.upload_dir)
    if not path.startswith(root + os.sep) or not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="The BRD file is no longer on the server")
    log_action(db, user.id, "download_brd", "service_request", req.id)
    return FileResponse(
        path,
        media_type="application/octet-stream",
        filename=original_filename(path),
        headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "private, no-store"},
    )


@router.post("/{request_id}/review", response_model=ServiceRequestOut)
def review_request(request_id: int, payload: ServiceRequestReview, db: Session = Depends(get_db), admin: User = Depends(require_feature("requests_review"))):
    req = db.get(ServiceRequest, request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if payload.decision not in ("approved", "rejected", "on_hold"):
        raise HTTPException(status_code=400, detail="decision must be approved, rejected, or on_hold")

    req.status = payload.decision
    req.reviewed_by_id = admin.id
    req.reviewed_at = datetime.utcnow()
    req.review_notes = payload.review_notes

    project_name = None
    if payload.decision == "approved":
        default_status = db.query(Status).filter(Status.is_active == True).order_by(Status.sort_order).first()  # noqa: E712
        project = Project(
            name=req.title,
            description=req.description,
            vertical_id=req.vertical_id,
            status_id=payload.status_id or (default_status.id if default_status else None),
            created_by_id=admin.id,
            source_request_id=req.id,
        )
        project.owners = [admin]
        db.add(project)
        db.flush()
        project_name = project.name

    db.commit()
    db.refresh(req)
    log_action(db, admin.id, f"review_request_{payload.decision}", "service_request", req.id)

    # Tell the person who raised it what happened, and copy their vertical head
    # who signed the BRD. Without this the decision only exists inside the app
    # and the requestor has to come looking for it.
    #
    # The decision is already committed by this point, so nothing in here may
    # escape: send_email swallows SMTP errors itself, but a missing template or
    # a bad address would still surface as a 500 on a review that in fact
    # succeeded, and the reviewer would press Approve a second time.
    try:
        requestor = db.get(User, req.requestor_id)
        vertical = db.get(Vertical, req.vertical_id)
        if requestor and requestor.email:
            label = DECISION_LABELS.get(payload.decision, payload.decision)
            html = _env.get_template("request_reviewed.html").render(
                request=req,
                decision_label=label,
                vertical_name=vertical.name if vertical else "-",
                vertical_head=vertical.head_name if vertical else "-",
                reviewer_name=admin.name,
                project_name=project_name,
                app_name=cfg.get(db, "app_name"),
                signature=cfg.get(db, "email_signature"),
            )
            cc = (
                [vertical.head_email]
                if vertical and vertical.head_email and vertical.head_email != requestor.email
                else []
            )
            send_email(
                db,
                to=[requestor.email],
                subject=f"{label}: {req.title}",
                html_body=html,
                cc=cc,
                reply_to=admin.email,
                from_display_name=admin.name,
            )
    except Exception:
        _log.exception("could not send the review notification for request %s", req.id)

    return req
