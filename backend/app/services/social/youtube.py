import re
from datetime import date, timedelta
from urllib.parse import urlencode

import httpx

from app.core.config import get_settings


DATA_API_BASE_URL = "https://www.googleapis.com/youtube/v3"
ANALYTICS_API_BASE_URL = "https://youtubeanalytics.googleapis.com/v2"


def build_youtube_auth_url(state: str) -> str:
    settings = get_settings()
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "access_type": "offline",
        "include_granted_scopes": "true",
        "prompt": "consent",
        "scope": settings.youtube_scopes,
        "state": state,
    }
    return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"


def _authorized_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def _normalize_limit(limit: int, *, default: int = 25, maximum: int = 100) -> int:
    try:
        parsed = int(limit)
    except (TypeError, ValueError):
        return default
    return max(1, min(parsed, maximum))


def _chunked(items: list[str], size: int = 50) -> list[list[str]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


async def exchange_youtube_code(code: str) -> dict:
    settings = get_settings()
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": settings.google_redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        response.raise_for_status()
        return response.json()


async def refresh_youtube_token(refresh_token: str) -> dict:
    settings = get_settings()
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
        )
        response.raise_for_status()
        return response.json()


async def _fetch_video_details(
    client: httpx.AsyncClient,
    access_token: str,
    video_ids: list[str],
) -> list[dict]:
    ordered_videos: list[dict] = []
    headers = _authorized_headers(access_token)
    for chunk in _chunked(video_ids, 50):
        response = await client.get(
            f"{DATA_API_BASE_URL}/videos",
            headers=headers,
            params={
                "part": "snippet,statistics,contentDetails",
                "id": ",".join(chunk),
            },
        )
        response.raise_for_status()
        by_id = {item.get("id"): item for item in response.json().get("items", [])}
        ordered_videos.extend(by_id[video_id] for video_id in chunk if video_id in by_id)
    return ordered_videos


async def fetch_youtube_channel(access_token: str) -> dict:
    headers = _authorized_headers(access_token)
    async with httpx.AsyncClient(timeout=30) as client:
        profile = await client.get("https://www.googleapis.com/oauth2/v2/userinfo", headers=headers)
        profile.raise_for_status()
        channel = await client.get(
            f"{DATA_API_BASE_URL}/channels",
            headers=headers,
            params={"part": "snippet,statistics,contentDetails", "mine": "true"},
        )
        channel.raise_for_status()
        channel_data = channel.json().get("items", [{}])[0]
        return {
            "profile": profile.json(),
            "channel": channel_data,
        }


def format_youtube_duration(raw_value: str | None) -> str:
    if not raw_value:
        return "n/a"

    hours = minutes = seconds = 0
    matched = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", raw_value)
    if matched:
        hours = int(matched.group(1) or 0)
        minutes = int(matched.group(2) or 0)
        seconds = int(matched.group(3) or 0)

    total_minutes = hours * 60 + minutes
    if total_minutes >= 60:
        display_hours = total_minutes // 60
        display_minutes = total_minutes % 60
        return f"{display_hours}:{display_minutes:02d}:{seconds:02d}"
    return f"{total_minutes}:{seconds:02d}"


async def fetch_youtube_video_bundle(access_token: str, limit: int = 100) -> dict:
    limit = _normalize_limit(limit, default=100)
    headers = _authorized_headers(access_token)

    async with httpx.AsyncClient(timeout=30) as client:
        profile = await client.get("https://www.googleapis.com/oauth2/v2/userinfo", headers=headers)
        profile.raise_for_status()

        channel = await client.get(
            f"{DATA_API_BASE_URL}/channels",
            headers=headers,
            params={"part": "snippet,statistics,contentDetails", "mine": "true"},
        )
        channel.raise_for_status()
        channel_data = channel.json().get("items", [{}])[0]

        uploads_playlist = channel_data.get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads")
        if not uploads_playlist:
            return {"profile": profile.json(), "channel": channel_data, "videos": []}

        video_ids: list[str] = []
        next_page_token: str | None = None
        while len(video_ids) < limit:
            playlist_items = await client.get(
                f"{DATA_API_BASE_URL}/playlistItems",
                headers=headers,
                params={
                    "part": "snippet,contentDetails",
                    "playlistId": uploads_playlist,
                    "maxResults": min(50, limit - len(video_ids)),
                    **({"pageToken": next_page_token} if next_page_token else {}),
                },
            )
            playlist_items.raise_for_status()
            payload = playlist_items.json()
            items = payload.get("items", [])
            video_ids.extend(
                item.get("contentDetails", {}).get("videoId")
                or item.get("snippet", {}).get("resourceId", {}).get("videoId")
                for item in items
            )
            video_ids = [video_id for video_id in video_ids if video_id]
            next_page_token = payload.get("nextPageToken")
            if not next_page_token:
                break

        videos = await _fetch_video_details(client, access_token, video_ids[:limit]) if video_ids else []
        return {"profile": profile.json(), "channel": channel_data, "videos": videos}


async def fetch_youtube_search_bundle(
    access_token: str,
    query: str,
    *,
    limit: int = 25,
    region_code: str = "US",
    page_token: str | None = None,
) -> dict:
    headers = _authorized_headers(access_token)
    limit = _normalize_limit(limit)

    async with httpx.AsyncClient(timeout=30) as client:
        video_ids: list[str] = []
        next_page_token = page_token
        payload: dict = {}

        while len(video_ids) < limit:
            response = await client.get(
                f"{DATA_API_BASE_URL}/search",
                headers=headers,
                params={
                    "part": "snippet",
                    "q": query,
                    "type": "video",
                    "order": "relevance",
                    "maxResults": min(50, limit - len(video_ids)),
                    "regionCode": region_code,
                    "safeSearch": "moderate",
                    **({"pageToken": next_page_token} if next_page_token else {}),
                },
            )
            response.raise_for_status()
            payload = response.json()
            items = payload.get("items", [])
            video_ids.extend(
                item.get("id", {}).get("videoId") for item in items if item.get("id", {}).get("videoId")
            )
            video_ids = list(dict.fromkeys(video_ids))
            next_page_token = payload.get("nextPageToken")
            if not next_page_token or not items:
                break

        videos = await _fetch_video_details(client, access_token, video_ids[:limit]) if video_ids else []

    return {
        "items": videos,
        "query": query,
        "next_page_token": next_page_token,
        "page_info": payload.get("pageInfo", {}),
    }


async def fetch_youtube_trending_bundle(
    access_token: str,
    *,
    limit: int = 25,
    region_code: str = "US",
    category_id: str | None = None,
) -> dict:
    headers = _authorized_headers(access_token)
    limit = _normalize_limit(limit)
    params = {
        "part": "snippet,statistics,contentDetails",
        "chart": "mostPopular",
        "maxResults": min(limit, 50),
        "regionCode": region_code,
    }
    if category_id:
        params["videoCategoryId"] = category_id

    async with httpx.AsyncClient(timeout=30) as client:
        items: list[dict] = []
        next_page_token: str | None = None
        payload: dict = {}

        while len(items) < limit:
            response = await client.get(
                f"{DATA_API_BASE_URL}/videos",
                headers=headers,
                params=params
                | {
                    "maxResults": min(50, limit - len(items)),
                    **({"pageToken": next_page_token} if next_page_token else {}),
                },
            )
            response.raise_for_status()
            payload = response.json()
            page_items = payload.get("items", [])
            items.extend(page_items)
            next_page_token = payload.get("nextPageToken")
            if not next_page_token or not page_items:
                break

    return {
        "items": items[:limit],
        "region_code": region_code,
        "page_info": payload.get("pageInfo", {}),
    }


def _table_rows_as_dicts(payload: dict) -> list[dict]:
    headers = [column.get("name") for column in payload.get("columnHeaders", [])]
    rows = payload.get("rows") or []
    return [dict(zip(headers, row, strict=False)) for row in rows]


async def _query_youtube_analytics(access_token: str, params: dict) -> dict:
    headers = _authorized_headers(access_token)
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(f"{ANALYTICS_API_BASE_URL}/reports", headers=headers, params=params)
        response.raise_for_status()
        return response.json()


async def fetch_youtube_video_analytics(
    access_token: str,
    video_id: str,
    *,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict:
    end_date = end_date or date.today()
    start_date = start_date or (end_date - timedelta(days=27))
    base_params = {
        "ids": "channel==MINE",
        "startDate": start_date.isoformat(),
        "endDate": end_date.isoformat(),
        "filters": f"video=={video_id}",
    }

    summary = await _query_youtube_analytics(
        access_token,
        base_params
        | {
            "metrics": "views,likes,comments,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,subscribersGained",
        },
    )
    timeline = await _query_youtube_analytics(
        access_token,
        base_params
        | {
            "dimensions": "day",
            "sort": "day",
            "metrics": "views,likes,comments,estimatedMinutesWatched",
        },
    )

    summary_rows = _table_rows_as_dicts(summary)
    timeline_rows = _table_rows_as_dicts(timeline)
    summary_row = summary_rows[0] if summary_rows else {}

    return {
        "summary": summary_row,
        "timeline": timeline_rows,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
    }
