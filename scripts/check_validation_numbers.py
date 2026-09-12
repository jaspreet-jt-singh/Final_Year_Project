"""Bounded, offline checks of named manuscript numbers against recorded evidence.

This is not a TeX parser or an independent rerun of the experiments. It checks
named tables/paragraphs and cross-report consistency; generated audit macros are
covered separately by generate_paper_evidence.py. No image, workbook, checkpoint,
local manifest, network, provider, or runtime-service access is required.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import sys
import tomllib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RUN = "validation-2026-09-12-v1"
REPORT_DIR = f"research/evidence/{RUN}"
PAPERS = {
    "journal": "Research_Paper_Journal/main.tex",
    "conference": "Research_Paper_Conference/main.tex",
}
NUMBER = r"([0-9][0-9,]*|one|two|three|four|five|six|seven|eight|nine|thirty)"
WORDS = dict(zip("one two three four five six seven eight nine thirty".split(),
                 [1, 2, 3, 4, 5, 6, 7, 8, 9, 30], strict=True))
SOURCE_KEYS = {
    "source_project_z0tql": "Indian food detection.v1i.yolov11",
    "source_microplastics": "indian food.v6i.yolov11",
    "source_indianfood7": "Indian_food.v2-indianfood-7.yolov11",
    "source_indianfoodnet": "indianfoodnet_yolo",
    "source_south_indian": "south indian food detection.v19i.yolov11",
}


def integer(value: str) -> int:
    value = value.lower().strip()
    return WORDS[value] if value in WORDS else int(value.replace(",", ""))


def visible_tex(text: str) -> str:
    """Ignore ordinary TeX comments, not escaped percentage signs."""
    return re.sub(r"(?<!\\)%[^\n]*", "", text)


def section(text: str, title: str) -> str:
    marker = re.compile(r"\\(?:sub)?section\*?\{" + re.escape(title) + r"\}")
    matches = list(marker.finditer(text))
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one section {title!r}, found {len(matches)}")
    rest = text[matches[0].end():]
    return re.split(r"\\(?:sub)?section\*?\{", rest, maxsplit=1)[0]


def table(text: str, label: str) -> str:
    matches = [value for value in re.findall(
        r"\\begin\{table\}.*?\\end\{table\}", text, re.S
    ) if rf"\label{{{label}}}" in value]
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one table {label!r}, found {len(matches)}")
    return matches[0]


def row_cells(text: str, row: str) -> list[str]:
    matches = re.findall(r"^" + re.escape(row) + r"\s*&\s*(.*?)\\\\\s*$", text, re.M)
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one row {row!r}, found {len(matches)}")
    return [cell.strip() for cell in matches[0].split("&")]


def supplemental_literals(source: str) -> list[dict[str, Any]]:
    """Read the constant without importing or executing the database builder."""
    values = []
    for node in ast.parse(source).body:
        targets = node.targets if isinstance(node, ast.Assign) else (
            [node.target] if isinstance(node, ast.AnnAssign) else []
        )
        if any(isinstance(target, ast.Name) and target.id == "SUPPLEMENTAL_NUTRITION_ROWS"
               for target in targets):
            values.append(ast.literal_eval(node.value))
    if len(values) != 1 or not isinstance(values[0], list):
        raise ValueError("Expected one literal SUPPLEMENTAL_NUTRITION_ROWS list")
    return values[0]


class Checks:
    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []

    def equal(self, name: str, actual: Any, expected: Any, source: str) -> None:
        self.rows.append({"id": name, "observed": actual, "expected": expected,
                          "source": source, "status": "pass" if actual == expected else "fail"})

    def capture(self, name: str, text: str, pattern: str, expected: Any, source: str,
                convert: Any = integer) -> None:
        matches = re.findall(pattern, text, re.I)
        actual: Any = {"matching_locations": len(matches)}
        if len(matches) == 1:
            try:
                actual = convert(matches[0])
            except (TypeError, ValueError) as error:
                actual = {"invalid_value": str(error)}
        self.equal(name, actual, expected, source)


def check_supplements(checks: Checks, citations: dict, source: str, expected_count: int) -> None:
    entries = [entry for entry in citations["entries"] if "per_100g" in entry]
    rows = supplemental_literals(source)
    checks.equal("supplements.source_count", len(entries), expected_count, "citation-review.json")
    checks.equal("supplements.builder_count", len(rows), expected_count, "backend/scripts/merge_db.py")
    by_url = {entry["url"]: entry for entry in entries}
    checks.equal("supplements.unique_source_urls", len(by_url), len(entries), "citation-review.json")
    checks.equal("supplements.url_sets", sorted(row["source_url"] for row in rows), sorted(by_url),
                 "citation-review.json / builder AST")
    for row in rows:
        entry = by_url.get(row["source_url"], {})
        for field in ("calories", "protein_g", "carbs_g", "fat_g"):
            checks.equal(f"supplements.{row['name']}.{field}", row.get(field),
                         entry.get("per_100g", {}).get(field),
                         f"{entry.get('key', 'missing citation')}: {entry.get('status', 'missing')}")
        checks.equal(f"supplements.{row['name']}.units", "per 100 g" in row["source_notes"].lower(),
                     True, "builder source_notes; numeric citation fields are explicitly per_100g")


def check_followup(checks: Checks, papers: dict[str, str], nutrition: dict, arithmetic: dict,
                   recommendations: dict, browser: dict, policy: dict) -> None:
    n, a, h = nutrition, arithmetic, nutrition["hash_seed_checks"]
    for name, actual, expected in (
        ("workbook_accounting", n["imported_workbook_rows"] + n["omitted_workbook_rows"], n["workbook_rows"]),
        ("database_accounting", n["imported_workbook_rows"] + n["supplemental_rows"], n["actual_database_rows"]),
        ("nutrient_field_accounting", n["actual_database_rows"] * 4, n["numeric_fields_compared"]),
        ("portion_case_product", n["canonical_classes"] * 40, a["frontend"]["portion_cases"]),
        ("portion_field_product", a["frontend"]["portion_cases"] * 4, a["frontend"]["portion_numeric_comparisons"]),
        ("fixture_parity_count", a["frontend"]["fixture_cases"], a["backend_fixture_cases"]),
        ("unique_hash_seeds", len(set(h["seeds"])), len(h["seeds"])),
    ):
        checks.equal("followup.consistency." + name, actual, expected,
                     "nutrition-validation.json / arithmetic-validation.json; 40 steps from 25..1000 g")
    for paper, text in papers.items():
        followup = section(text, "Validation follow-up")
        observations = {
            "database_rows": (NUMBER + (r"-row database" if paper == "journal" else r" database rows"),
                              n["actual_database_rows"], "nutrition-validation.json"),
            "nutrient_fields": (r"All " + NUMBER + r" nutrient-field comparisons" if paper == "journal" else
                                NUMBER + r" nutrient fields", n["numeric_fields_compared"],
                                "nutrition-validation.json"),
            "goal_cases": (NUMBER + (r" goal/context/calorie combinations" if paper == "journal" else
                                     r" goal cases per implementation"), a["backend_goal_cases"],
                           "arithmetic-validation.json: backend and frontend case totals"),
            "portion_cases": (NUMBER + (r" class/portion cases" if paper == "journal" else
                                         r" frontend portion cases"), a["frontend"]["portion_cases"],
                               "arithmetic-validation.json"),
            "hash_seeds": (NUMBER + r" (?:fixed )?hash seeds", len(h["seeds"]), "nutrition-validation.json"),
            "hash_labels": (NUMBER + (r" food-label inputs" if paper == "journal" else r" labels"),
                            h["labels_per_run"], "nutrition-validation.json"),
            "hash_modes": (NUMBER + r" lookup modes", h["methods"], "nutrition-validation.json"),
            "unstable_pairs": ((NUMBER + r" method/label pairs returned" if paper == "journal" else
                                NUMBER + r" changing method/label pairs"), h["changing_method_label_pairs"],
                               "nutrition-validation.json: changing method/label pairs, not wrong classes"),
            "recommendation_cases": (r"(?:matrix covered) " + NUMBER, recommendations["matrix"]["total"],
                                     "recommendations.json: matrix"),
            "provider_cases": ((NUMBER + r" SDK/mock-transport cases" if paper == "journal" else
                                r"SDK/mock transport covered " + NUMBER), recommendations["provider_adapter"]["total"],
                               "recommendations.json: provider_adapter"),
            "browser_combinations": (r"covered all " + NUMBER + r" goal/context combinations",
                                     browser["summary"]["goal_context_combinations"],
                                     "browser-extended-attempt3.json"),
        }
        for name, (pattern, expected, source) in observations.items():
            checks.capture(f"{paper}.followup.{name}", followup, pattern, expected, source)
    journal = section(papers["journal"], "Validation follow-up")
    for key, pattern in {
        "workbook_rows": NUMBER + r" source rows",
        "omitted_workbook_rows": NUMBER + r" duplicate-normalized-name omissions",
        "imported_workbook_rows": NUMBER + r" retained rows",
        "supplemental_rows": NUMBER + r" supplemental rows",
    }.items():
        checks.capture("journal.followup." + key, journal, pattern, n[key], "nutrition-validation.json")
    checks.capture("journal.followup.portion_fields", journal, r"with " + NUMBER + r" nutrient-field comparisons",
                   a["frontend"]["portion_numeric_comparisons"], "arithmetic-validation.json")
    checks.capture("journal.followup.canonical_unstable_pairs", journal, NUMBER + r" involved canonical labels",
                   h["changing_canonical_pairs"], "nutrition-validation.json")
    for key, expected in (("goals", len(policy["goals"])), ("contexts", len(policy["conditions"]))):
        checks.capture("journal.followup." + key, journal, NUMBER + " " + key, expected,
                       "backend/domain/nutrition_policy.json")
    checks.equal("followup.same_goal_case_counts", a["frontend"]["goal_cases"], a["backend_goal_cases"],
                 "arithmetic-validation.json")
    checks.equal("followup.goal_sweep_product", a["backend_goal_cases"],
                 len(policy["goals"]) * len(policy["conditions"]) * (5000 - 500 + 1),
                 "policy dimensions / declared inclusive 500..5000 sweep")
    checks.capture("journal.followup.minimum_calories", journal, r"target from " + NUMBER, 500,
                   "arithmetic-validation.json: limitations declare 500..5000 inclusive")
    checks.capture("journal.followup.maximum_calories", journal, r"target from [0-9,]+ to " + NUMBER, 5000,
                   "arithmetic-validation.json: limitations declare 500..5000 inclusive")
    for key in ("backend_goal_discrepancies", "backend_fixture_discrepancies"):
        checks.equal("followup." + key, a[key], 0, "arithmetic-validation.json")
    for key in ("goal_difference_count", "fixture_difference_count", "portion_difference_count"):
        checks.equal("followup.frontend." + key, a["frontend"][key], 0, "arithmetic-validation.json")
    checks.equal("followup.current_canonical_stable", h["changing_current_canonical_pairs"], 0,
                 "nutrition-validation.json")
    checks.equal("followup.numeric_reconciliation", n["reconciliation_difference_count"], 0,
                 "nutrition-validation.json")
    checks.equal("followup.reported_tolerance", n["numeric_absolute_tolerance"], 1e-9,
                 "journal followup absolute tolerance 10^-9")
    checks.capture("journal.followup.tolerance_exponent", journal,
                   r"absolute tolerance of \$10\^\{-(\d+)\}\$", 9, "nutrition-validation.json")
    checks.capture("journal.followup.error_exponent", journal,
                   r"deviation below \$10\^\{-(\d+)\}\$", 12, "arithmetic-validation.json")
    checks.equal("followup.portion_error_bound", a["frontend"]["max_portion_absolute_error"] < 1e-12, True,
                 "journal followup deviation below 10^-12")
    for block in ("matrix", "provider_adapter"):
        checks.equal(f"recommendations.{block}.actual_cases", len(recommendations[block]["cases"]),
                     recommendations[block]["total"], "recommendations.json")
        checks.equal(f"recommendations.{block}.all_passed", recommendations[block]["passed"],
                     recommendations[block]["total"], "recommendations.json")
    checks.equal("browser.actual_matrix_cases", len(browser["matrix"]),
                 browser["summary"]["goal_context_combinations"], "browser-extended-attempt3.json")


def check_dataset_followup(checks: Checks, papers: dict[str, str], inspection: dict,
                          perceptual: dict, queue: dict, support: dict, visual: dict, audit: dict) -> None:
    for paper, text in papers.items():
        followup = section(text, "Validation follow-up")
        patterns = {
            "strict_flags": (r"The " + NUMBER + r" (?:strict|zero-area) flags", inspection["flagged_images"]),
            "zero_width": (NUMBER + r" zero-width", inspection["invalid_line_reasons"]["zero_width"]),
            "zero_height": (NUMBER + r" zero-height", inspection["invalid_line_reasons"]["zero_height"]),
            "direct_conflict_groups": (NUMBER + r" identical-pixel groups", inspection["direct_label_conflict_pixel_groups"]),
            "edge_rows": (NUMBER + r" rows in [0-9,]+ images", inspection["additional_box_edge_check"]["lines"]),
            "edge_images": (r"rows in " + NUMBER + r" images", inspection["additional_box_edge_check"]["images"]),
            "perceptual_sample": ((r"sampled " + NUMBER + r" records" if paper == "journal" else
                                   NUMBER + r"-record perceptual screen"), perceptual["selected_images"]),
            "perceptual_candidates": ((r"yielding " + NUMBER + r" candidates" if paper == "journal" else
                                       r"yielded " + NUMBER + r" cross-partition candidates"),
                                      perceptual["candidate_pairs_before_cap"]),
        }
        for name, (pattern, expected) in patterns.items():
            checks.capture(f"{paper}.dataset_followup.{name}", followup, pattern, expected,
                           "dataset-inspection.json / dataset-perceptual-review.json")
        group_minima = "/".join(str(inspection["minimum_candidate_groups_per_class"][split])
                                for split in ("train", "valid", "test"))
        checks.capture(f"{paper}.dataset_followup.minimum_groups", followup,
                       r"candidate-group (?:counts are|support is) ([0-9]+/[0-9]+/[0-9]+)",
                       group_minima, "dataset-inspection.json", str)
    journal = section(papers["journal"], "Validation follow-up")
    for name, pattern, expected in (
        ("records", r"reader agreed on all " + NUMBER + r" records", inspection["records"]),
        ("empty_flagged", NUMBER + r" affected images have no accepted instances",
         inspection["flagged_images_without_accepted_instances"]),
        ("visual_originals", r"All " + NUMBER + r" originals", visual["reviewed_original_images"]),
        ("conflict_images", r"different label files \(" + NUMBER + r" images\)", inspection["direct_label_conflict_images"]),
        ("different_boxes", NUMBER + r" differ in boxes", inspection["label_conflict_classifications"]["different_boxes_same_class_multiset"]),
        ("different_classes", NUMBER + r" differ in class or instance", inspection["label_conflict_classifications"]["different_class_or_instance_multiset"]),
        ("pair_comparisons", r"compared " + NUMBER + r" eligible cross-candidate-partition pairs", perceptual["eligible_pair_comparisons"]),
        ("perceptual_threshold", r"Hamming distance at most " + NUMBER, perceptual["threshold"]),
        ("edge_tolerance", r"at a \$10\^\{-(\d+)\}\$ tolerance", 6),
    ):
        checks.capture("journal.dataset_followup." + name, journal, pattern, expected,
                       "dataset-inspection.json / dataset-perceptual-review.json / dataset-visual-review.json")
    checks.equal("dataset.edge_tolerance", inspection["additional_box_edge_check"]["tolerance"], 1e-6,
                 "journal declared tolerance")
    checks.capture("journal.dataset_followup.probe_originals", journal,
                   r"Synthetic probes used " + NUMBER + r" originals for each transform", 12,
                   "dataset-perceptual-review.json: count per transform, not total across transforms")
    checks.capture("journal.dataset_followup.detected_probes", journal,
                   r"all " + NUMBER + r" were detected separately", 12,
                   "dataset-perceptual-review.json: JPEG and resizing separately")
    checks.equal("dataset.fresh_records", inspection["records"], audit["image_count"], "dataset-inspection.json / audit.json")
    for split in ("train", "valid", "test"):
        checks.equal("dataset.fresh_flags." + split, inspection["flagged_images_by_split"][split],
                     audit["splits"][split]["issue_images"], "dataset-inspection.json / audit.json")
        checks.equal("dataset.fresh_instances." + split, inspection["accepted_instances"][split],
                     audit["splits"][split]["instances"], "dataset-inspection.json / audit.json")
        checks.equal("dataset.group_support_minimum." + split,
                     min(row[split]["groups"] for row in support["support"].values()),
                     inspection["minimum_candidate_groups_per_class"][split],
                     "dataset-class-group-support.json / dataset-inspection.json")
    for old_key, fresh_key in (("byte_duplicates", "sha256"), ("pixel_duplicates", "pixel_sha256")):
        old = audit[old_key]
        expected = {"groups": old["cross_split_groups"], "images": old["affected_images"],
                    "pairs": {key: {"groups": row["shared_groups"], "images": row["affected_images"]}
                              for key, row in old["pairs"].items()}}
        checks.equal("dataset.fresh_duplicates." + fresh_key, inspection["duplicates"][fresh_key], expected,
                     "dataset-inspection.json / audit.json")
    checks.equal("dataset.fresh_output_repeatability", all(inspection["old_artifact_comparison"].values()), True,
                 "dataset-inspection.json: reported fresh hashes compared with previous artifacts")
    checks.equal("dataset.conflict_categories_account_for_groups", sum(inspection["label_conflict_classifications"].values()),
                 inspection["direct_label_conflict_pixel_groups"], "dataset-inspection.json: numeric differences, not formatting-only")
    checks.equal("dataset.original_visual_records", len(visual["records"]), visual["reviewed_original_images"],
                 "dataset-visual-review.json: AI review record count, not expert approval")
    checks.equal("perceptual.sample_total", sum(perceptual["sample_by_candidate_split"].values()),
                 perceptual["selected_images"], "dataset-perceptual-review.json")
    checks.equal("perceptual.hashed_total", perceptual["successfully_hashed_images"], perceptual["selected_images"],
                 "dataset-perceptual-review.json")
    checks.equal("perceptual.queue_count", len(queue["queue"]), perceptual["candidate_pairs_before_cap"],
                 "dataset-perceptual-queue.json / dataset-perceptual-review.json")
    checks.equal("perceptual.queue_comparisons", queue["eligible_pair_comparisons"], perceptual["eligible_pair_comparisons"],
                 "dataset-perceptual-queue.json / dataset-perceptual-review.json")
    checks.equal("perceptual.no_truncation", perceptual["queue_truncated"], False, "dataset-perceptual-review.json")
    for transform, values in perceptual["calibration_probe_summary"].items():
        expected = values["count"] if transform in ("jpeg_quality_35", "resize_48_square") else 0
        checks.equal("perceptual.probe." + transform, values["within_threshold"], expected,
                     "dataset-perceptual-review.json; synthetic probes, not real-world sensitivity")
        checks.equal("perceptual.probe_count." + transform, values["count"], 12,
                     "journal followup: twelve original probes per transformation")


def run_checks(root: Path) -> dict[str, Any]:
    checks = Checks()
    inputs: dict[str, str] = {}

    def read(path: str) -> str:
        data = (root / path).read_bytes()
        inputs[path] = hashlib.sha256(data).hexdigest()
        return data.decode("utf-8-sig")

    def report(name: str) -> dict:
        return json.loads(read(f"{REPORT_DIR}/{name}.json"))

    try:
        papers = {key: visible_tex(read(path)) for key, path in PAPERS.items()}
        audit = json.loads(read("research/evidence/audit.json"))["dataset"]
        grouped = json.loads(read("research/evidence/grouped-split-v1.json"))
        baseline = report("baseline")
        training = report("training-results")
        nutrition = report("nutrition-validation")
        arithmetic = report("arithmetic-validation")
        recommendations = report("recommendations")
        citations = report("citation-review")
        browser = report("browser-extended-attempt3")
        policy = json.loads(read("backend/domain/nutrition_policy.json"))
        fixtures = json.loads(read("tests/contracts/macro-fixtures.json"))
        package = json.loads(read("frontend/package.json"))
        project = tomllib.loads(read("pyproject.toml"))["project"]
        builder = read("backend/scripts/merge_db.py")
        # This tracked summary contains source YAML facts, not ignored source paths.
        dataset_review = report("dataset-sources")
        inspection = report("dataset-inspection")
        perceptual = report("dataset-perceptual-review")
        queue = report("dataset-perceptual-queue")
        support = report("dataset-class-group-support")
        visual = report("dataset-visual-review")

        for paper, text in papers.items():
            export = table(text, "tab:export")
            for row, split in (("Train", "train"), ("Validation", "valid"), ("Test", "test")):
                checks.equal(f"{paper}.strict_flags.{split}", integer(row_cells(export, row)[-1]),
                             audit["splits"][split]["issue_images"], "audit.json: strict issue_images")
        for key in ("cross_split_groups", "affected_images", "pairs"):
            checks.equal("duplicates.byte_equals_pixels." + key, audit["byte_duplicates"][key],
                         audit["pixel_duplicates"][key], "audit.json: both duplicate counters")
        for split, values in grouped["splits"].items():
            checks.equal("candidate.class_presence." + split, sorted(values["images_per_class"]),
                         sorted(grouped["class_names"]), "grouped-split-v1.json")
            checks.equal("candidate.no_missing_classes." + split, values["missing_classes"], [],
                         "grouped-split-v1.json")
            checks.equal("candidate.positive_support." + split,
                         min(values["images_per_class"].values()) > 0, True, "grouped-split-v1.json")
        minimum = min(value for split in ("valid", "test")
                      for value in grouped["splits"][split]["images_per_class"].values())
        checks.capture("journal.candidate.minimum_support", papers["journal"],
                       r"only " + NUMBER + r" labeled records in a candidate validation/test partition",
                       minimum, "grouped-split-v1.json: minimum valid/test per-class image count")

        sources = {row["source"]: row for row in grouped["sources"]}
        reread_sources = {row["source"]: row for row in dataset_review["sources"]}
        for citation, name in SOURCE_KEYS.items():
            row = re.findall(r"\\cite\{" + citation + r"\}\s*&\s*([0-9,]+)\s*&\s*([0-9,]+)",
                             papers["journal"])
            expected = [reread_sources[name]["raw_class_count"], sources[name]["images"]]
            checks.equal("journal.source." + citation, list(map(integer, row[0])) if len(row) == 1 else row,
                         expected, "dataset-sources.json / grouped-split-v1.json")
            checks.equal("source.yaml_identity." + citation, reread_sources[name]["yaml_sha256"],
                         sources[name]["yaml_sha256"], "dataset-sources.json / grouped-split-v1.json")
            checks.equal("source.image_count." + citation, reread_sources[name]["images"],
                         sources[name]["images"], "dataset-sources.json / grouped-split-v1.json")
            checks.equal("source.class_count." + citation, len(reread_sources[name]["raw_class_names"]),
                         reread_sources[name]["raw_class_count"], "dataset-sources.json")

        evaluations = {row["split"]: row for row in training["final_notebook_evaluations"]}
        historical = table(papers["journal"], "tab:historical")
        for label, split in (("Validation", "val"), ("Test", "test")):
            evaluation = evaluations[split]
            aggregate = evaluation["console_aggregate"]
            expected = [f"{aggregate['precision']:.3f}", f"{aggregate['recall']:.3f}",
                        f"{evaluation['printed_metrics']['mAP50']:.3f}",
                        f"{evaluation['printed_metrics']['mAP50-95']:.3f}"]
            checks.equal("journal.historical." + split, row_cells(historical, label), expected,
                         "training-results.json: archived console and printed metrics, not a new evaluation")
        conference_history = section(papers["conference"], "Historical Scores, Not a Clean Benchmark")
        for metric, tex_name in (("mAP50", "50"), ("mAP50-95", "50:95")):
            expected = "/".join(f"{evaluations[split]['printed_metrics'][metric]:.3f}" for split in ("val", "test"))
            checks.capture("conference.historical." + metric, conference_history,
                           re.escape(f"mAP$_{{{tex_name}}}$ of ") + r"([0-9.]+/[0-9.]+)", expected,
                           "training-results.json", str)
        journal_history = section(papers["journal"], "Historical Detector Evidence, Not an Independent Benchmark")
        for paper, text in (("journal", journal_history), ("conference", conference_history)):
            for name, expression in (("Ultralytics", r"Ultralytics ([0-9.]+)"),
                                     ("Python", r"Python-?([0-9.]+)"),
                                     ("Torch", r"torch-?([0-9.]+\+cu[0-9]+)")):
                expected_versions = [re.search(expression, evaluation["printed_environment"], re.I)
                                     for evaluation in evaluations.values()]
                versions = [match.group(1) if match else None for match in expected_versions]
                checks.equal("historical.environment_consistency." + paper + "." + name,
                             len(set(versions)), 1, "training-results.json: both evaluation environments")
                checks.capture(paper + ".historical.environment." + name, text,
                               name + r" ([0-9.]+(?:\+cu[0-9]+)?)", versions[0],
                               "training-results.json", str)
            timings = [re.search(r"([0-9.]+)ms inference", evaluation["printed_speed"]).group(1)
                       for evaluation in evaluations.values()]
            checks.equal("historical.timing_consistency." + paper, len(set(timings)), 1,
                         "training-results.json")
            checks.capture(paper + ".historical.gpu_inference_ms", text, r"([0-9.]+) ms/image GPU",
                           float(timings[0]), "training-results.json: archived GPU timing only", float)
        checks.capture("journal.historical.gpu_memory", journal_history, NUMBER + r" MiB",
                       integer(re.search(r"([0-9]+)MiB", evaluations["val"]["printed_environment"]).group(1)),
                       "training-results.json")
        checks.capture("journal.historical.notebook_cells", journal_history, r"cells ([0-9]+) and ([0-9]+)",
                       [evaluations[split]["one_based_cell"] for split in ("val", "test")],
                       "training-results.json", lambda pair: [int(value) for value in pair])
        for split in ("valid", "test"):
            evaluation = evaluations["val" if split == "valid" else split]["console_aggregate"]
            checks.equal("historical.strict_instance_delta." + split,
                         evaluation["instances"] - audit["splits"][split]["instances"], 7,
                         "training-results.json / audit.json; both drafts describe seven additional rows")
        reconstruction = training["reconstruction"]
        for key, metric, pattern in (
            ("best_validation_map50", "metrics/mAP50(B)", r"maximum logged validation mAP\$_\{50\}\$ is ([0-9.]+) at epoch ([0-9]+)"),
            ("best_validation_map50_95", "metrics/mAP50-95(B)", r"maximum mAP\$_\{50:95\}\$ is ([0-9.]+) at epoch ([0-9]+)"),
        ):
            checks.capture("journal.training." + key, papers["journal"], pattern,
                           [reconstruction[key][metric], reconstruction[key]["epoch"]],
                           "training-results.json: reconstruction", list)
        checks.capture("journal.training.epochs", papers["journal"], NUMBER + r" distinct epochs",
                       len(set(reconstruction["epochs"])), "training-results.json")

        identities = {row["path"]: row for row in baseline["files"]}
        for path in ("backend/scripts/merge_db.py", "backend/domain/nutrition_policy.json",
                     "pyproject.toml", "frontend/package.json"):
            checks.equal("frozen_source." + path, inputs[path], identities[path]["sha256"],
                         "baseline.json: pinned runtime sources, not uncommitted manuscripts")
        artifacts = {row["path"]: row for row in training["artifacts"]}
        checkpoint = "results_after_discontinuation/yolo11s_indian_food_best.pt"
        checks.equal("checkpoint.baseline_equals_training", artifacts[checkpoint], identities[checkpoint],
                     "baseline.json / training-results.json: current-file identity only")
        checks.capture("journal.checkpoint.bytes", papers["journal"], r"occupies " + NUMBER + r" bytes",
                       identities[checkpoint]["bytes"], "baseline.json")
        checks.capture("journal.checkpoint.mib", papers["journal"], r"approximately ([0-9.]+) MiB",
                       f"{identities[checkpoint]['bytes'] / (1024 ** 2):.2f}", "baseline.json", str)
        hashes = table(papers["journal"], "tab:hashes")
        expected_hashes = {
            "Deployed checkpoint": identities[checkpoint]["sha256"],
            "Nutrition SQLite database": identities["data/nutrition.db"]["sha256"],
            "Original INDB workbook": identities["data/INDB.xlsx"]["sha256"],
            "Candidate assignments": grouped["assignments_sha256"],
            "Historical final-training notebook": artifacts["notebooks/final_version_training.ipynb"]["sha256"],
        }
        for label, digest in expected_hashes.items():
            checks.equal("journal.hash." + label, row_cells(hashes, label), [rf"\code{{{digest[:12]}}}"],
                         "baseline.json / training-results.json / grouped-split-v1.json")
        snapshot = section(papers["journal"], "Implementation Snapshot and Artifact Identity")
        python_version = re.fullmatch(r">=([0-9.]+),<([0-9.]+)", project["requires-python"])
        checks.capture("journal.production.Python", snapshot, r"Python ([0-9.]+),",
                       python_version.group(1) if python_version else None, "pyproject.toml", str)
        dependencies = dict(item.split("==", 1) for item in project["dependencies"] if "==" in item)
        for display, name in (("CPU Torch", "torch"), ("Torchvision", "torchvision"),
                              ("headless Ultralytics", "ultralytics-opencv-headless")):
            checks.capture("journal.production." + name, snapshot, re.escape(display) + r" ([0-9.]+),",
                           dependencies[name].removesuffix("+cpu"), "pyproject.toml", str)
        checks.equal("production.torch_cpu_build", dependencies["torch"].endswith("+cpu"), True, "pyproject.toml")
        checks.equal("production.torchvision_cpu_build", dependencies["torchvision"].endswith("+cpu"), True,
                     "pyproject.toml")
        for display, name in (("Next.js", "next"), ("React", "react")):
            checks.capture("journal.production." + name, snapshot, re.escape(display) + r" ([0-9]+\.[0-9]+\.[0-9]+)",
                           package["dependencies"][name], "frontend/package.json", str)
        checks.equal("production.react_dom", package["dependencies"]["react-dom"],
                     package["dependencies"]["react"], "frontend/package.json")
        check_supplements(checks, citations, builder, nutrition["supplemental_rows"])
        checks.equal("arithmetic.fixture_count", arithmetic["backend_fixture_cases"], len(fixtures),
                     "tests/contracts/macro-fixtures.json / arithmetic-validation.json")
        check_followup(checks, papers, nutrition, arithmetic, recommendations, browser, policy)
        check_dataset_followup(checks, papers, inspection, perceptual, queue, support, visual, audit)
    except (OSError, ValueError, KeyError, TypeError, IndexError, SyntaxError) as error:
        checks.equal("required_input_or_structure", f"{type(error).__name__}: {error}",
                     "All required tracked evidence and scoped manuscript structures available", "offline input validation")
    failed = sum(row["status"] == "fail" for row in checks.rows)
    return {"schema_version": 1, "run_id": RUN, "status": "pass" if not failed else "fail",
            "checker_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "scope": "Named hardcoded table/paragraph numbers and source consistency only; not exhaustive TeX parsing, "
                     "experiment replication, clinical validation, or verification of ignored artifacts.",
            "input_sha256": inputs, "summary": {"checks": len(checks.rows), "failed": failed}, "checks": checks.rows}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Recompute assertions without creating or modifying files")
    parser.add_argument("--root", type=Path, default=ROOT, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    report = run_checks(args.root)
    if report["status"] != "pass":
        print(json.dumps({"status": "fail", "failures": [row for row in report["checks"] if row["status"] == "fail"]},
                         indent=2))
        return 1
    if not args.check:
        output = args.root / REPORT_DIR / "numeric-checks.json"
        # Evidence is immutable by default; explicitly choose a new run for later work.
        try:
            with output.open("x", encoding="utf-8", newline="\n") as handle:
                json.dump(report, handle, indent=2, ensure_ascii=False)
                handle.write("\n")
        except OSError as error:
            print(f"No evidence overwritten: {error}", file=sys.stderr)
            return 1
    print(json.dumps({"status": "pass", **report["summary"], "read_only": args.check}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
