"""Excel export: one sheet per active status, in the same column layout as the
team's original Weekly_Update.xlsx, plus the tracker-only columns (vertical,
owners, target date) after them so nothing the tracker knows is lost."""
from datetime import date, datetime

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from sqlalchemy.orm import Session, selectinload

from app.models.project import Project
from app.models.status import Status
from app.models.vertical import Vertical

# The seven columns of the original workbook, in the original order.
ORIGINAL_COLUMNS = [
    "Project Name", "Project Description", "Assigned by", "Date of assignment",
    "Status", "Date of completion", "Remarks",
]
EXTRA_COLUMNS = ["Vertical", "Owners", "Target date", "Last updated"]
COLUMNS = ORIGINAL_COLUMNS + EXTRA_COLUMNS
WIDTHS = [38, 44, 22, 18, 14, 18, 40, 22, 28, 14, 18]

_INVALID_SHEET_CHARS = set('[]:*?/\\')


def _sheet_title(name: str, used: set[str]) -> str:
    title = "".join(ch for ch in name if ch not in _INVALID_SHEET_CHARS).strip() or "Status"
    title = title[:31]
    base, n = title, 2
    while title.lower() in used:
        suffix = f" ({n})"
        title = base[: 31 - len(suffix)] + suffix
        n += 1
    used.add(title.lower())
    return title


def _hex_to_fill(color: str | None) -> PatternFill:
    hex_color = (color or "#6b7280").lstrip("#")
    if len(hex_color) != 6:
        hex_color = "6b7280"
    return PatternFill("solid", fgColor=f"FF{hex_color.upper()}")


def _text_on(color: str | None) -> str:
    hex_color = (color or "#6b7280").lstrip("#")
    try:
        r, g, b = (int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return "FFFFFFFF"
    luminance = 0.299 * r + 0.587 * g + 0.114 * b
    return "FF111827" if luminance > 160 else "FFFFFFFF"


def build_projects_workbook(db: Session) -> Workbook:
    statuses = db.query(Status).filter(Status.is_active == True).order_by(Status.sort_order, Status.id).all()  # noqa: E712
    projects = (
        db.query(Project)
        .options(selectinload(Project.owners), selectinload(Project.vertical), selectinload(Project.status))
        .order_by(Project.created_at)
        .all()
    )
    by_status: dict[int, list[Project]] = {s.id: [] for s in statuses}
    orphans: list[Project] = []  # projects whose status is inactive/deleted
    for p in projects:
        if p.status_id in by_status:
            by_status[p.status_id].append(p)
        else:
            orphans.append(p)

    wb = Workbook()
    wb.remove(wb.active)
    used_titles: set[str] = set()
    thin = Side(style="thin", color="FFD1D5DB")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    def write_sheet(title: str, color: str | None, rows: list[Project]):
        ws = wb.create_sheet(_sheet_title(title, used_titles))
        ws.append(COLUMNS)
        head_fill = _hex_to_fill(color)
        head_font = Font(bold=True, color=_text_on(color))
        for col, width in enumerate(WIDTHS, start=1):
            ws.column_dimensions[get_column_letter(col)].width = width
            cell = ws.cell(row=1, column=col)
            cell.fill = head_fill
            cell.font = head_font
            cell.alignment = Alignment(vertical="center", wrap_text=True)
            cell.border = border
        ws.row_dimensions[1].height = 24
        ws.freeze_panes = "A2"
        for p in rows:
            ws.append([
                p.name,
                p.description,
                p.assigned_by,
                p.assigned_on,
                p.status.name if p.status else None,
                p.actual_completion_date,
                p.remarks,
                p.vertical.name if p.vertical else None,
                ", ".join(o.name for o in p.owners),
                p.target_date,
                p.updated_at.replace(tzinfo=None) if isinstance(p.updated_at, datetime) else p.updated_at,
            ])
            r = ws.max_row
            for col in range(1, len(COLUMNS) + 1):
                cell = ws.cell(row=r, column=col)
                cell.border = border
                cell.alignment = Alignment(vertical="top", wrap_text=col in (2, 7))
                if isinstance(cell.value, (date, datetime)):
                    cell.number_format = "DD-MMM-YYYY" if col != len(COLUMNS) else "DD-MMM-YYYY HH:MM"
        ws.auto_filter.ref = f"A1:{get_column_letter(len(COLUMNS))}{max(ws.max_row, 1)}"

    for s in statuses:
        write_sheet(s.name, s.color, by_status[s.id])
    if orphans:
        write_sheet("Other", None, orphans)
    return wb
