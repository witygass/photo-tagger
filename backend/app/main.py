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

    from app.model_manager import ModelManager
    app.state.model_manager = ModelManager()

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
