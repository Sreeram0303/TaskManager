from datetime import datetime, timezone


def utc_now() -> datetime:
    """Timezone-aware current time in UTC. Use this for every timestamp
    default instead of datetime.now()/datetime.utcnow() — both are naive
    and either drift by the server's local offset or lose the tz info
    a client needs to interpret them correctly."""
    return datetime.now(timezone.utc)
