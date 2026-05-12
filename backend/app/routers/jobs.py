import asyncio
import re
from datetime import datetime

import requests as http_requests
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.crypto import credentials_from_dict, decrypt_token
from app.database import AsyncSessionLocal, get_db
from app.deps import get_current_user, get_drive_service
from app.models import Job, KnownPerson, ReferenceEmbedding, TaggedPhoto, User
from app.recognizer import deserialize_embedding, identify_people
from app.schemas import JobCreate, JobOut, PhotoOut, ResultsOut

router = APIRouter()

IMAGE_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/heic",
    "image/gif",
    "image/x-sony-arw",
}

PREVIEW_SIZE = 1024


def _list_drive_images(drive, folder_id: str) -> list[dict]:
    images = []
    page_token = None
    query = f"'{folder_id}' in parents and trashed = false"
    while True:
        resp = drive.files().list(
            q=query,
            fields="nextPageToken, files(id, name, mimeType, thumbnailLink)",
            pageToken=page_token,
            pageSize=200,
        ).execute()
        for f in resp.get("files", []):
            if f["mimeType"] in IMAGE_MIME_TYPES:
                images.append(f)
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return images


def _download_thumbnail_bytes(token: str, file: dict) -> bytes | None:
    thumbnail_url = file.get("thumbnailLink")
    if not thumbnail_url:
        return None
    url = re.sub(r"=s\d+$", f"=s{PREVIEW_SIZE}", thumbnail_url)
    if not url.endswith(f"=s{PREVIEW_SIZE}"):
        url = f"{thumbnail_url.rstrip('/')}&sz=s{PREVIEW_SIZE}"
    try:
        resp = http_requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=30)
        resp.raise_for_status()
        return resp.content
    except Exception:
        return None


async def _run_tagging_job(job_id: str, user_id: str, face_app):
    async with AsyncSessionLocal() as db:
        job = await db.get(Job, job_id)
        user = await db.get(User, user_id)
        if not job or not user:
            return

        job.status = "running"
        job.updated_at = datetime.utcnow()
        await db.commit()

        try:
            creds_dict = decrypt_token(user.encrypted_token)
            creds = credentials_from_dict(creds_dict)
            from googleapiclient.discovery import build
            drive = build("drive", "v3", credentials=creds)

            # Get folder name
            try:
                folder_meta = drive.files().get(fileId=job.folder_id, fields="name").execute()
                job.folder_name = folder_meta.get("name", job.folder_id)
            except Exception:
                job.folder_name = job.folder_id
            await db.commit()

            # List images
            loop = asyncio.get_event_loop()
            images = await loop.run_in_executor(None, _list_drive_images, drive, job.folder_id)
            job.total = len(images)
            await db.commit()

            # Find already-processed photos so a resumed job skips them
            done_result = await db.execute(
                select(TaggedPhoto.drive_file_id).where(TaggedPhoto.job_id == job.id)
            )
            done_ids: set[str] = set(done_result.scalars().all())
            job.processed = len(done_ids)
            await db.commit()

            # Load this user's known embeddings from DB once
            emb_result = await db.execute(
                select(ReferenceEmbedding)
                .join(KnownPerson)
                .where(KnownPerson.user_id == user_id)
            )
            known_embeddings: dict[str, list] = {}
            for ref in emb_result.scalars().all():
                person_result = await db.get(KnownPerson, ref.person_id)
                if person_result:
                    known_embeddings.setdefault(person_result.name, []).append(
                        deserialize_embedding(ref.embedding)
                    )

            token = creds.token

            for file in images:
                if file["id"] in done_ids:
                    continue

                image_bytes = await loop.run_in_executor(
                    None, _download_thumbnail_bytes, token, file
                )

                if image_bytes:
                    people = await loop.run_in_executor(
                        None,
                        identify_people,
                        face_app,
                        image_bytes,
                        known_embeddings,
                        settings.SIMILARITY_THRESHOLD,
                    )
                else:
                    people = []

                photo = TaggedPhoto(
                    job_id=job.id,
                    user_id=user_id,
                    drive_file_id=file["id"],
                    file_name=file.get("name"),
                    thumbnail_url=file.get("thumbnailLink"),
                    drive_link=f"https://drive.google.com/file/d/{file['id']}/view",
                    people=",".join(people),
                )
                db.add(photo)
                done_ids.add(file["id"])
                job.processed = len(done_ids)
                job.updated_at = datetime.utcnow()
                await db.commit()

            job.status = "done"
            job.updated_at = datetime.utcnow()
            await db.commit()

        except Exception as e:
            job.status = "error"
            job.error_msg = str(e)
            job.updated_at = datetime.utcnow()
            await db.commit()


def _job_to_out(job: Job) -> JobOut:
    percent = int(job.processed / job.total * 100) if job.total > 0 else 0
    return JobOut(
        id=job.id,
        folder_id=job.folder_id,
        folder_name=job.folder_name,
        status=job.status,
        total=job.total,
        processed=job.processed,
        percent=percent,
        error_msg=job.error_msg,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


@router.post("/", response_model=JobOut)
async def submit_job(
    body: JobCreate,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    job = Job(user_id=user.id, folder_id=body.folder_id)
    db.add(job)
    await db.commit()
    await db.refresh(job)

    face_app = request.app.state.face_app
    asyncio.create_task(_run_tagging_job(job.id, user.id, face_app))

    return _job_to_out(job)


@router.get("/", response_model=list[JobOut])
async def list_jobs(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Job).where(Job.user_id == user.id).order_by(Job.created_at.desc()).limit(20)
    )
    return [_job_to_out(j) for j in result.scalars().all()]


@router.get("/{job_id}", response_model=JobOut)
async def get_job(
    job_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    job = await db.get(Job, job_id)
    if not job or job.user_id != user.id:
        raise HTTPException(404, "Job not found")
    return _job_to_out(job)


@router.delete("/{job_id}")
async def delete_job(
    job_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    job = await db.get(Job, job_id)
    if not job or job.user_id != user.id:
        raise HTTPException(404, "Job not found")
    await db.delete(job)
    await db.commit()
    return {"ok": True}


def _person_match(person: str):
    from sqlalchemy import or_
    return or_(
        TaggedPhoto.people == person,
        TaggedPhoto.people.like(f"{person},%"),
        TaggedPhoto.people.like(f"%,{person}"),
        TaggedPhoto.people.like(f"%,{person},%"),
    )


@router.get("/{job_id}/results", response_model=ResultsOut)
async def get_results(
    job_id: str,
    people: list[str] = Query(default=[]),
    exclusive: bool = False,
    page: int = 1,
    page_size: int = 50,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    job = await db.get(Job, job_id)
    if not job or job.user_id != user.id:
        raise HTTPException(404, "Job not found")

    query = select(TaggedPhoto).where(TaggedPhoto.job_id == job_id)

    # Each selected person must appear in the photo (AND logic = combination filter)
    for person in people:
        query = query.where(_person_match(person))

    # Get all distinct people across the job (needed for the filter UI and exclusive mode)
    all_photos_result = await db.execute(
        select(TaggedPhoto.people).where(TaggedPhoto.job_id == job_id)
    )
    all_people: set[str] = set()
    for (people_str,) in all_photos_result.all():
        if people_str:
            all_people.update(p.strip() for p in people_str.split(",") if p.strip())

    # Exclusive: exclude photos that contain any recognised person not in the selected set
    if exclusive and people:
        for excluded in all_people - set(people):
            query = query.where(~_person_match(excluded))

    # Paginate
    offset = (page - 1) * page_size
    result = await db.execute(
        query.order_by(TaggedPhoto.processed_at).offset(offset).limit(page_size)
    )
    photos = result.scalars().all()

    from sqlalchemy import func
    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar_one()

    return ResultsOut(
        job_id=job_id,
        total=total,
        page=page,
        page_size=page_size,
        people_in_job=sorted(all_people),
        photos=[
            PhotoOut(
                id=p.id,
                drive_file_id=p.drive_file_id,
                file_name=p.file_name,
                thumbnail_url=p.thumbnail_url,
                drive_link=p.drive_link,
                people=[x.strip() for x in p.people.split(",") if x.strip()],
            )
            for p in photos
        ],
    )


@router.get("/{job_id}/photos/{photo_id}/thumbnail")
async def proxy_thumbnail(
    job_id: str,
    photo_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    job = await db.get(Job, job_id)
    if not job or job.user_id != user.id:
        raise HTTPException(404, "Job not found")

    result = await db.execute(
        select(TaggedPhoto).where(TaggedPhoto.id == photo_id, TaggedPhoto.job_id == job_id)
    )
    photo = result.scalar_one_or_none()
    if not photo:
        raise HTTPException(404, "Photo not found")

    creds_dict = decrypt_token(user.encrypted_token)
    creds = credentials_from_dict(creds_dict)
    loop = asyncio.get_event_loop()

    # Try stored thumbnail URL first
    image_bytes = None
    if photo.thumbnail_url:
        image_bytes = await loop.run_in_executor(
            None, _download_thumbnail_bytes, creds.token, {"thumbnailLink": photo.thumbnail_url}
        )

    # Fall back to a fresh thumbnailLink from the Drive API
    if not image_bytes:
        from googleapiclient.discovery import build as drive_build
        drive = drive_build("drive", "v3", credentials=creds)
        try:
            meta = await loop.run_in_executor(
                None,
                lambda: drive.files().get(fileId=photo.drive_file_id, fields="thumbnailLink").execute(),
            )
            fresh_url = meta.get("thumbnailLink")
            if fresh_url:
                image_bytes = await loop.run_in_executor(
                    None, _download_thumbnail_bytes, creds.token, {"thumbnailLink": fresh_url}
                )
        except Exception:
            pass

    if not image_bytes:
        raise HTTPException(404, "Thumbnail not available")

    return Response(
        content=image_bytes,
        media_type="image/jpeg",
        headers={"Cache-Control": "private, max-age=3600"},
    )


async def resume_stuck_jobs(app) -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Job).where(Job.status.in_(["pending", "running"]))
        )
        stuck = result.scalars().all()

    for job in stuck:
        asyncio.create_task(
            _run_tagging_job(job.id, job.user_id, app.state.face_app)
        )
