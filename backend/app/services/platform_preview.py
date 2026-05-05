from collections import Counter
from datetime import datetime

import httpx

from app.core.config import get_settings
from app.db.mongo import get_database
from app.db.redis_client import delete_key, get_json, set_json
from app.services.analysis import classify_text
from app.services.social.instagram import fetch_instagram_media_bundle
from app.services.social.youtube import (
    fetch_youtube_video_bundle,
    format_youtube_duration,
    refresh_youtube_token,
)


THEMES = ("sunset", "ocean", "mint", "violet")
PLATFORM_DISPLAY = {
    "instagram": "Instagram",
    "youtube": "YouTube",
    "x": "X / Twitter",
}
PREVIEW_CACHE_PREFIX = "platform-preview:v1"


def _safe_int(value) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _format_count(value) -> str:
    number = _safe_int(value)
    if number >= 1_000_000:
        return f"{number / 1_000_000:.1f}M"
    if number >= 1_000:
        return f"{number / 1_000:.1f}K"
    return str(number)


def _theme(index: int) -> str:
    return THEMES[index % len(THEMES)]


def _preview_cache_key(user_id: str, platform: str) -> str:
    return f"{PREVIEW_CACHE_PREFIX}:{user_id}:{platform}"


def _short_text(text: str | None, limit: int = 88) -> str:
    cleaned = (text or "").replace("\n", " ").strip()
    if not cleaned:
        return ""
    if len(cleaned) <= limit:
        return cleaned
    return f"{cleaned[: limit - 3].rstrip()}..."


def _title_from_caption(text: str | None, fallback: str) -> str:
    cleaned = _short_text(text, 64)
    return cleaned or fallback


def _first_sentence(text: str | None, fallback: str) -> str:
    cleaned = (text or "").replace("\n", " ").strip()
    if not cleaned:
        return fallback
    if "." in cleaned:
        return _short_text(cleaned.split(".", 1)[0], 120)
    return _short_text(cleaned, 120)


def _extract_tags(*texts: str, fallback: list[str] | None = None) -> list[str]:
    hashtags: list[str] = []
    words: list[str] = []
    for raw_text in texts:
        text = (raw_text or "").replace("\n", " ")
        for token in text.split():
            lowered = token.strip(".,!?()[]{}:;\"'").lower()
            if not lowered:
                continue
            if lowered.startswith("#") and len(lowered) > 1:
                tag = lowered[1:]
                if tag not in hashtags:
                    hashtags.append(tag)
                continue
            if len(lowered) >= 4 and lowered.isascii():
                words.append(lowered)

    if hashtags:
        return hashtags[:4]

    counted = Counter(words)
    if counted:
        return [item for item, _ in counted.most_common(4)]

    return (fallback or ["connected", "live", "account"])[:4]


def _format_date(value: str | None) -> str:
    if not value:
        return "Recent"
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
        return parsed.strftime("%b %d")
    except ValueError:
        try:
            parsed = datetime.strptime(value, "%a %b %d %H:%M:%S %z %Y")
            return parsed.strftime("%b %d")
        except ValueError:
            return "Recent"


def _x_media_payload(post: dict) -> dict:
    media_items = post.get("media") or []
    if isinstance(media_items, dict):
        flattened = []
        for values in media_items.values():
            if isinstance(values, list):
                flattened.extend(values)
        media_items = flattened

    thumbnail = None
    media_url = None
    player_type = None
    for item in media_items:
        if not isinstance(item, dict):
            continue
        media_type = str(item.get("type") or "").lower()
        preview = item.get("preview_image_url") or item.get("media_url_https") or item.get("url")
        if not thumbnail and preview:
            thumbnail = preview
        if media_type in {"video", "animated_gif"}:
            media_url = item.get("url") or media_url
            player_type = "x-video"
            if thumbnail:
                break
        elif media_type == "photo" and not media_url:
            media_url = item.get("url") or preview
            player_type = "x-photo"

    return {"thumbnail": thumbnail, "media_url": media_url, "player_type": player_type}


def _youtube_video_type(duration_label: str) -> str:
    if duration_label.startswith("0:") or duration_label == "1:00":
        return "Short"
    return "Video"


def _instagram_media_type(media_type: str | None) -> str:
    mapping = {
        "VIDEO": "Reel",
        "CAROUSEL_ALBUM": "Carousel",
        "IMAGE": "Post",
    }
    return mapping.get((media_type or "").upper(), "Post")


def _youtube_channel_url(channel_id: str | None) -> str | None:
    if not channel_id:
        return None
    return f"https://www.youtube.com/channel/{channel_id}"


def _youtube_video_url(video_id: str | None) -> str | None:
    if not video_id:
        return None
    return f"https://www.youtube.com/watch?v={video_id}"


def _instagram_profile_url(username: str | None) -> str | None:
    if not username:
        return None
    return f"https://www.instagram.com/{username.removeprefix('@')}/"


async def _refresh_saved_youtube_token(connection: dict) -> str | None:
    refresh_token = (connection.get("tokens") or {}).get("refresh_token")
    if not refresh_token:
        return (connection.get("tokens") or {}).get("access_token")

    refreshed = await refresh_youtube_token(refresh_token)
    updated_tokens = (connection.get("tokens") or {}) | refreshed
    connection["tokens"] = updated_tokens
    db = get_database()
    await db.social_accounts.update_one({"_id": connection["_id"]}, {"$set": {"tokens": updated_tokens}})
    return updated_tokens.get("access_token")


async def _load_youtube_bundle(connection: dict) -> dict | None:
    access_token = (connection.get("tokens") or {}).get("access_token")
    if not access_token and (connection.get("tokens") or {}).get("refresh_token"):
        access_token = await _refresh_saved_youtube_token(connection)
    if not access_token:
        return None

    try:
        return await fetch_youtube_video_bundle(access_token, limit=100)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 401 and (connection.get("tokens") or {}).get("refresh_token"):
            access_token = await _refresh_saved_youtube_token(connection)
            if access_token:
                return await fetch_youtube_video_bundle(access_token, limit=100)
        raise


def _build_youtube_fallback(connection: dict) -> dict:
    statistics = ((connection.get("extra") or {}).get("statistics") or {})
    channel_name = connection.get("account_name") or "Connected YouTube channel"
    channel_url = _youtube_channel_url(((connection.get("extra") or {}).get("channel_id")))
    return {
        "platform": "youtube",
        "data_source": "connected",
        "headline": f"{channel_name} connected view",
        "summary": "Showing the connected YouTube account summary saved at the last successful connect.",
        "external_url": channel_url,
        "external_label": "Open channel",
        "search_placeholder": "Search your connected channel summary...",
        "preview_label": "Connected channel snapshot",
        "trending_cards": [
            {"name": "Subscribers", "value": _format_count(statistics.get("subscriberCount")), "tone": "positive"},
            {"name": "Channel views", "value": _format_count(statistics.get("viewCount")), "tone": "positive"},
            {"name": "Videos", "value": _format_count(statistics.get("videoCount")), "tone": "neutral"},
        ],
        "hero_metrics": [
            {"label": "Connected account", "value": channel_name},
            {"label": "Status", "value": "Connected successfully"},
            {"label": "Refresh", "value": "Reconnect if live video sync expires"},
        ],
        "featured_profiles": [
            {"name": channel_name, "type": "Channel", "insight": "Live catalog could not be refreshed, so the saved channel snapshot is shown."}
        ],
        "catalog": [
            {
                "id": f"{connection['_id']}-channel",
                "title": channel_name,
                "creator": channel_name,
                "type": "Channel",
                "duration": "Saved",
                "theme": "ocean",
                "description": "Your YouTube channel is connected. Reopen the connection if you want the latest upload list refreshed.",
                "url": channel_url,
                "url_label": "Open channel",
                "tags": ["youtube", "connected", "channel"],
                "metrics": [
                    {"label": "Subscribers", "value": _format_count(statistics.get("subscriberCount"))},
                    {"label": "Views", "value": _format_count(statistics.get("viewCount"))},
                    {"label": "Videos", "value": _format_count(statistics.get("videoCount"))},
                ],
                "insight": "The connection exists, but recent upload cards were not available from the provider response.",
            }
        ],
        "preview_charts": [
            {"label": "Subscribers", "value": _safe_int(statistics.get("subscriberCount"))},
            {"label": "Views", "value": _safe_int(statistics.get("viewCount"))},
            {"label": "Videos", "value": _safe_int(statistics.get("videoCount"))},
        ],
        "suggested_searches": ["latest upload", "comments", "watch time"],
        "side_insights": [
            {"title": "Source", "body": "This is your connected YouTube account snapshot, not public demo data."},
            {"title": "If this looks stale", "body": "Reconnect the channel once so the app can refresh live upload details again."},
        ],
    }


def _build_instagram_fallback(connection: dict) -> dict:
    instagram_account = ((connection.get("extra") or {}).get("instagram") or {})
    page = ((connection.get("extra") or {}).get("page") or {})
    username = instagram_account.get("username") or connection.get("account_name") or "Connected Instagram"
    followers = instagram_account.get("followers_count")
    profile_url = _instagram_profile_url(username)
    return {
        "platform": "instagram",
        "data_source": "connected",
        "headline": f"@{username} connected view",
        "summary": "Showing the connected Instagram profile summary saved at the last successful connect.",
        "external_url": profile_url,
        "external_label": "Open profile",
        "search_placeholder": "Search your connected profile summary...",
        "preview_label": "Connected profile snapshot",
        "trending_cards": [
            {"name": "Followers", "value": _format_count(followers), "tone": "positive"},
            {"name": "Profile", "value": f"@{username}", "tone": "positive"},
            {"name": "Page", "value": page.get("name") or "Connected", "tone": "neutral"},
        ],
        "hero_metrics": [
            {"label": "Connected handle", "value": f"@{username}"},
            {"label": "Followers", "value": _format_count(followers)},
            {"label": "Refresh", "value": "Reconnect if live media sync expires"},
        ],
        "featured_profiles": [
            {"name": f"@{username}", "type": "Profile", "insight": "Live media cards were not available, so the saved profile snapshot is shown."}
        ],
        "catalog": [
            {
                "id": f"{connection['_id']}-profile",
                "title": f"@{username}",
                "creator": username,
                "type": "Profile",
                "duration": "Saved",
                "theme": "sunset",
                "description": "Your Instagram business account is connected. Reconnect if you want fresh media cards to populate here.",
                "url": profile_url,
                "url_label": "Open profile",
                "tags": ["instagram", "connected", "profile"],
                "metrics": [
                    {"label": "Followers", "value": _format_count(followers)},
                    {"label": "Username", "value": f"@{username}"},
                ],
                "insight": "The account connection is fine, but recent Instagram media details were not available from the provider response.",
            }
        ],
        "preview_charts": [{"label": "Followers", "value": _safe_int(followers)}],
        "suggested_searches": ["reels", "carousel", "latest post"],
        "side_insights": [
            {"title": "Source", "body": "This is your connected Instagram account snapshot, not public demo data."},
            {"title": "If this looks stale", "body": "Reconnect Instagram once so the app can refresh live media details again."},
        ],
    }


async def _build_youtube_preview(connection: dict) -> dict:
    bundle = await _load_youtube_bundle(connection)
    if not bundle:
        return _build_youtube_fallback(connection)

    channel = bundle.get("channel") or {}
    profile = bundle.get("profile") or {}
    videos = bundle.get("videos") or []
    snippet = channel.get("snippet") or {}
    statistics = channel.get("statistics") or {}
    channel_name = snippet.get("title") or connection.get("account_name") or "Connected YouTube channel"
    channel_url = _youtube_channel_url(channel.get("id") or ((connection.get("extra") or {}).get("channel_id")))

    catalog = []
    chart_rows = []
    highlighted = []
    for index, video in enumerate(videos):
        video_snippet = video.get("snippet") or {}
        video_stats = video.get("statistics") or {}
        duration_label = format_youtube_duration((video.get("contentDetails") or {}).get("duration"))
        title = video_snippet.get("title") or f"Video {index + 1}"
        description = video_snippet.get("description") or ""
        views = _safe_int(video_stats.get("viewCount"))
        likes = _safe_int(video_stats.get("likeCount"))
        comments = _safe_int(video_stats.get("commentCount"))
        published_at = video_snippet.get("publishedAt")
        video_id = video.get("id")

        thumbnail_url = None
        thumbnails = video_snippet.get("thumbnails") or {}
        for quality in ("maxres", "high", "medium", "default"):
            if quality in thumbnails:
                thumbnail_url = thumbnails[quality].get("url")
                break

        catalog.append(
            {
                "id": video_id or f"yt-{index}",
                "video_id": video_id,
                "title": title,
                "creator": channel_name,
                "type": _youtube_video_type(duration_label),
                "duration": duration_label,
                "theme": _theme(index),
                "description": _first_sentence(description, "Recent upload from your connected YouTube channel."),
                "thumbnail": thumbnail_url,
                "url": _youtube_video_url(video_id),
                "url_label": "Watch on YouTube",
                "creator_url": channel_url,
                "creator_label": "Open channel",
                "tags": _extract_tags(title, description, fallback=["youtube", "upload", "video"]),
                "published_at": published_at,
                "metric_values": {
                    "views": views,
                    "likes": likes,
                    "comments": comments,
                },
                "analytics_source": "connected",
                "metrics": [
                    {"label": "Views", "value": _format_count(views)},
                    {"label": "Likes", "value": _format_count(likes)},
                    {"label": "Comments", "value": _format_count(comments)},
                ],
                "insight": "Live channel video metrics pulled from your connected YouTube account.",
            }
        )
        chart_rows.append({"label": _format_date(published_at), "value": views})
        highlighted.append(
            {
                "name": _short_text(title, 36),
                "type": "Video",
                "insight": f"{_format_count(views)} views and {_format_count(comments)} comments in the latest channel snapshot.",
            }
        )

    if not catalog:
        return _build_youtube_fallback(connection)

    suggested_searches = []
    for item in catalog:
        suggested_searches.extend(item["tags"])
    suggested_searches = list(dict.fromkeys(suggested_searches))[:4]

    return {
        "platform": "youtube",
        "data_source": "live",
        "headline": f"{channel_name} live channel view",
        "summary": "Showing recent uploads and current channel metrics from your connected YouTube account.",
        "external_url": channel_url,
        "external_label": "Open channel",
        "search_placeholder": "Search your video titles, descriptions, and hooks...",
        "preview_label": "Live connected channel",
        "trending_cards": [
            {"name": "Subscribers", "value": _format_count(statistics.get("subscriberCount")), "tone": "positive"},
            {"name": "Channel views", "value": _format_count(statistics.get("viewCount")), "tone": "positive"},
            {"name": "Published videos", "value": _format_count(statistics.get("videoCount")), "tone": "neutral"},
        ],
        "hero_metrics": [
            {"label": "Connected account", "value": channel_name},
            {"label": "Signed in as", "value": profile.get("email") or channel_name},
            {"label": "Latest upload seen", "value": _format_date((videos[0].get("snippet") or {}).get("publishedAt"))},
        ],
        "featured_profiles": highlighted[:3],
        "catalog": catalog,
        "preview_charts": chart_rows[:6],
        "suggested_searches": suggested_searches or ["latest upload", "shorts", "comments"],
        "side_insights": [
            {"title": "Source", "body": "This page is using your connected YouTube account data, not dummy preview cards."},
            {"title": "What you are seeing", "body": "Recent uploaded videos are shown first so you can inspect titles, views, likes, and comment activity quickly."},
        ],
    }


async def _build_instagram_preview(connection: dict) -> dict:
    instagram_account = ((connection.get("extra") or {}).get("instagram") or {})
    instagram_user_id = instagram_account.get("id")
    access_token = (connection.get("tokens") or {}).get("access_token")
    if not instagram_user_id or not access_token:
        return _build_instagram_fallback(connection)

    try:
        bundle = await fetch_instagram_media_bundle(access_token, instagram_user_id, limit=100)
    except httpx.HTTPError:
        return _build_instagram_fallback(connection)

    profile = bundle.get("profile") or {}
    media = bundle.get("media") or []
    username = profile.get("username") or instagram_account.get("username") or connection.get("account_name") or "connected"
    followers = profile.get("followers_count") or instagram_account.get("followers_count")
    media_count = profile.get("media_count")
    follows_count = profile.get("follows_count")
    profile_url = _instagram_profile_url(username)

    catalog = []
    chart_rows = []
    highlights = []
    comment_values = []
    for index, item in enumerate(media):
        caption = item.get("caption") or ""
        likes = _safe_int(item.get("like_count"))
        comments = _safe_int(item.get("comments_count"))
        media_type = _instagram_media_type(item.get("media_type"))
        posted_at = item.get("timestamp")
        comment_values.append(comments)
        title = _title_from_caption(caption, f"{media_type} update")

        catalog.append(
            {
                "id": item.get("id") or f"ig-{index}",
                "title": title,
                "creator": f"@{username}",
                "type": media_type,
                "media_url": item.get("media_url"),
                "duration": _format_date(posted_at),
                "theme": _theme(index),
                "description": _first_sentence(caption, "Recent media from your connected Instagram account."),
                "thumbnail": item.get("thumbnail_url") or item.get("media_url"),
                "url": item.get("permalink"),
                "url_label": "Open on Instagram",
                "creator_url": profile_url,
                "creator_label": "Open profile",
                "tags": _extract_tags(caption, fallback=["instagram", "media", "live"]),
                "published_at": posted_at,
                "metric_values": {
                    "likes": likes,
                    "comments": comments,
                },
                "analytics_source": "connected",
                "metrics": [
                    {"label": "Likes", "value": _format_count(likes)},
                    {"label": "Comments", "value": _format_count(comments)},
                ],
                "insight": "Live media pulled from your connected Instagram business account.",
            }
        )
        chart_rows.append({"label": _format_date(posted_at), "value": likes})
        highlights.append(
            {
                "name": _short_text(title, 36),
                "type": media_type,
                "insight": f"{_format_count(likes)} likes and {_format_count(comments)} comments in the latest sync.",
            }
        )

    if not catalog:
        return _build_instagram_fallback(connection)

    avg_comments = sum(comment_values) / len(comment_values) if comment_values else 0
    suggested_searches = []
    for item in catalog:
        suggested_searches.extend(item["tags"])
    suggested_searches = list(dict.fromkeys(suggested_searches))[:4]

    return {
        "platform": "instagram",
        "data_source": "live",
        "headline": f"@{username} live Instagram view",
        "summary": "Showing recent media and profile metrics from your connected Instagram business account.",
        "external_url": profile_url,
        "external_label": "Open profile",
        "search_placeholder": "Search your captions, formats, and hashtags...",
        "preview_label": "Live connected profile",
        "trending_cards": [
            {"name": "Followers", "value": _format_count(followers), "tone": "positive"},
            {"name": "Posts", "value": _format_count(media_count), "tone": "positive"},
            {"name": "Avg comments", "value": _format_count(round(avg_comments)), "tone": "neutral"},
        ],
        "hero_metrics": [
            {"label": "Connected handle", "value": f"@{username}"},
            {"label": "Following", "value": _format_count(follows_count)},
            {"label": "Latest post seen", "value": _format_date((media[0] or {}).get("timestamp"))},
        ],
        "featured_profiles": highlights[:3],
        "catalog": catalog,
        "preview_charts": chart_rows[:6],
        "suggested_searches": suggested_searches or ["reels", "carousel", "captions"],
        "side_insights": [
            {"title": "Source", "body": "This page is using your connected Instagram account data, not static demo content."},
            {"title": "What you are seeing", "body": "Recent media appears first so you can quickly review captions, likes, comments, and format mix."},
        ],
    }


def _build_x_preview(connection: dict) -> dict:
    extra = connection.get("extra") or {}
    profile = extra.get("profile") or {}
    posts = extra.get("posts") or []
    username = profile.get("username") or connection.get("handle") or "x"
    profile_metrics = profile.get("public_metrics") or {}
    profile_url = f"https://x.com/{username}" if username else None

    catalog = []
    highlights = []
    tags: list[str] = []
    timeline_rows = []
    for index, post in enumerate(posts[:200]):
        text = post.get("text") or ""
        classified = classify_text(text)
        tags_for_post = _extract_tags(text, fallback=["x", "timeline", "live"])
        tags.extend(tags_for_post)
        likes = _safe_int((post.get("public_metrics") or {}).get("like_count"))
        reposts = _safe_int((post.get("public_metrics") or {}).get("retweet_count"))
        replies = _safe_int((post.get("public_metrics") or {}).get("reply_count"))
        views = _safe_int((post.get("public_metrics") or {}).get("view_count"))
        created_at = post.get("created_at")
        post_title = _title_from_caption(text, f"Post {index + 1}")
        media_payload = _x_media_payload(post)

        catalog.append(
            {
                "id": post.get("id") or f"{connection['_id']}-apify-post-{index}",
                "title": post_title,
                "creator": f"@{username}" if username else connection.get("account_name") or "X profile",
                "type": "Post",
                "duration": _format_date(created_at) if created_at else f"Post {index + 1}",
                "theme": _theme(index),
                "description": _first_sentence(text, "Recent public post fetched through the connected live X source."),
                "thumbnail": media_payload["thumbnail"],
                "media_url": media_payload["media_url"],
                "player_type": media_payload["player_type"],
                "url": f"https://x.com/{username}/status/{post.get('id')}" if username and post.get("id") else profile_url,
                "url_label": "Open on X",
                "creator_url": profile_url,
                "creator_label": "Open profile",
                "tags": tags_for_post,
                "published_at": created_at,
                "metric_values": {
                    "views": views,
                    "likes": likes,
                    "reposts": reposts,
                    "replies": replies,
                },
                "analytics_source": "connected-apify",
                "metrics": [
                    {"label": "Views", "value": _format_count(views)},
                    {"label": "Likes", "value": _format_count(likes)},
                    {"label": "Replies", "value": _format_count(replies)},
                    {"label": "Reposts", "value": _format_count(reposts)},
                    {"label": "Mood", "value": classified["sentiment"].title()},
                ],
                "insight": "Public X metrics and media were refreshed through the connected live source.",
            }
        )

        if len(highlights) < 3:
            highlights.append(
                {
                    "name": _short_text(post_title, 32),
                    "type": "Post",
                    "insight": f"{_format_count(likes)} likes, {_format_count(replies)} replies, and {_format_count(reposts)} reposts.",
                }
            )

        if created_at:
            timeline_rows.append({"label": _format_date(created_at), "value": likes + reposts + replies})

    if not catalog:
        catalog.append(
            {
                "id": f"{connection['_id']}-apify-profile",
                "title": f"@{username}" if username else connection.get("account_name") or "Connected X profile",
                "creator": f"@{username}" if username else connection.get("account_name") or "X profile",
                "type": "Profile",
                "duration": "Live",
                "theme": "ocean",
                "description": _first_sentence(
                    profile.get("description"),
                    "The X profile is connected, but no recent posts were returned in the last refresh.",
                ),
                "url": profile_url,
                "url_label": "Open on X",
                "creator_url": profile_url,
                "creator_label": "Open profile",
                "tags": ["x", "profile", "live"],
                "metric_values": {
                    "followers": _safe_int(profile_metrics.get("followers_count")),
                    "following": _safe_int(profile_metrics.get("following_count")),
                    "posts": _safe_int(profile_metrics.get("tweet_count")),
                },
                "analytics_source": "connected-apify",
                "metrics": [
                    {"label": "Followers", "value": _format_count(profile_metrics.get("followers_count"))},
                    {"label": "Following", "value": _format_count(profile_metrics.get("following_count"))},
                    {"label": "Posts", "value": _format_count(profile_metrics.get("tweet_count"))},
                ],
                "insight": "The X account is connected, but the last refresh returned no timeline posts.",
            }
        )

    if not highlights:
        highlights.append(
            {
                "name": f"@{username}" if username else connection.get("account_name") or "Connected X profile",
                "type": "Profile",
                "insight": _first_sentence(profile.get("description"), "Live public profile data was fetched through the connected X source."),
            }
        )

    return {
        "platform": "x",
        "data_source": "live",
        "headline": f"@{username} connected X view" if username else "Connected X account view",
        "summary": "Showing profile and recent timeline data pulled through the connected live X source.",
        "external_url": profile_url,
        "external_label": "Open profile",
        "search_placeholder": "Search your connected X handle, keywords, or public conversations...",
        "preview_label": "Connected live handle",
        "trending_cards": [
            {"name": "Followers", "value": _format_count(profile_metrics.get("followers_count")), "tone": "positive"},
            {"name": "Following", "value": _format_count(profile_metrics.get("following_count")), "tone": "neutral"},
            {"name": "Posts", "value": _format_count(profile_metrics.get("tweet_count")), "tone": "positive"},
        ],
        "hero_metrics": [
            {"label": "Connected handle", "value": f"@{username}" if username else "n/a"},
            {"label": "Verified", "value": "Yes" if profile.get("verified") else "No"},
            {"label": "Recent posts loaded", "value": str(len(posts[:200]))},
        ],
        "featured_profiles": highlights[:3],
        "catalog": catalog,
        "preview_charts": timeline_rows[:6],
        "suggested_searches": list(dict.fromkeys(tags))[:4] or [f"@{username}" if username else "@AlwaysRamCharan", "@Cristiano", "@MrBeast"],
        "side_insights": [
            {
                "title": "Source",
                "body": "This page is using the connected X handle for timeline media and engagement reads.",
            },
            {
                "title": "Analytics scope",
                "body": "This feed exposes public X profile, media, and engagement counts. Private owner-only analytics are still not available here.",
            },
        ],
    }


async def get_connected_platform_preview(platform: str, user: dict | None) -> dict | None:
    if not user:
        return None

    db = get_database()
    connection = await db.social_accounts.find_one({"user_id": user["id"], "platform": platform})
    if not connection:
        return None

    cache_key = _preview_cache_key(user["id"], platform)
    cached = await get_json(cache_key)
    if isinstance(cached, dict) and cached:
        return cached

    preview: dict | None = None
    if platform == "youtube":
        try:
            preview = await _build_youtube_preview(connection)
        except httpx.HTTPError:
            preview = _build_youtube_fallback(connection)
    elif platform == "instagram":
        preview = await _build_instagram_preview(connection)
    elif platform == "x":
        preview = _build_x_preview(connection)

    if not preview:
        return None

    await set_json(cache_key, preview, get_settings().preview_cache_ttl_seconds)
    return preview


async def invalidate_platform_preview_cache(user_id: str, platform: str) -> None:
    await delete_key(_preview_cache_key(user_id, platform))


def get_platform_access_state(platform: str) -> dict:
    from app.services.demo_data import get_public_discovery

    return get_public_discovery(platform)
