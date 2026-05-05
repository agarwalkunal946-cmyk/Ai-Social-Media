from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse

from app.core.config import get_settings
from app.db.mongo import get_database
from app.services.analysis import get_model_stack
from app.services.auth import get_current_user
from app.services.dashboard_data import invalidate_dashboard_snapshot_cache
from app.services.platform_preview import invalidate_platform_preview_cache
from app.services.social.instagram import build_instagram_auth_url, exchange_instagram_code, fetch_instagram_business_profile
from app.services.social.oauth_states import consume_oauth_state, create_oauth_state
from app.services.social.x_apify import (
    fetch_x_apify_user_posts,
    is_x_apify_available,
)
from app.services.social.youtube import build_youtube_auth_url, exchange_youtube_code, fetch_youtube_channel


router = APIRouter(prefix="/providers", tags=["providers"])


def _normalize_x_handle(value: str) -> str:
    cleaned = (value or "").strip()
    if "x.com/" in cleaned:
        cleaned = cleaned.split("x.com/", 1)[1]
    if "twitter.com/" in cleaned:
        cleaned = cleaned.split("twitter.com/", 1)[1]
    return cleaned.strip().strip("/").removeprefix("@").split("/")[0].strip()


def _extract_x_error_message(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        payload = None

    if isinstance(payload, dict):
        for key in ("detail", "title", "error", "message"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        errors = payload.get("errors")
        if isinstance(errors, list) and errors:
            first = errors[0]
            if isinstance(first, dict):
                for key in ("detail", "message", "title"):
                    value = first.get(key)
                    if isinstance(value, str) and value.strip():
                        return value.strip()
            if isinstance(first, str) and first.strip():
                return first.strip()

    text = response.text.strip()
    return text or "Unknown X API error."


def _build_x_connect_error_detail(username: str, exc: httpx.HTTPStatusError) -> str:
    response = exc.response
    status = response.status_code
    message = _extract_x_error_message(response)
    if status == 402:
        return f"The X data source usage limit blocked @{username} right now. Provider said: {message}"
    if status == 401:
        return f"The configured X data source credentials were rejected while connecting @{username}. Provider said: {message}"
    if status == 403:
        return f"The X data source blocked this request for @{username}. Provider said: {message}"
    if status == 429:
        return f"The X data source rate limited the request for @{username}. Provider said: {message}"
    return f"The X data source returned {status} while connecting @{username}. Provider said: {message}"


async def _upsert_provider_connection(user_id: str, payload: dict) -> dict:
    db = get_database()
    platform = payload["platform"]
    payload["updated_at"] = datetime.now(timezone.utc)
    existing = await db.social_accounts.find_one({"user_id": user_id, "platform": platform})
    if existing:
        await db.social_accounts.update_one({"_id": existing["_id"]}, {"$set": payload})
        connection = await db.social_accounts.find_one({"_id": existing["_id"]})
    else:
        payload["_id"] = f"{user_id}-{platform}"
        payload["user_id"] = user_id
        payload["connected_at"] = datetime.now(timezone.utc)
        await db.social_accounts.insert_one(payload)
        connection = payload
    connection["id"] = connection["_id"]
    await invalidate_platform_preview_cache(user_id, platform)
    await invalidate_dashboard_snapshot_cache(user_id)
    return connection


def _provider_avatar_url(platform: str, connection: dict | None) -> str | None:
    extra = (connection or {}).get("extra") or {}
    if platform == "instagram":
        instagram_account = extra.get("instagram") or {}
        return instagram_account.get("profile_picture_url")
    if platform == "youtube":
        return (
            extra.get("thumbnail_url")
            or (((extra.get("channel") or {}).get("snippet") or {}).get("thumbnails") or {}).get("high", {}).get("url")
            or (((extra.get("channel") or {}).get("snippet") or {}).get("thumbnails") or {}).get("default", {}).get("url")
        )
    if platform == "x":
        return (extra.get("profile") or {}).get("avatar")
    return None


@router.get("")
async def list_provider_connections(user: dict = Depends(get_current_user)):
    db = get_database()
    existing = await db.social_accounts.find({"user_id": user["id"]}).to_list(length=20)
    indexed = {item["platform"]: item for item in existing}
    x_live_source_enabled = is_x_apify_available()
    defaults = []
    for platform in ["instagram", "youtube", "x"]:
        connection = indexed.get(platform)
        if connection:
            extra = connection.get("extra", {})
            access_mode = connection.get("access_mode", "oauth")
            if platform == "x":
                access_mode = "live_feed"
                extra = extra | {"live_source_enabled": x_live_source_enabled}
            defaults.append(
                {
                    "platform": platform,
                    "status": connection.get("status", "connected"),
                    "access_mode": access_mode,
                    "connected": True,
                    "handle": connection.get("handle"),
                    "account_name": connection.get("account_name"),
                    "avatar_url": _provider_avatar_url(platform, connection),
                    "scopes": connection.get("scopes", []),
                    "connected_at": connection.get("connected_at"),
                    "extra": extra,
                }
            )
        else:
            access_mode = "oauth"
            extra = {}
            if platform == "x":
                access_mode = "live_feed"
                extra["live_source_enabled"] = x_live_source_enabled
            defaults.append(
                {
                    "platform": platform,
                    "status": "not_connected",
                    "access_mode": access_mode,
                    "connected": False,
                    "handle": None,
                    "account_name": None,
                    "avatar_url": None,
                    "scopes": [],
                    "connected_at": None,
                    "extra": extra,
                }
            )
    return {"items": defaults, "models": get_model_stack()}


@router.delete("/{platform}")
async def disconnect_provider(platform: str, user: dict = Depends(get_current_user)):
    normalized_platform = (platform or "").strip().lower()
    if normalized_platform not in {"instagram", "youtube", "x"}:
        raise HTTPException(status_code=404, detail="Unknown provider.")

    db = get_database()
    connection = await db.social_accounts.find_one({"user_id": user["id"], "platform": normalized_platform})
    if not connection:
        label = {"instagram": "Instagram", "youtube": "YouTube", "x": "X / Twitter"}[normalized_platform]
        return {"message": f"{label} is already disconnected."}

    await db.social_accounts.delete_one({"_id": connection["_id"]})
    await invalidate_platform_preview_cache(user["id"], normalized_platform)
    await invalidate_dashboard_snapshot_cache(user["id"])
    label = {"instagram": "Instagram", "youtube": "YouTube", "x": "X / Twitter"}[normalized_platform]
    return {"message": f"{label} disconnected successfully."}


@router.get("/youtube/start")
async def start_youtube_connect(user: dict = Depends(get_current_user)):
    state = await create_oauth_state(user["id"], "youtube")
    return {"url": build_youtube_auth_url(state)}


@router.get("/youtube/callback")
async def finish_youtube_connect(code: str = Query(...), state: str = Query(...)):
    settings = get_settings()
    state_record = await consume_oauth_state(state, "youtube")
    if not state_record:
        raise HTTPException(status_code=400, detail="Invalid YouTube auth state.")
    token_payload = await exchange_youtube_code(code)
    channel_payload = await fetch_youtube_channel(token_payload["access_token"])

    profile = channel_payload["profile"]
    channel = channel_payload["channel"]
    await _upsert_provider_connection(
        state_record["user_id"],
        {
            "platform": "youtube",
            "status": "connected",
            "access_mode": "oauth",
            "handle": profile.get("email"),
            "account_name": channel.get("snippet", {}).get("title", profile.get("name")),
            "scopes": ["youtube.readonly", "yt-analytics.readonly"],
            "tokens": token_payload,
            "extra": {
                "channel_id": channel.get("id"),
                "channel": channel,
                "statistics": channel.get("statistics", {}),
                "thumbnail_url": (
                    ((channel.get("snippet") or {}).get("thumbnails") or {}).get("high", {}).get("url")
                    or ((channel.get("snippet") or {}).get("thumbnails") or {}).get("default", {}).get("url")
                ),
            },
        },
    )
    return RedirectResponse(url=f"{settings.frontend_url}/connect?platform=youtube&status=success")


@router.get("/instagram/start")
async def start_instagram_connect(user: dict = Depends(get_current_user)):
    state = await create_oauth_state(user["id"], "instagram")
    return {"url": build_instagram_auth_url(state)}


@router.get("/instagram/callback")
async def finish_instagram_connect(code: str = Query(...), state: str = Query(...)):
    settings = get_settings()
    state_record = await consume_oauth_state(state, "instagram")
    if not state_record:
        raise HTTPException(status_code=400, detail="Invalid Instagram auth state.")
    token_payload = await exchange_instagram_code(code)
    profile_payload = await fetch_instagram_business_profile(token_payload["access_token"])
    instagram_account = profile_payload.get("instagram") or {}
    page_payload = profile_payload.get("page") or {}

    await _upsert_provider_connection(
        state_record["user_id"],
        {
            "platform": "instagram",
            "status": "connected",
            "access_mode": "oauth",
            "handle": instagram_account.get("username"),
            "account_name": instagram_account.get("username") or page_payload.get("name"),
            "scopes": [
                "pages_show_list",
                "pages_read_engagement",
                "instagram_basic",
                "instagram_manage_insights",
                "instagram_manage_comments",
            ],
            "tokens": token_payload,
            "extra": {"page": page_payload, "instagram": instagram_account},
        },
    )
    return RedirectResponse(url=f"{settings.frontend_url}/connect?platform=instagram&status=success")


@router.get("/x/start")
async def start_x_connect(user: dict = Depends(get_current_user)):
    raise HTTPException(status_code=410, detail="X now uses handle-based connect only. Open the Connections page and enter a public X username.")


@router.get("/x/callback")
async def finish_x_connect(code: str = Query(...), state: str = Query(...)):
    raise HTTPException(status_code=410, detail="X OAuth callback is disabled. Use the handle-based X connect flow instead.")

@router.post("/x/connect")
async def connect_x_handle(
    payload: dict = Body(...),
    user: dict = Depends(get_current_user),
):
    username = _normalize_x_handle(str((payload or {}).get("handle") or ""))
    if not username:
        raise HTTPException(status_code=400, detail="Enter an X handle to connect.")
    if not is_x_apify_available():
        raise HTTPException(status_code=503, detail="The X live data source is not configured on the backend yet.")

    try:
        timeline_payload = await fetch_x_apify_user_posts(username, limit=get_settings().x_live_timeline_max_posts)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail=_build_x_connect_error_detail(username, exc)) from exc
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"Network error while connecting @{username} through the X data source.") from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Unexpected X connect failure for @{username}.") from exc

    profile = timeline_payload.get("profile") or {"username": username, "name": f"@{username}", "public_metrics": {}}
    timeline_posts = timeline_payload.get("items") or []
    canonical_username = profile.get("username") or username
    connection = await _upsert_provider_connection(
        user["id"],
        {
            "platform": "x",
            "status": "connected",
            "access_mode": "live_feed",
            "handle": canonical_username,
            "account_name": profile.get("name") or f"@{canonical_username}",
            "scopes": ["profile.read", "posts.read", "trends.read"],
            "tokens": {},
            "extra": {
                "provider": "x_live_source",
                "profile": profile,
                "posts": timeline_posts,
                "posts_processed": len(timeline_posts),
            },
        },
    )
    return {"message": "X / Twitter connected successfully.", "connection": connection}
