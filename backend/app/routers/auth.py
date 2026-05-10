import base64
import hashlib
import os
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.crypto import credentials_to_dict, encrypt_token
from app.database import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas import UserOut

router = APIRouter()

SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/drive.metadata",
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]


def _pkce_pair() -> tuple[str, str]:
    verifier = base64.urlsafe_b64encode(os.urandom(32)).rstrip(b"=").decode()
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).rstrip(b"=").decode()
    return verifier, challenge


def _build_flow() -> Flow:
    return Flow.from_client_config(
        client_config={
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
            }
        },
        scopes=SCOPES,
        redirect_uri=settings.GOOGLE_REDIRECT_URI,
    )


@router.get("/login")
async def login(request: Request):
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(500, "Google OAuth not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.")

    verifier, challenge = _pkce_pair()
    flow = _build_flow()
    auth_url, state = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        include_granted_scopes="true",
        code_challenge=challenge,
        code_challenge_method="S256",
    )
    request.session["oauth_state"] = state
    request.session["pkce_verifier"] = verifier
    return RedirectResponse(auth_url)


@router.get("/callback")
async def callback(
    request: Request,
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db),
):
    stored_state = request.session.pop("oauth_state", None)
    if not stored_state or state != stored_state:
        raise HTTPException(400, "Invalid OAuth state — possible CSRF")

    verifier = request.session.pop("pkce_verifier", None)
    flow = _build_flow()
    flow.fetch_token(code=code, code_verifier=verifier)
    credentials = flow.credentials

    # Get user profile from Google
    svc = build("oauth2", "v2", credentials=credentials)
    userinfo = svc.userinfo().get().execute()

    google_id = userinfo["id"]
    result = await db.execute(select(User).where(User.google_id == google_id))
    user = result.scalar_one_or_none()

    encrypted = encrypt_token(credentials_to_dict(credentials))

    if user:
        user.email = userinfo.get("email", user.email)
        user.name = userinfo.get("name")
        user.picture_url = userinfo.get("picture")
        user.encrypted_token = encrypted
        user.token_updated_at = datetime.utcnow()
    else:
        user = User(
            google_id=google_id,
            email=userinfo.get("email", ""),
            name=userinfo.get("name"),
            picture_url=userinfo.get("picture"),
            encrypted_token=encrypted,
            token_updated_at=datetime.utcnow(),
        )
        db.add(user)

    await db.commit()
    await db.refresh(user)

    request.session["user_id"] = user.id
    return RedirectResponse(settings.FRONTEND_URL + "/dashboard")


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    return UserOut(
        id=user.id,
        email=user.email,
        name=user.name,
        picture_url=user.picture_url,
    )


@router.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return {"ok": True}
