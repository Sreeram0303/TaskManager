from fastapi import Request
from src.utils.settings import settings


async def add_security_headers(request: Request, call_next):
    response = await call_next(request)

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"

    # Only ever sent once actually deployed behind real HTTPS — sending it
    # on plain http://localhost dev could make a browser start refusing
    # to connect at all for the duration of max-age. Reuses COOKIE_SECURE
    # rather than a second flag answering the same underlying question.
    if settings.COOKIE_SECURE:
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"

    return response
