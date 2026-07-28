import uuid


def _register_and_login(client):
    suffix = uuid.uuid4().hex[:8]
    user = {"username": f"u{suffix}", "email": f"{suffix}@test.com", "password": "longenoughpw"}
    client.post("/users/register", json=user)
    r = client.post("/users/login", json={"email": user["email"], "password": user["password"]})
    access = r.json()["access_token"]
    csrf = client.cookies.get("csrf_token")
    return access, csrf


def test_refresh_without_csrf_header_returns_403(client):
    _register_and_login(client)
    r = client.post("/users/refresh")
    assert r.status_code == 403


def test_refresh_with_wrong_csrf_returns_403(client):
    _register_and_login(client)
    r = client.post("/users/refresh", headers={"X-CSRF-Token": "not-the-real-token"})
    assert r.status_code == 403


def test_refresh_with_correct_csrf_rotates_tokens(client):
    _, csrf = _register_and_login(client)
    old_refresh = client.cookies.get("refresh_token")

    r = client.post("/users/refresh", headers={"X-CSRF-Token": csrf})
    assert r.status_code == 200
    assert client.cookies.get("refresh_token") != old_refresh  # rotated, not reused


def test_reusing_rotated_refresh_token_revokes_all_sessions(client):
    _, csrf = _register_and_login(client)
    old_refresh = client.cookies.get("refresh_token")

    # rotate once, legitimately
    client.post("/users/refresh", headers={"X-CSRF-Token": csrf})
    new_csrf = client.cookies.get("csrf_token")

    # now replay the OLD (already-rotated-away) refresh token
    r = client.post("/users/refresh", cookies={"refresh_token": old_refresh}, headers={"X-CSRF-Token": new_csrf})
    assert r.status_code == 401

    # even the legitimately-rotated new token should now be dead too
    r = client.post("/users/refresh", headers={"X-CSRF-Token": new_csrf})
    assert r.status_code == 401


def test_logout_clears_session(client):
    _, csrf = _register_and_login(client)
    r = client.post("/users/logout", headers={"X-CSRF-Token": csrf})
    assert r.status_code == 200
    assert client.cookies.get("refresh_token") is None

    # refresh should no longer work post-logout
    r = client.post("/users/refresh")
    assert r.status_code in (401, 403)
