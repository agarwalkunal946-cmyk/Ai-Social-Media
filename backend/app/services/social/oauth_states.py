from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.db.mongo import get_database


async def create_oauth_state(user_id: str, platform: str, extra: dict | None = None) -> str:
    db = get_database()
    state = uuid4().hex
    await db.oauth_states.insert_one(
        {
            "_id": state,
            "user_id": user_id,
            "platform": platform,
            "extra": extra or {},
            "created_at": datetime.now(timezone.utc),
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=15),
        }
    )
    return state


async def consume_oauth_state(state: str, platform: str) -> dict | None:
    db = get_database()
    record = await db.oauth_states.find_one({"_id": state, "platform": platform})
    if not record:
        return None
    await db.oauth_states.delete_one({"_id": state})
    return record
