from fastapi import APIRouter, Depends

from app.deps import get_current_user, get_drive_service
from app.models import User
from app.schemas import FolderOut

router = APIRouter()

FOLDER_MIME = "application/vnd.google-apps.folder"

IMAGE_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/heic",
    "image/gif",
    "image/x-sony-arw",
}


@router.get("/folders", response_model=list[FolderOut])
async def list_folders(
    parent_id: str = "root",
    user: User = Depends(get_current_user),
    drive=Depends(get_drive_service),
):
    query = f"'{parent_id}' in parents and mimeType = '{FOLDER_MIME}' and trashed = false"
    resp = drive.files().list(
        q=query,
        fields="files(id, name, mimeType)",
        orderBy="name",
        pageSize=100,
    ).execute()

    return [
        FolderOut(id=f["id"], name=f["name"], mime_type=f["mimeType"])
        for f in resp.get("files", [])
    ]


@router.get("/folders/{folder_id}")
async def get_folder(
    folder_id: str,
    user: User = Depends(get_current_user),
    drive=Depends(get_drive_service),
):
    folder = drive.files().get(
        fileId=folder_id,
        fields="id, name, mimeType",
    ).execute()

    # Count images inside
    query = f"'{folder_id}' in parents and trashed = false"
    count_resp = drive.files().list(
        q=query,
        fields="files(mimeType)",
        pageSize=1000,
    ).execute()
    image_count = sum(
        1 for f in count_resp.get("files", []) if f["mimeType"] in IMAGE_MIME_TYPES
    )

    return {
        "id": folder["id"],
        "name": folder["name"],
        "image_count": image_count,
    }
