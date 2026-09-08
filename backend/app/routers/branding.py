import hashlib

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_feature
from app.core.default_logo import (
    DEFAULT_LOGO_SVG,
    DEFAULT_LOGO_FILENAME,
    DEFAULT_LOGO_CONTENT_TYPE,
)
from app.models.user import User
from app.models.branding import BrandingAsset
from app.schemas.branding import LogoMeta
from app.services.audit import log_action
from app.services import settings as cfg

router = APIRouter(prefix="/branding", tags=["branding"])

LOGO_KIND = "logo"
ALLOWED_TYPES = {"image/svg+xml": ".svg", "image/png": ".png"}

# An uploaded SVG is a *document* and can carry script, so it is only ever served
# as its own sandboxed resource (never inlined into the app's HTML) and locked
# down with these headers.
SAFE_HEADERS = {
    "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; sandbox",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Cross-Origin-Resource-Policy": "cross-origin",
}


def _get_logo(db: Session) -> BrandingAsset | None:
    return db.query(BrandingAsset).filter(BrandingAsset.kind == LOGO_KIND).first()


def _version(asset: BrandingAsset | None) -> str:
    """Cache-busting version for the image URL, so a newly uploaded logo shows
    up immediately instead of the browser serving the cached old one.

    The last-updated timestamp alone is not quite enough: two uploads inside the
    same second would produce the same token (and a second-resolution clock is
    all some databases give you), leaving the admin looking at the logo they
    just replaced. Mixing in a short content hash makes the token change
    whenever the bytes change, whatever the clock resolution."""
    if asset is None:
        return "default"
    stamp = int(asset.updated_at.timestamp()) if asset.updated_at else 0
    digest = hashlib.sha256(asset.data).hexdigest()[:8]
    return f"{stamp}-{digest}"


@router.get("/logo/meta", response_model=LogoMeta)
def logo_meta(db: Session = Depends(get_db)):
    """Public on purpose: the login screen renders the logo before anyone has signed in."""
    asset = _get_logo(db)
    version = _version(asset)
    return LogoMeta(
        has_custom=asset is not None,
        version=version,
        url=f"/branding/logo?v={version}",
        content_type=asset.content_type if asset else DEFAULT_LOGO_CONTENT_TYPE,
        filename=asset.filename if asset else DEFAULT_LOGO_FILENAME,
        size_bytes=asset.size_bytes if asset else len(DEFAULT_LOGO_SVG),
    )


@router.get("/logo")
def get_logo(v: str | None = Query(None), db: Session = Depends(get_db)):
    """Public. Falls back to the built-in default mark when no logo is stored,
    so removing the uploaded one leaves the app branded rather than blank."""
    asset = _get_logo(db)
    if asset:
        data, content_type, filename = asset.data, asset.content_type, asset.filename
    else:
        data, content_type, filename = DEFAULT_LOGO_SVG, DEFAULT_LOGO_CONTENT_TYPE, DEFAULT_LOGO_FILENAME

    version = _version(asset)
    headers = dict(SAFE_HEADERS)
    headers["Content-Disposition"] = f'inline; filename="{filename}"'
    headers["ETag"] = f'"logo-{version}"'
    # Only let it cache hard when the caller asked for the version we actually
    # hold; otherwise a stale URL could pin an old logo in the browser forever.
    headers["Cache-Control"] = (
        "public, max-age=31536000, immutable" if v is not None and v == version else "no-cache"
    )
    return Response(content=data, media_type=content_type, headers=headers)


@router.put("/logo", response_model=LogoMeta)
async def upload_logo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin: User = Depends(require_feature("admin_panel")),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file was provided")

    # Read one byte past the cap so an oversized upload is rejected without
    # pulling the whole thing into memory.
    max_kb = int(cfg.get(db, "max_logo_kb"))
    max_bytes = max_kb * 1024
    raw = await file.read(max_bytes + 1)
    if len(raw) > max_bytes:
        raise HTTPException(status_code=413, detail=f"Logo must be {max_kb} KB or smaller")
    if not raw:
        raise HTTPException(status_code=400, detail="The uploaded file is empty")

    content_type = (file.content_type or "").split(";")[0].strip().lower()
    if content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=415, detail="Logo must be an SVG or PNG file")

    # Don't trust the declared type - check the bytes actually match it.
    if content_type == "image/png":
        if not raw.startswith(b"\x89PNG\r\n\x1a\n"):
            raise HTTPException(status_code=400, detail="That file isn't a valid PNG")
    else:
        try:
            head = raw[:2048].decode("utf-8", errors="strict").lower()
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="That file isn't a valid SVG")
        if "<svg" not in head:
            raise HTTPException(status_code=400, detail="That file isn't a valid SVG")

    asset = _get_logo(db)
    if asset is None:
        asset = BrandingAsset(kind=LOGO_KIND)
        db.add(asset)
    asset.filename = file.filename[:255]
    asset.content_type = content_type
    asset.size_bytes = len(raw)
    asset.data = raw
    asset.uploaded_by_id = admin.id
    db.commit()
    db.refresh(asset)

    log_action(db, admin.id, "upload_logo", "branding_asset", asset.id, details=f"{asset.filename} ({asset.size_bytes} bytes)")
    version = _version(asset)
    return LogoMeta(
        has_custom=True, version=version, url=f"/branding/logo?v={version}",
        content_type=asset.content_type, filename=asset.filename, size_bytes=asset.size_bytes,
    )


@router.delete("/logo", response_model=LogoMeta)
def delete_logo(db: Session = Depends(get_db), admin: User = Depends(require_feature("admin_panel"))):
    """Removes the uploaded logo; the app reverts to the built-in default mark."""
    asset = _get_logo(db)
    if asset is None:
        raise HTTPException(status_code=404, detail="No custom logo is set")
    asset_id, name = asset.id, asset.filename
    db.delete(asset)
    db.commit()
    log_action(db, admin.id, "delete_logo", "branding_asset", asset_id, details=name)
    return LogoMeta(
        has_custom=False, version=_version(None), url=f"/branding/logo?v={_version(None)}",
        content_type=DEFAULT_LOGO_CONTENT_TYPE, filename=DEFAULT_LOGO_FILENAME,
        size_bytes=len(DEFAULT_LOGO_SVG),
    )
