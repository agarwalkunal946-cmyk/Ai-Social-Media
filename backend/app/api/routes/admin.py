import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from app.db.mongo import get_database
from app.schemas.auth import AdminUpdateUserPayload
from app.services.admin_data import build_admin_snapshot
from app.services.auth import require_admin
from app.services.dashboard_data import build_dashboard_snapshot, invalidate_dashboard_snapshot_cache
from app.services.platform_preview import invalidate_platform_preview_cache
from app.services.reports import delete_report_as_admin


router = APIRouter(prefix="/admin", tags=["admin"])


def _platform_label(platform: str) -> str:
    return {"instagram": "Instagram", "youtube": "YouTube", "x": "X / Twitter"}.get(platform, platform.title())


def _access_mode_label(value: str | None) -> str:
    normalized = str(value or "oauth").strip().lower().replace("_", " ")
    if normalized == "apify":
        return "Live feed"
    if normalized == "live feed":
        return "Live feed"
    return normalized.title()


async def _managed_user_or_404(user_id: str) -> dict:
    db = get_database()
    user = await db.users.find_one({"_id": user_id, "role": {"$ne": "admin"}})
    if not user:
        raise HTTPException(status_code=404, detail="Managed user not found.")
    return user


@router.get("/overview")
async def admin_overview(_: dict = Depends(require_admin)):
    return await build_admin_snapshot()


@router.get("/users")
async def admin_users(_: dict = Depends(require_admin)):
    db = get_database()
    users = await db.users.find({"role": {"$ne": "admin"}}).sort("updated_at", -1).to_list(length=250)
    managed_user_ids = [user["_id"] for user in users]
    social_accounts = (
        await db.social_accounts.find({"user_id": {"$in": managed_user_ids}}).to_list(length=5000)
        if managed_user_ids
        else []
    )
    reports = (
        await db.reports.find({"user_id": {"$in": managed_user_ids}}, {"user_id": 1}).to_list(length=5000)
        if managed_user_ids
        else []
    )

    connections_by_user: dict[str, list[str]] = {}
    for account in social_accounts:
        user_id = account.get("user_id")
        platform = str(account.get("platform") or "").strip()
        if not user_id or not platform:
            continue
        connections_by_user.setdefault(user_id, [])
        if platform not in connections_by_user[user_id]:
            connections_by_user[user_id].append(platform)

    reports_by_user: dict[str, int] = {}
    for report in reports:
        user_id = report.get("user_id")
        if not user_id:
            continue
        reports_by_user[user_id] = reports_by_user.get(user_id, 0) + 1

    rows = []
    for user in users:
        platforms = [_platform_label(item) for item in connections_by_user.get(user["_id"], [])]
        rows.append(
            {
                "id": user["_id"],
                "display_name": user.get("display_name"),
                "email": user.get("email"),
                "role": user.get("role", "user"),
                "mode": user.get("mode", "creator"),
                "status": user.get("status", "active"),
                "connections": ", ".join(platforms) if platforms else "No connections",
                "connection_count": len(platforms),
                "report_count": reports_by_user.get(user["_id"], 0),
                "provider": user.get("provider", "unknown"),
                "created_at": user.get("created_at"),
                "updated_at": user.get("updated_at"),
            }
        )
    return {"items": rows}


@router.get("/users/{user_id}/analysis")
async def admin_user_analysis(user_id: str, _: dict = Depends(require_admin)):
    db = get_database()
    user = await _managed_user_or_404(user_id)
    snapshot = await build_dashboard_snapshot({"id": user_id})

    connections_raw = await db.social_accounts.find({"user_id": user_id}).sort("updated_at", -1).to_list(length=20)
    reports_raw = await db.reports.find({"user_id": user_id}).sort("created_at", -1).to_list(length=20)
    alerts_raw = await db.alerts.find({"$or": [{"user_id": user_id}, {"user_id": None}]}).sort("timestamp", -1).to_list(length=20)

    for item in reports_raw:
        item["id"] = item.pop("_id")
    for item in alerts_raw:
        item["id"] = item.pop("_id")

    connections = [
        {
            "id": item.get("_id"),
            "platform": _platform_label(str(item.get("platform") or "")),
            "account_name": item.get("account_name") or item.get("handle") or "Connected account",
            "handle": item.get("handle"),
            "status": str(item.get("status") or "connected").replace("_", " ").title(),
            "access_mode": _access_mode_label(item.get("access_mode")),
            "updated_at": item.get("updated_at"),
        }
        for item in connections_raw
    ]

    reports = [
        {
            "id": item.get("id"),
            "title": item.get("title") or "Insight report",
            "period": str(item.get("period") or "custom").title(),
            "created_at": item.get("created_at"),
            "public_token": item.get("public_token"),
        }
        for item in reports_raw
    ]

    alerts = [
        {
            "id": item.get("id"),
            "platform": item.get("platform"),
            "title": item.get("title"),
            "severity": item.get("severity"),
            "status": item.get("status"),
            "explanation": item.get("explanation"),
            "recommended_action": item.get("recommended_action"),
            "timestamp": item.get("timestamp"),
        }
        for item in alerts_raw
    ]

    return {
        "user": {
            "id": user["_id"],
            "display_name": user.get("display_name"),
            "email": user.get("email"),
            "mode": user.get("mode", "creator"),
            "status": user.get("status", "active"),
            "provider": user.get("provider", "unknown"),
        },
        "snapshot": snapshot,
        "connections": connections,
        "reports": reports,
        "alerts": alerts,
    }


@router.patch("/users/{user_id}")
async def admin_update_user(user_id: str, payload: AdminUpdateUserPayload, _: dict = Depends(require_admin)):
    user = await _managed_user_or_404(user_id)
    updates = {}

    if payload.display_name is not None:
        display_name = payload.display_name.strip()
        if len(display_name) < 2:
            raise HTTPException(status_code=400, detail="Display name must be at least 2 characters.")
        updates["display_name"] = display_name
        updates["manual_display_name"] = True

    if payload.mode is not None:
        if payload.mode not in {"creator", "brand"}:
            raise HTTPException(status_code=400, detail="Mode must be creator or brand.")
        updates["mode"] = payload.mode

    if payload.status is not None:
        normalized_status = payload.status.strip().lower()
        if normalized_status not in {"active", "inactive"}:
            raise HTTPException(status_code=400, detail="Status must be active or inactive.")
        updates["status"] = normalized_status

    if not updates:
        raise HTTPException(status_code=400, detail="No valid user updates were provided.")

    updates["updated_at"] = datetime.now(timezone.utc)
    db = get_database()
    await db.users.update_one({"_id": user_id}, {"$set": updates})
    updated = await db.users.find_one({"_id": user_id})
    return {
        "message": "User updated successfully.",
        "user": {
            "id": updated["_id"],
            "display_name": updated.get("display_name"),
            "email": updated.get("email"),
            "mode": updated.get("mode", "creator"),
            "status": updated.get("status", "active"),
        },
    }


@router.delete("/users/{user_id}")
async def admin_delete_user(user_id: str, _: dict = Depends(require_admin)):
    db = get_database()
    user = await _managed_user_or_404(user_id)

    connections = await db.social_accounts.find({"user_id": user_id}).to_list(length=100)
    reports = await db.reports.find({"user_id": user_id}, {"_id": 1}).to_list(length=200)

    cache_jobs = [
        invalidate_platform_preview_cache(connection["user_id"], connection["platform"])
        for connection in connections
        if connection.get("user_id") and connection.get("platform")
    ]
    report_jobs = [delete_report_as_admin(report["_id"]) for report in reports if report.get("_id")]

    if cache_jobs:
        await asyncio.gather(*cache_jobs)
    if report_jobs:
        await asyncio.gather(*report_jobs)
    await invalidate_dashboard_snapshot_cache(user_id)

    await asyncio.gather(
        db.blocked_users.update_one(
            {"email": user.get("email")},
            {
                "$set": {
                    "email": user.get("email"),
                    "display_name": user.get("display_name"),
                    "reason": "deleted_by_admin",
                    "blocked_at": datetime.now(timezone.utc),
                }
            },
            upsert=True,
        ),
        db.social_accounts.delete_many({"user_id": user_id}),
        db.alerts.delete_many({"user_id": user_id}),
        db.users.delete_one({"_id": user_id}),
    )
    return {"message": "User deleted successfully."}


@router.get("/connections")
async def admin_connections(_: dict = Depends(require_admin)):
    db = get_database()
    users = await db.users.find({"role": {"$ne": "admin"}}).to_list(length=5000)
    user_map = {user["_id"]: user for user in users}
    if not user_map:
        return {"items": []}

    accounts = await db.social_accounts.find({"user_id": {"$in": list(user_map)}}).sort("updated_at", -1).to_list(length=5000)
    rows = []
    for account in accounts:
        owner = user_map.get(account.get("user_id")) or {}
        rows.append(
            {
                "id": account.get("_id"),
                "user_id": account.get("user_id"),
                "user_name": owner.get("display_name") or owner.get("email") or "User",
                "user_email": owner.get("email"),
                "platform": _platform_label(str(account.get("platform") or "")),
                "status": str(account.get("status") or "connected").replace("_", " ").title(),
                "access_mode": _access_mode_label(account.get("access_mode")),
                "account_name": account.get("account_name") or account.get("handle") or "Connected account",
                "handle": account.get("handle"),
                "connected_at": account.get("connected_at"),
                "updated_at": account.get("updated_at"),
            }
        )
    return {"items": rows}


@router.get("/reports")
async def admin_reports(_: dict = Depends(require_admin)):
    db = get_database()
    users = await db.users.find({"role": {"$ne": "admin"}}).to_list(length=5000)
    user_map = {user["_id"]: user for user in users}
    if not user_map:
        return {"items": []}

    reports = await db.reports.find({"user_id": {"$in": list(user_map)}}).sort("created_at", -1).to_list(length=250)
    rows = []
    for report in reports:
        owner = user_map.get(report.get("user_id")) or {}
        rows.append(
            {
                "id": report.get("_id"),
                "title": report.get("title") or "Insight report",
                "period": str(report.get("period") or "custom").title(),
                "created_at": report.get("created_at"),
                "user_id": report.get("user_id"),
                "owner_name": owner.get("display_name") or owner.get("email") or "User",
                "owner_email": owner.get("email"),
                "public_token": report.get("public_token"),
            }
        )
    return {"items": rows}


@router.delete("/connections/{connection_id}")
async def admin_delete_connection(connection_id: str, _: dict = Depends(require_admin)):
    db = get_database()
    connection = await db.social_accounts.find_one({"_id": connection_id})
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found.")

    await db.social_accounts.delete_one({"_id": connection_id})
    if connection.get("user_id") and connection.get("platform"):
        await invalidate_platform_preview_cache(connection["user_id"], connection["platform"])
        await invalidate_dashboard_snapshot_cache(connection["user_id"])
    return {"message": "Connection removed successfully."}


@router.delete("/reports/{report_id}")
async def admin_delete_report(report_id: str, _: dict = Depends(require_admin)):
    deleted = await delete_report_as_admin(report_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Report not found.")
    return {"message": "Report removed successfully."}
