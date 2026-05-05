from fastapi import APIRouter, Body, Depends, HTTPException

from app.db.mongo import get_database
from app.services.alerts import build_alert, create_alert, ensure_admin_system_alerts, sync_workspace_alerts
from app.services.auth import get_current_user, require_admin


router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("")
async def list_alerts(user: dict = Depends(get_current_user)):
    db = get_database()
    await sync_workspace_alerts(user["id"])
    query = {"$or": [{"user_id": user["id"]}, {"user_id": None}]}
    alerts = await db.alerts.find(query).sort("timestamp", -1).to_list(length=100)
    for alert in alerts:
        alert["id"] = alert.pop("_id")
    return {"items": alerts}


@router.post("/{alert_id}/ack")
async def acknowledge_alert(alert_id: str, user: dict = Depends(get_current_user)):
    db = get_database()
    query = {"_id": alert_id, "$or": [{"user_id": user["id"]}, {"user_id": None}]}
    result = await db.alerts.update_one(query, {"$set": {"status": "acknowledged"}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Alert not found.")
    return {"message": "Alert acknowledged."}


@router.post("/ack-all")
async def acknowledge_all_alerts(user: dict = Depends(get_current_user)):
    db = get_database()
    query = {"$or": [{"user_id": user["id"]}, {"user_id": None}], "status": {"$ne": "acknowledged"}}
    result = await db.alerts.update_many(query, {"$set": {"status": "acknowledged"}})
    return {"message": "All alerts marked as read.", "updated": result.modified_count}


@router.get("/admin/system")
async def list_system_alerts(_: dict = Depends(require_admin)):
    db = get_database()
    await ensure_admin_system_alerts()
    alerts = await db.alerts.find({"source_type": "system"}).sort("timestamp", -1).to_list(length=100)
    for alert in alerts:
        alert["id"] = alert.pop("_id")
    return {"items": alerts}


@router.post("/admin/system")
async def create_system_alert(
    payload: dict = Body(...),
    _: dict = Depends(require_admin),
):
    title = str((payload or {}).get("title") or "").strip()
    explanation = str((payload or {}).get("explanation") or "").strip()
    recommended_action = str((payload or {}).get("recommended_action") or "").strip()
    platform = str((payload or {}).get("platform") or "system").strip().lower()
    severity = str((payload or {}).get("severity") or "medium").strip().lower()
    affected_content = str((payload or {}).get("affected_content") or "").strip() or None

    if not title or not explanation or not recommended_action:
        raise HTTPException(status_code=400, detail="Title, explanation, and recommended action are required.")
    if severity not in {"low", "medium", "high"}:
        raise HTTPException(status_code=400, detail="Severity must be low, medium, or high.")

    alert = build_alert(
        user_id=None,
        source_type="system",
        platform=platform or "system",
        title=title,
        severity=severity,
        explanation=explanation,
        recommended_action=recommended_action,
        affected_content=affected_content,
    )
    saved = await create_alert(alert)
    saved["id"] = saved.pop("_id")
    return {"message": "System alert created.", "alert": saved}
