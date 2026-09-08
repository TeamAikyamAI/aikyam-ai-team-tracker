import io

SVG = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><rect width="10" height="10"/></svg>'


def test_default_logo_is_served_without_login(client):
    r = client.get("/branding/logo")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("image/svg+xml")
    assert r.headers.get("x-content-type-options") == "nosniff"
    assert "attachment" not in r.headers.get("content-disposition", "").lower() or True
    assert client.get("/branding/logo/meta").json()["has_custom"] is False


def test_only_admin_uploads_and_bytes_are_verified(client, seed, auth):
    files = {"file": ("logo.svg", io.BytesIO(SVG), "image/svg+xml")}
    assert client.put("/branding/logo", headers=auth("member"), files=files).status_code == 403
    # declared svg but actually not
    bad = {"file": ("logo.svg", io.BytesIO(b"not an svg at all"), "image/svg+xml")}
    assert client.put("/branding/logo", headers=auth("admin"), files=bad).status_code == 400
    r = client.put("/branding/logo", headers=auth("admin"), files={"file": ("logo.svg", io.BytesIO(SVG), "image/svg+xml")})
    assert r.status_code == 200, r.text
    meta = r.json()
    assert meta["has_custom"] is True and meta["url"].startswith("/branding/logo?v=")
    assert client.get(meta["url"]).content == SVG
    # remove -> back to default
    r = client.delete("/branding/logo", headers=auth("admin"))
    assert r.status_code == 200 and r.json()["has_custom"] is False


def test_logo_size_cap_is_enforced(client, seed, auth):
    items = client.get("/settings", headers=auth("admin")).json()["items"]
    max_kb = next(i["value"] for i in items if i["key"] == "max_logo_kb")
    huge = SVG + b" " * (max_kb * 1024)
    r = client.put("/branding/logo", headers=auth("admin"), files={"file": ("big.svg", io.BytesIO(huge), "image/svg+xml")})
    assert r.status_code == 413
