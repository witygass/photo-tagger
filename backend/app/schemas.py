from datetime import datetime

from pydantic import BaseModel


# Auth
class UserOut(BaseModel):
    id: str
    email: str
    name: str | None
    picture_url: str | None


# Known People
class PersonCreate(BaseModel):
    name: str
    species: str = "human"  # human | dog | cat


class EmbeddingOut(BaseModel):
    id: str
    photo_label: str | None
    created_at: datetime


class PersonOut(BaseModel):
    id: str
    name: str
    species: str
    embedding_count: int
    created_at: datetime


class PersonDetail(PersonOut):
    embeddings: list[EmbeddingOut]


# Drive
class FolderOut(BaseModel):
    id: str
    name: str
    mime_type: str


# Jobs
class JobCreate(BaseModel):
    folder_id: str


class JobOut(BaseModel):
    id: str
    folder_id: str
    folder_name: str | None
    status: str
    total: int
    processed: int
    percent: int
    error_msg: str | None
    created_at: datetime
    updated_at: datetime


class PhotoOut(BaseModel):
    id: str
    drive_file_id: str
    file_name: str | None
    thumbnail_url: str | None
    drive_link: str | None
    people: list[str]


class ResultsOut(BaseModel):
    job_id: str
    total: int
    page: int
    page_size: int
    people_in_job: list[str]
    photos: list[PhotoOut]
