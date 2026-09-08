"""One-time setup script for a fresh Aikyam AI Team Tracker database.

Run this once after `alembic upgrade head`, from the backend/ directory:

    python -m scripts.seed

It is safe to re-run: every step checks for existing data first and skips
anything already there, so re-running after adding more verticals/statuses
by hand won't duplicate or overwrite them.

What it creates (all of this is admin-editable afterwards through the app -
nothing here is hardcoded into the running system, this script just gives
you a sensible starting point instead of an empty database):
  - The first admin user (you'll be prompted for name/email/password)
  - Optionally, a second user (e.g. a teammate) reporting to the admin
  - A starting set of Aikyam business verticals
  - A starting set of project statuses
"""
import getpass
import sys

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.user import User
from app.models.vertical import Vertical
from app.models.status import Status
from app.models.branding import BrandingAsset
from app.core.default_logo import DEFAULT_LOGO_SVG, DEFAULT_LOGO_FILENAME, DEFAULT_LOGO_CONTENT_TYPE

DEFAULT_VERTICALS = [
    ("Broking & Clearing", "", ""),
    ("Accounts", "", ""),
    ("Stressed Asset Management", "", ""),
    ("Asset Management", "", ""),
]

# The team's delivery pipeline, matching the sheets of Weekly_Update.xlsx.
# All of it is editable later in Admin > Statuses (names, colours, order,
# which stage counts as "done").
DEFAULT_STATUSES = [
    ("In queue", "#94a3b8", False, 1),
    ("WIP", "#3b82f6", False, 2),
    ("UAT", "#f59e0b", False, 3),
    ("Live", "#22c55e", True, 4),
]


def prompt(label: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{label}{suffix}: ").strip()
    return value or (default or "")


def seed_admin(db) -> User:
    existing_admin = db.query(User).filter(User.role == "admin").first()
    if existing_admin:
        print(f"Admin user already exists ({existing_admin.email}) - skipping.")
        return existing_admin

    print("\n-- Create the first admin user --")
    name = prompt("Full name", "Naman Jain")
    email = prompt("Email", "naman@aikyamcap.com")
    password = getpass.getpass("Password: ")
    while len(password) < 8:
        print("Password should be at least 8 characters.")
        password = getpass.getpass("Password: ")
    external_manager_email = prompt(
        "Your own manager's email, if they are NOT going to be a system user "
        "(leave blank if not applicable - the weekly team rollup goes here "
        "when set)",
        "",
    )

    admin = User(
        name=name,
        email=email,
        password_hash=hash_password(password),
        role="admin",
        external_manager_email=external_manager_email or None,
        is_active=True,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    print(f"Created admin: {admin.name} <{admin.email}>")
    return admin


def seed_second_user(db, admin: User):
    add_another = prompt("\nAdd another team member now? (y/N)", "N").lower()
    if add_another != "y":
        return
    name = prompt("Full name", "Pranjal Shukla")
    email = prompt("Email")
    if not email:
        print("No email given - skipping.")
        return
    if db.query(User).filter(User.email == email).first():
        print("A user with that email already exists - skipping.")
        return
    password = getpass.getpass("Temporary password for them: ")
    role = prompt("Role (admin/member/requestor)", "member")
    member = User(
        name=name,
        email=email,
        password_hash=hash_password(password or "changeme123"),
        role=role,
        reports_to_id=admin.id,
        is_active=True,
    )
    db.add(member)
    db.commit()
    print(f"Created {role}: {member.name} <{member.email}>, reporting to {admin.name}")


def seed_verticals(db):
    print("\n-- Verticals --")
    for name, head_name, head_email in DEFAULT_VERTICALS:
        if db.query(Vertical).filter(Vertical.name == name).first():
            print(f"  {name}: already exists, skipping")
            continue
        db.add(Vertical(name=name, head_name=head_name or "TBD", head_email=head_email or "tbd@aikyamcap.com"))
        print(f"  {name}: created (edit the head name/email in Admin > Verticals)")
    db.commit()


def seed_statuses(db):
    print("\n-- Statuses --")
    for name, color, is_terminal, sort_order in DEFAULT_STATUSES:
        if db.query(Status).filter(Status.name == name).first():
            print(f"  {name}: already exists, skipping")
            continue
        db.add(Status(name=name, color=color, is_terminal=is_terminal, sort_order=sort_order))
        print(f"  {name}: created")
    db.commit()


def seed_logo(db):
    print("\n-- Branding --")
    existing = db.query(BrandingAsset).filter(BrandingAsset.kind == "logo").first()
    if existing:
        print(f"  logo: already set ({existing.filename}), skipping")
        return
    db.add(BrandingAsset(
        kind="logo",
        filename=DEFAULT_LOGO_FILENAME,
        content_type=DEFAULT_LOGO_CONTENT_TYPE,
        size_bytes=len(DEFAULT_LOGO_SVG),
        data=DEFAULT_LOGO_SVG,
    ))
    db.commit()
    print("  logo: seeded the default Aikyam mark (swap it any time in Admin > Branding)")


def main():
    db = SessionLocal()
    try:
        admin = seed_admin(db)
        seed_second_user(db, admin)
        seed_verticals(db)
        seed_statuses(db)
        seed_logo(db)
        print("\nDone. Start the backend with: uvicorn app.main:app --reload --port 8002")
    finally:
        db.close()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelled.")
        sys.exit(1)
