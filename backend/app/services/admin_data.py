from collections import Counter, defaultdict

from app.db.mongo import get_database


def _format_count(value: int) -> str:
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"{value / 1_000:.1f}K"
    return str(value)


def _provider_health(platform: str, connected: int, degraded: int, total: int) -> dict:
    labels = {"instagram": "Instagram", "youtube": "YouTube", "x": "X / Twitter"}
    label = labels.get(platform, platform.title())

    if total == 0:
        return {
            "provider": platform,
            "label": label,
            "status": "warning",
            "message": f"No {label} connection has been added yet.",
        }

    if connected > 0:
        return {
            "provider": platform,
            "label": label,
            "status": "healthy",
            "message": (
                f"{connected} {label} connection(s) are active."
                if degraded <= 0
                else f"{connected} {label} connection(s) are active and {degraded} need review."
            ),
        }

    return {
        "provider": platform,
        "label": label,
        "status": "warning",
        "message": f"No active {label} connection is available right now, and {degraded} need reconnection or access review.",
    }


async def build_admin_snapshot() -> dict:
    db = get_database()

    managed_users = await db.users.find({"role": {"$ne": "admin"}}).to_list(length=5000)
    managed_user_ids = [item["_id"] for item in managed_users]

    total_managed_users = len(managed_users)
    active_users = sum(1 for item in managed_users if str(item.get("status") or "active").lower() != "inactive")
    inactive_users = max(total_managed_users - active_users, 0)
    accounts = (
        await db.social_accounts.find({"user_id": {"$in": managed_user_ids}}).to_list(length=5000)
        if managed_user_ids
        else []
    )
    total_connections = len(accounts)
    connected_accounts = [item for item in accounts if item.get("status") == "connected"]
    degraded_accounts = [
        item
        for item in accounts
        if str(item.get("status") or "").lower() in {"error", "expired", "limited", "disconnected"}
    ]
    open_alerts = await db.alerts.count_documents(
        {
            "status": {"$ne": "acknowledged"},
            "$or": [{"user_id": {"$in": managed_user_ids}}, {"user_id": None}],
        }
    )
    total_reports = await db.reports.count_documents({"user_id": {"$in": managed_user_ids}})

    by_platform: dict[str, list[dict]] = defaultdict(list)
    for account in accounts:
        platform = str(account.get("platform") or "").lower()
        if platform:
            by_platform[platform].append(account)

    provider_status = []
    for platform in ("instagram", "youtube", "x"):
        platform_accounts = by_platform.get(platform, [])
        connected = sum(1 for item in platform_accounts if item.get("status") == "connected")
        degraded = sum(
            1
            for item in platform_accounts
            if str(item.get("status") or "").lower() in {"error", "expired", "limited", "disconnected"}
        )
        provider_status.append(_provider_health(platform, connected, degraded, len(platform_accounts)))

    overview = [
        {
            "label": "Active Users",
            "value": _format_count(active_users),
            "delta": f"{_format_count(inactive_users)} user(s) are inactive",
            "tone": "positive" if active_users else "neutral",
        },
        {
            "label": "Connected Providers",
            "value": _format_count(total_connections),
            "delta": f"{_format_count(len(connected_accounts))} active connection(s)",
            "tone": "positive" if total_connections else "neutral",
        },
        {
            "label": "Failed Syncs",
            "value": _format_count(len(degraded_accounts)),
            "delta": "Needs review" if degraded_accounts else "All clear",
            "tone": "warning" if degraded_accounts else "positive",
        },
        {
            "label": "Open Alerts",
            "value": _format_count(open_alerts),
            "delta": "Requires attention",
            "tone": "warning" if open_alerts else "positive",
        },
    ]

    provider_totals = Counter(item.get("platform") for item in accounts if item.get("platform"))

    return {
        "overview": overview,
        "provider_status": provider_status,
        "meta": {
            "users": active_users,
            "inactive_users": inactive_users,
            "total_users": total_managed_users,
            "reports": total_reports,
            "provider_totals": dict(provider_totals),
        },
    }
