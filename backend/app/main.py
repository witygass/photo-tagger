from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.config import settings
from app.database import Base, engine
from app.routers import auth, drive, jobs, people
from app.routers.jobs import resume_stuck_jobs


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables (dev convenience; production uses Alembic)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Load InsightFace model once at startup
    from insightface.app import FaceAnalysis
    face_app = FaceAnalysis(
        name=settings.INSIGHTFACE_MODEL,
        providers=["CPUExecutionProvider"],
    )
    face_app.prepare(ctx_id=-1, det_size=(640, 640))
    app.state.face_app = face_app

    # Load pet recognition models (optional — disabled if checkpoints not present)
    from app.pet_recognizer import PetFaceApp
    pet_app = PetFaceApp()
    pet_app.load()
    app.state.pet_app = pet_app

    await resume_stuck_jobs(app)

    yield


app = FastAPI(title="Photo Tagger", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    same_site="lax",
    https_only=False,  # Set True in production with HTTPS
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(people.router, prefix="/people", tags=["people"])
app.include_router(drive.router, prefix="/drive", tags=["drive"])
app.include_router(jobs.router, prefix="/jobs", tags=["jobs"])


@app.get("/health")
async def health():
    return {"status": "ok"}
