from fastapi import APIRouter, Body, Depends, Query

from app.schemas.dashboard import DashboardPayload
from app.services.admin_data import build_admin_snapshot
from app.services.auth import get_current_user, get_optional_user
from app.services.dashboard_data import build_dashboard_chatbot_response, build_dashboard_snapshot
from app.services.demo_data import get_public_platform_cards
from app.services.public_platforms import get_platform_item_analytics, get_public_platform_payload


router = APIRouter(tags=["dashboard"])


@router.get("/public/overview")
async def public_overview():
    return {"cards": get_public_platform_cards()}


@router.get("/public/platform/{platform}")
async def public_platform(
    platform: str,
    user: dict | None = Depends(get_optional_user),
    mode: str | None = Query(default=None),
    q: str | None = Query(default=None),
):
    return await get_public_platform_payload(platform, user, mode=mode, query=q)


@router.post("/public/platform/{platform}/analytics")
async def public_platform_item_analytics(
    platform: str,
    payload: dict = Body(...),
    user: dict | None = Depends(get_optional_user),
):
    return await get_platform_item_analytics(platform, user, payload.get("item") or {}, mode=payload.get("mode"))


@router.get("/dashboard", response_model=DashboardPayload)
async def dashboard(user: dict = Depends(get_current_user)):
    return await build_dashboard_snapshot(user)


@router.post("/dashboard/chatbot")
async def dashboard_chatbot(payload: dict = Body(...), user: dict = Depends(get_current_user)):
    snapshot = await build_dashboard_snapshot(user)
    return await build_dashboard_chatbot_response(snapshot, user, str((payload or {}).get("message") or ""))


@router.get("/admin/snapshot")
async def admin_snapshot():
    return await build_admin_snapshot()
