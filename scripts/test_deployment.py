"""Focused deployment regression tests; never call paid/external services."""
import asyncio
from io import BytesIO
from pathlib import Path
import sys
from threading import Event
import unittest
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PIL import Image
from fastapi.testclient import TestClient
from backend.application import create_app
from backend.settings import Settings
from backend.services.inference_runtime import InferenceRuntime, InferenceBusy, InvalidImage, MAX_UPLOAD_BYTES
from backend.services.recommendation_service import RecommendationService


def image_bytes(size=(20, 10), orientation=None):
    output = BytesIO()
    image = Image.new("RGB", size, "white")
    exif = image.getexif()
    if orientation:
        exif[274] = orientation
    image.save(output, format="JPEG", exif=exif)
    return output.getvalue()


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(Settings(production=True))
        self.context = TestClient(self.app)
        self.client = self.context.__enter__()
        self.app.state.limiter.reset()

    def tearDown(self):
        self.context.__exit__(None, None, None)

    def test_health_does_not_import_torch(self):
        self.assertNotIn("torch", sys.modules)
        result = self.client.get("/api/health").json()
        self.assertEqual(result["model_status"], "not_loaded")
        self.assertTrue(result["model_available"])

    def test_nutrition_and_macros(self):
        self.assertEqual(self.client.get("/api/user/goals").status_code, 200)
        self.assertEqual(self.client.get("/api/user/health-conditions").status_code, 200)
        response = self.client.post("/api/user/calculate-macros", json={"goal": "Maintenance", "target_calories": 2000})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["target_calories"], 2000)
        self.assertTrue(self.client.get("/api/test-nutrition/Idli").json()["found"])

    def test_invalid_images(self):
        for content in (b"", b"not an image"):
            response = self.client.post("/api/analyze-food", files={"file": ("x.jpg", content, "image/jpeg")})
            self.assertEqual(response.status_code, 400)
        response = self.client.post("/api/analyze-food", files={"file": ("x.jpg", b"x" * (MAX_UPLOAD_BYTES + 1), "image/jpeg")})
        self.assertEqual(response.status_code, 413)

    def test_busy_and_no_detection(self):
        with patch.object(self.app.state.services.inference, "analyze", AsyncMock(side_effect=InferenceBusy("busy"))):
            response = self.client.post("/api/analyze-food", files={"file": ("x.jpg", image_bytes(), "image/jpeg")})
            self.assertEqual(response.status_code, 503)
            self.assertIn("retry-after", response.headers)
        with patch.object(self.app.state.services.inference, "analyze", AsyncMock(return_value=None)):
            response = self.client.post("/api/analyze-food", files={"file": ("x.jpg", image_bytes(), "image/jpeg")})
            self.assertTrue(response.json()["food_not_found"])

    def test_bad_recommendation_payload(self):
        for body in ([], {"detected_foods": [None]}, {"detected_foods": [{"food_label": "Idli", "macros": "bad"}]}):
            self.assertEqual(self.client.post("/api/recommendations", json=body).status_code, 400)

    def test_rate_limit(self):
        for _ in range(5):
            self.client.post("/api/recommendations", json={})
        response = self.client.post("/api/recommendations", json={})
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.headers["retry-after"], "60")


class RuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def test_invalid_image_with_missing_optional_plugin(self):
        runtime = InferenceRuntime()
        def unavailable_plugin(*args):
            raise ModuleNotFoundError("pi_heif")
        try:
            with patch.object(Image, "open", side_effect=unavailable_plugin):
                for content in (b"invalid image data", b"\xff\xd8\xffbroken JPEG", b"\x89PNG\r\n\x1a\nbroken PNG"):
                    with self.assertRaises(InvalidImage):
                        await runtime.analyze(content)
        finally:
            runtime.close()

    async def test_orientation_and_dimensions(self):
        runtime = InferenceRuntime()
        class Capture:
            def analyze_image(self, content, **kwargs):
                return Image.open(BytesIO(content)).size
        runtime.service = Capture()
        try:
            self.assertEqual(await runtime.analyze(image_bytes(orientation=6)), (10, 20))
            with self.assertRaises(InvalidImage):
                await runtime.analyze(image_bytes(size=(6000, 4200)))
        finally:
            runtime.close()

    async def test_supported_formats_without_generic_opener(self):
        runtime = InferenceRuntime()
        class Capture:
            def analyze_image(self, content, **kwargs):
                from PIL.PngImagePlugin import PngImageFile
                with PngImageFile(BytesIO(content)) as image:
                    return image.size
        runtime.service = Capture()
        try:
            for format_name in ("JPEG", "PNG", "WEBP"):
                data = BytesIO()
                Image.new("RGB", (30, 20), "white").save(data, format=format_name)
                with patch.object(Image, "open", side_effect=ModuleNotFoundError("pi_heif")):
                    self.assertEqual(await runtime.analyze(data.getvalue()), (30, 20))
        finally:
            runtime.close()

    async def test_capacity_survives_cancellation(self):
        runtime = InferenceRuntime()
        gate = Event()
        started = Event()
        def blocking(_):
            started.set()
            gate.wait(5)
        runtime._analyze = blocking
        first = asyncio.create_task(runtime.analyze(b"a"))
        second = asyncio.create_task(runtime.analyze(b"b"))
        try:
            await asyncio.to_thread(started.wait, 2)
            await asyncio.sleep(0)
            with self.assertRaises(InferenceBusy):
                await runtime.analyze(b"c")
            first.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await first
            with self.assertRaises(InferenceBusy):
                await runtime.analyze(b"d")
        finally:
            gate.set()
            await second
            runtime.close()

    async def test_groq_failure_uses_free_fallback(self):
        from backend.services.providers import GroqProvider
        settings = Settings(production=True, groq_key="fake", openai_key="must-not-be-used", ollama_host="must-not-be-used")
        with patch.object(GroqProvider, "recommend", AsyncMock(side_effect=TimeoutError)), \
             patch("backend.services.recommendation_service.OpenAIProvider") as paid, \
             patch("backend.services.recommendation_service.OllamaProvider") as local:
            service = RecommendationService(settings)
            await service.initialize()
            result = await service.get_recommendations([{"food_label": "Idli"}], "Maintenance")
            self.assertEqual(result["source"], "fallback")
            self.assertEqual(len(result["recommendations"]), 3)
            paid.assert_not_called()
            local.assert_not_called()
            await service.close()


if __name__ == "__main__":
    unittest.main()
