"""Synthetic independent-review format/scorer tests; no reviewer judgments invented."""

from copy import deepcopy
import json
import unittest

from score_mapping_reference import byte_hash, score


def encode(value):
    return json.dumps(value, sort_keys=True).encode()


def fixtures():
    packet = {"schema_version": 2, "classes": ["food", "unsupported", "uncertain"],
              "database_sha256": "d" * 64, "class_names_sha256": "c" * 64,
              "workbook_sha256": "w" * 64, "catalog_sha256": "a" * 64, "baseline_sha256": "b" * 64}
    packet_bytes = encode(packet)
    rows = [{"class": name, "status": status, "class_definition": f"Synthetic definition {name}",
             "acceptable_database_names": ["Food"] if status == "accepted" else [],
             "evidence": ["synthetic fixture, not a real review"], "rationale": "Synthetic regression case"}
            for name, status in (("food", "accepted"), ("unsupported", "unsupported"), ("uncertain", "indeterminate"))]
    review = {"schema_version": 2, "packet_sha256": byte_hash(packet_bytes),
              **{key: packet[key] for key in ("database_sha256", "class_names_sha256", "workbook_sha256", "catalog_sha256")},
              "reviewer": {"id": "fixture-a", "qualifications": "Synthetic fixture only", "completed_at": "2026-09-12T00:00:00Z",
                           "independent_of_mapping_authors": True, "blinded_to_predictions_until_complete": True}, "rows": rows}
    second = deepcopy(review)
    second["reviewer"]["id"] = "fixture-b"
    predictions = {"database_sha256": packet["database_sha256"], "class_names_sha256": packet["class_names_sha256"],
                   "baseline_sha256": packet["baseline_sha256"], "comparisons": [
                       {"class": "food", "normalized_exact": "Food", "automatic_without_precomputed": None, "current_mapping": "Other"},
                       {"class": "unsupported", "normalized_exact": None, "automatic_without_precomputed": "Other", "current_mapping": None},
                       {"class": "uncertain", "normalized_exact": "Food", "automatic_without_precomputed": "Food", "current_mapping": "Food"}]}
    return packet_bytes, review, second, predictions


class MappingReferenceTests(unittest.TestCase):
    def evaluate(self, review=None, second=None, predictions=None, adjudication=None):
        packet, first, other, candidates = fixtures()
        return score(packet, encode(review or first), encode(second or other), predictions or candidates, {"Food", "Other"}, adjudication)

    def test_indeterminate_exclusion_and_abstention_are_explicit(self):
        result = self.evaluate()
        exact = result["scores"]["normalized_exact"]
        self.assertEqual(exact["scorable_classes"], 2)
        self.assertEqual(exact["indeterminate"], 1)
        self.assertEqual(exact["decision_agreement"], 1)
        self.assertEqual(result["scores"]["automatic_without_precomputed"]["missed_supported"], 1)
        self.assertEqual(result["scores"]["automatic_without_precomputed"]["wrong_match"], 1)
        self.assertEqual(result["scores"]["current_mapping"]["correct_abstention"], 1)

    def test_rejects_pending_unblinded_and_incomplete_references(self):
        for change, message in (("pending", "pending"), ("unblinded", "attestation"), ("missing", "one reviewed row"), ("evidence", "traceable evidence")):
            with self.subTest(change=change):
                _, review, _, _ = fixtures()
                if change == "pending":
                    review["rows"][0]["status"] = "pending"
                elif change == "unblinded":
                    review["reviewer"]["blinded_to_predictions_until_complete"] = False
                elif change == "missing":
                    review["rows"].pop()
                else:
                    review["rows"][0]["evidence"] = []
                with self.assertRaisesRegex(ValueError, message):
                    self.evaluate(review=review)

    def test_rejects_stale_hash_and_unknown_database_reference(self):
        _, review, _, _ = fixtures()
        review["database_sha256"] = "stale"
        with self.assertRaisesRegex(ValueError, "database_sha256 mismatch"):
            self.evaluate(review=review)
        _, review, _, _ = fixtures()
        review["rows"][0]["acceptable_database_names"] = ["Nonexistent"]
        with self.assertRaisesRegex(ValueError, "exist in the frozen database"):
            self.evaluate(review=review)

    def test_each_source_hash_and_required_reviewer_metadata_is_checked(self):
        for field in ("packet_sha256", "class_names_sha256", "workbook_sha256", "catalog_sha256"):
            with self.subTest(field=field):
                _, review, _, _ = fixtures()
                review[field] = "stale"
                with self.assertRaisesRegex(ValueError, "mismatch"):
                    self.evaluate(review=review)
        for field in ("id", "qualifications", "completed_at"):
            with self.subTest(field=field):
                _, review, _, _ = fixtures()
                review["reviewer"][field] = ""
                with self.assertRaisesRegex(ValueError, "required"):
                    self.evaluate(review=review)
        _, review, _, _ = fixtures()
        review["reviewer"]["independent_of_mapping_authors"] = False
        with self.assertRaisesRegex(ValueError, "attestation"):
            self.evaluate(review=review)

    def test_duplicate_class_rows_and_prediction_rows_are_rejected(self):
        _, review, _, predictions = fixtures()
        review["rows"][1] = deepcopy(review["rows"][0])
        with self.assertRaisesRegex(ValueError, "one reviewed row"):
            self.evaluate(review=review)
        predictions["comparisons"][1] = deepcopy(predictions["comparisons"][0])
        with self.assertRaisesRegex(ValueError, "one row per frozen class"):
            self.evaluate(predictions=predictions)

    def test_all_indeterminate_has_no_accuracy_denominator(self):
        _, review, second, _ = fixtures()
        for reference in (review, second):
            for row in reference["rows"]:
                row["status"] = "indeterminate"
                row["acceptable_database_names"] = []
        result = self.evaluate(review=review, second=second)
        for method in result["scores"].values():
            self.assertEqual(method["scorable_classes"], 0)
            self.assertIsNone(method["decision_agreement"])
            self.assertIsNone(method["matched_precision"])

    def test_two_distinct_reviewers_are_required(self):
        _, review, _, _ = fixtures()
        with self.assertRaisesRegex(ValueError, "distinct independent reviewers"):
            self.evaluate(second=review)

    def test_disagreement_requires_hash_bound_independent_adjudication(self):
        packet, review, second, predictions = fixtures()
        second["rows"][0]["acceptable_database_names"] = ["Other"]
        with self.assertRaisesRegex(ValueError, "separate adjudication"):
            self.evaluate(second=second)
        adjudication = {"schema_version": 2, "packet_sha256": byte_hash(packet),
                        "review_a_sha256": byte_hash(encode(review)), "review_b_sha256": byte_hash(encode(second)),
                        "adjudicator": {"id": "fixture-c", "qualifications": "Synthetic fixture", "completed_at": "2026-09-12T00:00:00Z"},
                        "rows": [deepcopy(review["rows"][0])]}
        result = score(packet, encode(review), encode(second), predictions, {"Food", "Other"}, adjudication)
        self.assertEqual(result["initial_disagreements"], 1)
        self.assertEqual(result["scores"]["normalized_exact"]["correct_match"], 1)
        adjudication["review_b_sha256"] = "stale"
        with self.assertRaisesRegex(ValueError, "exact completed review hashes"):
            self.evaluate(second=second, adjudication=adjudication)

    def test_predictions_need_same_frozen_data_and_valid_names(self):
        _, _, _, predictions = fixtures()
        predictions["baseline_sha256"] = "stale"
        with self.assertRaisesRegex(ValueError, "frozen reference inputs"):
            self.evaluate(predictions=predictions)
        _, _, _, predictions = fixtures()
        predictions["comparisons"][0]["current_mapping"] = "Missing"
        with self.assertRaisesRegex(ValueError, "Predicted row must exist"):
            self.evaluate(predictions=predictions)


if __name__ == "__main__":
    unittest.main()
