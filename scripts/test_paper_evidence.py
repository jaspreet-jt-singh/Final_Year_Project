"""Offline manuscript derivation/drift regressions using small synthetic evidence."""

from copy import deepcopy
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from generate_paper_evidence import AUDIT, GROUPED, OUTPUTS, derive_macros, generate, render_evidence


def fixture():
    audit = {
        "schema_version": 1,
        "dataset": {
            "class_count": 3, "image_count": 15, "manifest_sha256": "a" * 64,
            "splits": {name: {"images": images, "instances": instances, "issue_images": issues}
                       for name, images, instances, issues in (("train", 9, 12, 1), ("valid", 3, 5, 0), ("test", 3, 4, 0))},
            "pixel_duplicates": {"cross_split_groups": 1, "affected_images": 2,
                                 "pairs": {"train:test": {"shared_groups": 1}}},
        },
        "nutrition": {"food_rows": 1001, "mapping_rows": 4, "review_score_below_0_9_or_missing": 1,
                      "coverage_not_accuracy": {"normalized_exact": 1, "automatic_without_precomputed": 2, "current_mapping": 3}},
    }
    grouped = {
        "schema_version": 1, "dataset_fingerprint": "a" * 64, "class_names": ["a", "b", "c"],
        "sources": [{"images": 7}, {"images": 9}], "total_groups": 7,
        "quarantined_images": 3, "quarantined_groups": 2,
        "splits": {"train": {"images": 8, "groups": 3, "unique_pixels": 6},
                   "valid": {"images": 2, "groups": 1, "unique_pixels": 2},
                   "test": {"images": 2, "groups": 1, "unique_pixels": 2}},
        "known_group_overlap_across_candidate_splits": 0, "source_family_groups_spanning_old_splits": 3,
        "quarantine_images_by_reason_nonexclusive": {"unresolved_source_lineage": 3, "annotation_or_decode_issue": 2,
                                                    "identical_pixels_different_labels": 1, "no_accepted_annotations": 0},
    }
    return audit, grouped


def encoded(audit, grouped):
    audit_bytes = (json.dumps(audit, indent=2) + "\n").encode()
    grouped = {**grouped, "audit_sha256": hashlib.sha256(audit_bytes).hexdigest()}
    return audit_bytes, (json.dumps(grouped, indent=2) + "\n").encode()


class PaperEvidenceTests(unittest.TestCase):
    def test_derives_counts_percentages_and_nonexclusive_reasons(self):
        values = derive_macros(*fixture())
        self.assertEqual(values["AuditImages"], 15)
        self.assertEqual(values["AuditTrainInstances"], 12)
        self.assertEqual(values["AuditFlaggedImages"], 1)
        self.assertEqual(values["AuditTrainValidGroups"], 0)
        self.assertEqual(values["AuditTrainTestGroups"], 1)
        self.assertEqual(values["CandidateSourceImages"], 16)
        self.assertEqual(values["CandidateEligibleImages"], 12)
        self.assertEqual(values["CandidateRepeatedPixels"], 2)
        self.assertEqual(values["CoverageCurrentPercent"], Decimal(100))
        self.assertEqual(values["CandidateIssueGroupImages"], 2)
        self.assertEqual(values["CandidateEmptyGroupImages"], 0)

    def test_renders_exact_macro_set_and_formats(self):
        content = render_evidence(*encoded(*fixture()))
        self.assertIn(r"\newcommand{\NutritionRows}{1,001}", content)
        self.assertIn(r"\newcommand{\CoverageExactPercent}{33.33}", content)
        self.assertIn(r"\newcommand{\CoverageAutomaticPercent}{66.67}", content)
        self.assertIn(r"\newcommand{\CoverageCurrentPercent}{100.00}", content)
        expected = set("""AuditClasses AuditImages AuditTrainImages AuditValidImages AuditTestImages
            AuditTrainInstances AuditValidInstances AuditTestInstances AuditFlaggedImages AuditDuplicateGroups
            AuditDuplicateImages AuditTrainValidGroups AuditTrainTestGroups AuditValidTestGroups NutritionRows
            MappingRows CoverageExact CoverageAutomatic CoverageCurrent MappingReviewCount CoverageExactPercent
            CoverageAutomaticPercent CoverageCurrentPercent CandidateSourceImages CandidateGroups
            CandidateQuarantinedImages CandidateQuarantinedGroups CandidateTrainImages CandidateTrainGroups
            CandidateTrainUniquePixels CandidateValidImages CandidateValidGroups CandidateValidUniquePixels
            CandidateTestImages CandidateTestGroups CandidateTestUniquePixels CandidateOldOverlapGroups
            CandidateEligibleImages CandidateRepeatedPixels CandidateUnresolvedImages CandidateConflictImages
            CandidateIssueGroupImages CandidateEmptyGroupImages""".split())
        self.assertEqual(set(derive_macros(*fixture())), expected)
        self.assertEqual(content.count("SHA256:"), 2)

    def test_rejects_invalid_counts_and_inconsistent_artifacts(self):
        cases = [
            ("audit", ("dataset", "image_count"), 16, "split image totals"),
            ("audit", ("dataset", "class_count"), True, "nonnegative integer"),
            ("audit", ("nutrition", "coverage_not_accuracy", "current_mapping"), 4, "exceeds class"),
            ("grouped", ("dataset_fingerprint",), "b" * 64, "fingerprints differ"),
            ("grouped", ("class_names",), ["a", "a", "c"], "Class counts"),
            ("grouped", ("quarantined_images",), 4, "Eligible plus quarantined"),
            ("grouped", ("total_groups",), 8, "group totals"),
            ("grouped", ("splits", "train", "unique_pixels"), 9, "group/pixel/image"),
            ("grouped", ("known_group_overlap_across_candidate_splits",), 1, "groups overlap"),
            ("audit", ("schema_version",), 2, "schema version"),
        ]
        for document, keys, value, error in cases:
            with self.subTest(document=document, keys=keys):
                audit, grouped = deepcopy(fixture())
                target = audit if document == "audit" else grouped
                for key in keys[:-1]:
                    target = target[key]
                target[keys[-1]] = value
                with self.assertRaisesRegex(ValueError, error):
                    derive_macros(audit, grouped)

    def test_rejects_wrong_audit_reference(self):
        audit_bytes, grouped_bytes = encoded(*fixture())
        grouped = json.loads(grouped_bytes)
        grouped["audit_sha256"] = "b" * 64
        with self.assertRaisesRegex(ValueError, "different audit artifact"):
            render_evidence(audit_bytes, json.dumps(grouped).encode())

    def test_check_is_read_only_and_rejects_missing_output_or_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for path, content in zip((AUDIT, GROUPED), encoded(*fixture())):
                (root / path).parent.mkdir(parents=True, exist_ok=True)
                (root / path).write_bytes(content)
            with self.assertRaisesRegex(ValueError, "missing or out of date"):
                generate(root, check=True)
            self.assertTrue(all(not (root / path).exists() for path in OUTPUTS))
            expected = generate(root)
            self.assertEqual(generate(root, check=True), expected)
            self.assertEqual((root / OUTPUTS[0]).read_bytes(), (root / OUTPUTS[1]).read_bytes())
            output = root / OUTPUTS[1]
            output.write_text("% deliberate drift\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Journal"):
                generate(root, check=True)
            self.assertEqual(output.read_text(encoding="utf-8"), "% deliberate drift\n")
            self.assertEqual((root / OUTPUTS[0]).read_text(encoding="utf-8"), expected)


if __name__ == "__main__":
    unittest.main()
