import uuid


def _register_and_get_auth_header(client):
    suffix = uuid.uuid4().hex[:8]
    user = {"username": f"u{suffix}", "email": f"{suffix}@test.com", "password": "longenoughpw"}
    client.post("/users/register", json=user)
    r = client.post("/users/login", json={"email": user["email"], "password": user["password"]})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_activity_requires_auth(client):
    r = client.get("/activity")
    assert r.status_code == 401


def test_activity_logs_task_mutations(client):
    auth = _register_and_get_auth_header(client)

    r = client.post("/tasks", json={"title": "log me"}, headers=auth)
    task_id = r.json()["id"]
    client.patch(f"/tasks/{task_id}", json={"is_completed": True}, headers=auth)
    client.delete(f"/tasks/{task_id}", headers=auth)

    r = client.get("/activity", headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"]) == 3
    # most-recent-first: the delete (last action taken) should lead
    actions = [item["action"] for item in body["items"]]
    assert actions == ["task_deleted", "task_modified", "task_created"]


def test_activity_pagination_and_ownership(client):
    auth_a = _register_and_get_auth_header(client)
    auth_b = _register_and_get_auth_header(client)

    for i in range(3):
        client.post("/tasks", json={"title": f"task {i}"}, headers=auth_a)

    r = client.get("/activity?page=1&page_size=2", headers=auth_a)
    body = r.json()
    assert len(body["items"]) == 2
    assert body["has_next"] is True

    r = client.get("/activity?page=2&page_size=2", headers=auth_a)
    body = r.json()
    assert len(body["items"]) == 1
    assert body["has_next"] is False

    # user B's activity feed must stay empty despite user A's actions
    r = client.get("/activity", headers=auth_b)
    assert r.json() == {"items": [], "has_next": False}
