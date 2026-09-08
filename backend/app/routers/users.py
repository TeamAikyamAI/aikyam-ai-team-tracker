from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_admin_or_member, require_feature
from app.core.security import hash_password
from app.models.user import User
from app.schemas.user import UserBrief, UserCreate, UserUpdate, UserOut
from app.services.audit import log_action
from app.services import settings as cfg

ROLES = ("admin", "member", "requestor")


def _check_password(db: Session, password: str):
    n = int(cfg.get(db, "min_password_length"))
    if len(password) < n:
        raise HTTPException(status_code=400, detail=f"Password must be at least {n} characters")
    if len(password.encode("utf-8")) > 72:
        raise HTTPException(status_code=400, detail="Password must be 72 bytes or fewer")

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), _: User = Depends(require_admin_or_member)):
    """The directory is for the AI team. A requestor has no reason to see
    every user's email, role and reporting chain - including management's
    address - so this is no longer open to any signed-in user."""
    return db.query(User).order_by(User.name).all()


@router.get("/directory", response_model=list[UserBrief])
def user_directory(db: Session = Depends(get_db), _: User = Depends(require_feature("dashboard"))):
    """Names only, for anyone who can open the dashboard.

    The board shows who owns each project, and requestors are meant to see
    that - but a name is all that takes. Emails, roles and the reporting
    chain stay in the full directory above, which is still team-only.
    """
    rows = db.query(User.id, User.name).filter(User.is_active == True).order_by(User.name).all()  # noqa: E712
    return [UserBrief(id=r.id, name=r.name) for r in rows]


@router.post("", response_model=UserOut, status_code=201)
def create_user(payload: UserCreate, db: Session = Depends(get_db), admin: User = Depends(require_feature("admin_panel"))):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="A user with this email already exists")
    if payload.role not in ROLES:
        raise HTTPException(status_code=400, detail="role must be admin, member, or requestor")
    _check_password(db, payload.password)
    user = User(
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role,
        reports_to_id=payload.reports_to_id,
        vertical_id=payload.vertical_id,
        external_manager_email=payload.external_manager_email,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    log_action(db, admin.id, "create_user", "user", user.id)
    return user


@router.patch("/{user_id}", response_model=UserOut)
def update_user(user_id: int, payload: UserUpdate, db: Session = Depends(get_db), admin: User = Depends(require_feature("admin_panel"))):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    data = payload.model_dump(exclude_unset=True)

    if "role" in data and data["role"] not in ROLES:
        raise HTTPException(status_code=400, detail="role must be admin, member, or requestor")
    if "email" in data and data["email"] != user.email:
        if db.query(User).filter(User.email == data["email"], User.id != user.id).first():
            raise HTTPException(status_code=400, detail="A user with this email already exists")

    # Never let the last active admin remove their own access - the only way
    # back from that is editing the database by hand.
    losing_admin = (data.get("role") not in (None, "admin")) or (data.get("is_active") is False)
    if user.role == "admin" and losing_admin:
        others = db.query(User).filter(
            User.role == "admin", User.is_active == True, User.id != user.id  # noqa: E712
        ).count()
        if others == 0:
            raise HTTPException(status_code=400, detail="This is the only active admin. Make someone else an admin first.")

    password = data.pop("password", None)
    if password:
        _check_password(db, password)
        user.password_hash = hash_password(password)

    for field, value in data.items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    log_action(db, admin.id, "update_user", "user", user.id)
    return user
