"""Versioned, offline dataset/training validation; no dataset or model mutation.

Reports distinguish current artifact consistency, heuristic review candidates,
historical notebook observations, and expert judgments not yet obtained.
No Torch import, training, provider access, upload, or clinical assessment.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import io
import json
import math
from pathlib import Path
import platform
import re
import subprocess
import sys
import time

from PIL import Image, ImageOps, __version__ as pillow_version
import yaml

ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "validation-2026-09-12-v1"
DATASET = ROOT / "data/food_dataset"


def sha256(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def jsonl(path):
    with Path(path).open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def write_json(path, value):
    """Exclusive outputs: existing validation evidence is never replaced."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def locations(run_id):
    if not re.fullmatch(r"validation-[0-9]{4}-[0-9]{2}-[0-9]{2}-v[1-9][0-9]*", run_id):
        raise ValueError("Use a versioned validation-YYYY-MM-DD-vN run identifier")
    return ROOT / ".deployment/research" / run_id, ROOT / "research/evidence" / run_id


def context():
    return {
        "schema_version": 1,
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "script_sha256_at_start": sha256(Path(__file__)),
        "environment": {"python": sys.version, "platform": platform.platform(),
                        "pillow": pillow_version, "pyyaml": yaml.__version__, "executable": sys.executable},
        "scope": "Offline read-only dataset/model access; generated evidence only; not independent scientific validation.",
    }


def execute_child(phase, run_id):
    local, reports = locations(run_id)
    report = context()
    if phase == "audit":
        targets = [local / "audit.json", local / "split-manifest.jsonl"]
        script = ROOT / "scripts/audit_publication.py"
        arguments = ["--output", str(targets[0]), "--manifest", str(targets[1])]
    elif phase == "grouped":
        targets = [local / "grouped"]
        script = ROOT / "scripts/prepare_research_split.py"
        arguments = ["--audit", str(local / "audit.json"), "--manifest", str(local / "split-manifest.jsonl"),
                     "--output", str(targets[0]), "--seed", "42"]
    else:
        raise ValueError("Unknown subprocess phase")
    destination = reports / f"dataset-{phase}-command.json"
    if destination.exists() or any(path.exists() for path in targets):
        raise ValueError("Phase output exists; preserve it and use a new versioned run")
    local.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, str(script), *arguments]
    report.update({"run_id": run_id, "command": command, "cwd": str(ROOT),
                   "child_script_sha256": sha256(script)})
    started = time.monotonic()
    output = []
    with subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True, encoding="utf-8", errors="replace") as child:
        for line in child.stdout:
            print(line, end="", flush=True)
            output.append(line)
        report["exit_code"] = child.wait()
    report.update({"duration_seconds": round(time.monotonic() - started, 3),
                   "finished_utc": datetime.now(timezone.utc).isoformat(), "output": "".join(output),
                   "status": "passed" if report["exit_code"] == 0 else "failed"})
    artifacts = [path for target in targets for path in (target.rglob("*") if target.is_dir() else [target])
                 if path.is_file()]
    report["artifacts"] = [{"path": path.relative_to(ROOT).as_posix(), "sha256": sha256(path),
                             "bytes": path.stat().st_size} for path in artifacts]
    write_json(destination, report)
    return report["exit_code"]


def parse_annotations(text, class_count):
    """Independent annotation parser; preserve malformed rows for inspection."""
    result = []
    for line_number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        fields, issues = line.split(), []
        category, coords = None, None
        if len(fields) != 5:
            issues.append("field_count")
        else:
            try:
                category = int(fields[0])
                coords = [float(value) for value in fields[1:]]
            except ValueError:
                issues.append("nonnumeric_or_noninteger_class")
            if category is not None and not 0 <= category < class_count:
                issues.append("class_out_of_range")
            if coords is not None:
                if not all(math.isfinite(value) for value in coords):
                    issues.append("nonfinite_coordinates")
                    coords = [value if math.isfinite(value) else None for value in coords]
                else:
                    x, y, width, height = coords
                    if not 0 <= x <= 1 or not 0 <= y <= 1:
                        issues.append("center_out_of_range")
                    if width == 0:
                        issues.append("zero_width")
                    if height == 0:
                        issues.append("zero_height")
                    if width < 0 or height < 0 or width > 1 or height > 1:
                        issues.append("dimension_out_of_range")
        outside = False
        if coords is not None and all(value is not None for value in coords):
            x, y, width, height = coords
            outside = min(x - width / 2, y - height / 2) < -1e-6 or max(x + width / 2, y + height / 2) > 1 + 1e-6
        result.append({"line": line_number, "raw": line, "class": category, "coordinates": coords,
                       "issues": issues, "accepted_by_range_checks": not issues,
                       "box_edges_outside_frame_tolerance_1e_6": outside})
    return result


def summarize_duplicates(rows, field):
    identities = defaultdict(list)
    for row in rows:
        if row.get(field):
            identities[row[field]].append(row)
    crossing = [group for group in identities.values() if len({row["split"] for row in group}) > 1]
    pairs = {}
    for left, right in (("train", "valid"), ("train", "test"), ("valid", "test")):
        matching = [group for group in crossing if {left, right} <= {row["split"] for row in group}]
        pairs[f"{left}:{right}"] = {"groups": len(matching),
                                   "images": sum(sum(row["split"] in {left, right} for row in group) for group in matching)}
    return {"groups": len(crossing), "images": sum(map(len, crossing)), "pairs": pairs,
            "members": [[row["path"] for row in group] for group in crossing]}


def classify_label_conflict(annotations):
    signatures = []
    for rows in annotations:
        if any(row["class"] is None or row["coordinates"] is None
               or any(value is None for value in row["coordinates"]) for row in rows):
            return "unparseable_numeric_content"
        signatures.append(tuple(sorted((row["class"], *row["coordinates"]) for row in rows)))
    if len(set(signatures)) == 1:
        return "format_or_order_only"
    classes = {tuple(sorted(row[0] for row in signature)) for signature in signatures}
    return "different_class_or_instance_multiset" if len(classes) > 1 else "different_boxes_same_class_multiset"


def candidate_support(groups, names):
    support = {name: {split: {"groups": 0, "images": 0, "instances": 0}
                      for split in ("train", "valid", "test", "quarantine")} for name in names}
    for group in groups:
        split = group["candidate_split"] or "quarantine"
        present = set()
        for row in group["rows"]:
            present.update(row["classes"])
            for category in set(row["classes"]):
                support[names[category]][split]["images"] += 1
            for category in row["classes"]:
                support[names[category]][split]["instances"] += 1
        for category in present:
            support[names[category]][split]["groups"] += 1
    return support


def inspect_dataset(run_id):
    local, reports = locations(run_id)
    destination = reports / "dataset-inspection.json"
    if destination.exists():
        raise ValueError("Inspection report exists; use a new run")
    report, started = context(), time.monotonic()
    rows = jsonl(local / "split-manifest.jsonl")
    audit = read_json(local / "audit.json")
    grouped = read_json(local / "grouped/summary.json")
    groups = jsonl(local / "grouped/assignments.jsonl")
    names = grouped["class_names"]
    labels, flagged, edges = {}, [], []
    reasons, splits, counts = Counter(), Counter(), Counter()
    for index, row in enumerate(rows, 1):
        image = DATASET / row["path"]
        label = image.parent.parent / "labels" / (image.stem + ".txt")
        parsed = parse_annotations(label.read_text(encoding="utf-8"), len(names)) if label.is_file() else []
        labels[row["path"]] = parsed
        accepted = [line["class"] for line in parsed if line["accepted_by_range_checks"]]
        if accepted != row["classes"]:
            raise ValueError(f"Independent annotation parser differs from census: {row['path']}")
        counts[row["split"]] += len(accepted)
        invalid = [line for line in parsed if line["issues"]]
        if invalid or row["issues"]:
            reasons.update(issue for line in invalid for issue in line["issues"])
            splits[row["split"]] += 1
            flagged.append({"path": row["path"], "sha256": row["sha256"],
                            "dimensions": row.get("dimensions"), "annotations": parsed,
                            "accepted_instances": len(accepted), "expert_semantic_review": "pending"})
        if any(line["box_edges_outside_frame_tolerance_1e_6"] for line in parsed):
            edges.append({"path": row["path"], "lines": [line["line"] for line in parsed
                                                         if line["box_edges_outside_frame_tolerance_1e_6"]]})
        if index % 10000 == 0:
            print(f"Independently parsed {index}/{len(rows)} annotation files", flush=True)
    duplicates = {field: summarize_duplicates(rows, field) for field in ("sha256", "pixel_sha256")}
    for field, recorded in (("sha256", "byte_duplicates"), ("pixel_sha256", "pixel_duplicates")):
        if duplicates[field]["groups"] != audit["dataset"][recorded]["cross_split_groups"]:
            raise ValueError("Independent duplicate grouping differs from census")
    pixels = defaultdict(list)
    for row in rows:
        if row.get("pixel_sha256"):
            pixels[row["pixel_sha256"]].append(row)
    conflicts = []
    for digest, same_image in pixels.items():
        if len({row["label_sha256"] for row in same_image}) > 1:
            conflicts.append({"pixel_sha256": digest, "paths": [row["path"] for row in same_image],
                              "classification": classify_label_conflict([labels[row["path"]] for row in same_image]),
                              "labels": [{"path": row["path"], "label_sha256": row["label_sha256"],
                                          "annotations": labels[row["path"]]} for row in same_image]})
    support = candidate_support(groups, names)
    previous_audit = read_json(ROOT / "research/evidence/audit.json")
    previous_grouped = read_json(ROOT / "research/evidence/grouped-split-v1.json")
    report.update({
        "run_id": run_id, "command": [sys.executable, str(Path(__file__)), "--run-id", run_id, "--phase", "inspect"],
        "status": "passed_automated_checks_expert_review_pending", "exit_code": 0,
        "duration_seconds": round(time.monotonic() - started, 3),
        "records": len(rows), "accepted_instances": dict(counts), "flagged_images": len(flagged),
        "flagged_images_by_split": dict(splits), "invalid_line_reasons": dict(reasons),
        "flagged_images_without_accepted_instances": sum(not row["accepted_instances"] for row in flagged),
        "additional_box_edge_check": {"tolerance": 1e-6, "images": len(edges),
                                      "lines": sum(len(row["lines"]) for row in edges),
                                      "interpretation": "Additional geometric review flags, not automatically invalid annotations."},
        "duplicates": {key: {field: value for field, value in result.items() if field != "members"}
                       for key, result in duplicates.items()},
        "direct_label_conflict_pixel_groups": len(conflicts),
        "direct_label_conflict_images": sum(len(row["paths"]) for row in conflicts),
        "label_conflict_classifications": dict(Counter(row["classification"] for row in conflicts)),
        "old_artifact_comparison": {
            "dataset_fingerprint_equal": audit["dataset"]["manifest_sha256"] == previous_audit["dataset"]["manifest_sha256"],
            "source_inventory_equal": grouped["source_inventory_sha256"] == previous_grouped["source_inventory_sha256"],
            "assignments_equal": grouped["assignments_sha256"] == previous_grouped["assignments_sha256"],
        },
        "minimum_candidate_groups_per_class": {split: min(value[split]["groups"] for value in support.values())
                                               for split in ("train", "valid", "test")},
        "limitations": ["No images/labels were repaired, removed, or reassigned in the live dataset.",
                        "Candidate groups and conflicts require expert adjudication; no semantic correctness rate is inferred.",
                        "Numerically different annotation sets may be different boxes, class labels or incomplete annotation, not necessarily wrong food names.",
                        "No independent checkpoint accuracy or clinical validity established."],
    })
    write_json(reports / "dataset-flagged-records.json", {"schema_version": 1, "records": flagged})
    write_json(reports / "dataset-class-group-support.json", {"schema_version": 1, "support": support,
               "unit": "Candidate groups, not independently verified photographs"})
    write_json(local / "label-conflicts.json", {"schema_version": 1, "groups": conflicts})
    write_json(local / "extra-edge-flags.json", {"schema_version": 1, "records": edges})
    write_json(local / "independent-duplicates.json", duplicates)
    report["details"] = [{"path": path.relative_to(ROOT).as_posix(), "sha256": sha256(path)}
                         for path in (reports / "dataset-flagged-records.json", reports / "dataset-class-group-support.json",
                                      local / "label-conflicts.json", local / "extra-edge-flags.json",
                                      local / "independent-duplicates.json")]
    write_json(destination, report)
    print(json.dumps({key: report[key] for key in ("flagged_images", "invalid_line_reasons",
                                                   "label_conflict_classifications", "old_artifact_comparison")}, indent=2))
    return 0


def csv_records(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        return [{key.strip(): (value or "").strip() for key, value in row.items()}
                for row in csv.DictReader(stream)]


def equal_csv_value(left, right):
    if left.strip().lower() in {"", "nan"} and right.strip().lower() in {"", "nan"}:
        return True
    try:
        return Decimal(left) == Decimal(right)
    except InvalidOperation:
        return left == right


def reconstruct_training(before, after, merged):
    reconstructed = sorted(before + after, key=lambda row: int(row["epoch"]))
    epochs = [int(row["epoch"]) for row in reconstructed]
    mismatches = []
    if epochs != list(range(1, len(reconstructed) + 1)):
        mismatches.append({"kind": "noncontiguous_or_duplicate_epochs", "epochs": epochs})
    if len(merged) != len(reconstructed):
        mismatches.append({"kind": "row_count", "expected": len(reconstructed), "actual": len(merged)})
    for position, (expected, actual) in enumerate(zip(reconstructed, merged), 1):
        for key in sorted(set(expected) | set(actual)):
            if not equal_csv_value(expected.get(key, ""), actual.get(key, "")):
                mismatches.append({"row": position, "column": key,
                                   "source": expected.get(key), "merged": actual.get(key)})
    return {"source_rows": [len(before), len(after)], "merged_rows": len(merged),
            "epochs": epochs, "mismatches": mismatches,
            "reconstructed_numeric_cells_match": not mismatches,
            "timer_resets_at_resume": float(after[0]["time"]) < float(before[-1]["time"]),
            "stage_last_logged_seconds": [float(stage[-1]["time"]) for stage in (before, after)],
            "sum_stage_last_logged_seconds_not_wall_clock": sum(float(stage[-1]["time"]) for stage in (before, after)),
            "best_validation_map50": max(merged, key=lambda row: float(row["metrics/mAP50(B)"])),
            "best_validation_map50_95": max(merged, key=lambda row: float(row["metrics/mAP50-95(B)"]))}


def notebook_evaluations(notebook):
    results = []
    for index, cell in enumerate(notebook.get("cells", []), 1):
        source = cell.get("source", [])
        source = source if isinstance(source, str) else "".join(source)
        if ".val(" not in source:
            continue
        output = ""
        for block in cell.get("outputs", []):
            content = block.get("text", "")
            output += content if isinstance(content, str) else "".join(content)
        output = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", output)
        split = re.search(r"split\s*=\s*[\"']([^\"']+)", source)
        aggregate = re.search(r"^\s*all\s+(\d+)\s+(\d+)\s+([.\d]+)\s+([.\d]+)\s+([.\d]+)\s+([.\d]+)", output, re.M)
        row = {"one_based_cell": index, "split": split[1] if split else "not_explicit",
               "source": source, "explicit_confidence": None, "explicit_nms_iou": None,
               "console_aggregate": None, "printed_metrics": {}}
        for parameter, field in (("conf", "explicit_confidence"), ("iou", "explicit_nms_iou")):
            match = re.search(rf"\b{parameter}\s*=\s*([.\d]+)", source)
            row[field] = float(match[1]) if match else None
        if aggregate:
            row["console_aggregate"] = {"images": int(aggregate[1]), "instances": int(aggregate[2]),
                                         "precision": float(aggregate[3]), "recall": float(aggregate[4]),
                                         "map50": float(aggregate[5]), "map50_95": float(aggregate[6]),
                                         "precision_note": "Console-rounded, not unrounded evaluator values."}
        for name in ("mAP50-95", "mAP50", "mAP75", "Precision", "Recall"):
            match = re.search(rf"^{re.escape(name)}:\s*([.\d]+)", output, re.M)
            if match:
                row["printed_metrics"][name] = float(match[1])
        environment = re.search(r"Ultralytics[^\n]+", output)
        speed = re.search(r"Speed:[^\n]+", output)
        row["printed_environment"] = environment[0] if environment else None
        row["printed_speed"] = speed[0] if speed else None
        results.append(row)
    return results


def redact_account_paths(value):
    """Retain method provenance while omitting hosted-notebook account names."""
    if isinstance(value, str):
        return re.sub(r"(/kaggle/input/(?:datasets|models)/)[^/\s\"']+/", r"\1[account-redacted]/", value)
    if isinstance(value, list):
        return [redact_account_paths(item) for item in value]
    if isinstance(value, dict):
        return {key: redact_account_paths(item) for key, item in value.items()}
    return value


def inspect_training(run_id):
    _, reports = locations(run_id)
    destination = reports / "training-results.json"
    if destination.exists():
        raise ValueError("Training report exists; use a new run")
    report, started = context(), time.monotonic()
    paths = [ROOT / "results_before_discontinuation/runs/yolo11s_indian_food/results.csv",
             ROOT / "results_after_discontinuation/runs/yolo11s_indian_food/results.csv",
             ROOT / "merge_results/merged_results_1_to_100.csv"]
    reconstruction = reconstruct_training(*(csv_records(path) for path in paths))
    final_notebook = ROOT / "notebooks/final_version_training.ipynb"
    old_notebook = ROOT / "notebooks/result-merge.ipynb"
    checkpoints = [ROOT / "results_after_discontinuation/yolo11s_indian_food_best.pt",
                   ROOT / "results_after_discontinuation/runs/yolo11s_indian_food/weights/best.pt",
                   ROOT / "results_before_discontinuation/runs/yolo11s_indian_food/weights/best.pt"]
    configs = [ROOT / f"results_{stage}_discontinuation/runs/yolo11s_indian_food/args.yaml"
               for stage in ("before", "after")]
    final_metrics = notebook_evaluations(read_json(final_notebook))
    if {row["split"] for row in final_metrics} != {"val", "test"}:
        raise ValueError("Historical notebook evaluation cell selection changed")
    artifact_paths = paths + [final_notebook, old_notebook, ROOT / "notebooks/initial_version_training.ipynb"] + checkpoints + configs
    report.update({"run_id": run_id, "command": [sys.executable, str(Path(__file__)), "--phase", "training", "--run-id", run_id],
                   "status": "passed_historical_artifact_checks" if not reconstruction["mismatches"] else "failed_csv_reconstruction",
                   "exit_code": int(bool(reconstruction["mismatches"])), "reconstruction": reconstruction,
                   "final_notebook_evaluations": final_metrics,
                   "older_checkpoint_notebook_evaluations_not_final_results": notebook_evaluations(read_json(old_notebook)),
                   "checkpoint_current_identity": {"deployed_equals_archived_final": sha256(checkpoints[0]) == sha256(checkpoints[1]),
                                                   "deployed_equals_older_checkpoint": sha256(checkpoints[0]) == sha256(checkpoints[2]),
                                                   "evaluated_checkpoint_hash_recorded_at_historical_execution": False},
                   "training_configurations": [{"path": path.relative_to(ROOT).as_posix(), "settings": yaml.safe_load(path.read_text())}
                                               for path in configs],
                   "artifacts": [{"path": path.relative_to(ROOT).as_posix(), "sha256": sha256(path), "bytes": path.stat().st_size}
                                 for path in artifact_paths],
                   "duration_seconds": round(time.monotonic() - started, 3),
                   "limitations": [
                       "This recomputes CSV summaries and extracts recorded notebook output; no detector was rerun.",
                       "Merged time resets at epoch 56; stage duration sum is logged execution time, not a complete measured wall-clock training duration.",
                       "The initial_version_training notebook contains a generic/legacy 30-class workflow and first-found YAML resolution; exact initial-stage 72-class execution provenance is incomplete.",
                       "Final notebook did not explicitly override confidence/NMS thresholds; current API values do not identify historical evaluator defaults.",
                       "merge_results prediction JSON and result-merge notebook belong to an older checkpoint, not an independently recomputable final-model prediction archive.",
                       "Current hashes cannot retroactively prove historical checkpoint/dataset identity. All old evaluation partitions have known overlap.",
                       "GPU timings are not production CPU/application latency. No clinical or independent generalization claims.",
                   ]})
    report = redact_account_paths(report)
    report["privacy_redaction"] = "Hosted-notebook account path segments omitted; notebook hashes and cell indices retain review-time provenance."
    write_json(destination, report)
    print(json.dumps({"status": report["status"], "csv_mismatches": len(reconstruction["mismatches"]),
                      "evaluations": [{"split": row["split"], "metrics": row["printed_metrics"]} for row in final_metrics]}, indent=2))
    return report["exit_code"]


def inspect_sources(run_id):
    local, reports = locations(run_id)
    report, started = context(), time.monotonic()
    grouped = read_json(local / "grouped/summary.json")
    sources, all_names = [], set()
    for recorded in grouped["sources"]:
        path = ROOT / "data" / recorded["source"] / "data.yaml"
        if sha256(path) != recorded["yaml_sha256"]:
            raise ValueError("Source YAML changed since the frozen source inventory")
        config = yaml.safe_load(path.read_text(encoding="utf-8"))
        names = config["names"]
        names = [names[key] for key in sorted(names)] if isinstance(names, dict) else names
        if config["nc"] != len(names):
            raise ValueError("Source YAML class count differs from names list")
        all_names.update(names)
        sources.append({"source": recorded["source"], "yaml_sha256": recorded["yaml_sha256"],
                        "images": recorded["images"], "raw_class_count": len(names), "raw_class_names": names})
    report.update({"run_id": run_id, "command": [sys.executable, str(Path(__file__)), "--phase", "sources", "--run-id", run_id],
                   "status": "passed_current_source_metadata_checks", "exit_code": 0,
                   "sources": sources, "summed_class_entries": sum(source["raw_class_count"] for source in sources),
                   "distinct_raw_class_names": sorted(all_names), "distinct_raw_class_count": len(all_names),
                   "total_images": sum(source["images"] for source in sources), "canonical_class_count": len(grouped["class_names"]),
                   "source_inventory_sha256": grouped["source_inventory_sha256"],
                   "grouped_summary_sha256": sha256(local / "grouped/summary.json"),
                   "duration_seconds": round(time.monotonic() - started, 3),
                   "limitations": ["Raw names are exact case-sensitive YAML strings, not unique semantic food concepts.",
                                   "114 is the sum of source class counts, not the number of distinct raw label strings.",
                                   "Source image counts come from the freshly rehashed inventory, not independent photographs.",
                                   "This does not verify asset rights, augmentation identity or class-label correctness."]})
    write_json(reports / "dataset-sources.json", report)
    print(json.dumps({key: report[key] for key in ("total_images", "summed_class_entries", "distinct_raw_class_count", "canonical_class_count")}))
    return 0


def dhash(image):
    """64 horizontal luminance differences; not a learned similarity score."""
    pixels = list(ImageOps.exif_transpose(image).convert("L").resize((9, 8), Image.Resampling.LANCZOS).get_flattened_data())
    value = 0
    for y in range(8):
        for x in range(8):
            value = (value << 1) | (pixels[y * 9 + x] > pixels[y * 9 + x + 1])
    return value


def stratified_sample(groups, per_class_split=10, seed=42):
    """At most one representative per group per stratum; deterministic cap."""
    buckets = defaultdict(dict)
    for group in groups:
        if group["candidate_split"] is None:
            continue
        for row in group["rows"]:
            score = hashlib.sha256(f"{seed}:{row['path']}".encode()).hexdigest()
            record = {**row, "group_id": group["group_id"], "candidate_split": group["candidate_split"], "score": score}
            for category in set(row["classes"]):
                bucket = buckets[(category, group["candidate_split"])]
                previous = bucket.get(group["group_id"])
                if previous is None or score < previous["score"]:
                    bucket[group["group_id"]] = record
    selected = {}
    for bucket in buckets.values():
        for row in sorted(bucket.values(), key=lambda row: (row["score"], row["path"]))[:per_class_split]:
            selected[row["path"]] = row
    return sorted(selected.values(), key=lambda row: row["path"])


def perceptual_candidates(rows, threshold=6, cap=200):
    candidates, comparisons = [], 0
    for index, left in enumerate(rows):
        for right in rows[index + 1:]:
            if (left["candidate_split"] == right["candidate_split"] or left["group_id"] == right["group_id"]
                    or left["pixel_sha256"] == right["pixel_sha256"]):
                continue
            comparisons += 1
            distance = (left["dhash"] ^ right["dhash"]).bit_count()
            if distance <= threshold:
                candidates.append({"left": left["path"], "right": right["path"], "distance": distance,
                                   "candidate_splits": [left["candidate_split"], right["candidate_split"]],
                                   "group_ids": [left["group_id"], right["group_id"]],
                                   "source_sha256": [left["sha256"], right["sha256"]],
                                   "expert_adjudication": "pending"})
    candidates.sort(key=lambda row: (row["distance"], row["left"], row["right"]))
    return {"eligible_pair_comparisons": comparisons, "candidate_pairs_before_cap": len(candidates),
            "queue_truncated": len(candidates) > cap, "queue": candidates[:cap]}


def calibration_probe(image):
    """In-memory robustness probes only; no transformed dataset files saved."""
    image = ImageOps.exif_transpose(image).convert("RGB")
    original = dhash(image)
    compressed = io.BytesIO()
    image.save(compressed, format="JPEG", quality=35)
    compressed.seek(0)
    width, height = image.size
    with Image.open(compressed) as jpeg:
        variants = {"jpeg_quality_35": jpeg.copy(),
                    "resize_48_square": image.resize((48, 48), Image.Resampling.LANCZOS),
                    "crop_10_percent_each_edge": image.crop((width // 10, height // 10, width * 9 // 10, height * 9 // 10)),
                    "rotate_10_degrees_black_fill": image.rotate(10, resample=Image.Resampling.BICUBIC),
                    "horizontal_mirror": ImageOps.mirror(image)}
    return {name: (original ^ dhash(variant)).bit_count() for name, variant in variants.items()}


def inspect_perceptual(run_id):
    local, reports = locations(run_id)
    destination = reports / "dataset-perceptual-review.json"
    if destination.exists():
        raise ValueError("Perceptual report exists; use a new run")
    report, started = context(), time.monotonic()
    groups = jsonl(local / "grouped/assignments.jsonl")
    selected = stratified_sample(groups)
    failures = []
    for index, row in enumerate(selected, 1):
        try:
            path = DATASET / row["path"]
            if sha256(path) != row["sha256"]:
                raise ValueError("Image bytes differ from frozen manifest")
            with Image.open(path) as image:
                row["dhash"] = dhash(image)
        except (OSError, ValueError) as error:
            failures.append({"path": row["path"], "error": str(error)})
        if index % 500 == 0:
            print(f"Perceptual sample {index}/{len(selected)}", flush=True)
    successfully_hashed = [row for row in selected if "dhash" in row]
    candidates = perceptual_candidates(successfully_hashed)
    probes = []
    for row in sorted(successfully_hashed, key=lambda row: row["score"])[:12]:
        with Image.open(DATASET / row["path"]) as image:
            probes.append({"path": row["path"], "sha256": row["sha256"], "distances": calibration_probe(image)})
    transformations = sorted(probes[0]["distances"]) if probes else []
    probe_summary = {name: {"count": len(probes),
                            "within_threshold": sum(row["distances"][name] <= 6 for row in probes),
                            "minimum": min(row["distances"][name] for row in probes),
                            "maximum": max(row["distances"][name] for row in probes)} for name in transformations}
    write_json(local / "perceptual-sample.json", {"schema_version": 1, "records": selected})
    write_json(local / "perceptual-calibration.json", {"schema_version": 1, "probes": probes})
    write_json(reports / "dataset-perceptual-queue.json", {"schema_version": 1, **candidates})
    report.update({"run_id": run_id, "command": [sys.executable, str(Path(__file__)), "--phase", "perceptual", "--run-id", run_id],
                   "status": "candidate_review_pending" if not failures else "failed_image_reads", "exit_code": int(bool(failures)),
                   "duration_seconds": round(time.monotonic() - started, 3), "failures": failures,
                   "method": "64-bit horizontal dHash, EXIF-normalized luminance, 9x8 Lanczos, Hamming distance <= 6",
                   "sample_policy": "Seed 42 SHA256(path) rank: up to 10 distinct candidate groups per class and split; deduplicate selected paths.",
                   "selected_images": len(selected), "successfully_hashed_images": len(successfully_hashed),
                   "eligible_images_in_candidate_partitions": sum(len(group["rows"]) for group in groups if group["candidate_split"]),
                   "sample_by_candidate_split": dict(Counter(row["candidate_split"] for row in selected)),
                   "threshold": 6, "queue_cap": 200, "eligible_pair_comparisons": candidates["eligible_pair_comparisons"],
                   "candidate_pairs_before_cap": candidates["candidate_pairs_before_cap"], "queue_truncated": candidates["queue_truncated"],
                   "calibration_probe_summary": probe_summary,
                   "limitations": [
                       "Bounded sample only; this is not a full-corpus perceptual census or independence certification.",
                       "Threshold 6 is a provisional screening choice, not calibrated against an expert-labeled positive/negative set.",
                       "Transform probes use 12 deterministic original images and known synthetic lineage; no transformed files were retained.",
                       "Probe recovery is not sensitivity on real near-duplicates; no verified negatives or precision/recall estimate exists.",
                       "Crops, rotations, collages, overlays, mirroring and source-family ambiguity can escape this screen; unrelated images can collide.",
                       "Cross-candidate-split pairs exclude equal known pixel identities and equal candidate groups, but unlinked source families may remain.",
                       "All queued pair identities and food annotations need qualified human adjudication. No dataset repair or detector run was performed.",
                   ]})
    report["artifacts"] = [{"path": path.relative_to(ROOT).as_posix(), "sha256": sha256(path)} for path in (
        local / "grouped/assignments.jsonl", local / "perceptual-sample.json", local / "perceptual-calibration.json",
        reports / "dataset-perceptual-queue.json")]
    write_json(destination, report)
    print(json.dumps({key: report[key] for key in ("selected_images", "candidate_pairs_before_cap", "calibration_probe_summary")}, indent=2))
    return report["exit_code"]


def verify_tools(run_id):
    _, reports = locations(run_id)
    destination = reports / "dataset-training-checks.json"
    if destination.exists():
        raise ValueError("Checks report exists; use a new run")
    report, started = context(), time.monotonic()
    paths = ["scripts/validate_dataset_training.py", "scripts/test_validate_dataset_training.py",
             "scripts/record_dataset_visual_review.py"]
    results = []
    for command in ([sys.executable, paths[1]], [sys.executable, "-m", "ruff", "check", *paths]):
        start = time.monotonic()
        child = subprocess.run(command, cwd=ROOT, text=True, encoding="utf-8", capture_output=True, check=False)
        output = child.stdout + child.stderr
        print(output, end="", flush=True)
        results.append({"command": command, "exit_code": child.returncode, "output": output,
                        "duration_seconds": round(time.monotonic() - start, 3)})
    failed = any(result["exit_code"] for result in results)
    report.update({"run_id": run_id, "results": results, "exit_code": int(failed),
                   "status": "failed" if failed else "passed_synthetic_tests_and_lint",
                   "duration_seconds": round(time.monotonic() - started, 3),
                   "artifacts": [{"path": path, "sha256": sha256(ROOT / path)} for path in paths],
                   "limitations": ["Passing tests check these offline helper rules, not dataset semantics, independent detector accuracy or publication approval."]})
    write_json(destination, report)
    return report["exit_code"]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default=RUN_ID)
    parser.add_argument("--phase", choices=("audit", "grouped", "inspect", "training", "perceptual", "sources", "checks"), required=True)
    args = parser.parse_args(argv)
    if args.phase == "inspect":
        return inspect_dataset(args.run_id)
    if args.phase == "training":
        return inspect_training(args.run_id)
    if args.phase == "perceptual":
        return inspect_perceptual(args.run_id)
    if args.phase == "sources":
        return inspect_sources(args.run_id)
    if args.phase == "checks":
        return verify_tools(args.run_id)
    return execute_child(args.phase, args.run_id)


if __name__ == "__main__":
    raise SystemExit(main())
