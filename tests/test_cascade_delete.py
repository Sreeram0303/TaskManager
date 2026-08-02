import uuid
from sqlalchemy import select
from src.utils.db import LocalSession
from src.user.models import User, RefreshToken
from src.task.models import Task


def _unique_user():
    suffix = uuid.uuid4().hex[:8]
    return {
        "username": f"u{suffix}",
        "email": f"{suffix}@test.com",
        "password": "longenoughpw",
    }


def test_deleting_a_user_cascades_to_tasks_and_refresh_tokens_and_roles(client):
    user = _unique_user()
    client.post("/users/register", json=user)  # gives the user its "member" role row too
    login_r = client.post("/users/login", json={"email": user["email"], "password": user["password"]})
    auth = {"Authorization": f"Bearer {login_r.json()['access_token']}"}
    client.post("/tasks", json={"title": "should disappear with its owner"}, headers=auth)

    async def _delete_user_and_check():
        async with LocalSession() as db:
            db_user = (await db.scalars(select(User).where(User.email == user["email"]))).first()
            user_id = db_user.id
            await db.delete(db_user)
            await db.commit()

        async with LocalSession() as db:
            remaining_tasks = (await db.scalars(select(Task).where(Task.user_id == user_id))).all()
            remaining_tokens = (await db.scalars(select(RefreshToken).where(RefreshToken.user_id == user_id))).all()
            return remaining_tasks, remaining_tokens

    remaining_tasks, remaining_tokens = client.portal.call(_delete_user_and_check)

    assert remaining_tasks == []
    assert remaining_tokens == []
