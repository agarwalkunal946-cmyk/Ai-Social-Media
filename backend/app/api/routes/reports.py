from fastapi import APIRouter, Depends, HTTPException

from app.db.mongo import get_database
from app.services.auth import get_current_user
from app.services.reports import delete_report_for_user, generate_report_for_user, get_public_report, get_report_download


router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("")
async def list_reports(user: dict = Depends(get_current_user)):
    db = get_database()
    reports = await db.reports.find({"user_id": user["id"]}).sort("created_at", -1).to_list(length=50)
    for report in reports:
        report["id"] = report.pop("_id")
    return {"items": reports}


@router.post("/generate")
async def generate_report(period: str = "weekly", user: dict = Depends(get_current_user)):
    report = await generate_report_for_user(user, period)
    return {
        "message": "Report generated.",
        "report": {
            "id": report["_id"],
            "title": report["title"],
            "period": report["period"],
            "created_at": report["created_at"],
            "public_token": report["public_token"],
            "public_url": f"/api/reports/public/{report['public_token']}",
        },
    }


@router.get("/public/{token}")
async def public_report(token: str):
    response = await get_public_report(token)
    if response is None:
        raise HTTPException(status_code=404, detail="Report not found.")
    return response


@router.get("/public/{token}/download")
async def download_public_report(token: str):
    response = await get_report_download(token)
    if response is None:
        raise HTTPException(status_code=404, detail="Report not found.")
    return response


@router.delete("/{report_id}")
async def delete_report(report_id: str, user: dict = Depends(get_current_user)):
    deleted = await delete_report_for_user(user["id"], report_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Report not found.")
    return {"message": "Report deleted successfully."}
