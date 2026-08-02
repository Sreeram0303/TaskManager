import uuid
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from src.utils.db import LocalSession
from src.authz.models import Role
from src.user.models import User


def _register_and_get_auth_header(client):
    suffix = uuid.uuid4().hex[:8]
    user = {"username": f"u{suffix}", "email": f"{suffix}@test.com", "password": "longenoughpw"}
    client.post("/users/register", json=user)
    r = client.post("/users/login", json={"email": user["email"], "password": user["password"]})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}, user["email"]


async def _promote_to_admin(email):
    async with LocalSession() as db:
        # selectinload(User.roles) — without it, user.roles.append() below
        # tries to lazily fetch the CURRENT contents of roles first (to
        # append onto something real), which async SQLAlchemy can't do
        # synchronously. Eager-loading it here avoids that entirely.
        user = (
            await db.scalars(select(User).where(User.email == email).options(selectinload(User.roles)))
        ).first()
        admin_role = (await db.scalars(select(Role).where(Role.name == "admin"))).first()
        user.roles.append(admin_role)
        await db.commit()


def test_admin_dashboard_requires_auth(client):
    r = client.get("/admin/dashboard")
    assert r.status_code == 401


def test_new_user_defaults_to_member_and_is_denied(client):
    auth, _ = _register_and_get_auth_header(client)
    r = client.get("/admin/dashboard", headers=auth)
    assert r.status_code == 403


def test_admin_can_access_dashboard(client):
    auth, email = _register_and_get_auth_header(client)
    client.portal.call(_promote_to_admin, email)

    r = client.get("/admin/dashboard", headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert body["total_users"] >= 1
    assert body["total_tasks"] >= 0
    assert "hits" in body["cache"] and "misses" in body["cache"]
