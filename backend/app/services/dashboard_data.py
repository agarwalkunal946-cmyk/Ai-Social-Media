from collections import Counter, defaultdict
import re
from datetime import datetime, timedelta, timezone
from statistics import mean

from app.core.config import get_settings
from app.db.mongo import get_database
from app.db.redis_client import delete_key, get_json, set_json
from app.services.analysis import analyze_text_batch, classify_text, get_model_stack
from app.services.platform_preview import _format_count, _safe_int, get_connected_platform_preview
from app.services.public_platforms import get_public_platform_payload


DAY_ORDER = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
TIME_WINDOWS = (
    ("Early morning", range(5, 9)),
    ("Morning", range(9, 12)),
    ("Afternoon", range(12, 17)),
    ("Evening", range(17, 21)),
    ("Late night", (21, 22, 23, 0, 1, 2, 3, 4)),
)
DASHBOARD_CACHE_PREFIX = "dashboard-snapshot:v1"
CHATBOT_DOMAIN_KEYWORDS = (
    "app",
    "application",
    "synapse",
    "dashboard",
    "analytics",
    "social",
    "instagram",
    "youtube",
    "twitter",
    "followers",
    "reach",
    "engagement",
    "views",
    "likes",
    "comments",
    "replies",
    "hashtags",
    "caption",
    "trend",
    "trending",
    "viral",
    "audience",
    "sentiment",
    "emotion",
    "toxic",
    "risk",
    "alert",
    "moderation",
    "connected",
    "account",
    "profile",
    "creator",
    "post",
    "reel",
    "video",
    "media",
    "public",
    "search",
)
CHATBOT_SEARCH_KEYWORDS = ("search", "find", "lookup", "analyze", "analyse", "analytics", "profile", "public search")
CHATBOT_NAME_LOOKUP_KEYWORDS = (
    "full name",
    "channel name",
    "creator name",
    "profile name",
    "account name",
    "real name",
    "who is",
)
CHATBOT_CODE_TERMS = (
    "code",
    "coding",
    "python",
    "javascript",
    "typescript",
    "react",
    "html",
    "css",
    "sql",
    "api",
    "backend",
    "frontend",
    "bug",
    "debug",
    "function",
    "class",
)
CHATBOT_SCOPE_REPLY = (
    "This assistant only answers AI social media analytics questions using your dashboard metrics "
    "and live public platform data from YouTube, Instagram, and X / Twitter."
)
CHATBOT_APP_FEATURES = [
    "Unified dashboard for Instagram, YouTube, and X / Twitter analytics",
    "Connected account summaries, public platform search, and live trend exploration",
    "Sentiment, emotion, toxicity, moderation queue, and crisis alerts",
    "Audience insights, predictive posting windows, and explainable AI summaries",
    "Top content cards, trending hashtags, and AI recommendations",
]
CHATBOT_ANALYTICS_METHODS = {
    "content_score": "views + likes*15 + comments*20 + replies*20 + reposts*18 + retweets*18 + quotes*16 + saves*18 + shares*18",
    "interaction_total": "likes + comments + replies + reposts + retweets + quotes + saves + shares",
    "engagement_rate": "interactions / reach * 100",
    "predictive_change": "((recent_average - baseline_average) / baseline_average) * 100",
}
CHATBOT_FILLER_WORDS = {
    "what",
    "which",
    "show",
    "tell",
    "give",
    "me",
    "about",
    "for",
    "find",
    "search",
    "lookup",
    "analytics",
    "analysis",
    "channel",
    "creator",
    "profile",
    "account",
    "full",
    "real",
    "name",
    "please",
    "the",
    "this",
    "that",
    "on",
    "of",
    "is",
    "ka",
    "ke",
    "ki",
    "kya",
    "kaun",
    "kaunsa",
    "kaunsi",
    "batao",
    "bolo",
    "hai",
}


def _dashboard_cache_key(user_id: str) -> str:
    return f"{DASHBOARD_CACHE_PREFIX}:{user_id}"


async def invalidate_dashboard_snapshot_cache(user_id: str) -> None:
    await delete_key(_dashboard_cache_key(user_id))


def _platform_label(platform: str) -> str:
    return {"youtube": "YouTube", "instagram": "Instagram", "x": "X / Twitter"}.get(platform, platform.title())


def _score_content(item: dict) -> int:
    metrics = item.get("metric_values") or {}
    return (
        _safe_int(metrics.get("views"))
        + _safe_int(metrics.get("likes")) * 15
        + _safe_int(metrics.get("comments")) * 20
        + _safe_int(metrics.get("replies")) * 20
        + _safe_int(metrics.get("reposts")) * 18
        + _safe_int(metrics.get("retweets")) * 18
        + _safe_int(metrics.get("quotes")) * 16
        + _safe_int(metrics.get("saved")) * 18
        + _safe_int(metrics.get("shares")) * 18
    )


def _interaction_total(metrics: dict) -> int:
    return (
        _safe_int(metrics.get("likes"))
        + _safe_int(metrics.get("comments"))
        + _safe_int(metrics.get("replies"))
        + _safe_int(metrics.get("reposts"))
        + _safe_int(metrics.get("retweets"))
        + _safe_int(metrics.get("quotes"))
        + _safe_int(metrics.get("saved"))
        + _safe_int(metrics.get("shares"))
    )


def _format_percent(value: float) -> str:
    return f"{value:.1f}%"


def _engagement_rate(reach: int, interactions: int) -> float:
    if reach <= 0:
        return 0.0
    return round((interactions / reach) * 100, 1)


def _parse_published_at(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            return datetime.strptime(value, "%a %b %d %H:%M:%S %z %Y")
        except ValueError:
            return None


def _connected_account_avatar(platform: str, connection: dict) -> str | None:
    extra = connection.get("extra") or {}
    if platform == "instagram":
        return (extra.get("instagram") or {}).get("profile_picture_url")
    if platform == "youtube":
        return (
            extra.get("thumbnail_url")
            or (((extra.get("channel") or {}).get("snippet") or {}).get("thumbnails") or {}).get("high", {}).get("url")
            or (((extra.get("channel") or {}).get("snippet") or {}).get("thumbnails") or {}).get("default", {}).get("url")
        )
    if platform == "x":
        return (extra.get("profile") or {}).get("avatar")
    return None


def _connected_account_url(platform: str, connection: dict, preview: dict | None) -> str | None:
    if preview and preview.get("external_url"):
        return preview.get("external_url")
    if platform == "instagram":
        username = connection.get("handle") or ((connection.get("extra") or {}).get("instagram") or {}).get("username")
        if username:
            return f"https://www.instagram.com/{str(username).removeprefix('@')}/"
    if platform == "youtube":
        channel_id = (connection.get("extra") or {}).get("channel_id")
        if channel_id:
            return f"https://www.youtube.com/channel/{channel_id}"
    if platform == "x":
        username = connection.get("handle") or ((connection.get("extra") or {}).get("profile") or {}).get("username")
        if username:
            return f"https://x.com/{str(username).removeprefix('@')}"
    return None


def _card(label: str, value: str, detail: str | None = None) -> dict:
    card = {"label": label, "value": value}
    if detail:
        card["detail"] = detail
    return card


def _metric_summary(item: dict, platform: str) -> str:
    metrics = item.get("metric_values") or {}
    if platform == "youtube":
        return f"{_format_count(metrics.get('views'))} views"
    if platform == "instagram":
        comments = _safe_int(metrics.get("comments"))
        likes = _safe_int(metrics.get("likes"))
        return (
            f"{_format_count(likes)} likes and {_format_count(comments)} comments"
            if comments
            else f"{_format_count(likes)} likes"
        )
    likes = _safe_int(metrics.get("likes"))
    replies = _safe_int(metrics.get("replies"))
    views = _safe_int(metrics.get("views"))
    if views:
        return f"{_format_count(views)} views and {_format_count(likes)} likes"
    if replies:
        return f"{_format_count(likes)} likes and {_format_count(replies)} replies"
    return f"{_format_count(likes)} likes"


def _catalog_item_to_chat_media(item: dict, platform: str) -> dict:
    metric = _metric_summary(item, platform)
    player_type = item.get("player_type")
    if not player_type and platform == "youtube" and item.get("video_id"):
        player_type = "youtube"
    if not player_type and platform == "instagram" and item.get("media_url") and str(item.get("type") or "").lower() in {"reel", "video"}:
        player_type = "instagram"
    return {
        "id": item.get("id"),
        "title": item.get("title") or "Content item",
        "platform": _platform_label(platform),
        "platform_key": platform,
        "creator": item.get("creator"),
        "type": item.get("type"),
        "metric": metric,
        "insight": item.get("insight") or item.get("description") or metric,
        "thumbnail": item.get("thumbnail"),
        "url": item.get("url"),
        "video_id": item.get("video_id"),
        "media_url": item.get("media_url"),
        "player_type": player_type,
        "published_at": item.get("published_at"),
    }


def _extract_platforms_from_prompt(prompt: str) -> list[str]:
    lowered = (prompt or "").lower()
    platforms = []
    if "instagram" in lowered or "insta" in lowered:
        platforms.append("instagram")
    if "youtube" in lowered or re.search(r"\byt\b", lowered):
        platforms.append("youtube")
    if "twitter" in lowered or "tweet" in lowered or re.search(r"\bx\b", lowered):
        platforms.append("x")
    return list(dict.fromkeys(platforms))


def _contains_any_phrase(text: str, phrases: tuple[str, ...] | list[str]) -> bool:
    return any(phrase in text for phrase in phrases)


def _is_code_request(prompt: str) -> bool:
    return _contains_any_phrase((prompt or "").lower(), CHATBOT_CODE_TERMS)


def _is_domain_prompt(prompt: str) -> bool:
    return _contains_any_phrase((prompt or "").lower(), CHATBOT_DOMAIN_KEYWORDS)


def _clean_public_query(query: str) -> str:
    cleaned = re.sub(r"\s+", " ", query or "").strip(" .,:;!?")
    cleaned = re.sub(r"^(for|about|of|on)\s+", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


def _infer_platform_from_context(prompt: str, requested_platforms: list[str]) -> str | None:
    lowered = (prompt or "").lower()
    if requested_platforms:
        return requested_platforms[0]
    if "youtube" in lowered or "channel" in lowered or "shorts" in lowered:
        return "youtube"
    if "instagram" in lowered or "insta" in lowered or "reel" in lowered:
        return "instagram"
    if "twitter" in lowered or "tweet" in lowered or "handle" in lowered or re.search(r"\bx\b", lowered):
        return "x"
    return None


def _extract_entity_lookup_request(prompt: str, requested_platforms: list[str]) -> tuple[str, str] | None:
    lowered = (prompt or "").lower()
    if not _contains_any_phrase(lowered, CHATBOT_NAME_LOOKUP_KEYWORDS):
        return None

    platform = _infer_platform_from_context(prompt, requested_platforms)
    if not platform:
        return None

    candidates = re.findall(r"[a-z0-9_@']+", lowered)
    query_tokens = [
        token
        for token in candidates
        if token not in CHATBOT_FILLER_WORDS
        and token not in {"youtube", "instagram", "twitter", "x", "social", "media", "app", "apps"}
        and not token.isdigit()
    ]
    query = _clean_public_query(" ".join(query_tokens[:6]))
    if not query:
        return None
    return platform, query


def _extract_public_search_request(prompt: str, requested_platforms: list[str]) -> tuple[str, str] | None:
    original = (prompt or "").strip()
    lowered = original.lower()
    if not original:
        return None

    handle_match = re.search(
        r"(@[a-z0-9_]{1,15}|(?:https?://)?(?:www\.)?(?:x|twitter)\.com/[a-z0-9_]{1,15})",
        original,
        re.IGNORECASE,
    )
    if handle_match and ("x" in requested_platforms or not requested_platforms or "twitter" in lowered):
        return "x", _clean_public_query(handle_match.group(1))

    patterns = (
        r"(?:search|find|lookup|analy[sz]e|show(?: me)?|give me)\s+(?P<query>.+?)\s+on\s+(?P<platform>youtube|instagram|x|twitter)\b",
        r"(?P<platform>youtube|instagram|x|twitter)\s+(?:search|analytics|analysis|profile|public search)\s+(?:for\s+)?(?P<query>.+)",
        r"(?P<platform>youtube|instagram|x|twitter)\s+(?:for|about)\s+(?P<query>.+)",
    )
    for pattern in patterns:
        match = re.search(pattern, original, re.IGNORECASE)
        if not match:
            continue
        platform = "x" if match.group("platform").lower() in {"x", "twitter"} else match.group("platform").lower()
        query = _clean_public_query(match.group("query"))
        if query:
            return platform, query

    if len(requested_platforms) == 1 and _contains_any_phrase(lowered, CHATBOT_SEARCH_KEYWORDS):
        cleaned = re.sub(
            r"\b(search|find|lookup|analy[sz]e|analytics|analysis|show|public|profile|stats|for|about|on|please)\b",
            " ",
            original,
            flags=re.IGNORECASE,
        )
        cleaned = re.sub(r"\b(youtube|instagram|twitter)\b", " ", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\bx\b", " ", cleaned, flags=re.IGNORECASE)
        query = _clean_public_query(cleaned)
        if query:
            return requested_platforms[0], query

    return None


def _sorted_latest_items(catalog: list[dict]) -> list[dict]:
    return sorted(
        catalog,
        key=lambda item: _parse_published_at(item.get("published_at")) or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )


def _json_safe(value):
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    return value


def _top_content_player_type(item: dict) -> str | None:
    platform = item.get("platform")
    if platform == "youtube" and item.get("video_id"):
        return "youtube"
    if platform == "instagram" and item.get("media_url") and str(item.get("type") or "").lower() in {"reel", "video"}:
        return "instagram"
    if platform == "x" and item.get("media_url") and item.get("player_type") == "x-video":
        return "x"
    return None


def _sentiment_percentages(texts: list[str]) -> list[dict]:
    if not texts:
        return []
    counts = Counter()
    for text in texts:
        counts[classify_text(text).get("sentiment", "neutral")] += 1
    total = sum(counts.values()) or 1
    rows = []
    for label in ("positive", "neutral", "negative"):
        rows.append({"name": label.title(), "value": round((counts.get(label, 0) / total) * 100)})
    return rows


def _build_text_payload(item: dict) -> str:
    tags = " ".join(f"#{tag}" for tag in (item.get("tags") or []))
    return " ".join(part for part in [item.get("title"), item.get("description"), tags] if part)


def _extract_trending_hashtags(items: list[dict]) -> list[dict]:
    counts = Counter()
    platforms: dict[str, set[str]] = defaultdict(set)
    for item in items:
        tag_candidates = item.get("tags") or []
        for raw_tag in tag_candidates:
            tag = str(raw_tag or "").strip().lower().removeprefix("#")
            if not tag:
                continue
            counts[tag] += 1
            platforms[tag].add(_platform_label(item.get("platform", "")))
    return [
        {"tag": f"#{tag}", "count": count, "platforms": sorted(platforms[tag])}
        for tag, count in counts.most_common(8)
    ]


def _best_time_window(dated_content: list[dict]) -> str:
    buckets = Counter()
    for item in dated_content:
        parsed = _parse_published_at(item.get("published_at"))
        if not parsed:
            continue
        hour = parsed.astimezone(timezone.utc).hour
        score = max(_score_content(item), 1)
        for label, hours in TIME_WINDOWS:
            if hour in hours:
                buckets[label] += score
                break
    if not buckets:
        return "Evening"
    return buckets.most_common(1)[0][0]


def _build_forecast(trend_rows: list[dict]) -> dict:
    values = [row.get("value", 0) for row in trend_rows]
    if not values:
        return {
            "trend_direction": "Stable",
            "predicted_change_pct": 0.0,
            "forecast_points": [],
            "viral_opportunity": "Medium",
            "best_day": "n/a",
            "best_time_window": "Evening",
        }

    recent_window = values[-2:] if len(values) >= 2 else values
    baseline_window = values[:-2] if len(values) > 2 else values
    recent_avg = mean(recent_window) if recent_window else 0
    baseline_avg = mean(baseline_window) if baseline_window else recent_avg
    if baseline_avg <= 0:
        predicted_change_pct = 0.0 if recent_avg <= 0 else 100.0
    else:
        predicted_change_pct = round(((recent_avg - baseline_avg) / baseline_avg) * 100, 1)

    if predicted_change_pct >= 12:
        trend_direction = "Upward"
        viral_opportunity = "High"
    elif predicted_change_pct <= -10:
        trend_direction = "Cooling"
        viral_opportunity = "Low"
    else:
        trend_direction = "Stable"
        viral_opportunity = "Medium"

    recent_delta = recent_avg - baseline_avg
    seed_value = values[-1]
    next_values = [
        max(0, round(seed_value + recent_delta * 0.6)),
        max(0, round(seed_value + recent_delta * 0.9)),
        max(0, round(seed_value + recent_delta * 1.15)),
    ]
    next_labels = ["Next 1", "Next 2", "Next 3"]
    forecast_points = [{"label": label, "value": value} for label, value in zip(next_labels, next_values)]

    peak_day = max(trend_rows, key=lambda row: row.get("value", 0), default={"day": "n/a"})
    return {
        "trend_direction": trend_direction,
        "predicted_change_pct": predicted_change_pct,
        "forecast_points": forecast_points,
        "viral_opportunity": viral_opportunity,
        "best_day": peak_day.get("day", "n/a"),
    }


def _build_audience_insights(
    comparison: list[dict],
    content_types: Counter,
    best_day: str,
    best_time_window: str,
    top_content: list[dict],
) -> dict:
    audience_leader = max(comparison, key=lambda item: item.get("reach", 0), default=None)
    engagement_leader = max(comparison, key=lambda item: item.get("engagement_rate", 0), default=None)
    content_type = content_types.most_common(1)[0][0] if content_types else "Mixed content"
    top_platform = audience_leader.get("platform", "n/a") if audience_leader else "n/a"

    cards = [
        {
            "label": "Audience leader",
            "value": top_platform,
            "detail": "Platform with the largest visible audience footprint.",
        },
        {
            "label": "Best engagement rate",
            "value": _format_percent(engagement_leader.get("engagement_rate", 0.0)) if engagement_leader else "0.0%",
            "detail": f"{engagement_leader.get('platform')} is currently generating the strongest response rate." if engagement_leader else "Connect more sources to compare engagement rates.",
        },
        {
            "label": "Top content format",
            "value": content_type,
            "detail": "Most frequent high-performing format in the indexed content set.",
        },
        {
            "label": "Best publishing window",
            "value": f"{best_day} {best_time_window}",
            "detail": "Recommended from the strongest historical interaction pattern.",
        },
    ]

    notes = [
        f"{top_platform} currently leads audience reach." if audience_leader else "Audience leadership appears after at least one platform connects.",
        f"{content_type} is the most visible format in the indexed sample.",
        f"Best posting window is {best_day} during the {best_time_window.lower()}.",
    ]
    if top_content:
        notes.append(f'Top content signal right now is "{top_content[0].get("title")}".')

    return {"cards": cards, "notes": notes}


def _build_moderation_queue(content_items: list[dict]) -> list[dict]:
    flagged = []
    for item in content_items:
        text = _build_text_payload(item)
        if not text.strip():
            continue
        result = classify_text(text)
        if result["toxicity"] < 0.2 and result["sentiment"] != "negative":
            continue
        flagged.append(
            {
                "id": item.get("id"),
                "title": item.get("title") or "Content item",
                "platform": _platform_label(item.get("platform", "")),
                "toxicity": round(result["toxicity"] * 100),
                "sentiment": result["sentiment"].title(),
                "emotion": result["emotion"].title(),
                "snippet": (item.get("description") or item.get("title") or "")[:140],
            }
        )
    return sorted(flagged, key=lambda row: (row["toxicity"], row["sentiment"] == "Negative"), reverse=True)[:6]


def _build_crisis_alerts(
    sentiment_breakdown: list[dict],
    moderation_queue: list[dict],
    forecast: dict,
    top_platform: str,
) -> list[dict]:
    negative_pct = next((item.get("value", 0) for item in sentiment_breakdown if item.get("name") == "Negative"), 0)
    alerts = []

    if negative_pct >= 30:
        alerts.append(
            {
                "severity": "high" if negative_pct >= 45 else "medium",
                "title": "Negative sentiment spike detected",
                "explanation": f"Negative audience tone is currently {negative_pct}% of the indexed conversation sample.",
                "recommended_action": f"Review the latest {top_platform} comments and post a clarifying response if needed.",
            }
        )

    if moderation_queue:
        top_flag = moderation_queue[0]
        if top_flag["toxicity"] >= 25:
            alerts.append(
                {
                    "severity": "high" if top_flag["toxicity"] >= 40 else "medium",
                    "title": "Toxic language needs moderation review",
                    "explanation": f'{top_flag["platform"]} content "{top_flag["title"]}" shows a toxicity risk score of {top_flag["toxicity"]}%.',
                    "recommended_action": "Review, hide, or respond to harmful language before the conversation escalates.",
                }
            )

    if forecast.get("trend_direction") == "Cooling":
        alerts.append(
            {
                "severity": "medium",
                "title": "Engagement is cooling down",
                "explanation": f'Predicted engagement is down {abs(forecast.get("predicted_change_pct", 0.0)):.1f}% compared with the earlier baseline.',
                "recommended_action": "Use the recommended posting window and refresh the next caption or hook format.",
            }
        )

    if forecast.get("viral_opportunity") == "High":
        alerts.append(
            {
                "severity": "low",
                "title": "Viral opportunity detected",
                "explanation": "Recent interaction momentum is climbing faster than the earlier baseline.",
                "recommended_action": "Post during the recommended window and reuse the strongest topic angle from top content.",
            }
        )

    return alerts[:4]


def _build_recommendations(
    hashtags: list[dict],
    top_item: dict | None,
    best_day: str,
    best_time_window: str,
    dominant_emotion: str,
    forecast: dict,
) -> list[dict]:
    recommended_tags = " ".join(item["tag"] for item in hashtags[:5]) or "#community #growth #creator"
    top_title = top_item.get("title", "your strongest post") if top_item else "your strongest post"
    caption_angle = (
        f"Lead with a clear payoff, then add a question that matches the current {dominant_emotion.lower()} audience tone."
        if dominant_emotion
        else "Lead with a clear payoff, then add one direct question to encourage replies."
    )
    return [
        {
            "title": "Best posting window",
            "body": f"Your strongest window is {best_day} during the {best_time_window.lower()}. Schedule the next post there first.",
            "category": "timing",
        },
        {
            "title": "Caption direction",
            "body": f'Reuse the hook pattern from "{top_title}" and keep the first line outcome-driven. {caption_angle}',
            "category": "caption",
        },
        {
            "title": "Hashtag pack",
            "body": f"Recommended mix: {recommended_tags}",
            "category": "hashtags",
        },
        {
            "title": "Trend outlook",
            "body": f'Current forecast is {forecast.get("trend_direction", "Stable").lower()} with a {forecast.get("viral_opportunity", "Medium").lower()} viral opportunity score.',
            "category": "prediction",
        },
    ]


def _build_explainability(
    comparison: list[dict],
    sentiment_breakdown: list[dict],
    moderation_queue: list[dict],
    forecast: dict,
    hashtags: list[dict],
) -> dict:
    top_platform = max(comparison, key=lambda item: item.get("reach", 0), default=None)
    negative_pct = next((item.get("value", 0) for item in sentiment_breakdown if item.get("name") == "Negative"), 0)
    factors = [
        {
            "label": "Reach weighting",
            "impact": "High",
            "reason": f'{top_platform.get("platform")} leads the audience footprint, so it strongly influences the audience insight summary.' if top_platform else "Audience leadership is calculated from visible reach and follower totals.",
        },
        {
            "label": "Interaction velocity",
            "impact": "High",
            "reason": f'The trend forecast is based on recent engagement compared with the earlier baseline and is currently {forecast.get("trend_direction", "Stable").lower()}.',
        },
        {
            "label": "Sentiment balance",
            "impact": "Medium",
            "reason": f"Negative tone currently represents {negative_pct}% of the indexed audience text, which feeds crisis detection.",
        },
        {
            "label": "Moderation risk",
            "impact": "Medium",
            "reason": "Toxicity is estimated from harmful-language signals in post text, captions, and conversation snippets." if moderation_queue else "No elevated moderation item was strong enough to dominate the explainability layer.",
        },
        {
            "label": "Topic recurrence",
            "impact": "Medium",
            "reason": f'Top recurring tags such as {", ".join(item["tag"] for item in hashtags[:3]) or "#community, #growth"} influence hashtag recommendations.',
        },
    ]

    return {
        "summary": "Explainable AI traces each recommendation back to visible engagement, content topics, sentiment, and moderation signals instead of a black-box score.",
        "factors": factors,
        "model_stack": get_model_stack(),
    }


def _build_chatbot_payload(best_day: str, best_time_window: str, top_platform: str) -> dict:
    return {
        "title": "AI social media analytics assistant",
        "greeting": (
            "Ask only about dashboard values, connected account performance, public platform searches, "
            "trends, hashtags, media, audience signals, and risk alerts for YouTube, Instagram, and X / Twitter."
        ),
        "input_placeholder": 'Ask about dashboard values or public analytics, for example: "Search MrBeast on YouTube"',
        "scope": [
            "Dashboard values",
            "Connected account analytics",
            "Public platform search",
            "Trends and hashtags",
            "App features, formulas, and models",
            "No coding or off-topic replies",
        ],
        "starter_questions": [
            "What is my best posting time?",
            f"Which platform currently leads my audience, {top_platform} or another source?",
            "Show the latest video or reel from my connected sources.",
            "What is trending publicly right now on YouTube and X / Twitter?",
            "Search MrBeast on YouTube and summarize the analytics.",
            "MrBeast ke channel ka full name kya hai?",
            "Which models are used in this app?",
            "How are trending hashtags calculated?",
            "Show analytics for @AlwaysRamCharan on X / Twitter.",
            "Do I have any crisis risks right now?",
            "Which hashtags should I reuse next?",
        ],
        "context": {
            "best_day": best_day,
            "best_time_window": best_time_window,
            "top_platform": top_platform,
        },
    }


async def _load_connected_preview_media(user: dict, platforms: list[str], limit: int = 3) -> list[dict]:
    items: list[dict] = []
    for platform in platforms:
        preview = await get_connected_platform_preview(platform, user)
        if not preview:
            continue
        for catalog_item in _sorted_latest_items(preview.get("catalog") or [])[:limit]:
            items.append(_catalog_item_to_chat_media(catalog_item, platform))
            if len(items) >= limit:
                return items
    return items[:limit]


async def _load_public_trending_media(user: dict, platforms: list[str], limit: int = 3) -> tuple[list[dict], list[dict]]:
    items: list[dict] = []
    stats: list[dict] = []
    for platform in platforms:
        try:
            payload = await get_public_platform_payload(platform, user, mode="trending", query=None)
        except Exception:  # noqa: BLE001
            continue

        cards = payload.get("trending_cards") or []
        if cards:
            stats.extend(
                [
                    _card(f"{_platform_label(platform)} {cards[0].get('name')}", str(cards[0].get("value") or "0")),
                ]
            )

        catalog = payload.get("catalog") or []
        for catalog_item in catalog:
            if platform == "x" and str(catalog_item.get("type") or "").lower() == "trend":
                continue
            items.append(_catalog_item_to_chat_media(catalog_item, platform))
            if len(items) >= limit:
                return items, stats[:4]
    return items[:limit], stats[:4]


async def _load_top_conversation_items(user: dict, platforms: list[str], limit: int = 3) -> list[dict]:
    scored: list[tuple[int, dict, str]] = []
    for platform in platforms:
        preview = await get_connected_platform_preview(platform, user)
        if not preview:
            continue
        for catalog_item in preview.get("catalog") or []:
            metrics = catalog_item.get("metric_values") or {}
            score = (
                _safe_int(metrics.get("comments"))
                + _safe_int(metrics.get("replies"))
                + _safe_int(metrics.get("quotes"))
            )
            if score <= 0:
                continue
            scored.append((score, catalog_item, platform))
    scored.sort(key=lambda row: row[0], reverse=True)
    return [_catalog_item_to_chat_media(item, platform) for _, item, platform in scored[:limit]]


def _build_public_payload_stat_cards(payload: dict, platform: str) -> list[dict]:
    cards = []
    for item in payload.get("trending_cards") or []:
        name = str(item.get("name") or "Metric").strip()
        cards.append(_card(f"{_platform_label(platform)} {name}", str(item.get("value") or "0")))
        if len(cards) >= 4:
            return cards

    for item in payload.get("hero_metrics") or []:
        label = str(item.get("label") or "Metric").strip()
        cards.append(_card(f"{_platform_label(platform)} {label}", str(item.get("value") or "n/a")))
        if len(cards) >= 4:
            break
    return cards


def _build_public_search_follow_up(platform: str, payload: dict) -> list[str]:
    label = _platform_label(platform)
    suggestions = []
    for suggestion in payload.get("suggested_searches") or []:
        cleaned = str(suggestion or "").strip()
        if not cleaned:
            continue
        suggestions.append(f"Search {cleaned} on {label}")
        if len(suggestions) >= 2:
            break
    suggestions.append(f"What public trends are live on {label}?")
    return suggestions[:3]


def _build_feature_summary_response(snapshot: dict) -> dict:
    overview = snapshot.get("overview") or []
    return {
        "answer": "This app is an AI social media analytics workspace for Instagram, YouTube, and X / Twitter.",
        "bullets": CHATBOT_APP_FEATURES[:5],
        "stat_cards": [
            _card(item.get("label", "Metric"), item.get("value", "0"), item.get("delta"))
            for item in overview[:3]
        ],
        "follow_up": [
            "Which models are used in this app?",
            "How are trending hashtags calculated?",
            "What is my best posting time?",
        ],
    }


def _build_model_stack_response(snapshot: dict) -> dict:
    model_stack = snapshot.get("model_stack") or get_model_stack()
    return {
        "answer": "These are the analytics models and fallback layers configured in the current build.",
        "bullets": [
            f"Sentiment model: {model_stack.get('sentiment')}",
            f"Toxicity model: {model_stack.get('toxicity')}",
            f"Emotion model: {model_stack.get('emotion')}",
            f"Runtime mode: {model_stack.get('mode', 'unknown')}",
        ],
        "stat_cards": [
            _card("Sentiment", str(model_stack.get("sentiment") or "n/a")),
            _card("Toxicity", str(model_stack.get("toxicity") or "n/a")),
            _card("Forecasting", str(model_stack.get("forecasting") or "n/a")),
            _card("Embeddings", str(model_stack.get("embeddings") or "n/a")),
        ],
        "follow_up": [
            "How are dashboard analytics calculated?",
            "How is toxicity detected?",
            "How are trending hashtags calculated?",
        ],
    }


def _build_accuracy_response(snapshot: dict) -> dict:
    return {
        "answer": "Visible provider metrics can be exact for the fetched source data, but AI insights are estimates and cannot be guaranteed 100% exact.",
        "bullets": [
            "Counts like followers, views, likes, comments, and loaded posts come from connected providers or live public sources.",
            "Sentiment, emotion, toxicity, recommendations, and prediction are derived analytics layers.",
            "The assistant is grounded to app data and should avoid guessing when data is unavailable.",
        ],
        "follow_up": [
            "Which models are used in this app?",
            "How are dashboard analytics calculated?",
            "Show my current dashboard summary.",
        ],
    }


def _build_methodology_response(prompt: str) -> dict:
    lowered = (prompt or "").lower()

    if "hashtag" in lowered:
        return {
            "answer": "Trending hashtags are built by counting recurring tags across indexed content items.",
            "bullets": [
                "The system reads tags from content items and caption-derived tags.",
                "Recurring tags are counted across platforms.",
                "The top recurring tags become the dashboard trending hashtags.",
            ],
            "stat_cards": [
                _card("Method", "Recurring tag count"),
                _card("Source", "Indexed content tags"),
            ],
            "follow_up": ["Which hashtags should I reuse next?", "How is top content scored?"],
        }

    if "sentiment" in lowered or "emotion" in lowered:
        return {
            "answer": "Sentiment and emotion are derived from the text collected from titles, descriptions, captions, and tags.",
            "bullets": [
                "Positive and negative keywords determine the dominant sentiment label.",
                "Emotion labels are mapped from keyword groups like joy, excitement, concern, frustration, anger, and surprise.",
                "Overall mood combines dominant sentiment and dominant emotion.",
            ],
            "stat_cards": [
                _card("Sentiment method", "Keyword-weighted fallback"),
                _card("Emotion method", "Mapped keyword groups"),
            ],
            "follow_up": ["How is toxicity detected?", "Show my current mood summary."],
        }

    if "toxic" in lowered or "toxicity" in lowered or "moderation" in lowered:
        return {
            "answer": "Toxicity is estimated from harmful-language keyword signals inside indexed content text.",
            "bullets": [
                "Harmful-language tokens increase the toxicity score.",
                "Items above the moderation threshold enter the moderation queue.",
                "High toxicity can also trigger crisis alerts.",
            ],
            "stat_cards": [
                _card("Toxicity method", "Keyword toxicity fallback"),
                _card("Queue trigger", "Toxic or negative content"),
            ],
            "follow_up": ["Do I have any crisis risks right now?", "Which content item is most at risk?"],
        }

    if "forecast" in lowered or "predict" in lowered or "posting time" in lowered or "best time" in lowered:
        return {
            "answer": "Prediction compares recent engagement momentum with the earlier trend baseline.",
            "bullets": [
                f'Predicted change formula: {CHATBOT_ANALYTICS_METHODS["predictive_change"]}',
                "A strong positive change becomes Upward, a strong negative change becomes Cooling, otherwise Stable.",
                "Best posting window is selected from the strongest score bucket by day and UTC time window.",
            ],
            "stat_cards": [
                _card("Forecast formula", CHATBOT_ANALYTICS_METHODS["predictive_change"]),
                _card("Engagement rate", CHATBOT_ANALYTICS_METHODS["engagement_rate"]),
            ],
            "follow_up": ["What is my best posting time?", "How is top content scored?"],
        }

    return {
        "answer": "Dashboard analytics are calculated from connected-platform metrics plus app-side AI analysis layers.",
        "bullets": [
            f'Content score: {CHATBOT_ANALYTICS_METHODS["content_score"]}',
            f'Interaction total: {CHATBOT_ANALYTICS_METHODS["interaction_total"]}',
            f'Engagement rate: {CHATBOT_ANALYTICS_METHODS["engagement_rate"]}',
        ],
        "stat_cards": [
            _card("Content score", CHATBOT_ANALYTICS_METHODS["content_score"]),
            _card("Interactions", CHATBOT_ANALYTICS_METHODS["interaction_total"]),
        ],
        "follow_up": [
            "How are trending hashtags calculated?",
            "Which models are used in this app?",
            "What is my best posting time?",
        ],
    }


async def _build_public_search_chat_response(user: dict, platform: str, query: str) -> dict:
    payload = await get_public_platform_payload(platform, user, mode="search", query=query)
    catalog = payload.get("catalog") or []
    stat_cards = _build_public_payload_stat_cards(payload, platform)
    bullets = []

    if catalog:
        lead = catalog[0]
        bullets.append(
            f'Top result: "{lead.get("title") or "Content"}" by {lead.get("creator") or _platform_label(platform)} '
            f'with {_metric_summary(lead, platform)}.'
        )
        bullets.append(f'Loaded {len(catalog)} public result(s) for "{query}".')
    if payload.get("summary"):
        bullets.append(str(payload.get("summary")))
    for insight in payload.get("side_insights") or []:
        body = str(insight.get("body") or "").strip()
        if body and body not in bullets:
            bullets.append(body)
        if len(bullets) >= 4:
            break

    if catalog:
        media_items = [_catalog_item_to_chat_media(item, platform) for item in catalog[:3]]
        return {
            "answer": f'Here is the live public {_platform_label(platform)} analytics summary for "{query}".',
            "bullets": bullets[:4],
            "stat_cards": stat_cards,
            "media_items": media_items,
            "follow_up": _build_public_search_follow_up(platform, payload),
        }

    return {
        "answer": payload.get("headline") or f"{_platform_label(platform)} public search is not ready right now.",
        "bullets": bullets[:4] or [CHATBOT_SCOPE_REPLY],
        "stat_cards": stat_cards,
        "follow_up": _build_public_search_follow_up(platform, payload),
    }


async def _build_entity_lookup_response(user: dict, platform: str, query: str) -> dict:
    payload = await get_public_platform_payload(platform, user, mode="search", query=query)
    catalog = payload.get("catalog") or []
    stat_cards = _build_public_payload_stat_cards(payload, platform)

    if not catalog:
        return {
            "answer": f'I could not confirm a public {_platform_label(platform)} identity for "{query}" right now.',
            "bullets": [payload.get("summary") or CHATBOT_SCOPE_REPLY],
            "stat_cards": stat_cards,
            "follow_up": _build_public_search_follow_up(platform, payload),
        }

    lead = catalog[0]
    creator = lead.get("creator") or lead.get("title") or query
    title = lead.get("title") or "Top result"
    return {
        "answer": f'The top public {_platform_label(platform)} match for "{query}" is "{creator}".',
        "bullets": [bullet for bullet in [
            f'Top content title: "{title}"',
            f'Visible analytics summary: {_metric_summary(lead, platform)}',
            str(payload.get("summary") or "").strip(),
        ] if bullet],
        "stat_cards": stat_cards,
        "media_items": [_catalog_item_to_chat_media(lead, platform)],
        "follow_up": [
            f"Search {query} on {_platform_label(platform)} and summarize the analytics.",
            f"What public trends are live on {_platform_label(platform)}?",
        ],
    }


async def build_dashboard_chatbot_response(snapshot: dict, user: dict, message: str) -> dict:
    prompt = (message or "").strip()
    if not prompt:
        return {
            "answer": "Ask about dashboard values, connected accounts, public search analytics, trends, hashtags, or risk alerts.",
            "bullets": [],
            "follow_up": snapshot.get("chatbot", {}).get("starter_questions", [])[:3],
        }

    lowered = prompt.lower()
    recommendations = snapshot.get("recommendations") or []
    hashtags = snapshot.get("trending_hashtags") or []
    audience_cards = (snapshot.get("audience_insights") or {}).get("cards") or []
    crisis_alerts = snapshot.get("crisis_alerts") or []
    forecast = snapshot.get("predictive_analysis") or {}
    top_content = snapshot.get("top_content") or []
    moderation_queue = snapshot.get("moderation_queue") or []
    connected_accounts = snapshot.get("connected_accounts") or []
    requested_platforms = _extract_platforms_from_prompt(lowered)
    active_platforms = requested_platforms or [item.get("platform") for item in connected_accounts if item.get("platform")]
    active_platforms = [platform for platform in active_platforms if platform in {"instagram", "youtube", "x"}]
    active_platforms = list(dict.fromkeys(active_platforms)) or ["youtube", "instagram", "x"]
    entity_lookup_request = _extract_entity_lookup_request(prompt, active_platforms)
    public_search_request = _extract_public_search_request(prompt, active_platforms)
    feature_request = _contains_any_phrase(
        lowered,
        ("what does this app do", "what can this app do", "app features", "features", "synapse", "platform features", "how this app works", "how does this app work"),
    )
    model_request = _contains_any_phrase(lowered, ("which model", "what model", "model used", "models used", "model stack", "kaunsa model"))
    methodology_request = _contains_any_phrase(
        lowered,
        ("how calculate", "formula", "calculation", "calculated", "nikalte", "kaise nikalte", "kaise calculate"),
    )
    accuracy_request = _contains_any_phrase(lowered, ("100% exact", "fully exact", "accuracy", "accurate", "reliable", "exact"))

    if re.fullmatch(r"(hi|hello|hey|help)\W*", lowered):
        return {
            "answer": CHATBOT_SCOPE_REPLY,
            "bullets": [
                "Use it for dashboard values, connected account performance, public creator searches, and trend summaries.",
                "It will not answer coding or unrelated questions.",
            ],
            "follow_up": snapshot.get("chatbot", {}).get("starter_questions", [])[:4],
        }

    if feature_request:
        return _build_feature_summary_response(snapshot)

    if model_request:
        return _build_model_stack_response(snapshot)

    if methodology_request:
        return _build_methodology_response(prompt)

    if accuracy_request:
        return _build_accuracy_response(snapshot)

    if entity_lookup_request:
        return await _build_entity_lookup_response(user, entity_lookup_request[0], entity_lookup_request[1])

    if _is_code_request(prompt):
        return {
            "answer": "Coding help is disabled in this assistant.",
            "bullets": [
                CHATBOT_SCOPE_REPLY,
                "Ask about engagement, audience reach, connected accounts, hashtags, public searches, or content performance instead.",
            ],
            "follow_up": snapshot.get("chatbot", {}).get("starter_questions", [])[:3],
        }

    if not _is_domain_prompt(prompt) and len(prompt.split()) >= 5:
        return {
            "answer": CHATBOT_SCOPE_REPLY,
            "bullets": [
                "It is restricted to AI social media analytics only.",
                "Use platform names, dashboard metrics, or public search queries in your question.",
            ],
            "follow_up": snapshot.get("chatbot", {}).get("starter_questions", [])[:3],
        }

    if public_search_request:
        return await _build_public_search_chat_response(user, public_search_request[0], public_search_request[1])

    timing_request = _contains_any_phrase(
        lowered,
        (
            "best posting time",
            "best time",
            "posting window",
            "post timing",
            "when should i post",
            "when to post",
            "schedule next post",
            "publish window",
        ),
    )
    hashtag_request = "hashtag" in lowered or bool(re.search(r"(?<!\w)#\w+", prompt))
    connected_request = _contains_any_phrase(
        lowered,
        (
            "connected account",
            "connected accounts",
            "connected source",
            "connected sources",
            "account summary",
            "my accounts",
            "my sources",
        ),
    )
    audience_request = _contains_any_phrase(lowered, ("audience", "reach", "followers", "follower"))
    risk_request = _contains_any_phrase(lowered, ("crisis", "risk", "toxic", "toxicity", "alert", "negative spike"))
    caption_request = _contains_any_phrase(lowered, ("caption", "hook", "sound like", "copy direction"))
    content_format_request = _contains_any_phrase(lowered, ("content format", "strongest format", "best format", "format is strongest"))
    trend_request = _contains_any_phrase(lowered, ("trending", "trend", "viral", "public trend", "public trends"))
    comment_activity_request = _contains_any_phrase(
        lowered,
        ("comment activity", "reply activity", "most comments", "most replies", "comment-heavy", "reply-heavy", "conversation"),
    )
    risk_item_request = _contains_any_phrase(lowered, ("most at risk", "highest risk", "most toxic item", "risky content"))
    top_content_request = _contains_any_phrase(
        lowered,
        ("top content", "best content", "strongest content", "top post", "best post", "performing best", "top performer"),
    )
    latest_media_request = _contains_any_phrase(
        lowered,
        ("latest media", "recent media", "latest video", "latest reel", "latest photo", "latest content", "show latest"),
    )
    moderation_queue_request = _contains_any_phrase(lowered, ("moderation queue", "review queue", "flagged item", "flagged items"))

    if timing_request:
        timing = next((item for item in recommendations if item.get("category") == "timing"), None)
        best_window = timing.get("body") if timing else "The best posting window is not available yet."
        return {
            "answer": best_window,
            "bullets": [
                f'Forecast direction: {forecast.get("trend_direction", "Stable")}',
                f'Predicted change: {forecast.get("predicted_change_pct", 0.0):.1f}%',
            ],
            "stat_cards": [
                _card("Best day", str(forecast.get("best_day", "n/a"))),
                _card("Best window", str(forecast.get("best_time_window", "Evening"))),
                _card("Momentum", f'{forecast.get("predicted_change_pct", 0.0):.1f}%'),
            ],
            "follow_up": ["Which content format is strongest?", "Which hashtags should I use next?"],
        }

    if hashtag_request:
        return {
            "answer": "These are the strongest recurring tags in the current indexed content set.",
            "bullets": [f'{item["tag"]} used {item["count"]} time(s)' for item in hashtags[:5]],
            "stat_cards": [
                _card("Recurring tags", str(len(hashtags))),
                _card("Top tag", hashtags[0]["tag"] if hashtags else "n/a"),
            ],
            "follow_up": ["What should the next caption sound like?", "Which platform is leading my audience?"],
        }

    if connected_request:
        if connected_accounts:
            return {
                "answer": "These are the connected social accounts currently feeding your workspace.",
                "bullets": [
                    f'{item["platform_label"]}: {item["account_name"]} ({item.get("primary_metric", "Connected")})'
                    for item in connected_accounts[:4]
                ],
                "stat_cards": [
                    _card(item["platform_label"], item.get("primary_metric", "Connected"), item.get("secondary_metric"))
                    for item in connected_accounts[:4]
                ],
                "follow_up": ["Show the latest media from my connected accounts.", "Which platform leads my audience right now?"],
            }
        return {
            "answer": "No social account is connected yet, so the assistant can only use the public explore modes right now.",
            "bullets": ["Connect Instagram, YouTube, or X / Twitter to unlock account-specific analytics."],
            "follow_up": ["What is trending publicly right now?", "Which hashtags should I watch?"],
        }

    if audience_request:
        return {
            "answer": "Here is the current audience summary across connected platforms.",
            "bullets": [f'{card["label"]}: {card["value"]}' for card in audience_cards[:4]],
            "stat_cards": [_card(card["label"], card["value"], card.get("detail")) for card in audience_cards[:4]],
            "follow_up": ["What is my best posting time?", "Do I have any crisis risks right now?"],
        }

    if caption_request:
        caption = next((item for item in recommendations if item.get("category") == "caption"), None)
        return {
            "answer": caption.get("body") if caption else "Caption direction will appear after enough content is indexed.",
            "bullets": [
                f'Trend outlook: {forecast.get("trend_direction", "Stable")}',
                f'Viral opportunity: {forecast.get("viral_opportunity", "Medium")}',
            ],
            "follow_up": ["Which hashtags should I reuse next?", "Which content format is strongest?"],
        }

    if content_format_request:
        format_card = next((card for card in audience_cards if card.get("label") == "Top content format"), None)
        window_card = next((card for card in audience_cards if card.get("label") == "Best publishing window"), None)
        return {
            "answer": (
                f'{format_card.get("value")} is the strongest visible format in the current indexed content set.'
                if format_card
                else "Content format guidance will appear after more content is indexed."
            ),
            "bullets": [detail for detail in [format_card.get("detail") if format_card else "", window_card.get("detail") if window_card else ""] if detail],
            "stat_cards": [
                _card(card["label"], card["value"], card.get("detail"))
                for card in audience_cards
                if card.get("label") in {"Top content format", "Best publishing window"}
            ],
            "follow_up": ["What should the next caption sound like?", "What is my best posting time?"],
        }

    if risk_request:
        if crisis_alerts:
            return {
                "answer": "The dashboard found moderation or sentiment signals that may need attention.",
                "bullets": [f'{item["title"]}: {item["recommended_action"]}' for item in crisis_alerts[:3]],
                "stat_cards": [
                    _card("Active alerts", str(len(crisis_alerts))),
                    _card("Moderation queue", str(len(moderation_queue))),
                ],
                "follow_up": ["Which content item is most at risk?", "What is my best posting time?"],
            }
        return {
            "answer": "No active crisis alert is dominating the workspace right now.",
            "bullets": ["Sentiment and toxicity are within the current safe threshold window."],
            "follow_up": ["Which platform leads my audience?", "Which hashtags should I reuse next?"],
        }

    if risk_item_request:
        top_flag = moderation_queue[0] if moderation_queue else None
        if top_flag:
            return {
                "answer": f'"{top_flag["title"]}" is the most at-risk indexed item right now.',
                "bullets": [
                    f'Platform: {top_flag["platform"]}',
                    f'Toxicity: {top_flag["toxicity"]}%',
                    f'Sentiment: {top_flag["sentiment"]} / Emotion: {top_flag["emotion"]}',
                ],
                "follow_up": ["Do I have any crisis risks right now?", "What is my best posting time?"],
            }
        return {
            "answer": "No indexed item is currently standing out as a high-risk moderation case.",
            "bullets": ["The review queue is currently below the stronger risk threshold."],
            "follow_up": ["Do I have any crisis risks right now?", "Which platform leads my audience?"],
        }

    if trend_request:
        media_items, stat_cards = await _load_public_trending_media(user, active_platforms, limit=4)
        if media_items:
            platforms_label = ", ".join(_platform_label(platform) for platform in active_platforms[:3])
            return {
                "answer": f"I pulled live public trend signals from {platforms_label} and attached the strongest media cards below.",
                "bullets": [
                    "Use the cards to inspect thumbnails, comments, views, and open the original post or video.",
                    "Ask for a specific platform if you want the assistant to narrow the trend scan.",
                ],
                "stat_cards": stat_cards,
                "media_items": media_items,
                "follow_up": ["Show the latest content from my connected accounts.", "Which hashtags from these trends should I test next?"],
            }
        return {
            "answer": "Live public trending data is not available right now for the requested platforms.",
            "bullets": ["Try asking for a connected account summary or a specific platform instead."],
            "follow_up": ["Show my connected account analytics.", "What is my best posting time?"],
        }

    if comment_activity_request:
        conversation_items = await _load_top_conversation_items(user, active_platforms, limit=4)
        if conversation_items:
            return {
                "answer": "These items currently have the strongest visible comment or reply activity in your connected feeds.",
                "bullets": [f'{item["platform"]}: {item["metric"]}' for item in conversation_items[:4]],
                "media_items": conversation_items,
                "follow_up": ["Do any of these comment threads look risky?", "Show the latest content from the same platform."],
            }
        return {
            "answer": "Comment-heavy items will appear here once connected feeds return visible comment or reply counts.",
            "bullets": [],
            "follow_up": ["Show the latest media from my connected accounts.", "Do I have any crisis risks right now?"],
        }

    if top_content_request:
        top_item = top_content[0] if top_content else None
        if not top_item:
            return {
                "answer": "Top content will appear after more connected posts are indexed.",
                "bullets": [],
                "follow_up": snapshot.get("chatbot", {}).get("starter_questions", [])[:3],
            }
        return {
            "answer": f'"{top_item.get("title")}" is the strongest current content signal.',
            "bullets": [
                f'Platform: {top_item.get("platform")}',
                f'Performance: {top_item.get("metric")}',
                top_item.get("insight") or "This item currently leads the scored content set.",
            ],
            "media_items": [top_item],
            "follow_up": ["What posting window should I use?", "Which hashtags match this content?"],
        }

    if latest_media_request:
        media_items = await _load_connected_preview_media(user, active_platforms, limit=4)
        if media_items:
            return {
                "answer": "Here are the latest connected media items I could surface right now.",
                "bullets": [
                    "Open the cards to play videos, inspect thumbnails, and jump to the original source.",
                    "Ask for YouTube, Instagram, or X / Twitter specifically if you want a narrower media list.",
                ],
                "media_items": media_items,
                "follow_up": ["Which of these latest items is performing best?", "What is trending publicly right now?"],
            }

        media_items, _ = await _load_public_trending_media(user, active_platforms, limit=4)
        if media_items:
            return {
                "answer": "No connected media was ready, so I surfaced live public media instead.",
                "bullets": ["Connect your account if you want owner-linked analytics on these cards."],
                "media_items": media_items,
                "follow_up": ["Show my connected account analytics.", "Which platform leads my audience right now?"],
            }

        return {
            "answer": "I could not find recent playable media for the requested platforms right now.",
            "bullets": [],
            "follow_up": snapshot.get("chatbot", {}).get("starter_questions", [])[:3],
        }

    if moderation_queue_request:
        return {
            "answer": "These are the current moderation-priority items from the indexed sample.",
            "bullets": [
                f'{item["platform"]}: {item["title"]} ({item["toxicity"]}% toxicity)'
                for item in moderation_queue[:4]
            ] or ["No moderation item is currently above the review threshold."],
            "stat_cards": [
                _card("Flagged items", str(len(moderation_queue))),
                _card("Highest toxicity", f'{moderation_queue[0]["toxicity"]}%' if moderation_queue else "0%"),
            ],
            "follow_up": ["Do I have any crisis risks right now?", "Which platform leads my audience?"],
        }

    return {
        "answer": "Here is the current AI social media dashboard summary in plain English.",
        "bullets": [
            f'Connected accounts: {next((item.get("value") for item in snapshot.get("overview", []) if item.get("label") == "Connected Accounts"), "0")}',
            f'Overall mood: {next((item.get("value") for item in snapshot.get("overview", []) if item.get("label") == "Overall Mood"), "n/a")}',
            f'Forecast: {forecast.get("trend_direction", "Stable")} ({forecast.get("predicted_change_pct", 0.0):.1f}%)',
        ],
        "stat_cards": [
            _card(item.get("label", "Metric"), item.get("value", "0"), item.get("delta"))
            for item in snapshot.get("overview", [])[:4]
        ],
        "media_items": top_content[:2],
        "follow_up": snapshot.get("chatbot", {}).get("starter_questions", [])[:3],
    }


async def build_dashboard_snapshot(user: dict, *, force_refresh: bool = False) -> dict:
    user_id = user["id"]
    cache_key = _dashboard_cache_key(user_id)
    if not force_refresh:
        cached = await get_json(cache_key)
        if isinstance(cached, dict) and cached:
            return cached

    db = get_database()
    connections = await db.social_accounts.find({"user_id": user_id}).to_list(length=20)
    connection_map = {item["platform"]: item for item in connections}
    reports = await db.reports.find({"user_id": user_id}).sort("created_at", -1).to_list(length=3)

    previews: dict[str, dict] = {}
    for platform in ("youtube", "instagram", "x"):
        if platform in connection_map:
            preview = await get_connected_platform_preview(platform, user)
            if preview:
                previews[platform] = preview

    if not previews:
        snapshot = {
            "overview": [
                {"label": "Connected Accounts", "value": "0", "delta": "Connect a source to start live analytics.", "tone": "neutral"},
                {"label": "Audience Total", "value": "0", "delta": "Waiting for connected audience data.", "tone": "neutral"},
                {"label": "Interactions", "value": "0", "delta": "No indexed content is available yet.", "tone": "neutral"},
                {"label": "Overall Mood", "value": "n/a", "delta": "Mood analysis will appear after captions and comments are indexed.", "tone": "neutral"},
            ],
            "sentiment_breakdown": [],
            "emotion_breakdown": [],
            "platform_comparison": [],
            "engagement_trend": [],
            "top_content": [],
            "recommendations": _build_recommendations([], None, "n/a", "Evening", "Neutral", _build_forecast([])),
            "alerts_preview": [],
            "report_preview": [],
            "platform_rollups": [],
            "toxicity_summary": {"label": "0%", "ratio": 0.0, "flagged_items": []},
            "audience_insights": {"cards": [], "notes": []},
            "predictive_analysis": _build_forecast([]),
            "explainable_ai": _build_explainability([], [], [], _build_forecast([]), []),
            "trending_hashtags": [],
            "chatbot": _build_chatbot_payload("n/a", "Evening", "n/a"),
            "moderation_queue": [],
            "crisis_alerts": [],
            "connected_accounts": [],
            "model_stack": get_model_stack(),
        }
        snapshot = _json_safe(snapshot)
        await set_json(cache_key, snapshot, get_settings().dashboard_cache_ttl_seconds)
        return snapshot

    audience_total = 0
    interaction_total = 0
    indexed_content_total = 0
    all_texts: list[str] = []
    all_content: list[dict] = []
    trend_buckets: dict[str, int] = defaultdict(int)
    content_types = Counter()
    platform_rollups: list[dict] = []
    platform_comparison: list[dict] = []

    for platform, preview in previews.items():
        catalog = preview.get("catalog") or []
        catalog_with_platform = [{**item, "platform": platform} for item in catalog]
        indexed_content_total += len(catalog_with_platform)
        all_content.extend(catalog_with_platform)
        all_texts.extend(_build_text_payload(item) for item in catalog_with_platform if _build_text_payload(item).strip())
        content_types.update(str(item.get("type") or "Content") for item in catalog_with_platform)

        for item in catalog_with_platform:
            parsed_date = _parse_published_at(item.get("published_at"))
            if parsed_date:
                trend_buckets[parsed_date.strftime("%a")] += _score_content(item)

        if platform == "youtube":
            stats = ((connection_map.get(platform, {}).get("extra") or {}).get("statistics") or {})
            subscribers = _safe_int(stats.get("subscriberCount"))
            total_views = sum(_safe_int((item.get("metric_values") or {}).get("views")) for item in catalog_with_platform)
            total_comments = sum(_safe_int((item.get("metric_values") or {}).get("comments")) for item in catalog_with_platform)
            total_likes = sum(_safe_int((item.get("metric_values") or {}).get("likes")) for item in catalog_with_platform)
            interactions = total_likes + total_comments
            rate = _engagement_rate(max(total_views, subscribers), interactions)
            audience_total += subscribers
            interaction_total += interactions
            platform_rollups.append(
                {
                    "platform": platform,
                    "title": "YouTube",
                    "headline": f"{_format_count(subscribers)} subscribers",
                    "metrics": [
                        {"label": "Loaded videos", "value": str(len(catalog_with_platform))},
                        {"label": "Views", "value": _format_count(total_views)},
                        {"label": "Interactions", "value": _format_count(interactions)},
                        {"label": "Engagement rate", "value": _format_percent(rate)},
                    ],
                }
            )
            platform_comparison.append(
                {
                    "platform": "YouTube",
                    "engagement": interactions,
                    "reach": max(subscribers, total_views),
                    "engagement_rate": rate,
                }
            )

        elif platform == "instagram":
            instagram_meta = ((connection_map.get(platform, {}).get("extra") or {}).get("instagram") or {})
            followers = _safe_int(instagram_meta.get("followers_count"))
            total_likes = sum(_safe_int((item.get("metric_values") or {}).get("likes")) for item in catalog_with_platform)
            total_comments = sum(_safe_int((item.get("metric_values") or {}).get("comments")) for item in catalog_with_platform)
            interactions = total_likes + total_comments
            rate = _engagement_rate(max(followers, len(catalog_with_platform) * 100), interactions)
            audience_total += followers
            interaction_total += interactions
            platform_rollups.append(
                {
                    "platform": platform,
                    "title": "Instagram",
                    "headline": f"{_format_count(followers)} followers",
                    "metrics": [
                        {"label": "Loaded posts", "value": str(len(catalog_with_platform))},
                        {"label": "Likes", "value": _format_count(total_likes)},
                        {"label": "Comments", "value": _format_count(total_comments)},
                        {"label": "Engagement rate", "value": _format_percent(rate)},
                    ],
                }
            )
            platform_comparison.append(
                {
                    "platform": "Instagram",
                    "engagement": interactions,
                    "reach": followers,
                    "engagement_rate": rate,
                }
            )

        elif platform == "x":
            extra = connection_map.get(platform, {}).get("extra") or {}
            profile = extra.get("profile") or {}
            profile_metrics = profile.get("public_metrics") or {}
            followers = _safe_int(profile_metrics.get("followers_count"))
            posts_processed = _safe_int(extra.get("posts_processed")) or len(catalog_with_platform)
            total_views = sum(_safe_int((item.get("metric_values") or {}).get("views")) for item in catalog_with_platform)
            total_likes = sum(_safe_int((item.get("metric_values") or {}).get("likes")) for item in catalog_with_platform)
            total_replies = sum(_safe_int((item.get("metric_values") or {}).get("replies")) for item in catalog_with_platform)
            total_reposts = sum(
                _safe_int((item.get("metric_values") or {}).get("reposts"))
                + _safe_int((item.get("metric_values") or {}).get("retweets"))
                for item in catalog_with_platform
            )
            toxicity_scores = [classify_text(_build_text_payload(item)).get("toxicity", 0) for item in catalog_with_platform]
            toxicity_avg = round(mean(toxicity_scores) * 100, 1) if toxicity_scores else 0.0
            interactions = total_likes + total_replies + total_reposts
            rate = _engagement_rate(max(followers, total_views, posts_processed), interactions)
            audience_total += followers
            interaction_total += interactions
            platform_rollups.append(
                {
                    "platform": platform,
                    "title": "X / Twitter",
                    "headline": f"{_format_count(followers)} followers",
                    "metrics": [
                        {"label": "Loaded posts", "value": str(posts_processed)},
                        {"label": "Views", "value": _format_count(total_views)},
                        {"label": "Engagement", "value": _format_count(interactions)},
                        {"label": "Toxicity", "value": _format_percent(toxicity_avg)},
                    ],
                }
            )
            platform_comparison.append(
                {
                    "platform": "X / Twitter",
                    "engagement": interactions,
                    "reach": max(followers, total_views, posts_processed),
                    "engagement_rate": rate,
                }
            )

    connected_accounts = []
    for platform in ("instagram", "youtube", "x"):
        connection = connection_map.get(platform)
        preview = previews.get(platform)
        if not connection or not preview:
            continue

        cards = preview.get("trending_cards") or []
        primary_metric = cards[0] if cards else {}
        secondary_metric = cards[1] if len(cards) > 1 else {}
        connected_accounts.append(
            {
                "platform": platform,
                "platform_label": _platform_label(platform),
                "account_name": connection.get("account_name") or connection.get("handle") or _platform_label(platform),
                "handle": connection.get("handle"),
                "avatar_url": _connected_account_avatar(platform, connection),
                "external_url": _connected_account_url(platform, connection, preview),
                "status": connection.get("status", "connected"),
                "connected_at": connection.get("connected_at"),
                "primary_metric": (
                    f'{primary_metric.get("value")} {str(primary_metric.get("name") or "").lower()}'.strip()
                    if primary_metric
                    else "Connected"
                ),
                "secondary_metric": (
                    f'{secondary_metric.get("value")} {str(secondary_metric.get("name") or "").lower()}'.strip()
                    if secondary_metric
                    else None
                ),
            }
        )

    sentiment_breakdown = _sentiment_percentages(all_texts)
    analysis_summary = analyze_text_batch(all_texts)
    dominant_sentiment = analysis_summary.get("sentiment_label", "neutral").title()
    dominant_emotion = (
        (analysis_summary.get("emotion_breakdown") or [{}])[0].get("name", "Concern")
        if analysis_summary.get("emotion_breakdown")
        else "Concern"
    )
    combined_mood = f"{dominant_sentiment} / {dominant_emotion}"
    top_content = sorted(all_content, key=_score_content, reverse=True)[:6]
    top_item = top_content[0] if top_content else None

    top_content_rows = []
    for item in top_content:
        metrics = item.get("metric_values") or {}
        if item.get("platform") == "youtube":
            metric = f"{_format_count(metrics.get('views'))} views"
        elif item.get("platform") == "instagram":
            metric = f"{_format_count(metrics.get('likes'))} likes"
        else:
            metric = f"{_format_count(metrics.get('views'))} views / {_format_count(metrics.get('likes'))} likes"
        top_content_rows.append(
            {
                "id": item.get("id"),
                "title": item.get("title"),
                "platform": _platform_label(item.get("platform", "")),
                "platform_key": item.get("platform"),
                "creator": item.get("creator"),
                "type": item.get("type"),
                "metric": metric,
                "insight": item.get("insight"),
                "thumbnail": item.get("thumbnail"),
                "url": item.get("url"),
                "video_id": item.get("video_id"),
                "media_url": item.get("media_url"),
                "player_type": _top_content_player_type(item),
            }
        )

    engagement_trend = [{"day": day, "value": trend_buckets.get(day, 0)} for day in DAY_ORDER if day in trend_buckets]
    if not engagement_trend:
        engagement_trend = [{"day": day, "value": 0} for day in DAY_ORDER[:3]]
    forecast = _build_forecast(engagement_trend)
    best_time_window = _best_time_window(all_content)
    forecast["best_time_window"] = best_time_window

    trending_hashtags = _extract_trending_hashtags(all_content)
    moderation_queue = _build_moderation_queue(all_content)
    audience_insights = _build_audience_insights(
        platform_comparison,
        content_types,
        forecast.get("best_day", "n/a"),
        best_time_window,
        top_content_rows,
    )
    crisis_alerts = _build_crisis_alerts(
        sentiment_breakdown,
        moderation_queue,
        forecast,
        max(platform_comparison, key=lambda item: item.get("reach", 0), default={"platform": "your connected source"}).get("platform", "your connected source"),
    )
    recommendations = _build_recommendations(
        trending_hashtags,
        top_item,
        forecast.get("best_day", "n/a"),
        best_time_window,
        dominant_emotion,
        forecast,
    )
    explainable_ai = _build_explainability(platform_comparison, sentiment_breakdown, moderation_queue, forecast, trending_hashtags)
    chatbot = _build_chatbot_payload(
        forecast.get("best_day", "n/a"),
        best_time_window,
        max(platform_comparison, key=lambda item: item.get("reach", 0), default={"platform": "n/a"}).get("platform", "n/a"),
    )

    report_preview = [
        {
            "id": item.get("_id"),
            "title": item.get("title") or "Insight report",
            "period": str(item.get("period") or "custom").title(),
            "created_at": item.get("created_at"),
        }
        for item in reports
    ]

    toxicity_summary = {
        "label": _format_percent((analysis_summary.get("toxicity_ratio", 0.0) or 0.0) * 100),
        "ratio": analysis_summary.get("toxicity_ratio", 0.0) or 0.0,
        "flagged_items": moderation_queue,
    }

    snapshot = {
        "overview": [
            {"label": "Connected Accounts", "value": str(len(previews)), "delta": f"{indexed_content_total} indexed content items are feeding live analytics.", "tone": "positive"},
            {"label": "Audience Total", "value": _format_count(audience_total), "delta": "Combined visible audience across connected platforms.", "tone": "positive"},
            {"label": "Interactions", "value": _format_count(interaction_total), "delta": "Likes, comments, replies, reposts, and other visible engagement signals.", "tone": "positive"},
            {"label": "Overall Mood", "value": combined_mood, "delta": "Built from current caption, post, and conversation text.", "tone": "neutral"},
        ],
        "sentiment_breakdown": sentiment_breakdown,
        "emotion_breakdown": analysis_summary.get("emotion_breakdown") or [],
        "platform_comparison": platform_comparison,
        "engagement_trend": engagement_trend,
        "top_content": top_content_rows,
        "recommendations": recommendations,
        "alerts_preview": crisis_alerts,
        "report_preview": report_preview,
        "platform_rollups": platform_rollups,
        "toxicity_summary": toxicity_summary,
        "audience_insights": audience_insights,
        "predictive_analysis": forecast,
        "explainable_ai": explainable_ai,
        "trending_hashtags": trending_hashtags,
        "chatbot": chatbot,
        "moderation_queue": moderation_queue,
        "crisis_alerts": crisis_alerts,
        "connected_accounts": connected_accounts,
        "model_stack": analysis_summary.get("model_stack") or get_model_stack(),
    }
    snapshot = _json_safe(snapshot)
    await set_json(cache_key, snapshot, get_settings().dashboard_cache_ttl_seconds)
    return snapshot
