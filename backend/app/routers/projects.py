import logging
from datetime import date, datetime
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.deps import require_feature
from app.models.user import User
from app.models.project import Project
from app.models.status import Status
from app.models.update import Update
from app.models.service_request import ServiceRequest
from app.models.vertical import Vertical
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectOut
from app.schemas.queue import QueueItem
from app.services.audit import log_action
from app.services.email import send_email
from app.services import recipients as rcp
from app.services import permissions as perms
from app.services import settings as cfg
from app.services.excel import build_projects_workbook
from jinja2 import Environment, FileSystemLoader

router = APIRouter(prefix="/projects", tags=["projects"])
_env = Environment(loader=FileSystemLoader("app/templates"))
_log = logging.getLogger("aikyam.projects")


def _visible(db: Session, project: Project, user: User) -> ProjectOut:
    """A project as this user is allowed to see it.

    Everything about a project is deliberately open across verticals so people
    can see how loaded the team is. Remarks are the one exception: that field
    is where the team writes internal notes, so it is blanked for roles without
    the 'project_remarks' permission rather than shipped to the browser and
    hidden there.
    """
    out = ProjectOut.model_validate(project)
    if not perms.is_allowed(db, user.role, "project_remarks"):
        out.remarks = None
    return out


def _name_taken(db: Session, name: str, exclude_id: int | None = None) -> bool:
    q = db.query(Project.id).filter(func.lower(Project.name) == name.strip().lower())
    if exclude_id is not None:
        q = q.filter(Project.id != exclude_id)
    return db.query(q.exists()).scalar()


def _check_refs(db: Session, vertical_id: int | None, status_id: int | None) -> None:
    if vertical_id is not None and db.get(Vertical, vertical_id) is None:
        raise HTTPException(status_code=400, detail="That vertical does not exist")
    if status_id is not None and db.get(Status, status_id) is None:
        raise HTTPException(status_code=400, detail="That status does not exist")


@router.get("", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db), user: User = Depends(require_feature("dashboard"))):
    rows = db.query(Project).options(selectinload(Project.owners)).order_by(Project.created_at.desc()).all()
    return [_visible(db, p, user) for p in rows]


@router.get("/queue", response_model=list[QueueItem])
def project_queue(db: Session = Depends(get_db), _: User = Depends(require_feature("queue"))):
    """Public-within-org read-only queue - what every logged-in user
    (including Requestors) can see before filing a new request."""
    rows = (
        db.query(Project, Vertical, Status)
        .join(Vertical, Project.vertical_id == Vertical.id)
        .join(Status, Project.status_id == Status.id)
        .order_by(Project.created_at.desc())
        .all()
    )
    return [
        QueueItem(id=p.id, name=p.name, vertical_name=v.name, status_name=s.name, status_color=s.color)
        for p, v, s in rows
    ]


@router.get("/export.xlsx")
def export_projects(db: Session = Depends(get_db), user: User = Depends(require_feature("projects_export"))):
    """Every project as an Excel workbook, one sheet per active status - the
    same layout as the team's original Weekly_Update.xlsx so it can replace it."""
    workbook = build_projects_workbook(db)
    buffer = BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    stamp = datetime.now().strftime("%Y-%m-%d")
    app_name = (cfg.get(db, "app_name") or "Projects").replace(" ", "_")
    filename = f"{app_name}_Weekly_Update_{stamp}.xlsx"
    log_action(db, user.id, "export_projects", details=filename)
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-store",
        },
    )


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: int, db: Session = Depends(get_db), user: User = Depends(require_feature("dashboard"))):
    project = db.query(Project).options(selectinload(Project.owners)).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return _visible(db, project, user)


@router.post("", response_model=ProjectOut, status_code=201)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db), user: User = Depends(require_feature("projects_manage"))):
    name = payload.name.strip()
    if _name_taken(db, name):
        raise HTTPException(status_code=409, detail=f'A project called "{name}" already exists')
    _check_refs(db, payload.vertical_id, payload.status_id)

    data = payload.model_dump(exclude={"owner_ids", "name"})
    project = Project(**data, name=name, created_by_id=user.id)
    if payload.owner_ids:
        project.owners = db.query(User).filter(User.id.in_(payload.owner_ids)).all()
    else:
        project.owners = [user]
    db.add(project)
    db.commit()
    db.refresh(project)
    log_action(db, user.id, "create_project", "project", project.id)
    return _visible(db, project, user)


def _announce_delivery(db: Session, project: Project, actor: User, notify_team: bool) -> None:
    """Tell the person who asked for this that it is done.

    Only projects that came from a service request have someone to tell - a
    project the team raised itself has no requestor, so nothing is sent.

    To: the requestor, plus the whole AI team when the person completing it
    ticked that box. Cc: the vertical head, management, and whoever the
    requestor chose to keep in the loop when they filed.

    Everything here runs after the status change is committed, so no failure in
    it may escape - a delivered project must not become a 500.
    """
    try:
        if not project.source_request_id:
            return
        req = db.get(ServiceRequest, project.source_request_id)
        if not req:
            return
        requestor = db.get(User, req.requestor_id)
        if not requestor or not requestor.email:
            return

        vertical = db.get(Vertical, project.vertical_id)
        status = db.get(Status, project.status_id)
        team = [
            u.email
            for u in db.query(User)
            .filter(User.role.in_(["admin", "member"]), User.is_active == True)  # noqa: E712
            .order_by(User.name)
            .all()
        ]
        management = [
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

        to_line = rcp.merge([requestor.email], rcp.parse(req.extra_to),
                            team if notify_team else [])
        cc = rcp.merge(
            [vertical.head_email] if vertical and vertical.head_email else [],
            management,
            rcp.parse(req.extra_cc),
            exclude=to_line,
        )

        html = _env.get_template("project_completed.html").render(
            project=project,
            status_name=status.name if status else "-",
            vertical_name=vertical.name if vertical else "-",
            vertical_head=vertical.head_name if vertical else "-",
            owners=", ".join(o.name for o in project.owners),
            from_request=True,
            request_date=req.created_at.date() if req.created_at else "",
            app_name=cfg.get(db, "app_name"),
            signature=cfg.get(db, "email_signature"),
        )
        send_email(
            db,
            to=to_line,
            subject=f"Delivered: {project.name}",
            html_body=html,
            cc=cc,
            reply_to=actor.email,
            from_display_name=actor.name,
        )
        log_action(db, actor.id, "project_delivered_email", "project", project.id,
                   details=", ".join(to_line))
    except Exception:
        _log.exception("could not send the delivery notification for project %s", project.id)


@router.patch("/{project_id}", response_model=ProjectOut)
def update_project(project_id: int, payload: ProjectUpdate, db: Session = Depends(get_db), user: User = Depends(require_feature("projects_manage"))):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    data = payload.model_dump(exclude_unset=True, exclude={"owner_ids", "notify_team"})
    was_terminal = bool(project.status and project.status.is_terminal)
    if "name" in data:
        data["name"] = data["name"].strip()
        if _name_taken(db, data["name"], exclude_id=project.id):
            raise HTTPException(status_code=409, detail=f'A project called "{data["name"]}" already exists')
    _check_refs(db, data.get("vertical_id"), data.get("status_id"))

    # Moving into a terminal status stamps the completion date automatically
    # (and only if the person did not set one themselves).
    if "status_id" in data and "actual_completion_date" not in data and project.actual_completion_date is None:
        new_status = db.get(Status, data["status_id"])
        if new_status and new_status.is_terminal:
            data["actual_completion_date"] = date.today()

    for field, value in data.items():
        setattr(project, field, value)
    if payload.owner_ids is not None:
        project.owners = db.query(User).filter(User.id.in_(payload.owner_ids)).all()
    db.commit()
    db.refresh(project)
    log_action(db, user.id, "update_project", "project", project.id)

    # Reaching a terminal status is what "delivered" means here - the same
    # moment that stamps the completion date. Only on the way IN, so editing a
    # project that is already Live never mails anyone a second time.
    now_terminal = bool(project.status and project.status.is_terminal)
    if now_terminal and not was_terminal:
        _announce_delivery(db, project, user, payload.notify_team)

    return _visible(db, project, user)


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: int, db: Session = Depends(get_db), admin: User = Depends(require_feature("projects_delete"))):
    """Remove a project for good.

    Separated from ``projects_manage`` on purpose: editing a project is
    everyday work for the whole team, deleting one is not, so it has its own
    feature and defaults to admin only.

    The update log goes with it - those rows are meaningless without the
    project, and leaving them would break the weekly digest, which joins every
    update back to its project. The audit trail keeps the name and who did it,
    which is the part that has to survive.

    An approved service request whose project is deleted stays approved and
    keeps its own record; it simply no longer points at a live project.
    """
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    name = project.name
    db.query(Update).filter(Update.project_id == project.id).delete(synchronize_session=False)
    project.owners = []
    db.delete(project)
    db.commit()

    log_action(db, admin.id, "delete_project", "project", project_id, details=name)
    return None
