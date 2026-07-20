from src.utils.db import LocalSession
from src.task.models import ActivityLog

def log_activity(user_id: int, action: str, detail: str | None = None):
    with LocalSession() as session:
        session.add(ActivityLog(user_id=user_id, action=action, detail=detail))
        session.commit()
