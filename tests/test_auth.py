import uuid


def _unique_user():
    suffix = uuid.uuid4().hex[:8]
    return {
        "username": f"u{suffix}",
        "email": f"{suffix}@test.com",
        "password": "longenoughpw",
    }


def test_register_creates_user(client):
    r = client.post("/users/register", json=_unique_user())
    assert r.status_code == 201
    body = r.json()
    assert "id" in body
    assert "created_at" in body


def test_register_duplicate_email_returns_409(client):
    user = _unique_user()
    client.post("/users/register", json=user)
    r = client.post("/users/register", json=user)
    assert r.status_code == 409


def test_login_wrong_password_returns_401(client):
    user = _unique_user()
    client.post("/users/register", json=user)
    r = client.post("/users/login", json={"email": user["email"], "password": "wrong-password"})
    assert r.status_code == 401


def test_login_sets_cookies_and_returns_access_token(client):
    user = _unique_user()
    client.post("/users/register", json=user)
    r = client.post("/users/login", json={"email": user["email"], "password": user["password"]})
    assert r.status_code == 200
    assert "access_token" in r.json()
    assert "refresh_token" not in r.json()  # must not leak into the body — cookie only
    assert client.cookies.get("refresh_token") is not None
    assert client.cookies.get("csrf_token") is not None
