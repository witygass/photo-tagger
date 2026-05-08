import os
import numpy as np
from pathlib import Path
from PIL import Image
import insightface
from insightface.app import FaceAnalysis

KNOWN_PEOPLE_DIR = os.path.join(os.path.dirname(__file__), "known_people")
SIMILARITY_THRESHOLD = 0.45  # cosine distance; lower = more strict


def _cosine_distance(a: np.ndarray, b: np.ndarray) -> float:
    return 1 - np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


class FaceRecognizer:
    def __init__(self):
        self.app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
        self.app.prepare(ctx_id=-1, det_size=(640, 640))
        self.known_embeddings: dict[str, list[np.ndarray]] = {}
        self._load_known_people()

    def _load_known_people(self):
        base = Path(KNOWN_PEOPLE_DIR)
        if not base.exists():
            return
        for person_dir in sorted(base.iterdir()):
            if not person_dir.is_dir():
                continue
            name = person_dir.name
            embeddings = []
            for img_path in person_dir.glob("*"):
                if img_path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
                    continue
                try:
                    img = np.array(Image.open(img_path).convert("RGB"))
                    faces = self.app.get(img)
                    if faces:
                        embeddings.append(faces[0].normed_embedding)
                except Exception as e:
                    print(f"  Warning: could not process {img_path}: {e}")
            if embeddings:
                self.known_embeddings[name] = embeddings
                print(f"  Loaded {len(embeddings)} reference(s) for '{name}'")

    def identify_people(self, image_path: str) -> list[str]:
        try:
            img = np.array(Image.open(image_path).convert("RGB"))
        except Exception:
            return []

        faces = self.app.get(img)
        if not faces:
            return []

        matched = set()
        for face in faces:
            embedding = face.normed_embedding
            for name, refs in self.known_embeddings.items():
                distances = [_cosine_distance(embedding, ref) for ref in refs]
                if min(distances) < SIMILARITY_THRESHOLD:
                    matched.add(name)

        return sorted(matched)
