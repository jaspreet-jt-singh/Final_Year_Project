"""Lazy, bounded CPU inference. No Torch import on the web startup path."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from io import BytesIO
import os
from pathlib import Path
from threading import BoundedSemaphore

from PIL import Image, ImageOps, UnidentifiedImageError

MAX_UPLOAD_BYTES = 4 * 1024 * 1024
MAX_IMAGE_PIXELS = 25_000_000


class InvalidImage(ValueError):
    pass


class InferenceBusy(RuntimeError):
    pass


class InferenceRuntime:
    def __init__(self):
        self.status = "not_loaded"
        self.service = None
        self.threads_configured = False
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="inference")
        # One running request and at most one waiting request per instance.
        self.capacity = BoundedSemaphore(2)

    @property
    def model_available(self):
        root = Path(__file__).resolve().parents[2]
        return (root / os.getenv("YOLO_MODEL_PATH", "results_after_discontinuation/yolo11s_indian_food_best.pt")).is_file()

    def _analyze(self, content):
        try:
            with Image.open(BytesIO(content)) as source:
                if source.format not in {"JPEG", "PNG", "WEBP"}:
                    raise InvalidImage("Use a JPEG, PNG, or WebP image")
                if source.width * source.height > MAX_IMAGE_PIXELS:
                    raise InvalidImage("Image must contain at most 25 megapixels")
                source.verify()
            with Image.open(BytesIO(content)) as source:
                normalized = ImageOps.exif_transpose(source).convert("RGB")
                buffer = BytesIO()
                normalized.save(buffer, format="PNG")
                normalized.close()
        except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError) as exc:
            raise InvalidImage("The uploaded image cannot be decoded") from exc

        if self.service is None:
            self.status = "loading"
            try:
                from .vision_service import VisionService
                import torch
                if not self.threads_configured:
                    torch.set_num_threads(1)
                    self.threads_configured = True
                service = VisionService()
                asyncio.run(service.initialize())
                self.service = service
                self.status = "ready"
            except Exception:
                self.status = "error"
                raise
        return self.service.analyze_image(buffer.getvalue(), conf=0.25, iou=0.45)

    async def analyze(self, content):
        if not self.capacity.acquire(blocking=False):
            raise InferenceBusy("The analyzer is busy. Please retry in a few seconds.")
        try:
            future = self.executor.submit(partial(self._analyze, content))
        except BaseException:
            self.capacity.release()
            raise
        # Release only when the actual thread finishes, even if HTTP is cancelled.
        future.add_done_callback(lambda _: self.capacity.release())
        try:
            return await asyncio.wait_for(asyncio.shield(asyncio.wrap_future(future)), timeout=110)
        except asyncio.TimeoutError as exc:
            raise InferenceBusy("Analysis took too long. Please retry shortly.") from exc

    def close(self):
        self.executor.shutdown(wait=False, cancel_futures=True)
