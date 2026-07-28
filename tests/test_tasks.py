import uuid


def _register_and_get_auth_header(client):
    suffix = uuid.uuid4().hex[:8]
    user = {"username": f"u{suffix}", "email": f"{suffix}@test.com", "password": "longenoughpw"}
    client.post("/users/register", json=user)
    r = client.post("/users/login", json={"email": user["email"], "password": user["password"]})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_task_crud_lifecycle(client):
    auth = _register_and_get_auth_header(client)

    r = client.post("/tasks", json={"title": "write tests", "description": "safety net for async"}, headers=auth)
    assert r.status_code == 201
    task_id = r.json()["id"]
    assert r.json()["is_completed"] is False

    r = client.get("/tasks", headers=auth)
    assert r.status_code == 200
    assert len(r.json()) == 1

    r = client.patch(f"/tasks/{task_id}", json={"is_completed": True}, headers=auth)
    assert r.status_code == 200
    assert r.json()["is_completed"] is True

    r = client.delete(f"/tasks/{task_id}", headers=auth)
    assert r.status_code == 204

    r = client.get(f"/tasks/{task_id}", headers=auth)
    assert r.status_code == 404


def test_task_routes_require_auth(client):
    r = client.get("/tasks")
    assert r.status_code == 401


def test_user_cannot_see_another_users_task(client):
    auth_a = _register_and_get_auth_header(client)
    auth_b = _register_and_get_auth_header(client)

    r = client.post("/tasks", json={"title": "user A's task", "description": "private"}, headers=auth_a)
    task_id = r.json()["id"]

    # user B probing user A's task should get the SAME 404 as a nonexistent id — no privacy leak
    r = client.get(f"/tasks/{task_id}", headers=auth_b)
    assert r.status_code == 404

    r = client.get("/tasks", headers=auth_b)
    assert r.json() == []
