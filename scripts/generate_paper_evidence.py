"""Generate manuscript numbers from tracked JSON evidence, without research data.

These are artifact-consistency checks, not assertions of scientific or clinical
validity. Percentage macros contain numbers only; add \\% at the point of use.
"""

import argparse
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
AUDIT = Path("research/evidence/audit.json")
GROUPED = Path("research/evidence/grouped-split-v1.json")
OUTPUTS = tuple(
    Path(f"Research_Paper_{kind}/generated/evidence.tex")
    for kind in ("Conference", "Journal")
)
SPLITS = ("train", "valid", "test")


def count(value, name):
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a nonnegative integer")
    return value


def require(condition, message):
    if not condition:
        raise ValueError(message)


def derive_macros(audit, grouped):
    """Derive numbers; never interpret lookup coverage as mapping accuracy."""
    require(audit["schema_version"] == 1 and grouped["schema_version"] == 1,
            "Unsupported evidence schema version")
    dataset = audit["dataset"]
    nutrition = audit["nutrition"]
    classes = count(dataset["class_count"], "class_count")
    require(classes > 0, "class_count must be positive")
    fingerprint = dataset["manifest_sha256"]
    require(isinstance(fingerprint, str) and re.fullmatch(r"[0-9a-f]{64}", fingerprint),
            "Invalid dataset fingerprint")
    require(fingerprint == grouped["dataset_fingerprint"], "Dataset fingerprints differ")
    names = grouped["class_names"]
    require(isinstance(names, list) and all(isinstance(name, str) and name for name in names)
            and len(names) == len(set(names)) == classes, "Class counts or names differ")

    macros = {"AuditClasses": classes, "AuditImages": count(dataset["image_count"], "image_count")}
    flagged = 0
    for split in SPLITS:
        values = dataset["splits"][split]
        images = count(values["images"], f"{split} images")
        issues = count(values["issue_images"], f"{split} issue_images")
        require(issues <= images, f"{split} issue count exceeds images")
        macros[f"Audit{split.title()}Images"] = images
        macros[f"Audit{split.title()}Instances"] = count(values["instances"], f"{split} instances")
        flagged += issues
    require(sum(macros[f"Audit{split.title()}Images"] for split in SPLITS) == macros["AuditImages"],
            "Audit split image totals do not match image_count")
    macros["AuditFlaggedImages"] = flagged

    # Oriented-RGB exact-pixel duplication includes recompressed identical pixels.
    duplicates = dataset["pixel_duplicates"]
    macros["AuditDuplicateGroups"] = count(duplicates["cross_split_groups"], "duplicate groups")
    macros["AuditDuplicateImages"] = count(duplicates["affected_images"], "duplicate images")
    require(2 * macros["AuditDuplicateGroups"] <= macros["AuditDuplicateImages"] <= macros["AuditImages"],
            "Inconsistent cross-split duplicate counts")
    for pair, name in (("train:valid", "TrainValid"), ("train:test", "TrainTest"), ("valid:test", "ValidTest")):
        value = count(duplicates["pairs"].get(pair, {}).get("shared_groups", 0), f"{pair} shared groups")
        require(value <= macros["AuditDuplicateGroups"], f"{pair} exceeds distinct duplicate groups")
        macros[f"Audit{name}Groups"] = value

    macros["NutritionRows"] = count(nutrition["food_rows"], "food_rows")
    macros["MappingRows"] = count(nutrition["mapping_rows"], "mapping_rows")
    coverage = nutrition["coverage_not_accuracy"]
    for name, key in (("Exact", "normalized_exact"), ("Automatic", "automatic_without_precomputed"),
                      ("Current", "current_mapping")):
        value = count(coverage[key], f"{name} coverage")
        require(value <= classes, f"{name} coverage exceeds class count")
        macros[f"Coverage{name}"] = value
        macros[f"Coverage{name}Percent"] = Decimal(value) * 100 / Decimal(classes)
    macros["MappingReviewCount"] = count(nutrition["review_score_below_0_9_or_missing"], "mapping review count")
    require(macros["MappingReviewCount"] <= classes, "Mapping review count exceeds class count")

    macros["CandidateSourceImages"] = sum(count(source["images"], "source images") for source in grouped["sources"])
    macros["CandidateGroups"] = count(grouped["total_groups"], "total_groups")
    macros["CandidateQuarantinedImages"] = count(grouped["quarantined_images"], "quarantined_images")
    macros["CandidateQuarantinedGroups"] = count(grouped["quarantined_groups"], "quarantined_groups")
    require(macros["CandidateQuarantinedGroups"] <= macros["CandidateQuarantinedImages"],
            "Quarantined groups exceed quarantined images")
    eligible = groups = unique_pixels = 0
    for split in SPLITS:
        values = grouped["splits"][split]
        for suffix, key in (("Images", "images"), ("Groups", "groups"), ("UniquePixels", "unique_pixels")):
            macros[f"Candidate{split.title()}{suffix}"] = count(values[key], f"candidate {split} {key}")
        require(values["groups"] <= values["unique_pixels"] <= values["images"],
                f"Inconsistent candidate {split} group/pixel/image counts")
        eligible += values["images"]
        groups += values["groups"]
        unique_pixels += values["unique_pixels"]
    require(eligible + macros["CandidateQuarantinedImages"] == macros["AuditImages"],
            "Eligible plus quarantined images do not match audited image count")
    require(groups + macros["CandidateQuarantinedGroups"] == macros["CandidateGroups"],
            "Candidate group totals do not match total_groups")
    require(count(grouped["known_group_overlap_across_candidate_splits"], "candidate overlap") == 0,
            "Known groups overlap across candidate splits")
    macros["CandidateOldOverlapGroups"] = count(grouped["source_family_groups_spanning_old_splits"], "old overlap")
    require(macros["CandidateOldOverlapGroups"] <= macros["CandidateGroups"], "Old overlap exceeds total groups")
    macros["CandidateEligibleImages"] = eligible
    # Excess records above unique pixels, NOT a count of duplicate groups.
    macros["CandidateRepeatedPixels"] = eligible - unique_pixels
    reasons = grouped["quarantine_images_by_reason_nonexclusive"]
    for name, key in (("Unresolved", "unresolved_source_lineage"), ("Conflict", "identical_pixels_different_labels"),
                      ("IssueGroup", "annotation_or_decode_issue"), ("EmptyGroup", "no_accepted_annotations")):
        value = count(reasons.get(key, 0), key)
        require(value <= macros["CandidateQuarantinedImages"], "Quarantine reason exceeds quarantine image count")
        macros[f"Candidate{name}Images"] = value
    return macros


def render_evidence(audit_bytes, grouped_bytes):
    audit = json.loads(audit_bytes)
    grouped = json.loads(grouped_bytes)
    audit_hash = hashlib.sha256(audit_bytes).hexdigest()
    require(grouped["audit_sha256"] == audit_hash, "Grouped evidence references a different audit artifact")
    macros = derive_macros(audit, grouped)
    lines = [
        "% Generated by scripts/generate_paper_evidence.py; do not edit.",
        f"% {AUDIT.as_posix()} SHA256: {audit_hash}",
        f"% {GROUPED.as_posix()} SHA256: {hashlib.sha256(grouped_bytes).hexdigest()}",
        "% Counts describe recorded artifacts, not independent or clinical validity.",
        "% AuditDuplicate* uses oriented-RGB exact-pixel groups; percentages omit the percent sign.",
        "% CandidateRepeatedPixels counts excess eligible records above unique pixels.",
    ]
    for name, value in macros.items():
        formatted = f"{value:.2f}" if isinstance(value, Decimal) else f"{value:,}"
        lines.append(f"\\newcommand{{\\{name}}}{{{formatted}}}")
    return "\n".join(lines) + "\n"


def generate(root=ROOT, check=False):
    """Check both outputs before any writes; --check never repairs missing files."""
    try:
        content = render_evidence((root / AUDIT).read_bytes(), (root / GROUPED).read_bytes())
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"Invalid paper evidence: {exc}") from exc
    if check:
        drift = [str(path) for path in OUTPUTS
                 if not (root / path).is_file() or (root / path).read_text(encoding="utf-8") != content]
        if drift:
            raise ValueError("Generated paper evidence is missing or out of date: " + ", ".join(drift))
    else:
        for path in OUTPUTS:
            (root / path).parent.mkdir(parents=True, exist_ok=True)
            (root / path).write_text(content, encoding="utf-8", newline="\n")
    return content


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail on missing or drifted output without writing")
    args = parser.parse_args(argv)
    try:
        generate(check=args.check)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Paper evidence check failed: {exc}\n")
    print("Paper evidence verified" if args.check else "Paper evidence generated")


if __name__ == "__main__":
    main()
