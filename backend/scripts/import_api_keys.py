"""Load an existing Api_Key.xlsx into the register.

The team kept this list in a spreadsheet long before the tracker existed, and
an empty register is worth nothing - the whole point is to see what already
exists and what is about to lapse. This reads that sheet in its own column
order and writes the rows in.

    python -m scripts.import_api_keys path/to/Api_Key.xlsx
    python -m scripts.import_api_keys path/to/Api_Key.xlsx --dry-run

Columns expected, exactly as the team wrote them:

    Project | API-Key | Purpose | Exp-date | email_id

What it does with each:

* **Project** is matched against the tracker's own projects by name first, so
  "Compliance Tracker" becomes a real link rather than loose text. Anything
  with no match is kept as a typed label - plenty of keys belong to work that
  never became a tracker project.
* **API-Key** is the provider. A provider that is not on the master list yet is
  added to it. The word "Pending" is not a provider: it means the key has not
  been taken out, so the row is stored with no provider and status ``pending``.
* **Exp-date** accepts a real date, a blank cell, or the words "No Expiry
  Date" - all three mean the same thing and are stored as no date.
* **email_id** is the account the key sits on.

Safe to run twice: a row that already exists - same project, same provider,
same purpose - is skipped rather than duplicated, so a corrected sheet can be
re-imported without cleaning up afterwards.
"""
import argparse
import sys
from datetime import date, datetime

from openpyxl import load_workbook

from app.core.database import SessionLocal
from app.models.api_key import ApiKeyEntry, ApiProvider
from app.models.project import Project

# Cells that mean "there is no expiry date", as opposed to a missing value.
NO_EXPIRY_WORDS = {"", "-", "na", "n/a", "none", "no expiry", "no expiry date", "never"}
# The provider column sometimes carries a status instead of a vendor name.
NOT_A_PROVIDER = {"pending", "tbd", "not decided", "-"}

HEADERS = ["project", "api-key", "purpose", "exp-date", "email_id"]


def _text(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _parse_date(value) -> date | None:
    """A blank, a dash or the words "No Expiry Date" all mean no date."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = _text(value)
    if text.lower() in NO_EXPIRY_WORDS:
        return None
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d-%b-%Y", "%d %b %Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"could not read {text!r} as a date")


def _column_map(header_row) -> dict[str, int]:
    """Find the five columns by name, so a reordered sheet still imports."""
    found = {}
    for index, cell in enumerate(header_row):
        name = _text(cell).lower()
        if name in HEADERS:
            found[name] = index
    missing = [h for h in HEADERS if h not in found]
    if missing:
        raise SystemExit(
            f"The sheet is missing these columns: {', '.join(missing)}.\n"
            f"Expected: {' | '.join(h.title() for h in HEADERS)}"
        )
    return found


def run(path: str, dry_run: bool = False) -> int:
    wb = load_workbook(path, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        raise SystemExit("That sheet is empty.")
    cols = _column_map(rows[0])

    db = SessionLocal()
    added = skipped = 0
    try:
        projects = {p.name.strip().lower(): p for p in db.query(Project).all()}
        providers = {p.name.strip().lower(): p for p in db.query(ApiProvider).all()}

        for number, raw in enumerate(rows[1:], start=2):
            project_text = _text(raw[cols["project"]])
            provider_text = _text(raw[cols["api-key"]])
            purpose = _text(raw[cols["purpose"]]) or None
            account = _text(raw[cols["email_id"]]) or None
            if not project_text and not provider_text:
                continue  # a blank spacer row

            try:
                expires_on = _parse_date(raw[cols["exp-date"]])
            except ValueError as err:
                print(f"  row {number}: skipped - {err}")
                skipped += 1
                continue

            project = projects.get(project_text.lower())

            provider = None
            status = "active"
            if provider_text.lower() in NOT_A_PROVIDER:
                status = "pending"
            else:
                provider = providers.get(provider_text.lower())
                if provider is None:
                    provider = ApiProvider(name=provider_text)
                    db.add(provider)
                    db.flush()
                    providers[provider_text.lower()] = provider
                    print(f"  added provider: {provider_text}")

            existing = (
                db.query(ApiKeyEntry)
                .filter(
                    ApiKeyEntry.project_id == (project.id if project else None),
                    ApiKeyEntry.project_label == (None if project else project_text),
                    ApiKeyEntry.provider_id == (provider.id if provider else None),
                    ApiKeyEntry.purpose == purpose,
                )
                .first()
            )
            if existing:
                print(f"  row {number}: already in the register - {project_text} / {provider_text}")
                skipped += 1
                continue

            db.add(ApiKeyEntry(
                project_id=project.id if project else None,
                project_label=None if project else project_text,
                provider_id=provider.id if provider else None,
                purpose=purpose,
                expires_on=expires_on,
                account_email=account,
                status=status,
            ))
            added += 1
            link = "linked to the project" if project else "kept as a label"
            print(f"  row {number}: {project_text} / {provider_text} ({link})")

        if dry_run:
            db.rollback()
            print(f"\nDry run - nothing written. Would add {added}, skip {skipped}.")
        else:
            db.commit()
            print(f"\nAdded {added}, skipped {skipped}.")
    finally:
        db.close()
    return added


def main() -> None:
    parser = argparse.ArgumentParser(description="Import an Api_Key.xlsx into the register.")
    parser.add_argument("path", help="Path to the spreadsheet")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be imported without writing anything")
    args = parser.parse_args()
    run(args.path, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
