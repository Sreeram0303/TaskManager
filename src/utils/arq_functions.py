from arq.connections import RedisSettings
from src.utils.settings import settings
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

class WorkerSettings:
    functions  = [send_welcome_email]
    redis_settings = REDIS_SETTINGS