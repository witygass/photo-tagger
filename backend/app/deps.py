from datetime import datetime

from fastapi import Depends, HTTPException, Request
from google.auth.transport.requests import Request as GoogleRequest
from googleapiclient.discovery import build
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.crypto import credentials_from_dict, credentials_to_dict, decrypt_token, encrypt_token
from app.database import get_db
from app.models import User


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


async def get_drive_service(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not user.encrypted_token:
        raise HTTPException(status_code=401, detail="No Google credentials stored")

    creds_dict = decrypt_token(user.encrypted_token)
    creds = credentials_from_dict(creds_dict)

    if creds.expired and creds.refresh_token:
        creds.refresh(GoogleRequest())
        user.encrypted_token = encrypt_token(credentials_to_dict(creds))
        user.token_updated_at = datetime.utcnow()
        await db.commit()

    return build("drive", "v3", credentials=creds)


def get_face_app(request: Request):
    return request.app.state.face_app


def get_pet_app(request: Request):
    return request.app.state.pet_app
