from __future__ import annotations

from typing import Any
from urllib.parse import quote_plus

import httpx

from app.core.config import get_settings


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def is_x_apify_available() -> bool:
    settings = get_settings()
    return bool((settings.x_live_source_token or "").strip())


def _actor_url() -> str:
    settings = get_settings()
    return f"https://api.apify.com/v2/acts/{settings.x_live_source_actor_id}/run-sync-get-dataset-items"


def _pick_best_video_variant(variants: list[dict]) -> str | None:
    best_url = None
    best_bitrate = -1
    for variant in variants or []:
        if variant.get("content_type") != "video/mp4":
            continue
        bitrate = _safe_int(variant.get("bitrate"))
        url = variant.get("url")
        if url and bitrate >= best_bitrate:
            best_bitrate = bitrate
            best_url = url
    return best_url


def _iter_media_sources(raw: dict) -> list[dict]:
    nested_keys = ("quoted", "quoted_tweet", "retweeted_tweet", "retweeted_status", "retweeted")
    queue: list[tuple[dict, int]] = [(raw, 0)]
    seen: set[int] = set()
    sources: list[dict] = []

    while queue:
        current, depth = queue.pop(0)
        if not isinstance(current, dict):
            continue
        marker = id(current)
        if marker in seen:
            continue
        seen.add(marker)
        sources.append(current)
        if depth >= 2:
            continue
        for key in nested_keys:
            nested = current.get(key)
            if isinstance(nested, dict):
                queue.append((nested, depth + 1))
    return sources


def _normalize_media(raw: dict) -> list[dict]:
    items: list[dict] = []

    def add_media(kind: str, payload: dict):
        preview = payload.get("media_url_https") or payload.get("media_url")
        media_url = preview
        if kind in {"video", "animated_gif"}:
            media_url = _pick_best_video_variant(payload.get("variants") or payload.get("video_info", {}).get("variants") or []) or preview
        items.append(
            {
                "type": kind,
                "preview_image_url": preview,
                "url": media_url,
                "duration_millis": payload.get("duration") or payload.get("video_info", {}).get("duration_millis"),
                "variants": payload.get("variants") or payload.get("video_info", {}).get("variants") or [],
            }
        )

    for source in _iter_media_sources(raw):
        media_block = source.get("media")
        entity_media = ((source.get("entities") or {}).get("media") or [])

        if isinstance(media_block, dict):
            for kind, values in media_block.items():
                if isinstance(values, list):
                    for payload in values:
                        if isinstance(payload, dict):
                            add_media(kind, payload)

        for payload in entity_media:
            if not isinstance(payload, dict):
                continue
            kind = payload.get("type")
            if kind:
                add_media(kind, payload)

    deduped: list[dict] = []
    seen: set[str] = set()
    for item in items:
        key = f"{item.get('type')}|{item.get('url')}|{item.get('preview_image_url')}"
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _normalize_post(raw: dict) -> dict:
    author = raw.get("user_info") or raw.get("author") or {}
    username = author.get("screen_name") or raw.get("screen_name") or ""
    return {
        "id": str(raw.get("tweet_id") or raw.get("id") or ""),
        "text": raw.get("text") or "",
        "created_at": raw.get("created_at"),
        "lang": raw.get("lang"),
        "source": raw.get("source"),
        "entities": raw.get("entities") or {},
        "conversation_id": raw.get("conversation_id"),
        "public_metrics": {
            "like_count": _safe_int(raw.get("favorites")),
            "reply_count": _safe_int(raw.get("replies")),
            "retweet_count": _safe_int(raw.get("retweets")),
            "quote_count": _safe_int(raw.get("quotes")),
            "view_count": _safe_int(raw.get("views")),
            "bookmark_count": _safe_int(raw.get("bookmarks")),
        },
        "author_username": username,
        "author_name": author.get("name") or username or "X user",
        "author_profile_image_url": author.get("avatar"),
        "author": {
            "id": author.get("rest_id"),
            "username": username,
            "name": author.get("name") or username or "X user",
            "avatar": author.get("avatar"),
            "followers_count": _safe_int(author.get("followers_count")),
            "following_count": _safe_int(author.get("friends_count") or author.get("following_count")),
            "description": author.get("description") or "",
            "verified": bool(author.get("blue_verified") or author.get("verified") or author.get("verified_type")),
        },
        "media": _normalize_media(raw),
        "url": (
            f"https://x.com/{username}/status/{raw.get('tweet_id')}"
            if username and raw.get("tweet_id")
            else None
        ),
        "quoted": raw.get("quoted") or None,
    }


def _build_profile(username: str, posts: list[dict]) -> dict:
    author = ((posts or [{}])[0].get("author") or {}) if posts else {}
    resolved_username = author.get("username") or username
    return {
        "id": author.get("id") or resolved_username,
        "username": resolved_username,
        "name": author.get("name") or f"@{resolved_username}",
        "avatar": author.get("avatar"),
        "description": author.get("description") or "",
        "verified": bool(author.get("verified")),
        "public_metrics": {
            "followers_count": _safe_int(author.get("followers_count")),
            "following_count": _safe_int(author.get("following_count")),
            "tweet_count": max(len(posts), _safe_int(author.get("tweet_count"))),
        },
        "url": f"https://x.com/{resolved_username}",
    }


async def _run_actor(payload: dict) -> list[dict]:
    settings = get_settings()
    if not is_x_apify_available():
        raise RuntimeError("The X data source token is not configured.")

    async with httpx.AsyncClient(timeout=settings.x_live_timeout_seconds) as client:
        response = await client.post(
            _actor_url(),
            params={"token": settings.x_live_source_token},
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and isinstance(data.get("items"), list):
        return data.get("items") or []
    if isinstance(data, dict) and isinstance(data.get("value"), list):
        return data.get("value") or []
    return []


async def fetch_x_apify_user_posts(username: str, *, limit: int | None = None) -> dict:
    settings = get_settings()
    max_posts = min(limit or settings.x_live_timeline_max_posts, settings.x_live_timeline_max_posts)
    raw_items = await _run_actor({"username": username, "max_posts": max_posts})
    posts = [_normalize_post(item) for item in raw_items if isinstance(item, dict)]
    profile = _build_profile(username, posts)
    return {"profile": profile, "items": posts[:max_posts]}


async def fetch_x_apify_recent_search(query: str, *, limit: int | None = None, search_type: str = "Top") -> dict:
    settings = get_settings()
    max_posts = min(limit or settings.x_live_search_max_posts, settings.x_live_search_max_posts)
    raw_items = await _run_actor({"query": query, "search_type": search_type, "max_posts": max_posts})
    posts = [_normalize_post(item) for item in raw_items if isinstance(item, dict)]
    return {"items": posts[:max_posts]}


async def fetch_x_apify_post_detail(tweet_id: str) -> dict:
    settings = get_settings()
    raw_items = await _run_actor({"lookup_post_ids": [tweet_id], "max_posts": settings.x_live_post_detail_max_posts})
    posts = [_normalize_post(item) for item in raw_items if isinstance(item, dict)]
    return posts[0] if posts else {}


async def fetch_x_apify_trends(*, country: str | None = None, limit: int = 30) -> dict:
    settings = get_settings()
    raw_items = await _run_actor(
        {
            "country": country or settings.x_live_trending_country,
            "max_posts": max(limit, 1),
        }
    )
    trends = []
    for index, item in enumerate(raw_items):
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        trends.append(
            {
                "id": f"apify-trend-{index}-{quote_plus(name)}",
                "name": name,
                "category": str(item.get("context") or "Trending").strip(),
                "description": item.get("description"),
                "url": f"https://x.com/search?q={quote_plus(name)}&src=typed_query",
                "post_count": 0,
            }
        )
    return {"items": trends[:limit]}
