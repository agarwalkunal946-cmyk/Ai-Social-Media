import hashlib
import random
import re
from datetime import date, datetime, timedelta
from statistics import mean
from urllib.parse import quote_plus

import httpx

from app.core.config import get_settings
from app.db.mongo import get_database
from app.services.analysis import classify_text
from app.services.platform_preview import (
    _build_x_preview,
    _extract_tags,
    _first_sentence,
    _format_count,
    _format_date,
    _instagram_media_type,
    _instagram_profile_url,
    _refresh_saved_youtube_token,
    _safe_int,
    _short_text,
    _theme,
    _title_from_caption,
    _x_media_payload,
    _youtube_channel_url,
    _youtube_video_type,
    _youtube_video_url,
    get_connected_platform_preview,
)
from app.services.social.instagram import (
    fetch_instagram_business_discovery,
    fetch_instagram_media_insights,
)
from app.services.social.x_apify import (
    fetch_x_apify_post_detail,
    fetch_x_apify_recent_search,
    fetch_x_apify_trends,
    fetch_x_apify_user_posts,
    is_x_apify_available,
)
from app.services.social.youtube import (
    fetch_youtube_search_bundle,
    fetch_youtube_trending_bundle,
    fetch_youtube_video_analytics,
    format_youtube_duration,
)


PLATFORM_NAMES = {"instagram": "Instagram", "youtube": "YouTube", "x": "X / Twitter"}


def _empty_state(
    platform: str,
    headline: str,
    summary: str,
    *,
    search_placeholder: str,
    suggested_searches: list[str] | None = None,
    side_insights: list[dict] | None = None,
    source: str = "access-state",
) -> dict:
    return {
        "platform": platform,
        "data_source": source,
        "headline": headline,
        "summary": summary,
        "search_placeholder": search_placeholder,
        "preview_label": "Live access required",
        "trending_cards": [],
        "hero_metrics": [],
        "featured_profiles": [],
        "catalog": [],
        "preview_charts": [],
        "suggested_searches": suggested_searches or [],
        "side_insights": side_insights or [],
    }


def _format_percent(value: float) -> str:
    return f"{value:.1f}%"


def _format_seconds(value: int | float | None) -> str:
    seconds = int(float(value or 0))
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


def _engagement_rate(views: int, interactions: int) -> float:
    if views <= 0:
        return 0.0
    return (interactions / views) * 100


def _parse_x_handle(query: str) -> str:
    value = query.strip()
    if "x.com/" in value:
        value = value.split("x.com/", 1)[1]
    if "twitter.com/" in value:
        value = value.split("twitter.com/", 1)[1]
    return value.strip().strip("/").removeprefix("@").split("/")[0]


def _is_x_profile_query(query: str) -> bool:
    stripped = query.strip()
    return stripped.startswith("@") or "x.com/" in stripped or "twitter.com/" in stripped


async def _get_connection(user: dict | None, platform: str) -> dict | None:
    if not user:
        return None
    db = get_database()
    return await db.social_accounts.find_one({"user_id": user["id"], "platform": platform})


async def _get_youtube_access_token(connection: dict | None) -> str | None:
    if not connection:
        return None
    tokens = connection.get("tokens") or {}
    access_token = tokens.get("access_token")
    if access_token:
        return access_token
    if tokens.get("refresh_token"):
        return await _refresh_saved_youtube_token(connection)
    return None


def _build_youtube_catalog_item(video: dict, index: int, source: str) -> dict:
    snippet = video.get("snippet") or {}
    stats = video.get("statistics") or {}
    content_details = video.get("contentDetails") or {}
    duration_label = format_youtube_duration(content_details.get("duration"))
    title = snippet.get("title") or f"Video {index + 1}"
    description = snippet.get("description") or ""
    views = _safe_int(stats.get("viewCount"))
    likes = _safe_int(stats.get("likeCount"))
    comments = _safe_int(stats.get("commentCount"))
    published_at = snippet.get("publishedAt")
    video_id = video.get("id")
    channel_id = snippet.get("channelId")
    channel_name = snippet.get("channelTitle") or "YouTube channel"

    thumbnail = None
    for quality in ("maxres", "high", "medium", "default"):
        if quality in (snippet.get("thumbnails") or {}):
            thumbnail = snippet["thumbnails"][quality].get("url")
            break

    return {
        "id": video_id or f"youtube-{index}",
        "video_id": video_id,
        "channel_id": channel_id,
        "title": title,
        "creator": channel_name,
        "type": _youtube_video_type(duration_label),
        "duration": duration_label,
        "theme": _theme(index),
        "description": _first_sentence(description, "Video discovered from live YouTube data."),
        "thumbnail": thumbnail,
        "url": _youtube_video_url(video_id),
        "url_label": "Watch on YouTube",
        "creator_url": _youtube_channel_url(channel_id),
        "creator_label": "Open channel",
        "tags": _extract_tags(title, description, fallback=["youtube", "video", "live"]),
        "published_at": published_at,
        "metric_values": {"views": views, "likes": likes, "comments": comments},
        "analytics_source": source,
        "metrics": [
            {"label": "Views", "value": _format_count(views)},
            {"label": "Likes", "value": _format_count(likes)},
            {"label": "Comments", "value": _format_count(comments)},
        ],
        "insight": "Public YouTube metadata was fetched live from the official API.",
    }


def _build_youtube_public_payload(items: list[dict], *, title: str, summary: str, data_source: str, query: str | None = None) -> dict:
    catalog = [_build_youtube_catalog_item(item, index, data_source) for index, item in enumerate(items)]
    view_values = [_safe_int((item.get("metric_values") or {}).get("views")) for item in catalog]
    like_values = [_safe_int((item.get("metric_values") or {}).get("likes")) for item in catalog]
    comment_values = [_safe_int((item.get("metric_values") or {}).get("comments")) for item in catalog]

    creator_totals: dict[str, dict] = {}
    for item in catalog:
        channel_key = item.get("channel_id") or item.get("creator") or item.get("id")
        aggregate = creator_totals.setdefault(
            channel_key,
            {
                "name": item.get("creator") or "YouTube creator",
                "videos": 0,
                "views": 0,
                "likes": 0,
                "comments": 0,
            },
        )
        aggregate["videos"] += 1
        aggregate["views"] += _safe_int((item.get("metric_values") or {}).get("views"))
        aggregate["likes"] += _safe_int((item.get("metric_values") or {}).get("likes"))
        aggregate["comments"] += _safe_int((item.get("metric_values") or {}).get("comments"))

    featured = []
    for aggregate in sorted(creator_totals.values(), key=lambda current: current["views"], reverse=True)[:3]:
        engagement = _engagement_rate(
            aggregate["views"],
            aggregate["likes"] + aggregate["comments"],
        )
        featured.append(
            {
                "name": aggregate["name"],
                "type": "Recommended creator",
                "insight": (
                    f"{_format_count(aggregate['views'])} total views across {aggregate['videos']} surfaced videos "
                    f"with {_format_percent(engagement)} engagement."
                ),
            }
        )

    tags: list[str] = []
    for item in catalog:
        tags.extend(item.get("tags") or [])

    return {
        "platform": "youtube",
        "data_source": data_source,
        "headline": title,
        "summary": summary,
        "search_placeholder": "Search YouTube channels, creators, or video topics...",
        "preview_label": "Live YouTube data",
        "trending_cards": [
            {"name": "Results", "value": str(len(catalog)), "tone": "positive"},
            {"name": "Avg views", "value": _format_count(round(mean(view_values))) if view_values else "0", "tone": "positive"},
            {"name": "Avg comments", "value": _format_count(round(mean(comment_values))) if comment_values else "0", "tone": "neutral"},
        ],
        "hero_metrics": [
            {"label": "Mode", "value": "Search" if query else "Trending"},
            {"label": "Query", "value": query or "US most popular"},
            {"label": "Avg engagement", "value": _format_percent(_engagement_rate(sum(view_values), sum(like_values) + sum(comment_values)))},
        ],
        "featured_profiles": featured,
        "catalog": catalog,
        "preview_charts": [
            {"label": _format_date(item.get("published_at")), "value": _safe_int((item.get("metric_values") or {}).get("views"))}
            for item in catalog[:8]
        ],
        "suggested_searches": list(dict.fromkeys(tags))[:6] or ["MrBeast", "CarryMinati", "gaming", "music"],
        "side_insights": [
            {"title": "Source", "body": "Results are using the official YouTube Data API in real time."},
            {
                "title": "Analytics scope",
                "body": "Public videos expose stats like views, likes, and comments. Deeper watch-time metrics are only available for the owner channel.",
            },
        ],
    }


def _build_instagram_catalog_item(item: dict, index: int, username: str, source: str) -> dict:
    caption = item.get("caption") or ""
    likes = _safe_int(item.get("like_count"))
    comments = _safe_int(item.get("comments_count"))
    posted_at = item.get("timestamp")
    media_type = _instagram_media_type(item.get("media_type"))
    return {
        "id": item.get("id") or f"instagram-{index}",
        "title": _title_from_caption(caption, f"{media_type} update"),
        "creator": f"@{username}",
        "type": media_type,
        "media_url": item.get("media_url"),
        "duration": _format_date(posted_at),
        "theme": _theme(index),
        "description": _first_sentence(caption, "Instagram media fetched from the official Graph API."),
        "thumbnail": item.get("thumbnail_url") or item.get("media_url"),
        "url": item.get("permalink"),
        "url_label": "Open on Instagram",
        "creator_url": _instagram_profile_url(username),
        "creator_label": "Open profile",
        "tags": _extract_tags(caption, fallback=["instagram", "professional", "media"]),
        "published_at": posted_at,
        "metric_values": {"likes": likes, "comments": comments},
        "analytics_source": source,
        "metrics": [
            {"label": "Likes", "value": _format_count(likes)},
            {"label": "Comments", "value": _format_count(comments)},
        ],
        "insight": "This post was discovered through the official Instagram business discovery flow.",
    }


def _build_x_catalog_item(post: dict, index: int, source: str) -> dict:
    public_metrics = post.get("public_metrics") or {}
    likes = _safe_int(public_metrics.get("like_count") or post.get("favorite_count"))
    replies = _safe_int(public_metrics.get("reply_count") or post.get("reply_count"))
    reposts = _safe_int(public_metrics.get("retweet_count") or post.get("retweet_count"))
    quotes = _safe_int(public_metrics.get("quote_count") or post.get("quote_count"))
    views = _safe_int(public_metrics.get("view_count") or post.get("views"))
    text = post.get("text") or ""
    classified = classify_text(text)
    is_connected_source = source.startswith("x-apify") or source == "connected-apify"
    media_payload = _x_media_payload(post)

    creator_username = post.get("author_username") or post.get("author_name") or "x"
    creator_label = f"@{creator_username}" if creator_username and not str(creator_username).startswith("@") else creator_username
    return {
        "id": post.get("id") or f"x-{index}",
        "title": _title_from_caption(text, f"Post {index + 1}"),
        "creator": creator_label,
        "type": "Post",
        "duration": _format_date(post.get("created_at")),
        "theme": _theme(index),
        "description": _first_sentence(
            text,
            "X post fetched through the connected live source." if is_connected_source else "X post fetched through the live source.",
        ),
        "thumbnail": media_payload["thumbnail"],
        "media_url": media_payload["media_url"],
        "player_type": media_payload["player_type"],
        "url": f"https://x.com/{creator_username}/status/{post.get('id')}" if creator_username and post.get("id") else None,
        "url_label": "Open on X",
        "creator_url": f"https://x.com/{creator_username}" if creator_username else None,
        "creator_label": "Open profile",
        "tags": _extract_tags(text, fallback=["x", "conversation", "live"]),
        "published_at": post.get("created_at"),
        "metric_values": {"likes": likes, "replies": replies, "reposts": reposts, "quotes": quotes, "views": views},
        "analytics_source": source,
        "metrics": [
            {"label": "Views", "value": _format_count(views)},
            {"label": "Likes", "value": _format_count(likes)},
            {"label": "Replies", "value": _format_count(replies)},
            {"label": "Reposts", "value": _format_count(reposts)},
            {"label": "Mood", "value": classified["sentiment"].title()},
        ],
        "insight": (
            "These public metrics and media came from the connected X live source."
            if is_connected_source
            else "These numbers are public metrics exposed by the live X source."
        ),
    }


def _build_x_profile_payload(
    profile: dict,
    catalog: list[dict],
    query: str,
    *,
    data_source: str,
    summary: str,
    preview_label: str,
    source_body: str,
    profile_body: str,
) -> dict:
    username = profile.get("username") or _parse_x_handle(query)
    public_metrics = profile.get("public_metrics") or {}
    return {
        "platform": "x",
        "data_source": data_source,
        "headline": f'X profile search for "@{username}"',
        "summary": summary,
        "external_url": f"https://x.com/{username}" if username else None,
        "external_label": "Open profile",
        "search_placeholder": "Search @username or a keyword...",
        "preview_label": preview_label,
        "trending_cards": [
            {"name": "Followers", "value": _format_count(public_metrics.get("followers_count")), "tone": "positive"},
            {"name": "Following", "value": _format_count(public_metrics.get("following_count")), "tone": "neutral"},
            {"name": "Posts", "value": _format_count(public_metrics.get("tweet_count")), "tone": "positive"},
        ],
        "hero_metrics": [
            {"label": "Profile", "value": f"@{username}"},
            {"label": "Verified", "value": "Yes" if profile.get("verified") else "No"},
            {"label": "Recent posts loaded", "value": str(len(catalog))},
        ],
        "featured_profiles": [
            {
                "name": f"@{username}",
                "type": "Profile",
                "insight": _first_sentence(profile.get("description"), profile_body),
            }
        ],
        "catalog": catalog,
        "preview_charts": [
            {"label": _format_date(item.get("published_at")), "value": _safe_int((item.get("metric_values") or {}).get("likes"))}
            for item in catalog[:8]
        ],
        "suggested_searches": list(dict.fromkeys(tag for item in catalog for tag in item.get("tags") or []))[:6] or ["community", "launch", "thread"],
        "side_insights": [
            {"title": "Source", "body": source_body},
            {
                "title": "History window",
                "body": "This view covers recent public posts and profile metrics, not private owner-only analytics.",
            },
        ],
    }


def _build_x_search_payload(
    catalog: list[dict],
    query: str,
    *,
    data_source: str,
    summary: str,
    preview_label: str,
    source_body: str,
    window_label: str,
) -> dict:
    return {
        "platform": "x",
        "data_source": data_source,
        "headline": f'X recent search for "{query}"',
        "summary": summary,
        "search_placeholder": "Search @username or a keyword...",
        "preview_label": preview_label,
        "trending_cards": [
            {"name": "Results", "value": str(len(catalog)), "tone": "positive"},
            {
                "name": "Avg likes",
                "value": _format_count(round(mean(_safe_int((item.get("metric_values") or {}).get("likes")) for item in catalog))) if catalog else "0",
                "tone": "neutral",
            },
            {
                "name": "Avg replies",
                "value": _format_count(round(mean(_safe_int((item.get("metric_values") or {}).get("replies")) for item in catalog))) if catalog else "0",
                "tone": "neutral",
            },
        ],
        "hero_metrics": [
            {"label": "Query", "value": query},
            {"label": "Window", "value": window_label},
            {"label": "Loaded posts", "value": str(len(catalog))},
        ],
        "featured_profiles": [
            {
                "name": item.get("creator") or "Public post",
                "type": "Post",
                "insight": item.get("insight"),
            }
            for item in catalog[:3]
        ],
        "catalog": catalog,
        "preview_charts": [
            {"label": _format_date(item.get("published_at")), "value": _safe_int((item.get("metric_values") or {}).get("likes"))}
            for item in catalog[:8]
        ],
        "suggested_searches": list(dict.fromkeys(tag for item in catalog for tag in item.get("tags") or []))[:6] or ["AI", "launch", "community"],
        "side_insights": [
            {"title": "Source", "body": source_body},
            {
                "title": "History window",
                "body": "This search focuses on recent public posts rather than a guaranteed full historical archive.",
            },
        ],
    }


def _build_x_trending_payload(
    trends: list[dict],
    *,
    headline: str = "X live trend stream",
    data_source: str = "x-apify-trending",
    source_label: str = "Live X source",
    preview_label: str = "Live public trends",
    summary: str = "Trending topics gathered through the configured live X source.",
    source_body: str = "These topics come from the live X source rather than saved demo content.",
    analytics_source: str = "x-apify-trends",
    item_insight: str = "This trend was fetched from the live X source.",
) -> dict:
    catalog = []
    categories = []
    with_volume = 0
    for index, trend in enumerate(trends):
        name = trend.get("name") or f"Trend {index + 1}"
        description = trend.get("description") or ""
        post_count = _safe_int(trend.get("post_count"))
        category = (trend.get("category") or "trend").title()
        categories.append(category)
        if post_count:
            with_volume += 1
        catalog.append(
            {
                "id": trend.get("id") or f"x-trend-{index}",
                "title": name,
                "creator": "X trend stream",
                "type": "Trend",
                "duration": category,
                "theme": _theme(index),
                "description": _first_sentence(description, "Trending topic gathered through the live X source."),
                "thumbnail": None,
                "url": trend.get("url") or f"https://x.com/search?q={quote_plus(name)}&src=typed_query",
                "url_label": "Open on X",
                "creator_url": None,
                "creator_label": None,
                "tags": _extract_tags(name, description, fallback=["x", "trend", "live"]),
                "published_at": None,
                "metric_values": {"mentions": post_count},
                "analytics_source": analytics_source,
                "metrics": [
                    {"label": "Mentions", "value": _format_count(post_count)},
                    {"label": "Category", "value": category},
                ],
                "insight": item_insight,
            }
        )

    category_count = len({item for item in categories if item})
    suggested = list(dict.fromkeys(tag for item in catalog for tag in item.get("tags") or []))[:6] or ["AI", "gaming", "launch"]
    return {
        "platform": "x",
        "data_source": data_source,
        "headline": headline,
        "summary": summary,
        "search_placeholder": "Search @username or a keyword...",
        "preview_label": preview_label,
        "trending_cards": [
            {"name": "Topics", "value": str(len(catalog)), "tone": "positive"},
            {"name": "With volume", "value": str(with_volume), "tone": "neutral"},
            {"name": "Categories", "value": str(category_count), "tone": "positive"},
        ],
        "hero_metrics": [
            {"label": "Mode", "value": "Trending"},
            {"label": "Source", "value": source_label},
            {"label": "Loaded topics", "value": str(len(catalog))},
        ],
        "featured_profiles": [
            {
                "name": item.get("title") or "Trend",
                "type": "Trend",
                "insight": item.get("description") or "Public trend topic captured from the live X stream.",
            }
            for item in catalog[:3]
        ],
        "catalog": catalog,
        "preview_charts": [],
        "suggested_searches": suggested,
        "side_insights": [
            {"title": "Source", "body": source_body},
            {
                "title": "What this means",
                "body": "You can still inspect public topics and open them on X even when full private account analytics are not part of this feed.",
            },
        ],
    }


async def get_public_platform_payload(
    platform: str,
    user: dict | None,
    *,
    mode: str | None = None,
    query: str | None = None,
) -> dict:
    normalized_mode = (mode or "").strip().lower()
    normalized_query = (query or "").strip()
    if not normalized_mode:
        normalized_mode = "search" if normalized_query else "connected"

    connection = await _get_connection(user, platform)

    if platform == "youtube":
        if normalized_mode == "connected" and connection:
            return await get_connected_platform_preview(platform, user)

        if normalized_mode == "search" and not normalized_query:
            return _empty_state(
                "youtube",
                "Search YouTube videos and channels",
                "Type a creator name, topic, or channel keyword to fetch live YouTube results.",
                search_placeholder="Search YouTube creators like MrBeast...",
                suggested_searches=["MrBeast", "CarryMinati", "gaming", "shorts"],
                source="search-ready",
            )

        access_token = await _get_youtube_access_token(connection)
        if not access_token:
            return _empty_state(
                "youtube",
                "Connect YouTube to search live videos",
                "Official YouTube search and trending results need an authenticated YouTube connection in this app.",
                search_placeholder="Connect YouTube, then search creators like MrBeast...",
                suggested_searches=["MrBeast", "CarryMinati", "gaming", "shorts"],
                side_insights=[
                    {"title": "Why connect first", "body": "This build uses OAuth-based YouTube API access rather than demo content."},
                ],
            )

        if normalized_mode == "trending" and not normalized_query:
            try:
                bundle = await fetch_youtube_trending_bundle(access_token, limit=100)
            except httpx.HTTPError:
                return _empty_state(
                    "youtube",
                    "YouTube trending could not be refreshed",
                    "The official API request failed just now. Reconnect the provider or try again shortly.",
                    search_placeholder="Search YouTube creators like MrBeast...",
                    suggested_searches=["MrBeast", "CarryMinati", "gaming", "shorts"],
                )
            return _build_youtube_public_payload(
                bundle.get("items") or [],
                title="YouTube live trending view",
                summary="Current most-popular YouTube videos fetched live from the official API.",
                data_source="youtube-trending",
            )

        try:
            bundle = await fetch_youtube_search_bundle(access_token, normalized_query, limit=100)
        except httpx.HTTPError:
            return _empty_state(
                "youtube",
                "YouTube search could not be refreshed",
                "The official API request failed just now. Reconnect the provider or try again shortly.",
                search_placeholder="Search YouTube creators like MrBeast...",
                suggested_searches=["MrBeast", "CarryMinati", "gaming", "shorts"],
            )
        return _build_youtube_public_payload(
            bundle.get("items") or [],
            title=f'YouTube search for "{normalized_query}"',
            summary="Search results are coming from the official YouTube Data API.",
            data_source="youtube-search",
            query=normalized_query,
        )

    if platform == "instagram":
        if normalized_mode == "connected" and connection:
            return await get_connected_platform_preview(platform, user)

        if normalized_mode == "search" and not normalized_query:
            return _empty_state(
                "instagram",
                "Search an Instagram professional username",
                "Type a public business or creator handle to fetch profile and media through Meta business discovery.",
                search_placeholder="Search a professional Instagram username...",
                suggested_searches=["cristiano", "nike", "natgeo"],
                source="search-ready",
            )

        if not connection:
            return _empty_state(
                "instagram",
                "Connect Instagram to search professional profiles",
                "Meta's official API only lets this app discover public professional accounts through a connected Instagram business or creator account.",
                search_placeholder="Connect Instagram, then search a public professional username...",
                suggested_searches=["cristiano", "zara", "natgeo"],
                side_insights=[
                    {
                        "title": "Official limitation",
                        "body": "Instagram Graph API does not expose open public search or global trending for arbitrary accounts in this app context.",
                    }
                ],
            )

        if normalized_mode == "trending" and not normalized_query:
            return _empty_state(
                "instagram",
                "Search Instagram creator profiles",
                "Use a professional username to explore a public creator or brand profile with live Instagram data.",
                search_placeholder="Search a professional Instagram username...",
                suggested_searches=["cristiano", "nike", "natgeo"],
                side_insights=[
                    {
                        "title": "Best way to explore",
                        "body": "Search public business or creator usernames to load profile metrics and recent media directly.",
                    }
                ],
                source="search-ready",
            )

        instagram_account = ((connection.get("extra") or {}).get("instagram") or {})
        instagram_user_id = instagram_account.get("id")
        access_token = (connection.get("tokens") or {}).get("access_token")
        if not instagram_user_id or not access_token:
            return _empty_state(
                "instagram",
                "Reconnect Instagram to enable public profile discovery",
                "The existing Instagram connection does not currently have enough live access data to run public profile discovery.",
                search_placeholder="Reconnect Instagram, then search a professional username...",
                suggested_searches=["cristiano", "natgeo", "netflix"],
            )

        try:
            discovery = await fetch_instagram_business_discovery(access_token, instagram_user_id, normalized_query, limit=100)
        except httpx.HTTPError:
            return _empty_state(
                "instagram",
                "Instagram profile discovery could not be loaded",
                "The requested profile may not be a public professional account, or Meta rejected the lookup.",
                search_placeholder="Search a professional Instagram username...",
                suggested_searches=["cristiano", "nike", "natgeo"],
                source="limitation",
            )
        username = discovery.get("username") or normalized_query.removeprefix("@")
        media = discovery.get("media") or []
        catalog = [_build_instagram_catalog_item(item, index, username, "business-discovery") for index, item in enumerate(media)]
        like_values = [_safe_int((item.get("metric_values") or {}).get("likes")) for item in catalog]
        comment_values = [_safe_int((item.get("metric_values") or {}).get("comments")) for item in catalog]
        followers = _safe_int(discovery.get("followers_count"))
        posts = _safe_int(discovery.get("media_count"))

        return {
            "platform": "instagram",
            "data_source": "business-discovery",
            "headline": f'Instagram profile search for "@{username}"',
            "summary": "Professional-account profile and media data fetched through the official Instagram Graph API business discovery flow.",
            "external_url": _instagram_profile_url(username),
            "external_label": "Open profile",
            "search_placeholder": "Search a professional Instagram username...",
            "preview_label": "Professional account search",
            "trending_cards": [
                {"name": "Followers", "value": _format_count(followers), "tone": "positive"},
                {"name": "Posts", "value": _format_count(posts), "tone": "positive"},
                {"name": "Avg likes", "value": _format_count(round(mean(like_values))) if like_values else "0", "tone": "neutral"},
            ],
            "hero_metrics": [
                {"label": "Profile", "value": f"@{username}"},
                {"label": "Following", "value": _format_count(_safe_int(discovery.get("follows_count")))},
                {"label": "Latest media seen", "value": _format_date((media[0] or {}).get("timestamp")) if media else "n/a"},
            ],
            "featured_profiles": [
                {
                    "name": f"@{username}",
                    "type": "Professional",
                    "insight": _first_sentence(discovery.get("biography"), "Profile discovered through Meta business discovery."),
                }
            ],
            "catalog": catalog,
            "preview_charts": [
                {"label": _format_date(item.get("published_at")), "value": _safe_int((item.get("metric_values") or {}).get("likes"))}
                for item in catalog[:8]
            ],
            "suggested_searches": list(dict.fromkeys(tag for item in catalog for tag in item.get("tags") or []))[:6] or ["reels", "fashion", "creator"],
            "side_insights": [
                {"title": "Source", "body": "These results come from Meta's official Instagram business discovery API."},
                {
                    "title": "Analytics scope",
                    "body": "Public profile search exposes public media stats like likes and comments. Private insights such as reach are only available for connected owned media.",
                },
            ],
        }

    if platform == "x":
        if normalized_mode == "connected" and connection:
            return _build_x_preview(connection)

        if not is_x_apify_available():
            if connection:
                return _build_x_preview(connection)
            return _empty_state(
                "x",
                "Connect X / Twitter to continue",
                "This build uses a live X source for public search, trends, and connected-handle timeline reads.",
                search_placeholder="Search an X handle or a keyword...",
                suggested_searches=["@AlwaysRamCharan", "@Cristiano", "@MrBeast"],
            )

        if normalized_mode == "trending" and not normalized_query:
            try:
                trends_payload = await fetch_x_apify_trends(limit=30)
            except httpx.HTTPError:
                return _empty_state(
                    "x",
                    "X trending could not be refreshed",
                    "The live X source could not return current trending topics right now. Try again shortly.",
                    search_placeholder="Search an X handle or a keyword...",
                    suggested_searches=["@AlwaysRamCharan", "@Cristiano", "@MrBeast"],
                )
            return _build_x_trending_payload(
                trends_payload.get("items") or [],
                headline="Trending on X / Twitter",
                data_source="x-apify-trending",
                source_label="Live X source",
                preview_label="Live public trends",
                summary="Trending topics fetched through the configured live X source.",
                source_body="These topics come from the live X source rather than saved demo content.",
                analytics_source="x-apify-trends",
                item_insight="This trend was fetched from the live X source.",
            )

        if _is_x_profile_query(normalized_query):
            lookup_handle = _parse_x_handle(normalized_query)
            try:
                posts_payload = await fetch_x_apify_user_posts(lookup_handle, limit=48)
            except httpx.HTTPError:
                return _empty_state(
                    "x",
                    f'X profile search for "@{lookup_handle}" could not be loaded',
                    "The live X source could not refresh that public X profile right now.",
                    search_placeholder="Search an X handle or a keyword...",
                    suggested_searches=["@AlwaysRamCharan", "@Cristiano", "@MrBeast"],
                )
            profile = posts_payload.get("profile") or {"username": lookup_handle, "name": f"@{lookup_handle}", "public_metrics": {}}
            catalog = [
                _build_x_catalog_item(item, index, "x-apify-user-timeline")
                for index, item in enumerate(posts_payload.get("items") or [])
            ]
            return _build_x_profile_payload(
                profile,
                catalog,
                normalized_query,
                data_source="x-apify-user-timeline",
                summary="Recent public posts fetched through the connected live X source.",
                preview_label="Live X profile",
                source_body="Results come from the live X timeline mode.",
                profile_body="Profile data was fetched through the live X source.",
            )

        if normalized_mode == "search" and not normalized_query:
            return _empty_state(
                "x",
                "Search X / Twitter",
                "Type a keyword or @username to fetch live public X results.",
                search_placeholder="Search an X handle or a keyword...",
                suggested_searches=["@AlwaysRamCharan", "@Cristiano", "@MrBeast", "football"],
                source="search-ready",
            )

        try:
            search_payload = await fetch_x_apify_recent_search(normalized_query, limit=48)
        except httpx.HTTPError:
            return _empty_state(
                "x",
                "X search could not be refreshed",
                "The live X source could not return public search results right now. Try again shortly.",
                search_placeholder="Search an X handle or a keyword...",
                suggested_searches=["@AlwaysRamCharan", "@Cristiano", "@MrBeast"],
            )
        catalog = [
            _build_x_catalog_item(item, index, "x-apify-search")
            for index, item in enumerate(search_payload.get("items") or [])
        ]
        return _build_x_search_payload(
            catalog,
            normalized_query,
            data_source="x-apify-search",
            summary="Recent public posts fetched through the live X source.",
            preview_label="Live public posts",
            source_body="Results come from the live X search mode.",
            window_label="Public search",
        )

    return _empty_state(
        platform,
        f"{PLATFORM_NAMES.get(platform, platform.title())} data is unavailable",
        "The requested platform is not configured in this build.",
        search_placeholder="Unsupported platform",
    )


async def get_platform_item_analytics(
    platform: str,
    user: dict | None,
    item: dict,
    *,
    mode: str | None = None,
) -> dict:
    metric_values = item.get("metric_values") or {}

    if platform == "youtube":
        cards = [
            {"label": "Views", "value": _format_count(metric_values.get("views"))},
            {"label": "Likes", "value": _format_count(metric_values.get("likes"))},
            {"label": "Comments", "value": _format_count(metric_values.get("comments"))},
            {
                "label": "Engagement",
                "value": _format_percent(
                    _engagement_rate(
                        _safe_int(metric_values.get("views")),
                        _safe_int(metric_values.get("likes")) + _safe_int(metric_values.get("comments")),
                    )
                ),
            },
        ]
        chart = []
        insights = ["Public YouTube stats were available for this video."]

        if item.get("analytics_source") == "connected":
            connection = await _get_connection(user, "youtube")
            access_token = await _get_youtube_access_token(connection)
            if access_token and item.get("video_id"):
                try:
                    analytics = await fetch_youtube_video_analytics(access_token, item["video_id"])
                    summary = analytics.get("summary") or {}
                    chart = [
                        {"label": row.get("day", "Day"), "value": _safe_int(row.get("views"))}
                        for row in analytics.get("timeline") or []
                    ]
                    cards.extend(
                        [
                            {"label": "Watch time", "value": _format_count(summary.get("estimatedMinutesWatched")) + " min"},
                            {"label": "Avg duration", "value": _format_seconds(summary.get("averageViewDuration"))},
                            {
                                "label": "Avg viewed",
                                "value": _format_percent(float(summary.get("averageViewPercentage") or 0)),
                            },
                        ]
                    )
                    insights = [
                        "This panel includes owner-only YouTube Analytics API data for your connected channel video.",
                        f"Subscribers gained in range: {_format_count(summary.get('subscribersGained'))}.",
                    ]
                except httpx.HTTPError:
                    insights.append("Deep owner-only YouTube analytics could not be refreshed right now, so public stats are shown.")
        else:
            insights.append("Watch-time and retention metrics are only available when the video belongs to your connected channel.")

        return {
            "title": item.get("title") or "YouTube video analytics",
            "summary": item.get("description") or "Video analytics summary",
            "cards": cards,
            "chart": chart,
            "insights": insights,
            "external_url": item.get("url"),
        }

    if platform == "instagram":
        cards = [
            {"label": "Likes", "value": _format_count(metric_values.get("likes"))},
            {"label": "Comments", "value": _format_count(metric_values.get("comments"))},
        ]
        chart = []
        insights = ["Public Instagram metrics were available for this media item."]

        if item.get("analytics_source") == "connected":
            connection = await _get_connection(user, "instagram")
            access_token = (connection.get("tokens") or {}).get("access_token") if connection else None
            if access_token and item.get("id"):
                extra_insights = await fetch_instagram_media_insights(access_token, item["id"], media_type=item.get("type"))
                for key in ("reach", "views", "engagement", "saved", "shares", "total_interactions"):
                    if key in extra_insights:
                        cards.append({"label": key.replace("_", " ").title(), "value": _format_count(extra_insights[key])})
                insights = [
                    "This panel includes owner-only Instagram media insights from your connected account.",
                    "Public-discovery profiles do not expose private reach or view metrics for third-party accounts.",
                ]
        else:
            insights.append("Private Instagram insights like reach and views are only available for connected owned media.")

        return {
            "title": item.get("title") or "Instagram media analytics",
            "summary": item.get("description") or "Instagram media analytics summary",
            "cards": cards,
            "chart": chart,
            "insights": insights,
            "external_url": item.get("url"),
        }

    if platform == "x":
        if item.get("type") == "Profile":
            cards = [
                {"label": "Followers", "value": _format_count(metric_values.get("followers"))},
                {"label": "Following", "value": _format_count(metric_values.get("following"))},
                {"label": "Posts", "value": _format_count(metric_values.get("posts"))},
            ]
            return {
                "title": item.get("title") or "X profile snapshot",
                "summary": item.get("description") or "Connected X public profile snapshot",
                "cards": cards,
                "chart": [],
                "insights": [
                    "This profile snapshot comes from the connected live X response.",
                    "Profile-level public counts are shown here, while post-by-post analytics appear on timeline cards.",
                ],
                "external_url": item.get("url"),
            }

        if item.get("type") == "Trend":
            cards = [{"label": "Category", "value": item.get("duration") or "Trend"}]
            trend_title = item.get("title") or ""
            if (item.get("analytics_source") or "").startswith("x-apify"):
                try:
                    trend_posts = await fetch_x_apify_recent_search(trend_title, limit=8)
                except httpx.HTTPError:
                    trend_posts = {"items": []}
                items = trend_posts.get("items") or []
                if items:
                    total_likes = sum(_safe_int((post.get("public_metrics") or {}).get("like_count")) for post in items)
                    total_replies = sum(_safe_int((post.get("public_metrics") or {}).get("reply_count")) for post in items)
                    cards = [
                        {"label": "Sample posts", "value": str(len(items))},
                        {"label": "Likes", "value": _format_count(total_likes)},
                        {"label": "Replies", "value": _format_count(total_replies)},
                    ]
            return {
                "title": item.get("title") or "X trend analytics",
                "summary": item.get("description") or "X trend summary",
                "cards": cards,
                "chart": [],
                "insights": [
                    "This topic was fetched from the live X source.",
                    "Open the topic on X for the live conversation stream.",
                ],
                "external_url": item.get("url"),
            }

        cards = [
            {"label": "Likes", "value": _format_count(metric_values.get("likes"))},
            {"label": "Replies", "value": _format_count(metric_values.get("replies"))},
            {"label": "Reposts", "value": _format_count(metric_values.get("reposts") or metric_values.get("retweets"))},
        ]
        chart = []
        text_body = item.get("description") or item.get("title") or ""
        classified = classify_text(text_body)
        insights = [
            f"Detected mood: {classified['sentiment'].title()}",
            f"Toxicity hint: {round(classified['toxicity'] * 100)}%",
        ]

        if item.get("analytics_source") in {"x-apify-search", "x-apify-user-timeline", "connected-apify"} and item.get("id"):
            try:
                detail = await fetch_x_apify_post_detail(item["id"])
                public_metrics = detail.get("public_metrics") or {}
                cards = [
                    {"label": "Views", "value": _format_count(public_metrics.get("view_count"))},
                    {"label": "Likes", "value": _format_count(public_metrics.get("like_count"))},
                    {"label": "Replies", "value": _format_count(public_metrics.get("reply_count"))},
                    {"label": "Reposts", "value": _format_count(public_metrics.get("retweet_count"))},
                    {"label": "Quotes", "value": _format_count(public_metrics.get("quote_count"))},
                ]
                insights.insert(0, "Metrics were refreshed from the live X post lookup.")
            except httpx.HTTPError:
                insights.insert(0, "Latest public post metrics could not be refreshed, so cached values are shown.")

        return {
            "title": item.get("title") or "X post analytics",
            "summary": item.get("description") or "X post analytics summary",
            "cards": cards,
            "chart": chart,
            "insights": insights,
            "external_url": item.get("url"),
        }

    return {
        "title": "Analytics unavailable",
        "summary": "Unsupported platform",
        "cards": [],
        "chart": [],
        "insights": [],
        "external_url": None,
    }
