import asyncio
import gc
import logging

logger = logging.getLogger(__name__)

# Unload models after this many seconds of inactivity.
_DORMANCY_SECONDS = 5 * 60


class ModelManager:
    """Loads InsightFace + PyTorch models on demand and unloads them after a quiet period.

    Usage:
        face_app, pet_app = await manager.acquire()
        try:
            ...
        finally:
            manager.release()
    """

    def __init__(self) -> None:
        self._face_app = None
        self._pet_app = None
        self._load_lock = asyncio.Lock()
        self._active = 0
        self._dormancy_task: asyncio.Task | None = None

    async def acquire(self):
        """Ensure models are loaded, cancel any pending unload, return (face_app, pet_app)."""
        self._cancel_dormancy()

        # Double-checked load: only one coroutine enters the executor at a time.
        if self._face_app is None:
            async with self._load_lock:
                if self._face_app is None:
                    loop = asyncio.get_running_loop()
                    await loop.run_in_executor(None, self._load)

        self._active += 1
        return self._face_app, self._pet_app

    def release(self) -> None:
        """Signal that a caller is done with the models. Starts the dormancy timer when idle."""
        self._active = max(0, self._active - 1)
        if self._active == 0:
            self._dormancy_task = asyncio.create_task(self._dormancy_countdown())

    def _cancel_dormancy(self) -> None:
        if self._dormancy_task and not self._dormancy_task.done():
            self._dormancy_task.cancel()
            self._dormancy_task = None

    async def _dormancy_countdown(self) -> None:
        try:
            await asyncio.sleep(_DORMANCY_SECONDS)
            if self._active == 0:
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, self._unload)
        except asyncio.CancelledError:
            pass

    def _load(self) -> None:
        logger.info("Loading ML models...")
        from insightface.app import FaceAnalysis

        from app.config import settings
        from app.pet_recognizer import PetFaceApp

        face_app = FaceAnalysis(name=settings.INSIGHTFACE_MODEL, providers=["CPUExecutionProvider"])
        face_app.prepare(ctx_id=-1, det_size=(640, 640))
        self._face_app = face_app

        pet_app = PetFaceApp()
        pet_app.load()
        self._pet_app = pet_app
        logger.info("ML models loaded.")

    def _unload(self) -> None:
        logger.info("Unloading ML models (dormant).")
        self._face_app = None
        self._pet_app = None
        gc.collect()
        logger.info("ML models unloaded.")
