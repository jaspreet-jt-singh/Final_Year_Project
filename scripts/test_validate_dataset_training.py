"""Synthetic offline tests; never read dataset images or load a detector."""

import copy
import json
from pathlib import Path
import tempfile
import unittest

from PIL import Image

from validate_dataset_training import (
    calibration_probe,
    candidate_support,
    classify_label_conflict,
    csv_records,
    dhash,
    equal_csv_value,
    locations,
    notebook_evaluations,
    parse_annotations,
    perceptual_candidates,
    redact_account_paths,
    reconstruct_training,
    stratified_sample,
    summarize_duplicates,
    write_json,
)


def record(path, split="train", group="a", classes=None, digest=None, fingerprint=0):
    return {"path": path, "split": split, "candidate_split": split, "group_id": group,
            "classes": [0] if classes is None else classes, "sha256": digest or path,
            "pixel_sha256": digest or path, "dhash": fingerprint}


def training_row(epoch, seconds, metric):
    return {"epoch": str(epoch), "time": str(seconds), "metrics/mAP50(B)": str(metric),
            "metrics/mAP50-95(B)": str(metric / 2)}


class AnnotationTests(unittest.TestCase):
    def test_valid_and_edge_flags_are_distinct(self):
        valid, edge = parse_annotations("0 .5 .5 .5 .5\n1 .95 .5 .5 .5", 2)
        self.assertTrue(valid["accepted_by_range_checks"])
        self.assertFalse(valid["box_edges_outside_frame_tolerance_1e_6"])
        self.assertTrue(edge["accepted_by_range_checks"])
        self.assertTrue(edge["box_edges_outside_frame_tolerance_1e_6"])

    def test_degenerate_dimensions_and_all_other_rejections(self):
        lines = ["0 .5 .5 0 .2", "0 .5 .5 .2 0", "0 nan .5 .2 .2", "0 .5 .5 -.1 .2",
                 "2 .5 .5 .2 .2", "0 2 .5 .2 .2", "x .5 .5 .2 .2", "0 .5"]
        parsed = parse_annotations("\n".join(lines), 2)
        self.assertEqual([row["issues"][0] for row in parsed], [
            "zero_width", "zero_height", "nonfinite_coordinates", "dimension_out_of_range",
            "class_out_of_range", "center_out_of_range", "nonnumeric_or_noninteger_class", "field_count"])
        self.assertFalse(any(row["accepted_by_range_checks"] for row in parsed))
        json.dumps(parsed, allow_nan=False)

    def test_blank_lines_are_not_annotations(self):
        self.assertEqual(parse_annotations(" \n\n", 2), [])

    def test_label_formatting_and_semantic_set_differences(self):
        parse = lambda text: parse_annotations(text, 2)  # noqa: E731
        base = parse("0 .5 .5 .2 .2\n1 .4 .4 .3 .3")
        self.assertEqual(classify_label_conflict([base, parse("1 0.40 .4 .3 .30\n0 .5 .50 .20 .2")]), "format_or_order_only")
        self.assertEqual(classify_label_conflict([base, parse("0 .5 .5 .2 .2")]), "different_class_or_instance_multiset")
        self.assertEqual(classify_label_conflict([base, parse("0 .5 .5 .25 .2\n1 .4 .4 .3 .3")]), "different_boxes_same_class_multiset")
        self.assertEqual(classify_label_conflict([base, parse("0 nan .5 .2 .2")]), "unparseable_numeric_content")


class DatasetTests(unittest.TestCase):
    def test_duplicate_groups_not_pair_products(self):
        rows = [record("a", digest="same"), record("b", digest="same"),
                record("c", "valid", digest="same"), record("d", "test", digest="same"), record("e")]
        result = summarize_duplicates(rows, "sha256")
        self.assertEqual((result["groups"], result["images"]), (1, 4))
        self.assertEqual(result["pairs"]["train:valid"], {"groups": 1, "images": 3})

    def test_group_support_counts_instances_and_images_separately(self):
        groups = [{"group_id": "a", "candidate_split": "train", "rows": [record("a", classes=[0, 0, 1]), record("b")]},
                  {"group_id": "b", "candidate_split": None, "rows": [record("c", classes=[1])]}]
        support = candidate_support(groups, ["first", "second"])
        self.assertEqual(support["first"]["train"], {"groups": 1, "images": 2, "instances": 3})
        self.assertEqual(support["second"]["quarantine"]["groups"], 1)
        self.assertEqual(support["first"]["test"]["groups"], 0)

    def test_sample_bounded_reproducible_and_excludes_quarantine(self):
        groups = [{"group_id": str(i), "candidate_split": "train", "rows": [record(f"a{i}"), record(f"b{i}")]}
                  for i in range(5)]
        groups.append({"group_id": "q", "candidate_split": None, "rows": [record("q")]})
        selected = stratified_sample(groups, per_class_split=2)
        self.assertEqual(len(selected), 2)
        self.assertEqual(len({row["group_id"] for row in selected}), 2)
        self.assertEqual(selected, stratified_sample(list(reversed(groups)), per_class_split=2))

    def test_pair_screen_exclusions_threshold_and_cap(self):
        rows = [record("a", "train", "a", fingerprint=0), record("b", "test", "b", fingerprint=1),
                record("c", "valid", "c", fingerprint=3), record("d", "test", "a", fingerprint=0),
                record("e", "test", "e", digest="a", fingerprint=0)]
        result = perceptual_candidates(rows, threshold=1, cap=1)
        self.assertGreater(result["candidate_pairs_before_cap"], 1)
        self.assertTrue(result["queue_truncated"])
        self.assertEqual(len(result["queue"]), 1)
        full = perceptual_candidates(rows, threshold=1)["queue"]
        pairs = {(row["left"], row["right"]) for row in full}
        self.assertNotIn(("a", "d"), pairs)
        self.assertNotIn(("a", "e"), pairs)
        self.assertNotIn(("a", "c"), pairs)

    def test_hash_and_probe_are_deterministic_not_identity_proofs(self):
        dark, light = Image.new("RGB", (20, 20), "black"), Image.new("RGB", (20, 20), "white")
        self.assertEqual(dhash(dark), 0)
        self.assertEqual(dhash(dark), dhash(light))  # Collision: never a byte-identity proof.
        self.assertEqual(set(calibration_probe(dark)), {"jpeg_quality_35", "resize_48_square", "crop_10_percent_each_edge",
                                                       "rotate_10_degrees_black_fill", "horizontal_mirror"})


class TrainingTests(unittest.TestCase):
    def test_account_redaction_preserves_method_path_and_metrics(self):
        value = {"source": '/kaggle/input/datasets/example-user/project/weights/best.pt',
                 "nested": ["/kaggle/input/models/example-user/model/1.pt", .75],
                 "unrelated": "/kaggle/working/data.yaml"}
        redacted = redact_account_paths(value)
        self.assertNotIn("example-user", json.dumps(redacted))
        self.assertIn("[account-redacted]/project/weights/best.pt", redacted["source"])
        self.assertEqual(redacted["nested"][1], .75)
        self.assertEqual(redacted["unrelated"], value["unrelated"])
        self.assertIn("example-user", value["source"])

    def test_reconstruction_and_timer_reset(self):
        before = [training_row(1, 100, .4), training_row(2, 200, .5)]
        after = [training_row(3, 80, .7), training_row(4, 150, .6)]
        result = reconstruct_training(before, after, copy.deepcopy(before + after))
        self.assertTrue(result["reconstructed_numeric_cells_match"])
        self.assertTrue(result["timer_resets_at_resume"])
        self.assertEqual(result["sum_stage_last_logged_seconds_not_wall_clock"], 350)
        self.assertEqual(result["best_validation_map50"]["epoch"], "3")

    def test_wrong_cell_and_duplicate_epoch_fail(self):
        before, after = [training_row(1, 100, .4)], [training_row(1, 10, .5)]
        merged = copy.deepcopy(before + after)
        merged[0]["metrics/mAP50(B)"] = ".9"
        result = reconstruct_training(before, after, merged)
        self.assertFalse(result["reconstructed_numeric_cells_match"])
        self.assertEqual(len(result["mismatches"]), 2)

    def test_csv_whitespace_and_numeric_equivalence(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rows.csv"
            path.write_text(" epoch, time\n 1, 2.00\n", encoding="utf-8")
            self.assertEqual(csv_records(path), [{"epoch": "1", "time": "2.00"}])
        self.assertTrue(equal_csv_value("2", "2.00"))
        self.assertTrue(equal_csv_value("", "nan"))
        self.assertFalse(equal_csv_value("2", "3"))

    def test_notebook_only_eval_cells_and_rounding_provenance(self):
        notebook = {"cells": [{"source": ["print('ignored')"]},
                              {"source": ["model.val(split='test', conf=.25, iou=0.45)"], "outputs": [{"text": [
                                  "Ultralytics 8.x Python-3.x\n", " all 12 15 .8 .7 .75 .6\n",
                                  "mAP50: 0.753456\n", "Speed: 2 ms\n"]}]}]}
        result = notebook_evaluations(notebook)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["one_based_cell"], 2)
        self.assertEqual(result[0]["explicit_confidence"], .25)
        self.assertEqual(result[0]["explicit_nms_iou"], .45)
        self.assertEqual(result[0]["console_aggregate"]["map50"], .75)
        self.assertEqual(result[0]["printed_metrics"]["mAP50"], .753456)


class OutputTests(unittest.TestCase):
    def test_existing_output_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            write_json(path, {"first": True})
            with self.assertRaises(FileExistsError):
                write_json(path, {"second": True})
            self.assertEqual(json.loads(path.read_text()), {"first": True})

    def test_run_id_cannot_escape_workspace(self):
        with self.assertRaises(ValueError):
            locations("../../outside")
        self.assertEqual(locations("validation-2026-09-12-v1")[0].name, "validation-2026-09-12-v1")


if __name__ == "__main__":
    unittest.main()
