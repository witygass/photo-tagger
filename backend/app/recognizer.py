import io

import numpy as np
from PIL import Image


def _cosine_distance(a: np.ndarray, b: np.ndarray) -> float:
    return 1 - np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


def extract_embedding(face_app, image_bytes: bytes) -> np.ndarray | None:
    """Extract the first face's normed_embedding from raw image bytes, or None."""
    img = np.array(Image.open(io.BytesIO(image_bytes)).convert("RGB"))
    faces = face_app.get(img)
    if not faces:
        return None
    return faces[0].normed_embedding


def serialize_embedding(embedding: np.ndarray) -> bytes:
    buf = io.BytesIO()
    np.save(buf, embedding)
    return buf.getvalue()


def deserialize_embedding(data: bytes) -> np.ndarray:
    return np.load(io.BytesIO(data))


def identify_people(
    face_app,
    image_bytes: bytes,
    known_embeddings: dict[str, list[np.ndarray]],
    threshold: float = 0.45,
) -> list[str]:
    """
    Pure function. Returns sorted list of matched person names.
    known_embeddings: {name: [embedding, ...]} built from DB rows.
    """
    try:
        img = np.array(Image.open(io.BytesIO(image_bytes)).convert("RGB"))
    except Exception:
        return []

    faces = face_app.get(img)
    if not faces:
        return []

    matched: set[str] = set()
    for face in faces:
        embedding = face.normed_embedding
        for name, refs in known_embeddings.items():
            if min(_cosine_distance(embedding, ref) for ref in refs) < threshold:
                matched.add(name)

    return sorted(matched)
