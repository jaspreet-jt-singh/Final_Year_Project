"""Read-only nutrition reconciliation and independent arithmetic evidence.

No model import, external provider, database rebuild, or clinical ground truth.
Full catalogs and case details remain in the ignored local validation directory.
"""

import argparse
import ast
import asyncio
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from fractions import Fraction
import hashlib
import json
import math
import os
from pathlib import Path
import posixpath
import re
import sqlite3
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ("calories", "protein_g", "carbs_g", "fat_g")
GOAL_FIELDS = ("carbs_percent", "protein_percent", "fat_percent", "carbs_g", "protein_g", "fat_g")
SEEDS = (0, 1, 7, 42, 97, 123, 321, 999)
NS = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
REQUIRED = (
    "data/INDB.xlsx", "data/nutrition.db", "data/food_dataset/data.yaml",
    "backend/scripts/merge_db.py", "backend/utils/food_normalizer.py", "backend/config/food_aliases.json",
    "backend/services/nutrition_service.py", "backend/domain/nutrition_policy.json", "backend/domain/rules.py",
    "frontend/lib/goals.ts", "frontend/lib/meals.ts", "frontend/lib/generated/nutritionPolicy.ts",
    "frontend/package-lock.json", "tests/contracts/macro-fixtures.json", "research/evidence/nutrition-provenance.json",
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation protects earlier results, including failed validation runs.
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def independent_normalize(value):
    """Reproduce documented import cleanup without importing application code."""
    value = "" if value is None else str(value).lower()
    value = re.sub(r"\([^)]*\)", "", value)
    return "".join(char for char in value if char in "abcdefghijklmnopqrstuvwxyz0123456789")


def workbook_records(path):
    """Read raw cached XLSX cell values with stdlib XML, independently of pandas."""
    with zipfile.ZipFile(path) as book:
        strings = []
        if "xl/sharedStrings.xml" in book.namelist():
            strings = ["".join(row.itertext()) for row in ET.fromstring(book.read("xl/sharedStrings.xml"))]
        relationships = {item.attrib["Id"]: item.attrib["Target"]
                         for item in ET.fromstring(book.read("xl/_rels/workbook.xml.rels"))}
        sheets = ET.fromstring(book.read("xl/workbook.xml")).find("s:sheets", NS)
        selected = next(sheet for sheet in sheets if sheet.attrib["name"] == "Nutrient Data")
        relation = selected.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]
        target = relationships[relation]
        sheet_path = target.lstrip("/") if target.startswith("/") else posixpath.normpath("xl/" + target)
        headers = None
        for row in ET.fromstring(book.read(sheet_path)).findall("s:sheetData/s:row", NS):
            cells = {}
            for cell in row.findall("s:c", NS):
                column = re.sub(r"\d", "", cell.attrib["r"])
                value = cell.find("s:v", NS)
                if cell.attrib.get("t") == "inlineStr":
                    inline = cell.find("s:is", NS)
                    cells[column] = "".join(inline.itertext()) if inline is not None else None
                elif value is None:
                    cells[column] = None
                elif cell.attrib.get("t") == "s":
                    cells[column] = strings[int(value.text)]
                else:
                    cells[column] = value.text
            if headers is None:
                headers = cells
                needed = {"food_name", "energy_kcal", "protein_g", "carb_g", "fat_g"}
                if not needed.issubset(set(headers.values())):
                    raise ValueError("Workbook is missing required nutrient columns")
            elif any(value is not None for value in cells.values()):
                yield {headers[key]: value for key, value in cells.items() if key in headers} | {"excel_row": int(row.attrib["r"])}


def literal_from_builder(path, name):
    """Read a literal; never import or execute the destructive database builder."""
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == name:
            return ast.literal_eval(node.value)
    raise ValueError(f"Builder literal missing: {name}")


def expected_import(records, supplements):
    expected, omitted, seen = [], [], set()
    mapping = {"food_name": "name", "energy_kcal": "calories", "protein_g": "protein_g", "carb_g": "carbs_g", "fat_g": "fat_g"}
    for row in records:
        key = independent_normalize(row.get("food_name"))
        if key in seen:
            omitted.append({"excel_row": row["excel_row"], "name": row.get("food_name"), "reason": "duplicate_normalized_name"})
            continue
        seen.add(key)  # The historical importer deduplicates BEFORE dropping missing macros.
        entry = {target: row.get(source) for source, target in mapping.items()}
        try:
            for field in FIELDS:
                entry[field] = float(entry[field])
                if not math.isfinite(entry[field]):
                    raise ValueError("nonfinite")
        except (TypeError, ValueError):
            omitted.append({"excel_row": row["excel_row"], "name": row.get("food_name"), "reason": "missing_or_nonnumeric_macro"})
            continue
        entry.update(normalized_name=key, source="INDB", source_url="",
                     source_notes="Imported from data/INDB.xlsx Nutrient Data sheet.", excel_row=row["excel_row"])
        expected.append(entry)
    retained = {row["normalized_name"] for row in expected}
    for supplement in supplements:
        entry = dict(supplement, normalized_name=independent_normalize(supplement["name"]), excel_row=None)
        if entry["normalized_name"] not in retained:
            expected.append(entry)
            retained.add(entry["normalized_name"])
    return expected, omitted


def read_database(path):
    with sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True) as db:
        db.row_factory = sqlite3.Row
        foods = [dict(row) for row in db.execute("SELECT * FROM indb_foods ORDER BY name")]
        mappings = [dict(row) for row in db.execute("SELECT * FROM yolo_mappings ORDER BY yolo_class")]
        integrity = db.execute("PRAGMA integrity_check").fetchall()
    return foods, mappings, [row[0] for row in integrity]


def reconcile(expected, actual):
    left = {row["name"]: row for row in expected}
    right = {row["name"]: row for row in actual}
    differences = []
    for name in sorted(left.keys() | right.keys()):
        if name not in left or name not in right:
            differences.append({"name": name, "kind": "unexpected_database_row" if name not in left else "missing_database_row"})
            continue
        for field in (*FIELDS, "normalized_name", "source", "source_url", "source_notes"):
            want, got = left[name].get(field), right[name].get(field)
            equal = (isinstance(got, (int, float)) and math.isfinite(got) and math.isclose(want, got, rel_tol=0, abs_tol=1e-9)) if field in FIELDS else want == got
            if not equal:
                differences.append({"name": name, "field": field, "expected": want, "actual": got})
    return differences


def classes_from_yaml(path):
    # This frozen export contains a simple block list; do not load training tools.
    content = path.read_text(encoding="utf-8").split("names:\n", 1)[1]
    names = [line[2:].strip() for line in content.splitlines() if line.startswith("- ")]
    if len(names) != len(set(names)) or not names:
        raise ValueError("Invalid class names")
    return names


def lookup_labels(names, mappings, aliases):
    configured = [name for values in aliases.values() if isinstance(values, list) for name in values]
    probes = ["definitely_unknown_xyz", "", "!!!", "paneer chutney", "red rice", "mixed curry", "aloo gobi", "dhall", "gobi paneer"]
    return sorted(set(names + [row["yolo_class"] for row in mappings] + configured + probes))


async def lookup_worker(root):
    sys.path.insert(0, str(root))
    from backend.services.nutrition_service import NutritionService
    database = root / "data/nutrition.db"
    _, mappings, _ = read_database(database)
    names = classes_from_yaml(root / "data/food_dataset/data.yaml")
    aliases = json.loads((root / "backend/config/food_aliases.json").read_text(encoding="utf-8"))
    labels = lookup_labels(names, mappings, aliases)
    result = {}
    for method in ("current_mapping", "automatic_without_precomputed"):
        service = NutritionService(database)
        await service.initialize()
        if method == "automatic_without_precomputed":
            service._yolo_mappings.clear()
        rows = {}
        for label in labels:
            try:
                match = await service.get_nutrition_for_food(label)
                rows[label] = {"name": match["display_name"], "macros": match["macros"]} if match else None
            except Exception as exc:
                rows[label] = {"error_type": type(exc).__name__}
        result[method] = rows
    return {"seed": int(os.environ["PYTHONHASHSEED"]), "labels": labels, "methods": result}


def lookup_across_seeds(root):
    def worker(seed):
        env = dict(os.environ, PYTHONHASHSEED=str(seed), PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8")
        command = [sys.executable, str(Path(__file__).resolve()), "--lookup-worker"]
        result = subprocess.run(command, cwd=root, env=env, text=True, encoding="utf-8", capture_output=True, timeout=180, check=True)
        return json.loads(result.stdout)
    with ThreadPoolExecutor(max_workers=4) as pool:
        runs = list(pool.map(worker, SEEDS))
    differing = []
    for method in runs[0]["methods"]:
        for label in runs[0]["labels"]:
            outcomes = {str(run["seed"]): run["methods"][method][label] for run in runs}
            if len({json.dumps(value, sort_keys=True) for value in outcomes.values()}) > 1:
                differing.append({"method": method, "label": label, "outcomes": outcomes})
    return runs, differing


def round_rational(value):
    quotient, remainder = divmod(value.numerator, value.denominator)
    twice = 2 * remainder
    return quotient + int(twice > value.denominator or (twice == value.denominator and quotient % 2 == 1))


def goal_oracle(policy, goal, condition, calories):
    split = policy["goals"][goal]
    modifiers = policy["modifiers"][condition]
    weights = [Fraction(str(split[f"{key}_percent"])) * Fraction(str(modifiers[key])) for key in ("carbs", "protein", "fat")]
    total = sum(weights)
    percentages = [round_rational(100 * weight / total) for weight in weights[:2]]
    percentages.append(100 - sum(percentages))
    grams = [round_rational(Fraction(calories * percent, denominator)) for percent, denominator in zip(percentages, (400, 400, 900))]
    return dict(zip(GOAL_FIELDS, percentages + grams))


def validate_backend_arithmetic(root, policy):
    sys.path.insert(0, str(root))
    from backend.domain.rules import NutritionRules
    rules = NutritionRules()
    differences, cases = [], 0
    for goal in policy["goals"]:
        for condition in policy["conditions"]:
            for calories in range(500, 5001):
                expected = goal_oracle(policy, goal, condition, calories)
                actual = rules.calculate_macros(goal, calories, condition)
                cases += 1
                if any(actual[key] != value for key, value in expected.items()):
                    differences.append({"goal": goal, "condition": condition, "calories": calories,
                                        "expected": expected, "actual": {key: actual[key] for key in GOAL_FIELDS}})
    fixtures = json.loads((root / "tests/contracts/macro-fixtures.json").read_text(encoding="utf-8"))
    fixture_differences = [{"goal": row["goal"], "condition": row["condition"], "calories": row["calories"]}
                           for row in fixtures if any(row["expected"][key] != value for key, value in
                                                     goal_oracle(policy, row["goal"], row["condition"], row["calories"]).items())]
    return {"cases": cases, "differences": differences, "fixture_cases": len(fixtures), "fixture_differences": fixture_differences}


def validate_baseline(root, run_id):
    if not re.fullmatch(r"validation-[a-z0-9-]+", run_id):
        raise ValueError("Invalid validation run identifier")
    path = root / "research/evidence" / run_id / "baseline.json"
    baseline = json.loads(path.read_text(encoding="utf-8"))
    frozen = {row["path"]: row["sha256"] for row in baseline["files"]}
    current = {name: digest(root / name) for name in REQUIRED}
    if any(current[name] != frozen.get(name) for name in REQUIRED):
        raise ValueError("Required nutrition/arithmetic input differs from frozen baseline")
    return baseline, current, digest(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default="validation-2026-09-12-v1")
    parser.add_argument("--lookup-worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.lookup_worker:
        print(json.dumps(asyncio.run(lookup_worker(ROOT)), ensure_ascii=True, allow_nan=False))
        return
    baseline, inputs, baseline_hash = validate_baseline(ROOT, args.run_id)
    local = ROOT / ".deployment/research" / args.run_id
    reports = ROOT / "research/evidence" / args.run_id
    for filename in ("nutrition-validation.json", "arithmetic-validation.json"):
        if (reports / filename).exists():
            parser.error(f"Report already exists: {filename}; preserve it and choose a new frozen run")
    workbook = list(workbook_records(ROOT / "data/INDB.xlsx"))
    supplements = literal_from_builder(ROOT / "backend/scripts/merge_db.py", "SUPPLEMENTAL_NUTRITION_ROWS")
    expected, omitted = expected_import(workbook, supplements)
    foods, mappings, integrity = read_database(ROOT / "data/nutrition.db")
    differences = reconcile(expected, foods)
    names = classes_from_yaml(ROOT / "data/food_dataset/data.yaml")
    food_names = {row["name"] for row in foods}
    invalid = [{"name": row["name"], "fields": [key for key in FIELDS if not isinstance(row[key], (int, float)) or not math.isfinite(row[key]) or row[key] < 0]}
               for row in foods if any(not isinstance(row[key], (int, float)) or not math.isfinite(row[key]) or row[key] < 0 for key in FIELDS)]
    dangling = [row["yolo_class"] for row in mappings if row["matched_food_name"] not in food_names]
    collisions = {key: value for key, value in Counter(row["normalized_name"] for row in foods).items() if value > 1}
    energy = [{"name": row["name"], "energy_kcal": row["calories"],
               "macro_4_4_9_kcal": 4 * row["protein_g"] + 4 * row["carbs_g"] + 9 * row["fat_g"],
               "residual_kcal": row["calories"] - (4 * row["protein_g"] + 4 * row["carbs_g"] + 9 * row["fat_g"])} for row in foods]
    print("Workbook/database reconciled; measuring eight fixed hash-seed lookup runs.", flush=True)
    runs, ambiguity = lookup_across_seeds(ROOT)
    current = runs[0]["methods"]["current_mapping"]
    automatic = runs[0]["methods"]["automatic_without_precomputed"]
    exact = {row["normalized_name"]: row["name"] for row in foods}
    comparisons = [{"class": name, "normalized_exact": exact.get(independent_normalize(name)),
                    "automatic_without_precomputed": (automatic[name] or {}).get("name"),
                    "current_mapping": (current[name] or {}).get("name")} for name in names]
    write_json(local / "nutrition-details.json", {"omitted_workbook_rows": omitted, "reconciliation_differences": differences,
               "invalid_rows": invalid, "energy_residuals": energy, "hash_seed_runs": runs, "ambiguous_lookups": ambiguity})
    catalog = {"database_sha256": inputs["data/nutrition.db"], "workbook_sha256": inputs["data/INDB.xlsx"], "foods": foods}
    write_json(local / "review/nutrition-catalog.json", catalog)
    write_json(local / "mapping-predictions.json", {"schema_version": 2, "database_sha256": inputs["data/nutrition.db"],
               "class_names_sha256": inputs["data/food_dataset/data.yaml"], "baseline_sha256": baseline_hash,
               "hash_seed": SEEDS[0], "comparisons": comparisons})
    common = {"schema_version": 1, "run_id": args.run_id, "source_commit": baseline["source_commit"],
              "baseline_sha256": baseline_hash, "input_sha256": inputs, "created_at_utc": datetime.now(timezone.utc).isoformat(),
              "script_sha256": digest(Path(__file__)), "clinical_validity_established": False}
    nutrition_report = {**common, "workbook_rows": len(workbook), "imported_workbook_rows": len(expected) - len(supplements),
        "omitted_workbook_rows": len(omitted), "omissions_by_reason": dict(Counter(row["reason"] for row in omitted)),
        "supplemental_rows": len(supplements), "expected_database_rows": len(expected), "actual_database_rows": len(foods),
        "integrity_check": integrity, "reconciliation_difference_count": len(differences), "numeric_fields_compared": len(expected) * 4,
        "numeric_absolute_tolerance": 1e-9, "invalid_macro_rows": len(invalid), "normalized_name_collisions": collisions,
        "mapping_rows": len(mappings), "canonical_classes": len(names), "dangling_mapping_targets": dangling,
        "coverage_not_accuracy": {method: sum(row[method] is not None for row in comparisons) for method in ("normalized_exact", "automatic_without_precomputed", "current_mapping")},
        "hash_seed_checks": {"seeds": SEEDS, "labels_per_run": len(runs[0]["labels"]), "methods": 2,
                             "changing_method_label_pairs": len(ambiguity),
                             "changing_canonical_pairs": sum(row["label"] in names for row in ambiguity),
                             "changing_current_canonical_pairs": sum(row["label"] in names and row["method"] == "current_mapping" for row in ambiguity),
                             "examples": [{"label": row["label"], "method": row["method"], "matched_names": sorted({str((value or {}).get("name")) for value in row["outcomes"].values()})} for row in ambiguity[:12]]},
        "energy_residuals": {"rows": len(energy), "min_kcal": min(row["residual_kcal"] for row in energy),
                             "max_kcal": max(row["residual_kcal"] for row in energy), "interpretation": "Descriptive 4/4/9 residuals only; no correctness threshold or clinical conclusion."},
        "status": "discrepancies_found" if differences or invalid or dangling or ambiguity else "automated_checks_passed",
        "limitations": ["Supplemental literals are reconciled to the builder, not independently verified against live source pages.",
                        "Mapping coverage and stable behavior do not establish recipe equivalence or clinical correctness.",
                        "Hash-seed checks characterize eight executions; no unobserved-case determinism guarantee."]}
    policy = json.loads((ROOT / "backend/domain/nutrition_policy.json").read_text(encoding="utf-8"))
    print("Running independent rational goal sweep and actual frontend portion arithmetic.", flush=True)
    backend = validate_backend_arithmetic(ROOT, policy)
    payload = {"policy": policy, "fixtures": json.loads((ROOT / "tests/contracts/macro-fixtures.json").read_text(encoding="utf-8")),
               "foods": [{"class": name, "macros": (current[name] or {}).get("macros")} for name in names]}
    write_json(local / "arithmetic-input.json", payload)
    command = ["node", str(ROOT / "frontend/node_modules/tsx/dist/cli.mjs"), str(ROOT / "scripts/test_nutrition_oracle.mjs"), "--input", str(local / "arithmetic-input.json")]
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=True, timeout=180)
    frontend = json.loads(completed.stdout)
    write_json(local / "arithmetic-details.json", {"backend": backend, "frontend": frontend})
    arithmetic_report = {**common, "oracle": "Independent exact rational arithmetic from frozen decimal policy values; ties-to-even integer rounding.",
        "frontend_oracle_script_sha256": digest(ROOT / "scripts/test_nutrition_oracle.mjs"),
        "backend_goal_cases": backend["cases"], "backend_goal_discrepancies": len(backend["differences"]),
        "backend_fixture_cases": backend["fixture_cases"], "backend_fixture_discrepancies": len(backend["fixture_differences"]),
        "frontend": {key: value for key, value in frontend.items() if key not in {"goal_differences", "portion_differences", "fixture_differences"}},
        "status": "discrepancies_found" if backend["differences"] or backend["fixture_differences"] or frontend["goal_difference_count"] or frontend["portion_difference_count"] or frontend["fixture_difference_count"] else "automated_checks_passed",
        "limitations": ["Tests verify implementation arithmetic, not clinical appropriateness of goal weights or condition modifiers.",
                        "UI calorie sweep covers 500 through 5000 inclusive; API currently accepts positive integers below 500 too.",
                        "Nutrient values remain database estimates and portions remain user estimates."]}
    for report, filename, detail in ((nutrition_report, "nutrition-validation.json", "nutrition-details.json"),
                                     (arithmetic_report, "arithmetic-validation.json", "arithmetic-details.json")):
        report["local_detail_sha256"] = digest(local / detail)
        report["local_detail_path"] = (local / detail).relative_to(ROOT).as_posix()
        write_json(reports / filename, report)
    validate_baseline(ROOT, args.run_id)  # Detect concurrent mutation of frozen inputs.
    print(json.dumps({"nutrition": nutrition_report["status"], "arithmetic": arithmetic_report["status"],
                      "reports": str(reports)}, indent=2))


if __name__ == "__main__":
    main()
