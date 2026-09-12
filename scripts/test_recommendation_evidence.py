"""Synthetic regression checks for the offline evidence producer itself."""

import asyncio
import json
import unittest
from pathlib import Path

from validate_recommendation_evidence import (
    canonical_bytes,
    canonical_request,
    fixture_scenarios,
    review_rubric,
    run_adapter_suite,
    run_matrix,
    triage_text,
)


class RecommendationEvidenceTests(unittest.TestCase):
    def test_scenarios_are_deterministic_and_nullable_names_follow_router(self):
        self.assertEqual(canonical_bytes(fixture_scenarios()), canonical_bytes(fixture_scenarios()))
        self.assertEqual(len(fixture_scenarios()), 6)
        scenario = fixture_scenarios()[-1]
        foods, goal, condition = canonical_request(scenario["foods"], "Maintenance", "BP")
        self.assertNotIn("display_name", foods[0])
        self.assertEqual((goal, condition), ("maintenance", "hypertension"))

    def test_matrix_has_all_216_unique_structural_cases(self):
        report = asyncio.run(run_matrix())
        self.assertEqual((report["total"], report["passed"]), (216, 216))
        self.assertEqual(len({row["id"] for row in report["cases"]}), 216)
        self.assertTrue(report["observations"]["same_named_food_different_macros_produces_identical_fallback"])
        self.assertTrue(report["observations"]["non_general_context_fallback_is_identical_across_goals"])

    def test_real_sdk_mock_transport_suite(self):
        report = asyncio.run(run_adapter_suite())
        self.assertEqual(report["passed"], report["total"], json.dumps(report, indent=2))
        self.assertEqual(report["total"], 16)

    def test_triage_does_not_mistake_food_name_for_uncertainty_notice(self):
        flags = triage_text(["Your Synthetic Unknown is fine."], "digestive_issues", True)
        self.assertIn("food_suitability_reassurance_without_assessment", flags)
        self.assertIn("missing_nutrition_not_explicitly_acknowledged", flags)
        self.assertNotIn("missing_nutrition_not_explicitly_acknowledged", triage_text(["Nutrition unavailable."], "none", True))

    def test_review_is_pending_and_no_live_key_loader_is_used(self):
        self.assertFalse(review_rubric()["clinical_validation_performed"])
        self.assertEqual(review_rubric()["status"], "pending_qualified_expert")
        source = Path(__file__).with_name("validate_recommendation_evidence.py").read_text(encoding="utf-8")
        self.assertNotIn("Settings.from_environment(", source)
        self.assertNotIn("os.getenv(", source)
        self.assertIn("httpx.MockTransport(handler)", source)


if __name__ == "__main__":
    unittest.main()
