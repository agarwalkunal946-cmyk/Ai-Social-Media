import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings  # noqa: E402
from app.db.mongo import get_database  # noqa: E402


async def main():
    settings = get_settings()
    email = settings.first_admin_email.lower()
    db = get_database()
    existing = await db.users.find_one({"email": email})
    if existing:
        await db.users.update_one({"_id": existing["_id"]}, {"$set": {"role": "admin", "updated_at": datetime.now(timezone.utc)}})
        print(f"Updated existing user as admin: {email}")
    else:
        await db.users.insert_one(
            {
                "_id": email,
                "firebase_uid": email,
                "email": email,
                "display_name": "Primary Admin",
                "role": "admin",
                "mode": "brand",
                "provider": "seed-script",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }
        )
        print(f"Seeded admin user: {email}")


if __name__ == "__main__":
    asyncio.run(main())
