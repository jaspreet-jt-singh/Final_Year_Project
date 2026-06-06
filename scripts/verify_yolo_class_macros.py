#!/usr/bin/env python3
"""Verify macro availability and mapping quality for YOLO dataset classes."""

from __future__ import annotations

import csv
import sqlite3
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET_YAML = PROJECT_ROOT / "data" / "food_dataset" / "data.yaml"
NUTRITION_DB = PROJECT_ROOT / "data" / "nutrition.db"
OUTPUT_DIR = PROJECT_ROOT / "data" / "nutrition_verification"
CSV_REPORT = OUTPUT_DIR / "yolo_class_macro_verification.csv"
MD_REPORT = OUTPUT_DIR / "yolo_class_macro_verification.md"


DIRECT_MATCH_SCORE = 1.0
GOOD_MATCH_SCORE = 0.90
LOW_CONFIDENCE_SCORE = 0.80
MAX_REASONABLE_KCAL_PER_100G = 900.0
MAX_KCAL_DELTA_ABS = 30.0
MAX_KCAL_DELTA_RATIO = 0.20


@dataclass(frozen=True)
class MacroRecord:
    yolo_class: str
    db_name: str | None
    match_score: float | None
    calories: float | None
    protein_g: float | None
    carbs_g: float | None
    fat_g: float | None
    source: str | None
    source_url: str | None
    source_notes: str | None

    @property
    def macro_kcal(self) -> float | None:
        if self.protein_g is None or self.carbs_g is None or self.fat_g is None:
            return None
        return (self.protein_g * 4.0) + (self.carbs_g * 4.0) + (self.fat_g * 9.0)

    @property
    def kcal_delta(self) -> float | None:
        if self.calories is None or self.macro_kcal is None:
            return None
        return self.calories - self.macro_kcal


def load_dataset_class_names(path: Path) -> list[str]:
    if not path.exists():
        raise FileNotFoundError(f"Dataset YAML not found: {path}")

    class_names: list[str] = []
    in_names = False

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped == "names:":
            in_names = True
            continue
        if not in_names:
            continue
        if stripped.startswith("- "):
            class_name = stripped[2:].strip().strip("'\"")
            if class_name:
                class_names.append(class_name)
            continue
        if class_names:
            break

    if not class_names:
        raise ValueError(f"No class names found in {path}")
    return class_names


def load_macro_records(class_names: list[str]) -> list[MacroRecord]:
    if not NUTRITION_DB.exists():
        raise FileNotFoundError(f"Nutrition database not found: {NUTRITION_DB}")

    query = """
        SELECT
            y.yolo_class,
            y.matched_food_name,
            y.match_score,
            f.calories,
            f.protein_g,
            f.carbs_g,
            f.fat_g,
            f.source,
            f.source_url,
            f.source_notes
        FROM yolo_mappings AS y
        LEFT JOIN indb_foods AS f
            ON f.name = y.matched_food_name
        WHERE y.yolo_class = ?
    """

    records: list[MacroRecord] = []
    with sqlite3.connect(NUTRITION_DB) as conn:
        cursor = conn.cursor()
        for class_name in class_names:
            cursor.execute(query, (class_name,))
            row = cursor.fetchone()
            if row is None:
                records.append(
                    MacroRecord(
                        yolo_class=class_name,
                        db_name=None,
                        match_score=None,
                        calories=None,
                        protein_g=None,
                        carbs_g=None,
                        fat_g=None,
                        source=None,
                        source_url=None,
                        source_notes=None,
                    )
                )
                continue

            records.append(
                MacroRecord(
                    yolo_class=row[0],
                    db_name=row[1],
                    match_score=float(row[2]) if row[2] is not None else None,
                    calories=float(row[3]) if row[3] is not None else None,
                    protein_g=float(row[4]) if row[4] is not None else None,
                    carbs_g=float(row[5]) if row[5] is not None else None,
                    fat_g=float(row[6]) if row[6] is not None else None,
                    source=row[7],
                    source_url=row[8],
                    source_notes=row[9],
                )
            )
    return records


def classify_record(record: MacroRecord) -> tuple[str, str]:
    if record.db_name is None:
        return "FAIL", "No YOLO mapping row."

    missing_fields = [
        name
        for name, value in [
            ("calories", record.calories),
            ("protein_g", record.protein_g),
            ("carbs_g", record.carbs_g),
            ("fat_g", record.fat_g),
        ]
        if value is None
    ]
    if missing_fields:
        return "FAIL", f"Missing macro fields: {', '.join(missing_fields)}."

    assert record.calories is not None
    assert record.protein_g is not None
    assert record.carbs_g is not None
    assert record.fat_g is not None

    if min(record.calories, record.protein_g, record.carbs_g, record.fat_g) < 0:
        return "FAIL", "Negative macro value present."

    if record.calories > MAX_REASONABLE_KCAL_PER_100G:
        return "REVIEW", "Calories exceed the expected food range for per-100g values."

    if record.kcal_delta is not None:
        delta_abs = abs(record.kcal_delta)
        delta_ratio = delta_abs / max(record.calories, 1.0)
        if delta_abs > MAX_KCAL_DELTA_ABS and delta_ratio > MAX_KCAL_DELTA_RATIO:
            return "REVIEW", "Calorie value differs materially from protein/carb/fat-derived kcal."

    if record.match_score is None:
        return "REVIEW", "Mapping score missing."

    if record.match_score >= DIRECT_MATCH_SCORE:
        return "VERIFIED", "Direct class-to-food mapping with complete per-100g macros."

    if record.match_score >= GOOD_MATCH_SCORE:
        return "VERIFIED", "High-confidence semantic mapping with complete per-100g macros."

    if record.match_score >= LOW_CONFIDENCE_SCORE:
        return "REVIEW", "Acceptable substitute mapping; verify against project scope."

    return "REVIEW", "Low-confidence substitute mapping; keep documented as an approximation."


def format_float(value: float | None, digits: int = 2) -> str:
    if value is None:
        return ""
    return f"{value:.{digits}f}"


def write_csv(records: list[MacroRecord]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with CSV_REPORT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "yolo_class",
                "mapped_database_name",
                "match_score",
                "calories_per_100g",
                "protein_g_per_100g",
                "carbs_g_per_100g",
                "fat_g_per_100g",
                "macro_calculated_kcal",
                "kcal_minus_macro_kcal",
                "source",
                "source_url",
                "status",
                "verification_note",
            ]
        )
        for record in records:
            status, note = classify_record(record)
            writer.writerow(
                [
                    record.yolo_class,
                    record.db_name or "",
                    format_float(record.match_score),
                    format_float(record.calories, 1),
                    format_float(record.protein_g, 2),
                    format_float(record.carbs_g, 2),
                    format_float(record.fat_g, 2),
                    format_float(record.macro_kcal, 1),
                    format_float(record.kcal_delta, 1),
                    record.source or "",
                    record.source_url or "",
                    status,
                    note,
                ]
            )


def write_markdown(records: list[MacroRecord]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    status_counts: dict[str, int] = {}
    for record in records:
        status, _ = classify_record(record)
        status_counts[status] = status_counts.get(status, 0) + 1

    lines = [
        "# YOLO Class Macro Verification",
        "",
        "Generated from `data/food_dataset/data.yaml` and `data/nutrition.db`.",
        "All values are per 100g. `Macro kcal` is calculated as protein*4 + carbs*4 + fat*9 and is included as a consistency aid, not as a replacement for the database calorie field.",
        "",
        "## Summary",
        "",
        f"- Dataset classes checked: {len(records)}",
        f"- Verified mappings: {status_counts.get('VERIFIED', 0)}",
        f"- Review mappings: {status_counts.get('REVIEW', 0)}",
        f"- Failed mappings: {status_counts.get('FAIL', 0)}",
        "",
        "## Class-by-Class Results",
        "",
        "| YOLO class | Database name | Score | kcal | Protein | Carbs | Fat | Macro kcal | Delta | Source | Status | Note |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|---|",
    ]

    for record in records:
        status, note = classify_record(record)
        source = record.source or ""
        if record.source_url:
            source = f"{source} ({record.source_url})"
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{record.yolo_class}`",
                    f"`{record.db_name}`" if record.db_name else "",
                    format_float(record.match_score),
                    format_float(record.calories, 1),
                    format_float(record.protein_g, 2),
                    format_float(record.carbs_g, 2),
                    format_float(record.fat_g, 2),
                    format_float(record.macro_kcal, 1),
                    format_float(record.kcal_delta, 1),
                    source.replace("|", "\\|"),
                    status,
                    note.replace("|", "\\|"),
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Review Notes",
            "",
            "- `VERIFIED` means the class has a direct or high-confidence semantic mapping and complete per-100g macro fields.",
            "- `REVIEW` means the macro fields are present, but the mapped database row is a substitute or lower-confidence semantic approximation.",
            "- `FAIL` means the class is missing a mapping or one of the required macro fields.",
            "- Supplemental rows retain source URLs in the database and in this report.",
        ]
    )

    MD_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    class_names = load_dataset_class_names(DATASET_YAML)
    records = load_macro_records(class_names)
    write_csv(records)
    write_markdown(records)

    status_counts: dict[str, int] = {}
    for record in records:
        status, _ = classify_record(record)
        status_counts[status] = status_counts.get(status, 0) + 1

    print(f"Checked {len(records)} YOLO dataset classes")
    print(f"VERIFIED: {status_counts.get('VERIFIED', 0)}")
    print(f"REVIEW: {status_counts.get('REVIEW', 0)}")
    print(f"FAIL: {status_counts.get('FAIL', 0)}")
    print(f"Wrote {CSV_REPORT.relative_to(PROJECT_ROOT)}")
    print(f"Wrote {MD_REPORT.relative_to(PROJECT_ROOT)}")
    return 1 if status_counts.get("FAIL", 0) else 0


if __name__ == "__main__":
    raise SystemExit(main())
