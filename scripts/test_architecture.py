"""Contract, lifecycle and bounded-resource tests; no external services."""
import asyncio
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from backend.application import create_app
from backend.domain.policy import resolve_condition
from backend.services.container import get_services
from backend.services.nutrition_service import NutritionService
from backend.services.recommendation_service import RecommendationBusy, RecommendationService
from backend.settings import Settings


class ContractTests(unittest.TestCase):
    def test_prompt_keeps_database_units_and_unknowns_explicit(self):
        from backend.domain.rules import NutritionRules
        prompt = NutritionRules()._build_prompt([
            {'food_label': 'Idli', 'display_name': None, 'macros': {'calories': 123}},
            {'food_label': 'Unknown', 'macros': None},
        ], 'Maintenance', 'diabetic')
        self.assertIn('Idli (123 kcal per 100 g (database estimate))', prompt)
        self.assertIn('Nutrition unavailable; do not treat as zero', prompt)
        self.assertIn('NOT the amount eaten', prompt)
        self.assertIn("today's saved meals are not provided", prompt)
        self.assertNotIn('None (', prompt)

    def test_analysis_preserves_supplemental_provenance(self):
        from io import BytesIO
        from PIL import Image
        image = BytesIO()
        Image.new('RGB', (20, 20)).save(image, format='PNG')
        app = create_app(Settings(production=True))
        detection = {'food_label': 'bhakarwadi', 'confidence': .8, 'bounding_box': [0, 0, 10, 10]}
        with TestClient(app) as client:
            with patch.object(app.state.services.inference, 'analyze', AsyncMock(return_value={'detections': [detection], 'img_width': 20, 'img_height': 20})):
                response = client.post('/api/analyze-food', files={'file': ('food.png', image.getvalue(), 'image/png')})
                self.assertEqual(response.status_code, 200, response.text)
                food = response.json()['detections'][0]
                self.assertTrue(food['nutrition_source'].startswith('Supplemental:'))
                self.assertTrue(food['nutrition_source_url'].startswith('https://'))
                self.assertIn('not independently validated', food['nutrition_mapping_note'])
            result = asyncio.run(app.state.services.nutrition.get_nutrition_for_food('beetroot_poriyal'))
            self.assertIn('Approximate', result['nutrition_mapping_note'])

    def test_analysis_deduplicates_lookups_and_preserves_null_nutrition(self):
        from io import BytesIO
        from PIL import Image
        image = BytesIO()
        Image.new('RGB', (20, 20)).save(image, format='PNG')
        detection = {'food_label': 'Unknown', 'confidence': .8, 'bounding_box': [0, 0, 10, 10]}
        app = create_app(Settings(production=True))
        with TestClient(app) as client:
            with patch.object(app.state.services.inference, 'analyze', AsyncMock(return_value={'detections': [detection, detection], 'img_width': 20, 'img_height': 20})), \
                 patch.object(app.state.services.nutrition, 'get_nutrition_for_food', AsyncMock(return_value=None)) as lookup:
                response = client.post('/api/analyze-food', files={'file': ('private.png', image.getvalue(), 'image/png')})
                self.assertEqual(response.status_code, 200, response.text)
                self.assertIsNone(response.json()['detections'][0]['macros'])
                self.assertIsNone(response.json()['detections'][0]['nutrition_source'])
                lookup.assert_awaited_once()

    def test_aliases_validation_and_response_contract(self):
        app = create_app(Settings(production=True, recommendation_rate=100))
        with TestClient(app) as client:
            self.assertEqual(client.get('/api').status_code, 200)
            for name, key in [('diabetes', 'diabetic'), ('Diabetic', 'diabetic'), ('BP', 'hypertension'), (' high-blood-pressure ', 'hypertension'), ('None', 'none')]:
                response = client.post('/api/recommendations', json={'detected_foods': [{'food_label': 'Idli'}], 'health_condition': name})
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(response.json()['health_condition'], key)
                self.assertEqual(response.json()['source'], 'fallback')
                self.assertEqual(len(response.json()['recommendations']), 3)
                self.assertTrue(response.headers['x-request-id'])
            bad = client.post('/api/recommendations', json={'detected_foods': [{'food_label': 'Idli'}], 'health_condition': 'not a known condition'})
            self.assertEqual(bad.status_code, 400)
            self.assertEqual(client.post('/api/user/calculate-macros', json={'goal': 'Maintenance', 'target_calories': 0}).status_code, 400)
            self.assertEqual(client.post('/api/user/calculate-macros', json={}).status_code, 422)
            options = client.get('/api/user/health-conditions').json()['health_conditions']
            self.assertEqual(next(item for item in options if item['key'] == 'diabetic')['adjustment_label'], 'Adjusted for diabetes')
            self.assertNotIn('torch', sys.modules)
        with self.assertRaises(ValueError):
            resolve_condition('diab')

    def test_dependency_override_and_private_logging(self):
        app = create_app(Settings(production=True))
        inference = SimpleNamespace(status='not_loaded', model_available=True)
        app.dependency_overrides[get_services] = lambda: SimpleNamespace(inference=inference)
        with TestClient(app) as client, self.assertLogs('food.operations', level='INFO') as logs:
            response = client.get('/api/health?private=secret-condition', headers={'X-Request-ID': 'untrusted-id'})
        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(response.headers['x-request-id'], 'untrusted-id')
        self.assertNotIn('secret-condition', '\n'.join(logs.output))

    def test_partial_startup_always_cleans_up(self):
        resources = SimpleNamespace(start=AsyncMock(side_effect=RuntimeError('start failed')), close=AsyncMock())
        app = create_app(Settings(), services_factory=lambda _: resources)
        with self.assertRaises(RuntimeError):
            with TestClient(app):
                pass
        resources.close.assert_awaited_once()


class ResourceTests(unittest.IsolatedAsyncioTestCase):
    async def test_provider_capacity_and_cancellation(self):
        entered = 0
        ready = asyncio.Event()
        release = asyncio.Event()

        async def recommend(_):
            nonlocal entered
            entered += 1
            if entered == 2:
                ready.set()
            await release.wait()
            return ['one', 'two', 'three']

        provider = SimpleNamespace(name='groq', recommend=recommend, close=AsyncMock())
        service = RecommendationService(Settings(), providers=[provider])
        call = lambda: service.get_recommendations([{'food_label': 'Idli'}], 'Maintenance')
        first, second = asyncio.create_task(call()), asyncio.create_task(call())
        await ready.wait()
        with self.assertRaises(RecommendationBusy):
            await call()
        first.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await first
        release.set()
        await second
        self.assertEqual((await call())['source'], 'groq')
        await service.close()
        provider.close.assert_awaited_once()

    async def test_provider_errors_do_not_log_payload_and_fallback_keeps_context(self):
        provider = SimpleNamespace(name='groq', recommend=AsyncMock(side_effect=RuntimeError('PRIVATE health/key/prompt')), close=AsyncMock())
        service = RecommendationService(Settings(), providers=[provider])
        with self.assertLogs('food.operations', level='INFO') as logs:
            response = await service.get_recommendations([{'food_label': 'Idli'}], 'Maintenance', 'BP')
        self.assertEqual(response['health_condition'], 'hypertension')
        self.assertEqual(response['source'], 'fallback')
        self.assertNotIn('PRIVATE', '\n'.join(logs.output))
        await service.close()

    async def test_nutrition_cache_is_bounded_and_copies_results(self):
        service = NutritionService()
        lookup = AsyncMock(return_value={'macros': {'calories': 10}})
        with patch.object(service, '_lookup_nutrition', lookup):
            first = await service.get_nutrition_for_food('Idli')
            first['macros']['calories'] = 999
            self.assertEqual((await service.get_nutrition_for_food('Idli'))['macros']['calories'], 10)
            lookup.assert_awaited_once()
            for index in range(300):
                await service.get_nutrition_for_food(str(index))
            self.assertEqual(len(service._results), 256)


if __name__ == '__main__':
    unittest.main()
