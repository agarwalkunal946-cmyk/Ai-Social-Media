from datetime import datetime, timezone
from uuid import uuid4

from app.db.mongo import get_database
from app.services.admin_data import build_admin_snapshot
from app.services.dashboard_data import build_dashboard_snapshot


def build_alert(
    *,
    user_id: str | None,
    source_type: str,
    platform: str,
    title: str,
    severity: str,
    explanation: str,
    recommended_action: str,
    affected_content: str | None = None,
    metadata: dict | None = None,
) -> dict:
    return {
        "_id": uuid4().hex,
        "user_id": user_id,
        "source_type": source_type,
        "platform": platform,
        "title": title,
        "severity": severity,
        "timestamp": datetime.now(timezone.utc),
        "explanation": explanation,
        "recommended_action": recommended_action,
        "status": "unread",
        "affected_content": affected_content,
        "metadata": metadata or {},
    }


async def create_alert(alert: dict) -> dict:
    db = get_database()
    await db.alerts.insert_one(alert)
    return alert


def _auto_alert_id(user_id: str, kind: str) -> str:
    return f"auto-{user_id}-{kind}"


async def ensure_demo_alerts(user_id: str) -> None:
    db = get_database()
    existing = await db.alerts.count_documents({"user_id": user_id})
    if existing:
        return
    alerts = [
        build_alert(
            user_id=user_id,
            source_type="ui",
            platform="instagram",
            title="Negative sentiment spike detected",
            severity="medium",
            explanation="Comments on your latest reel turned 17% more negative in the last 4 hours.",
            recommended_action="Review highlighted comments and pin a clarifying reply.",
            affected_content="Launch reel",
        ),
        build_alert(
            user_id=user_id,
            source_type="system",
            platform="youtube",
            title="Weekly report is ready",
            severity="low",
            explanation="A fresh performance report is available for review and sharing.",
            recommended_action="Open the report and download the public view.",
            affected_content="Weekly report",
        ),
    ]
    await db.alerts.insert_many(alerts)


async def sync_workspace_alerts(user_id: str) -> None:
    db = get_database()
    snapshot = await build_dashboard_snapshot({"id": user_id})
    existing = await db.alerts.find({"user_id": user_id, "source_type": "auto"}).to_list(length=20)
    existing_map = {item["_id"]: item for item in existing}

    overview = snapshot.get("overview") or []
    connected_accounts = next((item.get("value") for item in overview if item.get("label") == "Connected Accounts"), "0")
    crisis_alerts = snapshot.get("crisis_alerts") or []
    moderation_queue = snapshot.get("moderation_queue") or []
    auto_alerts = []

    if connected_accounts == "0":
        alert_id = _auto_alert_id(user_id, "connect-source")
        auto_alerts.append(
            {
                **build_alert(
                    user_id=user_id,
                    source_type="auto",
                    platform="system",
                    title="Connect a source to unlock live analytics",
                    severity="low",
                    explanation="No social platform is connected right now, so the dashboard cannot calculate live audience, trend, or moderation insights.",
                    recommended_action="Connect Instagram, YouTube, or X / Twitter from the Connections page.",
                    metadata={"kind": "connect-source", "auto_generated": True},
                ),
                "_id": alert_id,
                "status": existing_map.get(alert_id, {}).get("status", "unread"),
            }
        )

    for index, item in enumerate(crisis_alerts):
        kind = item.get("title", f"crisis-{index}").lower().replace(" ", "-")
        alert_id = _auto_alert_id(user_id, kind)
        auto_alerts.append(
            {
                **build_alert(
                    user_id=user_id,
                    source_type="auto",
                    platform=str(item.get("platform") or "system").lower(),
                    title=item.get("title") or "Workspace alert",
                    severity=item.get("severity") or "medium",
                    explanation=item.get("explanation") or "",
                    recommended_action=item.get("recommended_action") or "",
                    metadata={"kind": kind, "auto_generated": True},
                ),
                "_id": alert_id,
                "status": existing_map.get(alert_id, {}).get("status", "unread"),
            }
        )

    if moderation_queue and not any("toxic" in (item.get("title", "").lower()) for item in crisis_alerts):
        top_item = moderation_queue[0]
        alert_id = _auto_alert_id(user_id, "moderation-watch")
        auto_alerts.append(
            {
                **build_alert(
                    user_id=user_id,
                    source_type="auto",
                    platform=str(top_item.get("platform") or "system").lower(),
                    title="Moderation watchlist updated",
                    severity="medium" if top_item.get("toxicity", 0) >= 25 else "low",
                    explanation=f'{top_item.get("platform")} content "{top_item.get("title")}" currently leads the moderation watchlist.',
                    recommended_action="Review the watchlist card and decide whether the content needs a response or moderation action.",
                    metadata={"kind": "moderation-watch", "auto_generated": True},
                ),
                "_id": alert_id,
                "status": existing_map.get(alert_id, {}).get("status", "unread"),
            }
        )

    desired_ids = {item["_id"] for item in auto_alerts}
    stale_ids = [item["_id"] for item in existing if item["_id"] not in desired_ids]
    if stale_ids:
        await db.alerts.delete_many({"_id": {"$in": stale_ids}})

    for alert in auto_alerts:
        update_fields = {k: v for k, v in alert.items() if k != "timestamp"}
        await db.alerts.update_one(
            {"_id": alert["_id"]},
            {"$set": update_fields, "$setOnInsert": {"timestamp": datetime.now(timezone.utc)}},
            upsert=True,
        )


async def ensure_admin_system_alerts() -> None:
    db = get_database()
    snapshot = await build_admin_snapshot()
    meta = snapshot.get("meta") or {}
    provider_totals = meta.get("provider_totals") or {}

    now = datetime.now(timezone.utc)
    iso = now.isocalendar()
    weekly_key = f"{iso.year}-W{iso.week:02d}"
    monthly_key = f"{now.year}-{now.month:02d}"

    weekly_exists = await db.alerts.count_documents(
        {"source_type": "system", "metadata.kind": "weekly-summary", "metadata.period_key": weekly_key}
    )
    monthly_exists = await db.alerts.count_documents(
        {"source_type": "system", "metadata.kind": "monthly-summary", "metadata.period_key": monthly_key}
    )

    pending_alerts = []
    if not weekly_exists:
        pending_alerts.append(
            build_alert(
                user_id=None,
                source_type="system",
                platform="system",
                title="Weekly operations summary is ready",
                severity="low" if meta.get("users", 0) else "medium",
                explanation=(
                    f"{meta.get('users', 0)} managed users, {sum(provider_totals.values())} connected sources, "
                    f"and {meta.get('reports', 0)} reports are currently tracked in this week's workspace summary."
                ),
                recommended_action="Review connection health, unread alerts, and user activity from the control center.",
                metadata={"kind": "weekly-summary", "period_key": weekly_key, "cadence": "weekly"},
            )
        )

    if not monthly_exists:
        pending_alerts.append(
            build_alert(
                user_id=None,
                source_type="system",
                platform="system",
                title="Monthly platform summary is ready",
                severity="low" if provider_totals else "medium",
                explanation=(
                    f"Current managed source totals - Instagram: {provider_totals.get('instagram', 0)}, "
                    f"YouTube: {provider_totals.get('youtube', 0)}, X: {provider_totals.get('x', 0)}."
                ),
                recommended_action="Use this monthly checkpoint to review inactive accounts, report volume, and platform coverage.",
                metadata={"kind": "monthly-summary", "period_key": monthly_key, "cadence": "monthly"},
            )
        )

    if pending_alerts:
        await db.alerts.insert_many(pending_alerts)
