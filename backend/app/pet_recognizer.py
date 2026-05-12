import io
from pathlib import Path

import cv2
import numpy as np
import torch
import torch.nn.functional as F
import torchvision.models
import torchvision.models.detection
from PIL import Image

CKPT_BASE = Path(__file__).parent.parent / "third_party/pets_face_recognition/configs/to_reproduce"

# Target landmark positions in the 224x224 aligned output: left-eye, right-eye, nose
_BASE_PTS = np.array([[70, 92], [154, 92], [112, 160]], dtype=np.float32)


class PetFaceApp:
    def __init__(self):
        self.detector = None
        self.dog_model = None
        self.cat_model = None
        self.available = False

    def load(self) -> None:
        kp_path = CKPT_BASE / "keypoint/epoch=14.ckpt"
        dog_path = CKPT_BASE / "dog_fe/epoch=36_head.ckpt"
        cat_path = CKPT_BASE / "cat_fe/epoch=42_head.ckpt"

        if not all(p.exists() for p in [kp_path, dog_path, cat_path]):
            print("Pet recognition models not found — pet recognition disabled.")
            return

        print("Loading pet recognition models...")

        detector = torchvision.models.detection.keypointrcnn_resnet50_fpn(
            weights=None,
            num_classes=2,
            num_keypoints=3,
            box_detections_per_img=1,
            min_size=(320, 336, 352, 368, 384, 400),
            max_size=640,
        )
        ckpt = torch.load(kp_path, map_location="cpu", weights_only=False)
        sd = {k.replace("model_loss.model.", ""): v for k, v in ckpt.items() if k.startswith("model_loss.model.")}
        detector.load_state_dict(sd)
        detector.eval()
        self.detector = detector

        dog_model = torchvision.models.resnet50(weights=None)
        dog_model.fc = torch.nn.Linear(2048, 512)
        ckpt2 = torch.load(dog_path, map_location="cpu", weights_only=False)
        sd2 = {k.replace("model_loss.module.", ""): v for k, v in ckpt2.items() if k.startswith("model_loss.module.")}
        dog_model.load_state_dict(sd2)
        dog_model.eval()
        self.dog_model = dog_model

        cat_model = torchvision.models.resnet50(weights=None)
        cat_model.fc = torch.nn.Linear(2048, 512)
        ckpt3 = torch.load(cat_path, map_location="cpu", weights_only=False)
        sd3 = {k.replace("model_loss.module.", ""): v for k, v in ckpt3.items() if k.startswith("model_loss.module.")}
        cat_model.load_state_dict(sd3)
        cat_model.eval()
        self.cat_model = cat_model

        self.available = True
        print("Pet recognition models loaded.")


def _detect_and_align(pet_app: PetFaceApp, img_rgb: np.ndarray) -> np.ndarray | None:
    """Detect pet head keypoints and return a 224x224 aligned crop, or None."""
    t = torch.tensor(img_rgb).permute(2, 0, 1).unsqueeze(0).float() / 255
    with torch.no_grad():
        preds = pet_app.detector(t)

    scores = preds[0]["scores"].cpu().numpy()
    if len(scores) == 0 or scores[0] < 0.5:
        return None

    kpts = preds[0]["keypoints"].cpu().numpy()
    pts = np.round(kpts[0, :, :2]).astype(np.float32)  # (3, 2)

    dists = [np.sqrt(((pts[i] - pts[j]) ** 2).sum()) for i in range(3) for j in range(i + 1, 3)]
    if not all(d > 5 for d in dists):
        return None

    pts1 = np.vstack([pts.mean(axis=0), pts])
    pts2 = np.vstack([_BASE_PTS.mean(axis=0), _BASE_PTS])
    H, _ = cv2.findHomography(pts1, pts2, cv2.RANSAC)
    if H is None:
        return None

    return cv2.warpPerspective(img_rgb, H, (224, 224))


def extract_pet_embedding(pet_app: PetFaceApp, image_bytes: bytes, species: str) -> np.ndarray | None:
    """Extract L2-normalised 512-d embedding for a dog/cat face, or None."""
    if not pet_app.available:
        return None
    try:
        img_rgb = np.array(Image.open(io.BytesIO(image_bytes)).convert("RGB"))
        aligned = _detect_and_align(pet_app, img_rgb)
        if aligned is None:
            return None
        t = torch.tensor(aligned).permute(2, 0, 1).unsqueeze(0).float() / 255
        model = pet_app.dog_model if species == "dog" else pet_app.cat_model
        with torch.no_grad():
            emb = F.normalize(model(t), dim=1)
        return emb[0].cpu().numpy()
    except Exception:
        return None


def identify_pets(
    pet_app: PetFaceApp,
    image_bytes: bytes,
    known_embeddings: dict[str, list[np.ndarray]],
    species: str,
    threshold: float = 0.45,
) -> list[str]:
    """Return sorted list of matched pet names (same cosine-distance convention as human recognizer)."""
    if not pet_app.available or not known_embeddings:
        return []
    try:
        img_rgb = np.array(Image.open(io.BytesIO(image_bytes)).convert("RGB"))
        aligned = _detect_and_align(pet_app, img_rgb)
        if aligned is None:
            return []
        t = torch.tensor(aligned).permute(2, 0, 1).unsqueeze(0).float() / 255
        model = pet_app.dog_model if species == "dog" else pet_app.cat_model
        with torch.no_grad():
            emb = F.normalize(model(t), dim=1)
        embedding = emb[0].cpu().numpy()

        matched: set[str] = set()
        for name, refs in known_embeddings.items():
            dists = [1 - np.dot(embedding, ref) / (np.linalg.norm(embedding) * np.linalg.norm(ref)) for ref in refs]
            if min(dists) < threshold:
                matched.add(name)
        return sorted(matched)
    except Exception:
        return []
