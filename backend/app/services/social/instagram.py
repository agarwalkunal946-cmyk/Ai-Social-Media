from urllib.parse import urlencode

import httpx

from app.core.config import get_settings


def build_instagram_auth_url(state: str) -> str:
    settings = get_settings()
    params = {
        "client_id": settings.meta_app_id,
        "redirect_uri": settings.meta_redirect_uri,
        "state": state,
        "scope": settings.instagram_scopes,
        "response_type": "code",
    }
    return f"https://www.facebook.com/{settings.meta_api_version}/dialog/oauth?{urlencode(params)}"


def _normalize_limit(limit: int, *, default: int = 25, maximum: int = 100) -> int:
    try:
        parsed = int(limit)
    except (TypeError, ValueError):
        return default
    return max(1, min(parsed, maximum))


def _clean_username(value: str) -> str:
    return value.strip().removeprefix("@").rstrip("/").split("/")[-1].strip()


async def exchange_instagram_code(code: str) -> dict:
    settings = get_settings()
    url = f"https://graph.facebook.com/{settings.meta_api_version}/oauth/access_token"
    params = {
        "client_id": settings.meta_app_id,
        "client_secret": settings.meta_app_secret,
        "redirect_uri": settings.meta_redirect_uri,
        "code": code,
    }
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        return response.json()


async def fetch_instagram_business_profile(access_token: str) -> dict:
    settings = get_settings()
    headers = {"Authorization": f"Bearer {access_token}"}
    async with httpx.AsyncClient(timeout=30) as client:
        pages_response = await client.get(
            f"https://graph.facebook.com/{settings.meta_api_version}/me/accounts",
            params={"access_token": access_token},
            headers=headers,
        )
        pages_response.raise_for_status()
        pages = pages_response.json().get("data", [])
        if not pages:
            return {"pages": [], "instagram": None}

        first_page = pages[0]
        page_id = first_page["id"]
        page_token = first_page.get("access_token", access_token)

        instagram_response = await client.get(
            f"https://graph.facebook.com/{settings.meta_api_version}/{page_id}",
            params={
                "fields": "name,instagram_business_account{id,username,profile_picture_url,followers_count}",
                "access_token": page_token,
            },
            headers=headers,
        )
        instagram_response.raise_for_status()
        instagram_page = instagram_response.json()
        return {
            "pages": pages,
            "instagram": instagram_page.get("instagram_business_account"),
            "page": {"id": page_id, "name": instagram_page.get("name")},
        }


async def fetch_instagram_media_bundle(access_token: str, instagram_user_id: str, limit: int = 100) -> dict:
    settings = get_settings()
    headers = {"Authorization": f"Bearer {access_token}"}
    limit = _normalize_limit(limit, default=100)

    async with httpx.AsyncClient(timeout=30) as client:
        profile = await client.get(
            f"https://graph.facebook.com/{settings.meta_api_version}/{instagram_user_id}",
            params={
                "fields": "id,username,followers_count,follows_count,media_count,profile_picture_url",
                "access_token": access_token,
            },
            headers=headers,
        )
        profile.raise_for_status()

        media_items: list[dict] = []
        after: str | None = None
        while len(media_items) < limit:
            media = await client.get(
                f"https://graph.facebook.com/{settings.meta_api_version}/{instagram_user_id}/media",
                params={
                    "fields": "id,caption,media_type,media_url,thumbnail_url,permalink,timestamp,like_count,comments_count",
                    "limit": min(50, limit - len(media_items)),
                    "access_token": access_token,
                    **({"after": after} if after else {}),
                },
                headers=headers,
            )
            media.raise_for_status()
            payload = media.json()
            media_items.extend(payload.get("data", []))
            after = ((payload.get("paging") or {}).get("cursors") or {}).get("after")
            if not after:
                break

        return {
            "profile": profile.json(),
            "media": media_items[:limit],
        }


def _business_discovery_fields(username: str, limit: int, after: str | None = None) -> str:
    media_edge = f"media.limit({limit})"
    if after:
        media_edge = f"media.after({after}).limit({limit})"
    return (
        f"business_discovery.username({username})"
        "{"
        "id,name,username,profile_picture_url,biography,website,followers_count,follows_count,media_count,"
        f"{media_edge}"
        "{id,caption,media_type,media_url,thumbnail_url,permalink,timestamp,comments_count,like_count}"
        "}"
    )


async def fetch_instagram_business_discovery(
    access_token: str,
    instagram_user_id: str,
    username: str,
    *,
    limit: int = 25,
) -> dict:
    settings = get_settings()
    headers = {"Authorization": f"Bearer {access_token}"}
    username = _clean_username(username)
    limit = _normalize_limit(limit)

    async with httpx.AsyncClient(timeout=30) as client:
        media_items: list[dict] = []
        after: str | None = None
        profile_data: dict = {}

        while len(media_items) < limit:
            fields = _business_discovery_fields(username, min(25, limit - len(media_items)), after)
            response = await client.get(
                f"https://graph.facebook.com/{settings.meta_api_version}/{instagram_user_id}",
                params={
                    "fields": fields,
                    "access_token": access_token,
                },
                headers=headers,
            )
            response.raise_for_status()
            discovery = response.json().get("business_discovery") or {}
            profile_data = discovery
            media_block = discovery.get("media") or {}
            media_items.extend(media_block.get("data", []))
            after = ((media_block.get("paging") or {}).get("cursors") or {}).get("after")
            if not after:
                break

    profile_data["media"] = media_items[:limit]
    return profile_data


def _extract_insight_value(payload: dict) -> int | float | None:
    entries = payload.get("data") or []
    if not entries:
        return None
    entry = entries[0]
    if isinstance(entry.get("total_value"), dict):
        value = entry["total_value"].get("value")
        if isinstance(value, (int, float)):
            return value
    values = entry.get("values") or []
    if values:
        value = values[-1].get("value")
        if isinstance(value, (int, float)):
            return value
    if isinstance(entry.get("value"), (int, float)):
        return entry["value"]
    return None


def _insight_candidates(media_type: str | None) -> list[str]:
    normalized_type = (media_type or "").upper()
    if normalized_type == "VIDEO":
        return ["views", "reach", "engagement", "comments", "likes", "saved", "shares", "total_interactions"]
    return ["reach", "engagement", "comments", "likes", "saved", "shares", "total_interactions", "views"]


async def fetch_instagram_media_insights(
    access_token: str,
    media_id: str,
    *,
    media_type: str | None = None,
) -> dict[str, int | float]:
    settings = get_settings()
    headers = {"Authorization": f"Bearer {access_token}"}
    insights: dict[str, int | float] = {}

    async with httpx.AsyncClient(timeout=30) as client:
        for metric in _insight_candidates(media_type):
            response = await client.get(
                f"https://graph.facebook.com/{settings.meta_api_version}/{media_id}/insights",
                params={
                    "metric": metric,
                    "access_token": access_token,
                },
                headers=headers,
            )
            if response.status_code >= 400:
                continue
            value = _extract_insight_value(response.json())
            if isinstance(value, (int, float)):
                insights[metric] = value

    return insights
