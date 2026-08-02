from arq.connections import RedisSettings
from arq.cron import cron
from sqlalchemy import delete, or_
from src.utils.settings import settings
from src.utils.db import LocalSession
from src.utils.helpers import utc_now
from src.user.models import RefreshToken
# Unused directly here, but this worker process never imports the task
# feature's module chain the way main.py does — without this import,
# SQLAlchemy can't resolve User.tasks' string-form "Task" relationship
# reference, and any query touching User (even indirectly, via mapper
# configuration) blows up at runtime inside the worker only.
from src.task.models import Task
import httpx
REDIS_SETTINGS = RedisSettings.from_dsn(settings.REDIS_URL)

async def send_welcome_email(ctx,email:str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {settings.RESEND_API_KEY}"},
            json={
                "from": "onboarding@resend.dev",
                "to": email,
                "subject": "Welcome to TaskManager",
                "html": "<p>Thanks for registering!</p>",
            },
        )
        response.raise_for_status()


async def cleanup_expired_refresh_tokens(ctx):
    # No Depends(get_db) out here — this isn't an HTTP request, so we open
    # a session directly from the same factory the app itself uses.
    async with LocalSession() as db:
        await db.execute(
            delete(RefreshToken).where(
                or_(RefreshToken.expires_at < utc_now(), RefreshToken.revoked.is_(True))
            )
        )
        
        await db.commit()


class WorkerSettings:
    functions  = [send_welcome_email]
    redis_settings = REDIS_SETTINGS
    # Runs automatically, once a day at 03:00 — no enqueue_job() call
    # anywhere triggers this; the worker itself watches the clock.
    cron_jobs = [cron(cleanup_expired_refresh_tokens, hour={3}, minute={0})]