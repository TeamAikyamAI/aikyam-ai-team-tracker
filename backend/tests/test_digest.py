def test_preview_goes_only_to_admin_and_follows_reporting_chain(client, seed, auth, outbox):
    client.patch("/settings", headers=auth("admin"), json={"values": {"smtp_host": "smtp.example.com"}})
    outbox.clear()
    r = client.post("/settings/digest-preview", headers=auth("admin"))
    assert r.status_code == 200, r.text
    assert r.json()["emails_sent"] == 2
    # nothing leaves to the real recipients in preview mode
    assert all(m["to"] == ["admin@example.com"] for m in outbox)
    subjects = [m["subject"] for m in outbox]
    assert any(s.startswith("[Preview] Weekly update - Max Member") for s in subjects)
    assert any("weekly rollup" in s for s in subjects)


def test_real_send_routes_member_to_manager_and_manager_to_management(seed, db, outbox):
    from app.services.digest import send_weekly_digests
    outbox.clear()
    sent = send_weekly_digests(db)
    assert sent == 2
    by_to = {tuple(m["to"]): m for m in outbox}
    # member's own digest -> their manager (the admin)
    assert ("admin@example.com",) in by_to
    assert by_to[("admin@example.com",)]["reply_to"] == "member@example.com"
    # admin is top of chain inside the app -> rollup goes to external_manager_email
    assert ("management@example.com",) in by_to
    assert by_to[("management@example.com",)]["reply_to"] == "admin@example.com"


def test_digest_dates_follow_configured_timezone(seed, db):
    from app.services.digest import _week_window
    from app.services import settings as cfg
    cfg.set_many(db, {"digest_timezone": "Asia/Kolkata"})
    start, end = _week_window(db)
    assert str(end.tzinfo) == "Asia/Kolkata"
    assert (end - start).days == 7
