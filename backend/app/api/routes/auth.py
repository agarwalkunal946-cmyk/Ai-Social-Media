from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile

from app.db.mongo import get_database
from app.schemas.auth import UpdateModePayload, UpdateProfilePayload
from app.services.auth import get_current_user
from app.services.storage import save_upload


router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/password-reset-status")
async def password_reset_status(email: str = Query(...)):
    normalized_email = email.strip().lower()
    if not normalized_email:
        raise HTTPException(status_code=400, detail="Email is required.")

    db = get_database()
    user = await db.users.find_one({"email": normalized_email})

    return {
        "exists": bool(user),
        "provider": user.get("provider") if user else None,
        "email": normalized_email,
    }


@router.get("/me")
async def get_me(user: dict = Depends(get_current_user)):
    return {"user": user}


@router.patch("/mode")
async def update_mode(payload: UpdateModePayload, user: dict = Depends(get_current_user)):
    if payload.mode not in {"creator", "brand"}:
        raise HTTPException(status_code=400, detail="Mode must be creator or brand.")
    db = get_database()
    await db.users.update_one({"_id": user["id"]}, {"$set": {"mode": payload.mode, "updated_at": datetime.now(timezone.utc)}})
    user["mode"] = payload.mode
    return {"message": "Mode updated.", "user": user}


@router.patch("/profile")
async def update_profile(payload: UpdateProfilePayload, user: dict = Depends(get_current_user)):
    display_name = payload.display_name.strip()
    if len(display_name) < 2:
        raise HTTPException(status_code=400, detail="Display name must be at least 2 characters.")

    db = get_database()
    await db.users.update_one(
        {"_id": user["id"]},
        {
            "$set": {
                "display_name": display_name,
                "manual_display_name": True,
                "updated_at": datetime.now(timezone.utc),
            }
        },
    )
    user["display_name"] = display_name
    user["manual_display_name"] = True
    return {"message": "Profile updated.", "user": user}


@router.post("/avatar")
async def upload_avatar(
    image: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    saved = await save_upload(image, "avatars")
    db = get_database()
    await db.users.update_one(
        {"_id": user["id"]},
        {
            "$set": {
                "avatar_url": saved["public_path"],
                "manual_avatar_url": True,
                "updated_at": datetime.now(timezone.utc),
            }
        },
    )
    user["avatar_url"] = saved["public_path"]
    user["manual_avatar_url"] = True
    return {"message": "Avatar updated.", "avatar_url": saved["public_path"], "user": user}
