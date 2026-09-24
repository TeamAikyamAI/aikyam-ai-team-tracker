"""Who can see and do what, editable from the Admin panel.

The registry below is the single source of truth for the features an admin can
grant or revoke. Nothing about access is written into a screen or an endpoint:
the sidebar asks this service what to show, and every protected endpoint asks
it again on the server, so hiding a menu is never mistaken for security.

Roles are deliberately a fixed, short list. A team of a handful of people does
not need a role builder - it needs the three tiers it actually has, with the
feature toggles under each one editable without a deploy.

Two guard rails, both enforced here rather than in the UI:
  * a locked (role, feature) pair can never be switched off - this is what
    stops an admin removing their own way back into the Admin panel;
  * the matrix itself lives behind ``admin_panel``, which is locked for admins.
"""
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.models.role_permission import RolePermission

# The three tiers the app ships with. Kept fixed on purpose - see module docstring.
ROLES: tuple[str, ...] = ("admin", "member", "requestor")

ROLE_LABELS: dict[str, str] = {
    "admin": "Admin",
    "member": "Team member",
    "requestor": "Requestor",
}


@dataclass(frozen=True)
class Feature:
    key: str
    label: str
    group: str
    defaults: frozenset[str]
    help: str = ""
    # Roles whose access to this feature can never be turned off.
    locked_for: frozenset[str] = field(default_factory=frozenset)


REGISTRY: tuple[Feature, ...] = (
    # --- Everyday screens ---------------------------------------------------
    Feature(
        "dashboard", "Dashboard", "Screens",
        frozenset({"admin", "member", "requestor"}),
        "The board and table of every project. Deliberately open to requestors "
        "as well, so other verticals can see what the team is already loaded with.",
    ),
    Feature(
        "queue", "Project Queue", "Screens",
        frozenset({"admin", "member", "requestor"}),
        "The read-only list people check before filing a new request.",
    ),
    Feature(
        "apply", "Apply for Service", "Screens",
        frozenset({"admin", "requestor"}),
        "Submitting a new service request with a signed BRD. Off for team "
        "members by default - the AI team receives requests, it does not file "
        "them against itself. Tick it here if that ever changes.",
    ),
    Feature(
        "my_requests", "My Requests", "Screens",
        frozenset({"admin", "requestor"}),
        "Someone's own submitted requests. Off for team members by default, "
        "since they cannot file one - they see every request in Requests Review "
        "instead.",
    ),
    Feature(
        "requests_review", "Requests Review", "Screens",
        frozenset({"admin", "member"}),
        "Approving, rejecting or holding incoming requests, and reading anyone's BRD.",
    ),
    Feature(
        "ask", "Ask the Tracker", "Screens",
        frozenset({"admin", "member"}),
        "The assistant page and the chat widget.",
    ),
    Feature(
        "api_keys", "API Key Register", "Screens",
        frozenset({"admin", "member"}),
        "Which provider's key each project uses, what for and when it lapses. "
        "The AI team's own record - requestors have no reason to see it.",
    ),

    # --- My Day -------------------------------------------------------------
    Feature(
        "my_day", "My Day (own daily list)", "My Day",
        frozenset({"admin", "member"}),
        "A private daily to-do. Everyone with this can only ever see their own list.",
    ),
    Feature(
        "team_day", "See everyone's daily list", "My Day",
        frozenset({"admin"}),
        "Read-only view of every team member's day. Nobody can tick or edit "
        "someone else's task, whatever this is set to.",
    ),

    # --- Actions ------------------------------------------------------------
    Feature(
        "projects_manage", "Create and edit projects", "Actions",
        frozenset({"admin", "member"}),
        "Without this a role can still read the dashboard, just not change anything.",
    ),
    Feature(
        "projects_delete", "Delete a project", "Actions",
        frozenset({"admin"}),
        "Removes a project and its update log for good. Admin only by default - "
        "editing is everyday work, deleting is not.",
    ),
    Feature(
        "projects_export", "Export projects to Excel", "Actions",
        frozenset({"admin", "member"}),
    ),
    Feature(
        "project_remarks", "See internal Remarks", "Actions",
        frozenset({"admin", "member"}),
        "Remarks are where the team writes internal notes about a project. Roles "
        "without this see everything else about the project, just not that field.",
    ),

    # --- Administration -----------------------------------------------------
    Feature(
        "admin_panel", "Admin Panel", "Administration",
        frozenset({"admin"}),
        "Users, verticals, statuses, settings, branding and this permissions grid.",
        locked_for=frozenset({"admin"}),
    ),
    Feature(
        "audit_trail", "Audit Trail", "Administration",
        frozenset({"admin"}),
    ),
)

BY_KEY: dict[str, Feature] = {f.key: f for f in REGISTRY}


def is_allowed(db: Session, role: str, feature: str) -> bool:
    """Whether ``role`` may use ``feature`` right now."""
    defn = BY_KEY.get(feature)
    if defn is None:
        raise ValueError(f"Unknown feature: {feature}")
    if role in defn.locked_for:
        return True
    row = (
        db.query(RolePermission)
        .filter(RolePermission.role == role, RolePermission.feature == feature)
        .first()
    )
    if row is None:
        return role in defn.defaults
    return bool(row.allowed)


def allowed_features(db: Session, role: str) -> list[str]:
    """Every feature key this role may use - what the frontend builds its menu from."""
    return [f.key for f in REGISTRY if is_allowed(db, role, f.key)]


def matrix(db: Session) -> list[dict]:
    """The full grid for the Admin screen: one entry per feature, per role."""
    out: list[dict] = []
    for defn in REGISTRY:
        out.append(
            {
                "key": defn.key,
                "label": defn.label,
                "group": defn.group,
                "help": defn.help,
                "roles": {
                    role: {
                        "allowed": is_allowed(db, role, defn.key),
                        "locked": role in defn.locked_for,
                    }
                    for role in ROLES
                },
            }
        )
    return out


def set_many(db: Session, changes: dict[str, dict[str, bool]], user_id: int | None = None) -> list[str]:
    """Apply ``{feature: {role: allowed}}`` and return the pairs that changed.

    A locked pair is rejected outright rather than silently ignored, so a UI
    bug can never quietly drop an admin's access to the Admin panel.
    """
    changed: list[str] = []
    for feature, per_role in changes.items():
        defn = BY_KEY.get(feature)
        if defn is None:
            raise ValueError(f"Unknown feature: {feature}")
        for role, allowed in per_role.items():
            if role not in ROLES:
                raise ValueError(f"Unknown role: {role}")
            if role in defn.locked_for and not allowed:
                raise ValueError(
                    f"{ROLE_LABELS[role]} access to {defn.label} cannot be switched off"
                )
            if is_allowed(db, role, feature) == bool(allowed):
                continue
            row = (
                db.query(RolePermission)
                .filter(RolePermission.role == role, RolePermission.feature == feature)
                .first()
            )
            if row is None:
                db.add(
                    RolePermission(
                        role=role, feature=feature, allowed=bool(allowed), updated_by_id=user_id
                    )
                )
            else:
                row.allowed = bool(allowed)
                row.updated_by_id = user_id
            changed.append(f"{role}:{feature}")
    db.commit()
    return changed
