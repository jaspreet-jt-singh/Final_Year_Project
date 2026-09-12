"""Prepare blinded v2 materials or score completed independent mapping references.

Preserves the legacy v1 template/scorer. No judgments are generated. Completeness
and self-attestation checks do not independently verify reviewer qualifications.
"""

import argparse
import hashlib
import json
from pathlib import Path

from validate_nutrition_evidence import ROOT, digest, read_database, validate_baseline, write_json

METHODS = ("normalized_exact", "automatic_without_precomputed", "current_mapping")
STATUSES = {"accepted", "unsupported", "indeterminate"}


def byte_hash(value):
    return hashlib.sha256(value).hexdigest()


def ensure(condition, message):
    if not condition:
        raise ValueError(message)


def prepare(root, run_id):
    _, inputs, baseline_hash = validate_baseline(root, run_id)
    local = root / ".deployment/research" / run_id
    directory = root / "research/review" / run_id
    predictions = json.loads((local / "mapping-predictions.json").read_text(encoding="utf-8"))
    classes = [row["class"] for row in predictions["comparisons"]]
    catalog = local / "review/nutrition-catalog.json"
    packet = {"schema_version": 2, "run_id": run_id, "status": "awaiting_independent_review",
              "baseline_sha256": baseline_hash, "database_sha256": inputs["data/nutrition.db"],
              "class_names_sha256": inputs["data/food_dataset/data.yaml"], "workbook_sha256": inputs["data/INDB.xlsx"],
              "builder_sha256": inputs["backend/scripts/merge_db.py"], "catalog_sha256": digest(catalog),
              "local_catalog": catalog.relative_to(root).as_posix(), "classes": classes,
              "scope": "Class-to-database recipe correspondence only, not measured meal nutrition or clinical suitability.",
              "reference_policy": {"accepted": "One or more independently justified database names for the defined class scope.",
                                   "unsupported": "Review completed; no database row is defensible for the class definition.",
                                   "indeterminate": "Evidence/definition too ambiguous for a defensible decision; exclude from correctness denominator and report separately."},
              "blinding": "Reviewers receive this packet and full catalog, not predicted mappings, heuristic scores, or algorithm names.",
              "source_limitations": "Catalog source labels reflect the frozen database; workbook identity and transcription are not independent nutrient/recipe or rights validation."}
    write_json(directory / "packet.json", packet)
    packet_hash = digest(directory / "packet.json")
    reference = {"schema_version": 2, "packet_sha256": packet_hash,
                 "database_sha256": packet["database_sha256"], "class_names_sha256": packet["class_names_sha256"],
                 "workbook_sha256": packet["workbook_sha256"], "catalog_sha256": packet["catalog_sha256"],
                 "reviewer": {"id": "", "qualifications": "", "completed_at": "", "independent_of_mapping_authors": False,
                              "blinded_to_predictions_until_complete": False},
                 "rows": [{"class": name, "status": "pending", "class_definition": "", "acceptable_database_names": [],
                           "evidence": [], "rationale": ""} for name in classes]}
    for name in ("reference-a-v2.template.json", "reference-b-v2.template.json"):
        write_json(directory / name, reference)
    write_json(directory / "adjudication-v2.template.json", {
        "schema_version": 2, "packet_sha256": packet_hash, "review_a_sha256": "", "review_b_sha256": "",
        "adjudicator": {"id": "", "qualifications": "", "completed_at": ""},
        "rows": [], "instructions": "After both references are frozen, add exactly one resolved row for each disagreement. Use the reference row format; indeterminate is permitted."})
    return directory


def validate_row(row, database_names):
    ensure(row.get("status") in STATUSES, "Every row needs accepted, unsupported, or indeterminate status; pending rows cannot be scored")
    for field in ("class_definition", "rationale"):
        ensure(isinstance(row.get(field), str) and row[field].strip(), f"Every row requires {field}")
    evidence = row.get("evidence")
    ensure(isinstance(evidence, list) and evidence and all(isinstance(item, str) and item.strip() for item in evidence),
           "Every row requires source citations or traceable evidence locations")
    names = row.get("acceptable_database_names")
    ensure(isinstance(names, list) and all(isinstance(name, str) for name in names) and len(names) == len(set(names)),
           "Acceptable names must be a unique string list")
    ensure(set(names).issubset(database_names), "Reference names must exist in the frozen database")
    ensure(bool(names) == (row["status"] == "accepted"), "Only accepted references have one or more acceptable names")
    return row


def decision(row):
    return row["status"], tuple(sorted(row["acceptable_database_names"]))


def validate_review(data, packet, packet_hash, database_names):
    ensure(data.get("schema_version") == 2 and data.get("packet_sha256") == packet_hash, "Review schema or packet hash mismatch")
    for field in ("database_sha256", "class_names_sha256", "workbook_sha256", "catalog_sha256"):
        ensure(data.get(field) == packet[field], f"Review {field} mismatch")
    reviewer = data.get("reviewer", {})
    for field in ("id", "qualifications", "completed_at"):
        ensure(isinstance(reviewer.get(field), str) and reviewer[field].strip(), f"Reviewer {field} is required")
    ensure(reviewer.get("independent_of_mapping_authors") is True and reviewer.get("blinded_to_predictions_until_complete") is True,
           "Independent blinded review attestation is required")
    rows = data.get("rows", [])
    ensure(isinstance(rows, list) and len(rows) == len(packet["classes"])
           and {row.get("class") for row in rows} == set(packet["classes"]), "Exactly one reviewed row per frozen class is required")
    return {row["class"]: validate_row(row, database_names) for row in rows}


def score(packet_bytes, review_a_bytes, review_b_bytes, predictions, database_names, adjudication=None):
    packet = json.loads(packet_bytes)
    ensure(packet.get("schema_version") == 2, "Packet schema must be v2")
    classes = packet.get("classes")
    ensure(isinstance(classes, list) and classes and all(isinstance(name, str) and name for name in classes)
           and len(classes) == len(set(classes)), "Packet must contain unique nonempty classes")
    packet_hash = byte_hash(packet_bytes)
    ensure(predictions.get("database_sha256") == packet["database_sha256"]
           and predictions.get("class_names_sha256") == packet["class_names_sha256"]
           and predictions.get("baseline_sha256") == packet["baseline_sha256"], "Predictions do not match frozen reference inputs")
    a, b = json.loads(review_a_bytes), json.loads(review_b_bytes)
    left = validate_review(a, packet, packet_hash, database_names)
    right = validate_review(b, packet, packet_hash, database_names)
    ensure(a["reviewer"]["id"] != b["reviewer"]["id"], "Two distinct independent reviewers are required")
    # A differing class definition also needs adjudication, even when row choices agree.
    disagreements = {name for name in left if decision(left[name]) != decision(right[name])
                     or left[name]["class_definition"].strip() != right[name]["class_definition"].strip()}
    resolved = dict(left)
    if disagreements:
        ensure(adjudication is not None, "Disagreements require a separate adjudication artifact")
        ensure(adjudication.get("schema_version") == 2 and adjudication.get("packet_sha256") == packet_hash,
               "Adjudication packet/schema mismatch")
        ensure(adjudication.get("review_a_sha256") == byte_hash(review_a_bytes)
               and adjudication.get("review_b_sha256") == byte_hash(review_b_bytes), "Adjudication must reference exact completed review hashes")
        person = adjudication.get("adjudicator", {})
        for field in ("id", "qualifications", "completed_at"):
            ensure(isinstance(person.get(field), str) and person[field].strip(), f"Adjudicator {field} is required")
        ensure(person["id"] not in {a["reviewer"]["id"], b["reviewer"]["id"]}, "Adjudicator must be distinct from both reviewers")
        rows = adjudication.get("rows", [])
        ensure(len(rows) == len(disagreements) and {row.get("class") for row in rows} == disagreements,
               "Adjudicate exactly the disagreement classes")
        resolved.update({row["class"]: validate_row(row, database_names) for row in rows})
    comparisons = predictions["comparisons"]
    ensure(len(comparisons) == len(packet["classes"]) and {row["class"] for row in comparisons} == set(packet["classes"]),
           "Predictions need exactly one row per frozen class")
    scores, outcomes = {}, []
    for method in METHODS:
        counts = {key: 0 for key in ("correct_match", "wrong_match", "correct_abstention", "missed_supported", "indeterminate")}
        matched = 0
        for row in comparisons:
            reference = resolved[row["class"]]
            prediction = row[method]
            ensure(prediction is None or prediction in database_names, "Predicted row must exist in the frozen database")
            matched += int(prediction is not None)
            if reference["status"] == "indeterminate":
                outcome = "indeterminate"
            elif prediction is None:
                outcome = "correct_abstention" if reference["status"] == "unsupported" else "missed_supported"
            else:
                outcome = "correct_match" if prediction in reference["acceptable_database_names"] else "wrong_match"
            counts[outcome] += 1
            outcomes.append({"class": row["class"], "method": method, "outcome": outcome})
        eligible = len(comparisons) - counts["indeterminate"]
        correct = counts["correct_match"] + counts["correct_abstention"]
        matched_eligible = counts["correct_match"] + counts["wrong_match"]
        scores[method] = {**counts, "total_classes": len(comparisons), "scorable_classes": eligible,
                          "lookup_coverage": matched / len(comparisons),
                          "decision_agreement": correct / eligible if eligible else None,
                          "matched_precision": counts["correct_match"] / matched_eligible if matched_eligible else None}
    return {"schema_version": 2, "packet_sha256": packet_hash, "database_sha256": packet["database_sha256"],
            "review_a_sha256": byte_hash(review_a_bytes), "review_b_sha256": byte_hash(review_b_bytes),
            "initial_disagreements": len(disagreements), "scores": scores, "class_outcomes": outcomes,
            "limitations": ["Reviewer qualification/independence are self-attested, not verified by this program.",
                            "Class-level reference agreement is not photographed-meal nutritional or clinical accuracy.",
                            "All frozen classes form a finite census; no population-level independence or confidence interval is asserted."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default="validation-2026-09-12-v1")
    parser.add_argument("--prepare", action="store_true")
    for name in ("packet", "review-a", "review-b", "predictions", "adjudication", "output"):
        parser.add_argument("--" + name, type=Path)
    args = parser.parse_args()
    if args.prepare:
        print(prepare(ROOT, args.run_id))
        return
    if not all((args.packet, args.review_a, args.review_b, args.predictions, args.output)):
        parser.error("Supply --packet --review-a --review-b --predictions --output; optional --adjudication")
    packet_bytes = args.packet.read_bytes()
    packet = json.loads(packet_bytes)
    ensure(digest(ROOT / "data/nutrition.db") == packet["database_sha256"], "Database differs from frozen packet")
    ensure(digest(ROOT / "data/INDB.xlsx") == packet["workbook_sha256"], "Workbook differs from frozen packet")
    ensure(digest(ROOT / "data/food_dataset/data.yaml") == packet["class_names_sha256"], "Class names differ from frozen packet")
    ensure(digest(ROOT / "backend/scripts/merge_db.py") == packet["builder_sha256"], "Builder differs from frozen packet")
    catalog_path = (ROOT / packet["local_catalog"]).resolve()
    ensure(catalog_path.is_relative_to((ROOT / ".deployment/research").resolve()), "Catalog must stay in local research artifacts")
    ensure(digest(catalog_path) == packet["catalog_sha256"], "Catalog differs from frozen packet")
    foods, _, _ = read_database(ROOT / "data/nutrition.db")
    result = score(packet_bytes, args.review_a.read_bytes(), args.review_b.read_bytes(),
                   json.loads(args.predictions.read_text(encoding="utf-8")), {row["name"] for row in foods},
                   json.loads(args.adjudication.read_text(encoding="utf-8")) if args.adjudication else None)
    result.update(scorer_sha256=digest(Path(__file__)), predictions_sha256=digest(args.predictions),
                  adjudication_sha256=digest(args.adjudication) if args.adjudication else None)
    write_json(args.output, result)
    print("Completed independent references scored; no clinical validation inferred.")


if __name__ == "__main__":
    main()
