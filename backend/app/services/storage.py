from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import get_settings


async def save_upload(file: UploadFile, folder: str) -> dict:
    settings = get_settings()
    destination_dir = settings.uploads_dir / folder
    destination_dir.mkdir(parents=True, exist_ok=True)

    suffix = Path(file.filename or "upload.bin").suffix
    filename = f"{uuid4().hex}{suffix}"
    destination = destination_dir / filename

    with destination.open("wb") as buffer:
        while chunk := await file.read(1024 * 1024):
            buffer.write(chunk)

    relative = destination.relative_to(settings.uploads_dir.parent)
    public_path = "/" + str(relative).replace("\\", "/")
    return {
        "filename": filename,
        "path": str(destination),
        "public_path": public_path,
    }
