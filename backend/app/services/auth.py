from datetime import datetime, timezone

import httpx
from fastapi import Depends, Header, HTTPException, status
from google.auth.transport.requests import Request
from google.oauth2 import id_token

from app.core.config import get_settings
from app.db.mongo import get_database


async def upsert_user_from_claims(claims: dict) -> dict:
    settings = get_settings()
    db = get_database()
    email = (claims.get("email") or "").lower()
    if not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email missing from auth token.")

    blocked_user = await db.blocked_users.find_one({"email": email})
    if blocked_user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This account has been removed by an administrator.")

    existing = await db.users.find_one({"email": email})
    role = "admin" if email in settings.admin_email_list or email == settings.first_admin_email.lower() else "user"
    now = datetime.now(timezone.utc)
    fallback_display_name = email.split("@")[0].title()

    preserve_custom_display_name = bool(existing and existing.get("manual_display_name"))
    preserve_custom_avatar = bool(
        existing
        and (
            existing.get("manual_avatar_url")
            or str(existing.get("avatar_url") or "").startswith("/uploads/")
        )
    )

    display_name = claims.get("name") or (existing.get("display_name") if existing else None)
    if preserve_custom_display_name and existing:
        display_name = existing.get("display_name")
    display_name = display_name or fallback_display_name

    avatar_url = claims.get("picture") or (existing.get("avatar_url") if existing else None)
    if preserve_custom_avatar and existing:
        avatar_url = existing.get("avatar_url")

    payload = {
        "firebase_uid": claims.get("uid") or claims.get("user_id") or email,
        "email": email,
        "display_name": display_name,
        "avatar_url": avatar_url,
        "provider": claims.get("firebase", {}).get("sign_in_provider") or (existing.get("provider") if existing else "unknown"),
        "status": existing.get("status", "active") if existing else "active",
        "updated_at": now,
    }
    if existing:
        if existing.get("role") == "admin":
            role = "admin"
        await db.users.update_one({"_id": existing["_id"]}, {"$set": payload | {"role": role}})
        user = await db.users.find_one({"_id": existing["_id"]})
    else:
        user = {
            "_id": claims.get("uid") or claims.get("user_id") or email,
            "role": role,
            "mode": "creator",
            "status": "active",
            "created_at": now,
            **payload,
        }
        await db.users.insert_one(user)

    return {
        "id": user["_id"],
        "email": user["email"],
        "display_name": user["display_name"],
        "role": user.get("role", role),
        "mode": user.get("mode", "creator"),
        "status": user.get("status", "active"),
        "avatar_url": user.get("avatar_url"),
        "provider": user.get("provider"),
        "created_at": user.get("created_at"),
        "manual_display_name": user.get("manual_display_name", False),
        "manual_avatar_url": user.get("manual_avatar_url", False),
    }


async def lookup_firebase_user(token: str) -> dict | None:
    settings = get_settings()
    if not settings.firebase_api_key:
        return None

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            f"https://identitytoolkit.googleapis.com/v1/accounts:lookup?key={settings.firebase_api_key}",
            json={"idToken": token},
        )
        if response.status_code >= 400:
            return None
        payload = response.json()
        users = payload.get("users", [])
        if not users:
            return None
        user = users[0]
        provider = "password"
        provider_data = user.get("providerUserInfo") or []
        if provider_data:
            provider = provider_data[0].get("providerId", provider)
        return {
            "email": user.get("email"),
            "name": user.get("displayName") or (user.get("email") or "").split("@")[0].title(),
            "picture": user.get("photoUrl"),
            "uid": user.get("localId") or user.get("email"),
            "firebase": {"sign_in_provider": provider},
        }


async def get_current_user(
    authorization: str | None = Header(default=None),
    x_dev_user_email: str | None = Header(default=None),
    x_dev_user_name: str | None = Header(default=None),
) -> dict:
    settings = get_settings()
    if authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()
        try:
            claims = id_token.verify_firebase_token(token, Request(), settings.firebase_project_id)
            user = await upsert_user_from_claims(claims)
            if user.get("status") == "inactive" and user.get("role") != "admin":
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This account is inactive.")
            return user
        except HTTPException:
            raise
        except Exception as exc:  # noqa: BLE001
            claims = await lookup_firebase_user(token)
            if claims:
                user = await upsert_user_from_claims(claims)
                if user.get("status") == "inactive" and user.get("role") != "admin":
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This account is inactive.")
                return user
            if not settings.auth_fallback_enabled:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Firebase token.") from exc

    if settings.auth_fallback_enabled and x_dev_user_email:
        claims = {
            "email": x_dev_user_email,
            "name": x_dev_user_name or x_dev_user_email.split("@")[0].title(),
            "uid": x_dev_user_email,
            "firebase": {"sign_in_provider": "dev-fallback"},
        }
        user = await upsert_user_from_claims(claims)
        if user.get("status") == "inactive" and user.get("role") != "admin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This account is inactive.")
        return user

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")


async def get_optional_user(
    authorization: str | None = Header(default=None),
    x_dev_user_email: str | None = Header(default=None),
    x_dev_user_name: str | None = Header(default=None),
) -> dict | None:
    try:
        return await get_current_user(authorization, x_dev_user_email, x_dev_user_name)
    except HTTPException as exc:
        if exc.status_code == status.HTTP_401_UNAUTHORIZED:
            return None
        raise


async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if user["role"] != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required.")
    return user
