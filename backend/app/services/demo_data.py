from datetime import datetime, timedelta, timezone
from random import randint


def utcnow():
    return datetime.now(timezone.utc)


def _clean_demo_value(value):
    if isinstance(value, str):
        return (
            value.replace("\u00e2\u20ac\u201d", "-")
            .replace("\u2014", "-")
            .replace("\u00c2\u00a9", "(c)")
            .replace("\u00a9", "(c)")
            .replace("caf\u00c3\u00a9", "cafe")
            .replace("caf\u00e9", "cafe")
        )
    if isinstance(value, list):
        return [_clean_demo_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _clean_demo_value(item) for key, item in value.items()}
    return value


PUBLIC_DISCOVERY = {
    "instagram": {
        "headline": "Trending on Instagram",
        "summary": "Discover what's trending right now - top reels, popular creators, and engagement insights across Instagram.",
        "search_placeholder": "Search reels, creators, beauty, fashion...",
        "preview_label": "Trending content",
        "trending_cards": [
            {"name": "Avg Reel Reach", "value": "84K", "tone": "positive"},
            {"name": "Save Rate", "value": "7.4%", "tone": "positive"},
            {"name": "Positive Mood", "value": "76%", "tone": "positive"},
        ],
        "hero_metrics": [
            {"label": "Top format", "value": "Short tutorial reel"},
            {"label": "Best posting time", "value": "7:15 PM"},
            {"label": "Best CTA", "value": "Save this for later"},
        ],
        "featured_profiles": [
            {"name": "Astra Beauty", "type": "Brand", "insight": "Tutorial reels outperform offer posts by 2.3x."},
            {"name": "Noor Frames", "type": "Creator", "insight": "Behind-the-scenes clips trigger comment spikes."},
            {"name": "Studio Eight", "type": "Brand", "insight": "Weekly recaps drive saves and profile revisits."},
        ],
        "catalog": [
            {
                "id": "ig-1",
                "title": "Glow serum tutorial in 20 seconds",
                "creator": "Astra Beauty",
                "creator_url": "https://www.instagram.com/aabortiux/",
                "type": "Reel",
                "duration": "0:21",
                "theme": "sunset",
                "description": "Fast hook, product close-up, and clear before/after payoff.",
                "url": "https://www.instagram.com/reel/example1/",
                "url_label": "View on Instagram",
                "tags": ["beauty", "tutorial", "skincare", "product launch"],
                "metrics": [
                    {"label": "Views", "value": "84.2K"},
                    {"label": "Likes", "value": "9.6K"},
                    {"label": "Comments", "value": "612"},
                    {"label": "Saves", "value": "1.8K"},
                ],
                "insight": "The first 2 seconds create the entire retention curve here.",
            },
            {
                "id": "ig-2",
                "title": "Wardrobe reset before a live event",
                "creator": "Noor Frames",
                "creator_url": "https://www.instagram.com/noorframes/",
                "type": "Carousel",
                "duration": "7 slides",
                "theme": "ocean",
                "description": "A step-by-step creator workflow with clean cover text.",
                "url": "https://www.instagram.com/p/example2/",
                "url_label": "View on Instagram",
                "tags": ["fashion", "creator", "routine", "event prep"],
                "metrics": [
                    {"label": "Reach", "value": "52.7K"},
                    {"label": "Likes", "value": "6.1K"},
                    {"label": "Comments", "value": "284"},
                    {"label": "Shares", "value": "931"},
                ],
                "insight": "Swipe-based storytelling is driving the share rate here.",
            },
            {
                "id": "ig-3",
                "title": "Studio morning BTS with voice-over",
                "creator": "Studio Eight",
                "creator_url": "https://www.instagram.com/studioeight/",
                "type": "Reel",
                "duration": "0:33",
                "theme": "mint",
                "description": "Ambient cuts plus one-line voice-over showing the making process.",
                "url": "https://www.instagram.com/reel/example3/",
                "url_label": "View on Instagram",
                "tags": ["behind the scenes", "studio", "creator process", "community"],
                "metrics": [
                    {"label": "Views", "value": "71.9K"},
                    {"label": "Likes", "value": "8.3K"},
                    {"label": "Comments", "value": "421"},
                    {"label": "Saves", "value": "1.1K"},
                ],
                "insight": "Community comments increased when the creator appeared on camera earlier.",
            },
            {
                "id": "ig-4",
                "title": "Travel edit with hidden gem cafe stop",
                "creator": "Luma Trails",
                "creator_url": "https://www.instagram.com/lumatrails/",
                "type": "Reel",
                "duration": "0:18",
                "theme": "violet",
                "description": "Fast transitions, location text overlay, and geo-style storytelling.",
                "url": "https://www.instagram.com/reel/example4/",
                "url_label": "View on Instagram",
                "tags": ["travel", "reels", "cafe", "lifestyle"],
                "metrics": [
                    {"label": "Views", "value": "93.5K"},
                    {"label": "Likes", "value": "10.4K"},
                    {"label": "Comments", "value": "359"},
                    {"label": "Shares", "value": "1.3K"},
                ],
                "insight": "Place-based hooks are generating higher shares than generic lifestyle edits.",
            },
        ],
        "preview_charts": [
            {"label": "Mon", "value": 38},
            {"label": "Tue", "value": 56},
            {"label": "Wed", "value": 49},
            {"label": "Thu", "value": 68},
            {"label": "Fri", "value": 82},
        ],
        "suggested_searches": ["beauty tutorials", "music reels", "travel edits", "community management"],
        "side_insights": [
            {"title": "What to notice", "body": "Likes alone are misleading. Saves and shares usually predict stronger long-tail performance."},
            {"title": "Why this matters", "body": "Explore trending content to understand what performs well before connecting your own account."},
        ],
    },
    "youtube": {
        "headline": "Trending on YouTube",
        "summary": "Explore trending videos, popular channels, and watch-time insights across YouTube. Click any video to watch it right here.",
        "search_placeholder": "Search tutorials, creators, trending topics...",
        "preview_label": "Trending videos",
        "trending_cards": [
            {"name": "Avg Watch Time", "value": "6m 12s", "tone": "positive"},
            {"name": "CTR Signal", "value": "7.8%", "tone": "positive"},
            {"name": "Comment Depth", "value": "412 avg", "tone": "positive"},
        ],
        "hero_metrics": [
            {"label": "Best thumbnail style", "value": "Face + bold promise"},
            {"label": "Top growth driver", "value": "Short + long-form pairing"},
            {"label": "Sweet spot length", "value": "8 to 11 min explainers"},
        ],
        "featured_profiles": [
            {"name": "MrBeast", "type": "Channel", "insight": "High production + philanthropy content drives massive engagement."},
            {"name": "Fireship", "type": "Channel", "insight": "100-second explainers get highest retention in tech niche."},
            {"name": "Veritasium", "type": "Channel", "insight": "Science storytelling with strong hooks outperforms traditional lectures."},
        ],
        "catalog": [
            {
                "id": "yt-1",
                "title": "I Built 100 Wells in Africa",
                "creator": "MrBeast",
                "creator_url": "https://www.youtube.com/@MrBeast",
                "type": "Video",
                "duration": "18:42",
                "theme": "sunset",
                "description": "MrBeast's philanthropy video combining entertainment with making a real difference.",
                "video_id": "hJVOaSwJHQ0",
                "url": "https://www.youtube.com/watch?v=hJVOaSwJHQ0",
                "url_label": "Watch on YouTube",
                "tags": ["philanthropy", "mrbeast", "trending", "entertainment"],
                "metrics": [
                    {"label": "Views", "value": "180M"},
                    {"label": "Likes", "value": "8.2M"},
                    {"label": "Comments", "value": "142K"},
                ],
                "insight": "Combining entertainment with real impact creates the strongest emotional connection with viewers.",
            },
            {
                "id": "yt-2",
                "title": "God-Tier Developer Roadmap",
                "creator": "Fireship",
                "creator_url": "https://www.youtube.com/@Fireship",
                "type": "Short",
                "duration": "0:58",
                "theme": "ocean",
                "description": "A rapid-fire developer roadmap that packs maximum value into under a minute.",
                "video_id": "pEfrdAtAmqk",
                "url": "https://www.youtube.com/watch?v=pEfrdAtAmqk",
                "url_label": "Watch on YouTube",
                "tags": ["coding", "developer", "roadmap", "tech"],
                "metrics": [
                    {"label": "Views", "value": "4.2M"},
                    {"label": "Likes", "value": "198K"},
                    {"label": "Comments", "value": "3.4K"},
                ],
                "insight": "Short, punchy educational content with fast pacing retains viewers better than long explanations.",
            },
            {
                "id": "yt-3",
                "title": "The Surprising Satisfying of How Things Are Made",
                "creator": "Veritasium",
                "creator_url": "https://www.youtube.com/@veritasium",
                "type": "Video",
                "duration": "21:14",
                "theme": "violet",
                "description": "Exploring the fascinating science behind everyday manufacturing processes.",
                "video_id": "bLNJZVTFpwI",
                "url": "https://www.youtube.com/watch?v=bLNJZVTFpwI",
                "url_label": "Watch on YouTube",
                "tags": ["science", "education", "manufacturing", "satisfying"],
                "metrics": [
                    {"label": "Views", "value": "32M"},
                    {"label": "Likes", "value": "890K"},
                    {"label": "Comments", "value": "12K"},
                ],
                "insight": "Curiosity-driven hooks paired with satisfying visuals create binge-worthy educational content.",
            },
            {
                "id": "yt-4",
                "title": "Every Programmer Should Know This",
                "creator": "Fireship",
                "creator_url": "https://www.youtube.com/@Fireship",
                "type": "Video",
                "duration": "11:08",
                "theme": "mint",
                "description": "Essential programming concepts explained with Fireship's signature fast-paced style.",
                "video_id": "Uo3cL4nrGOk",
                "url": "https://www.youtube.com/watch?v=Uo3cL4nrGOk",
                "url_label": "Watch on YouTube",
                "tags": ["programming", "fundamentals", "developer", "education"],
                "metrics": [
                    {"label": "Views", "value": "2.1M"},
                    {"label": "Likes", "value": "89K"},
                    {"label": "Comments", "value": "2.1K"},
                ],
                "insight": "One clear message per video with visual demonstrations creates the strongest learning retention.",
            },
        ],
        "preview_charts": [
            {"label": "Mon", "value": 41},
            {"label": "Tue", "value": 47},
            {"label": "Wed", "value": 52},
            {"label": "Thu", "value": 66},
            {"label": "Fri", "value": 79},
        ],
        "suggested_searches": ["MrBeast", "tech tutorials", "shorts", "trending"],
        "side_insights": [
            {"title": "What to notice", "body": "Views are only one metric. Watch time, CTR, and comment quality tell the real story."},
            {"title": "Why this matters", "body": "Explore what's working for top creators before connecting your own channel analytics."},
        ],
    },
    "x": {
        "headline": "Trending on X / Twitter",
        "summary": "See what's buzzing on X - trending conversations, viral tweets, and sentiment analysis across the platform.",
        "search_placeholder": "Search trending topics, creators, campaigns...",
        "preview_label": "Trending conversations",
        "trending_cards": [
            {"name": "Mood Score", "value": "68% positive", "tone": "positive"},
            {"name": "Hot Topic", "value": "AI & Tech", "tone": "positive"},
            {"name": "Viral Threads", "value": "24 today", "tone": "positive"},
        ],
        "hero_metrics": [
            {"label": "Top format", "value": "Thread + opinion"},
            {"label": "Best engagement", "value": "Question-style openers"},
            {"label": "Peak activity", "value": "12 PM - 3 PM"},
        ],
        "featured_profiles": [
            {"name": "@elonmusk", "type": "Creator", "insight": "Short, provocative takes generate highest engagement on the platform."},
            {"name": "@naval", "type": "Thought Leader", "insight": "Thread-style wisdom posts create strong bookmark and repost patterns."},
            {"name": "@levelsio", "type": "Indie Maker", "insight": "Building-in-public posts create authentic community engagement."},
        ],
        "catalog": [
            {
                "id": "x-1",
                "title": "We finally shipped the beta. Tell us what feels slow.",
                "creator": "@LaunchWire",
                "type": "Thread opener",
                "duration": "2h ago",
                "theme": "ocean",
                "description": "High-reply launch thread with support and criticism mixed together.",
                "tags": ["launch", "feedback", "community", "beta"],
                "metrics": [
                    {"label": "Replies", "value": "684"},
                    {"label": "Reposts", "value": "219"},
                    {"label": "Likes", "value": "1.8K"},
                    {"label": "Mood", "value": "Mixed"},
                ],
                "insight": "Launch posts that ask for feedback get 3x more engagement than announcement-only posts.",
            },
            {
                "id": "x-2",
                "title": "3 things creators still get wrong about retention",
                "creator": "@PulseNotes",
                "type": "Opinion post",
                "duration": "5h ago",
                "theme": "violet",
                "description": "A creator-style insight post that attracts quote-post discussion.",
                "tags": ["creator economy", "retention", "opinion", "education"],
                "metrics": [
                    {"label": "Replies", "value": "192"},
                    {"label": "Reposts", "value": "411"},
                    {"label": "Likes", "value": "3.4K"},
                    {"label": "Mood", "value": "Positive"},
                ],
                "insight": "Quote-post style spread is often stronger than reply count for expert threads.",
            },
            {
                "id": "x-3",
                "title": "Customers keep asking for dark mode and team export.",
                "creator": "@StudioThread",
                "type": "Feedback post",
                "duration": "8h ago",
                "theme": "mint",
                "description": "A request-collection post with useful product language buried in replies.",
                "tags": ["feature requests", "product", "users", "feedback"],
                "metrics": [
                    {"label": "Replies", "value": "301"},
                    {"label": "Reposts", "value": "74"},
                    {"label": "Likes", "value": "1.1K"},
                    {"label": "Mood", "value": "Neutral"},
                ],
                "insight": "Archive analysis helps turn messy reply threads into trend clusters and priorities.",
            },
            {
                "id": "x-4",
                "title": "This campaign headline missed the mark for me.",
                "creator": "@CommunityVoice",
                "type": "Reaction post",
                "duration": "1d ago",
                "theme": "sunset",
                "description": "A public criticism post where toxicity and negative spikes can grow fast.",
                "tags": ["campaign", "negative sentiment", "reaction", "brand safety"],
                "metrics": [
                    {"label": "Replies", "value": "127"},
                    {"label": "Reposts", "value": "88"},
                    {"label": "Likes", "value": "742"},
                    {"label": "Mood", "value": "Negative"},
                ],
                "insight": "Sentiment alerts and toxic-language filters help catch problems before they escalate.",
            },
        ],
        "preview_charts": [
            {"label": "Mon", "value": 29},
            {"label": "Tue", "value": 44},
            {"label": "Wed", "value": 62},
            {"label": "Thu", "value": 58},
            {"label": "Fri", "value": 71},
        ],
        "suggested_searches": ["launch feedback", "sentiment spike", "product complaints", "creator threads"],
        "side_insights": [
            {"title": "What to notice", "body": "Replies and repost patterns often matter more than raw likes for real conversation insight."},
            {"title": "Why this matters", "body": "Understanding conversation trends helps protect your brand and find opportunities."},
        ],
    },
}


def get_public_platform_cards() -> list[dict]:
    return _clean_demo_value([
        {
            "platform": "instagram",
            "title": "Instagram Insights",
            "subtitle": "Track your reels, stories, and engagement. See what's trending.",
            "cta": "Explore Instagram",
            "stats": ["Reels & Stories", "Engagement tracking", "Audience insights"],
        },
        {
            "platform": "youtube",
            "title": "YouTube Analytics",
            "subtitle": "Monitor your channel growth, video performance, and audience.",
            "cta": "Explore YouTube",
            "stats": ["Video analytics", "Watch time insights", "Subscriber growth"],
        },
        {
            "platform": "x",
            "title": "X / Twitter Pulse",
            "subtitle": "Analyze conversations, sentiment, and trending topics.",
            "cta": "Explore X",
            "stats": ["Sentiment analysis", "Trending topics", "Community mood"],
        },
    ])


def get_public_discovery(platform: str) -> dict:
    selected = PUBLIC_DISCOVERY.get(platform, PUBLIC_DISCOVERY["instagram"])
    return _clean_demo_value({"platform": platform, "data_source": "demo", **selected, "famous_cards": selected["featured_profiles"]})


def get_dashboard_snapshot(mode: str = "creator") -> dict:
    timestamp = utcnow()
    return {
        "overview": [
            {"label": "Total Reach", "value": "248K", "delta": "+14.2%", "tone": "positive"},
            {"label": "Engagement Rate", "value": "8.7%", "delta": "+1.1%", "tone": "positive"},
            {"label": "Toxic Comments", "value": "12", "delta": "-4", "tone": "positive"},
            {"label": "Negative Spike Risk", "value": "Low", "delta": "Stable", "tone": "neutral"},
        ],
        "sentiment_breakdown": [
            {"name": "Positive", "value": 68},
            {"name": "Neutral", "value": 21},
            {"name": "Negative", "value": 11},
        ],
        "platform_comparison": [
            {"platform": "Instagram", "engagement": 87, "reach": 92},
            {"platform": "YouTube", "engagement": 74, "reach": 81},
            {"platform": "X / Twitter", "engagement": 54, "reach": 46},
        ],
        "engagement_trend": [
            {"day": "Mon", "value": 36},
            {"day": "Tue", "value": 41},
            {"day": "Wed", "value": 39},
            {"day": "Thu", "value": 55},
            {"day": "Fri", "value": 63},
            {"day": "Sat", "value": 72},
            {"day": "Sun", "value": 66},
        ],
        "top_content": [
            {
                "id": "post-1",
                "title": "Behind the scenes studio reel",
                "platform": "Instagram",
                "metric": "11.8% ER",
                "insight": "Short hook + fast captions increased saves by 31%",
            },
            {
                "id": "post-2",
                "title": "Weekly creator recap",
                "platform": "YouTube",
                "metric": "6m 12s avg watch",
                "insight": "Mid-video CTA lifted comments without hurting retention",
            },
        ],
        "recommendations": [
            {"title": "Best posting window", "body": "Next 48 hours strongest window is 7:00 PM to 8:15 PM."},
            {"title": "Caption angle", "body": "Lead with a direct promise, then add one curiosity question."},
            {"title": "Hashtag mix", "body": "Use 2 broad tags, 3 niche tags, and 1 branded tag for balance."},
        ],
        "alerts_preview": [
            {
                "id": "alert-demo-1",
                "source_type": "ui",
                "platform": "instagram",
                "title": "Audience mood dipped on launch reel",
                "severity": "medium",
                "timestamp": timestamp,
                "explanation": "Negative comments grew by 18% in the last 6 hours.",
                "recommended_action": "Reply with a clarification comment and pin it.",
                "status": "unread",
                "affected_content": "Launch reel",
            },
            {
                "id": "alert-demo-2",
                "source_type": "system",
                "platform": "youtube",
                "title": "YouTube sync finished",
                "severity": "low",
                "timestamp": timestamp - timedelta(hours=3),
                "explanation": "Channel metrics and comments refreshed successfully.",
                "recommended_action": "Review the newest report snapshot.",
                "status": "acknowledged",
                "affected_content": "Weekly metrics sync",
            },
        ],
        "report_preview": [
            {
                "id": "report-demo-1",
                "title": f"{mode.title()} Weekly Pulse",
                "period": "weekly",
                "created_at": timestamp,
                "public_token": "demo-weekly-pulse",
                "insights": [
                    "Reels outperform static posts by 2.1x this week.",
                    "Comment tone stabilized after faster moderation.",
                ],
            }
        ],
    }


def get_admin_snapshot() -> dict:
    return {
        "overview": [
            {"label": "Active Users", "value": "42", "delta": "+8", "tone": "positive"},
            {"label": "Connected Providers", "value": "68", "delta": "+5", "tone": "positive"},
            {"label": "Failed Syncs", "value": "3", "delta": "-2", "tone": "positive"},
            {"label": "Open Moderation Items", "value": "14", "delta": "+4", "tone": "warning"},
        ],
        "provider_status": [
            {"provider": "instagram", "status": "healthy", "message": "Insights sync under 4m"},
            {"provider": "youtube", "status": "healthy", "message": "Quota usage at 23%"},
            {"provider": "x", "status": "healthy", "message": "Live X reads available"},
        ],
        "job_log": [
            {"job": "weekly-report-generator", "status": "completed", "time": "02:15 AM"},
            {"job": "moderation-queue", "status": "running", "time": "02:18 AM"},
            {"job": "instagram-refresh", "status": "warning", "time": "02:23 AM"},
        ],
        "user_rows": [
            {
                "name": "Sneha Ghadge",
                "mode": "brand",
                "providers": "Instagram, YouTube",
                "status": "active",
                "alerts": randint(1, 5),
            },
            {
                "name": "Anibeats",
                "mode": "creator",
                "providers": "Instagram, X / Twitter",
                "status": "active",
                "alerts": randint(0, 3),
            },
        ],
    }
