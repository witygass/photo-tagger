from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.deps import get_current_user, get_face_app, get_pet_app
from app.models import KnownPerson, ReferenceEmbedding, User
from app.pet_recognizer import extract_pet_embedding
from app.recognizer import extract_embedding, serialize_embedding
from app.schemas import EmbeddingOut, PersonCreate, PersonDetail, PersonOut

router = APIRouter()


@router.get("/", response_model=list[PersonOut])
async def list_people(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(KnownPerson).where(KnownPerson.user_id == user.id).order_by(KnownPerson.name)
    )
    people = result.scalars().all()

    out = []
    for person in people:
        emb_result = await db.execute(
            select(ReferenceEmbedding).where(ReferenceEmbedding.person_id == person.id)
        )
        embeddings = emb_result.scalars().all()
        out.append(
            PersonOut(
                id=person.id,
                name=person.name,
                species=person.species,
                embedding_count=len(embeddings),
                created_at=person.created_at,
            )
        )
    return out


@router.post("/", response_model=PersonOut)
async def create_person(
    body: PersonCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Check for duplicate name
    result = await db.execute(
        select(KnownPerson).where(KnownPerson.user_id == user.id, KnownPerson.name == body.name)
    )
    if result.scalar_one_or_none():
        raise HTTPException(400, f"Person '{body.name}' already exists")

    person = KnownPerson(user_id=user.id, name=body.name, species=body.species)
    db.add(person)
    await db.commit()
    await db.refresh(person)

    return PersonOut(id=person.id, name=person.name, species=person.species, embedding_count=0, created_at=person.created_at)


@router.delete("/{person_id}")
async def delete_person(
    person_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(KnownPerson).where(KnownPerson.id == person_id, KnownPerson.user_id == user.id)
    )
    person = result.scalar_one_or_none()
    if not person:
        raise HTTPException(404, "Person not found")

    await db.delete(person)
    await db.commit()
    return {"ok": True}


@router.post("/{person_id}/photos", response_model=EmbeddingOut)
async def upload_reference_photo(
    person_id: str,
    request: Request,
    photo: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(KnownPerson).where(KnownPerson.id == person_id, KnownPerson.user_id == user.id)
    )
    person = result.scalar_one_or_none()
    if not person:
        raise HTTPException(404, "Person not found")

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    image_bytes = await photo.read(max_bytes + 1)
    if len(image_bytes) > max_bytes:
        raise HTTPException(413, f"File too large (max {settings.MAX_UPLOAD_SIZE_MB}MB)")

    if person.species in ("dog", "cat"):
        pet_app = get_pet_app(request)
        embedding = extract_pet_embedding(pet_app, image_bytes, person.species)
        if embedding is None:
            raise HTTPException(422, "No pet face detected. Please upload a clear photo showing the pet's face.")
    else:
        face_app = get_face_app(request)
        embedding = extract_embedding(face_app, image_bytes)
        if embedding is None:
            raise HTTPException(422, "No face detected in this photo. Please upload a clear front-facing photo.")

    ref = ReferenceEmbedding(
        person_id=person.id,
        embedding=serialize_embedding(embedding),
        photo_label=photo.filename,
    )
    db.add(ref)
    await db.commit()
    await db.refresh(ref)

    return EmbeddingOut(id=ref.id, photo_label=ref.photo_label, created_at=ref.created_at)


@router.delete("/{person_id}/photos/{photo_id}")
async def delete_reference_photo(
    person_id: str,
    photo_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ReferenceEmbedding)
        .join(KnownPerson)
        .where(
            ReferenceEmbedding.id == photo_id,
            KnownPerson.id == person_id,
            KnownPerson.user_id == user.id,
        )
    )
    ref = result.scalar_one_or_none()
    if not ref:
        raise HTTPException(404, "Reference photo not found")

    await db.delete(ref)
    await db.commit()
    return {"ok": True}
