#!/usr/bin/env python3
"""
Build the SQLite nutrition database from INDB.xlsx.

The script imports INDB nutrition rows and precomputes YOLO class to INDB food
mappings. Dataset classes from data/food_dataset/data.yaml are preferred, with
models/class_names.json appended for backward compatibility with older weights.
"""

import json
import os
import sqlite3
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.food_normalizer import find_best_match, normalize_food_name


MIN_FUZZY_MAPPING_SCORE = 0.78

SUPPLEMENTAL_NUTRITION_ROWS: list[dict[str, object]] = [
    {
        "name": "Bhakarwadi",
        "calories": 510.0,
        "protein_g": 10.76,
        "carbs_g": 57.03,
        "fat_g": 26.55,
        "source": "Supplemental: FatSecret Evolve Bhakarwadi nutrition label",
        "source_url": "https://www.fatsecret.co.in/calories-nutrition/evolve/bhakarwadi/100g",
        "source_notes": "Per 100 g product nutrition facts; used because INDB has no Bhakarwadi row.",
    },
    {
        "name": "Ghevar",
        "calories": 351.2,
        "protein_g": 3.5,
        "carbs_g": 39.6,
        "fat_g": 19.9,
        "source": "Supplemental: Clearcals Ghevar recipe nutrition",
        "source_url": "https://clearcals.com/recipes/ghevar/",
        "source_notes": "Per 100 g prepared recipe nutrition; used because INDB has no Ghevar row.",
    },
    {
        "name": "Jalebi",
        "calories": 316.8,
        "protein_g": 3.4,
        "carbs_g": 44.6,
        "fat_g": 13.8,
        "source": "Supplemental: Clearcals Jalebi recipe nutrition",
        "source_url": "https://clearcals.com/recipes/jalebi/",
        "source_notes": "Per 100 g prepared recipe nutrition; used because INDB has no Jalebi row.",
    },
    {
        "name": "Khandvi",
        "calories": 232.7,
        "protein_g": 9.3,
        "carbs_g": 21.7,
        "fat_g": 12.1,
        "source": "Supplemental: Clearcals Khandvi recipe nutrition",
        "source_url": "https://clearcals.com/recipes/khandvi/",
        "source_notes": "Per 100 g prepared recipe nutrition; used because INDB has no Khandvi row.",
    },
    {
        "name": "Nandu Kari (Crab masala)",
        "calories": 128.1,
        "protein_g": 7.0,
        "carbs_g": 7.0,
        "fat_g": 8.0,
        "source": "Supplemental: Clearcals Nandu Kari recipe nutrition",
        "source_url": "https://clearcals.com/recipes/nandu-kari/",
        "source_notes": "Per 100 g prepared crab curry/masala nutrition; used for nandu_masala because INDB has no Nandu Masala row.",
    },
]

# Manual mappings are used before fuzzy matching so that dish labels map to
# semantically appropriate INDB rows instead of high-scoring but wrong strings.
# Scores below 1.0 indicate the nearest available INDB substitute.
MANUAL_CLASS_MAPPINGS: dict[str, tuple[str, float]] = {
    "aloo_gobi": ("Potato cauliflower (Aloo gobhi)", 1.00),
    "aloo_masala": ("Potato curry (Aloo ki sabzi)", 0.90),
    "appam": ("Appam", 1.00),
    "beetroot_poriyal": ("Vegetables stir fry", 0.75),
    "besan_cheela": ("Gram flour chilla/cheela (Besan chilla/cheela)", 1.00),
    "bhakarwadi": ("Bhakarwadi", 1.00),
    "bhakri": ("Chapati/Roti", 0.80),
    "bhatura": ("Bhatura", 1.00),
    "bhindi_masala": ("Okra/Lady's fingers fry (Bhindi sabzi/sabji/subji)", 0.95),
    "biryani": ("Vegetable biryani/biriyani", 0.85),
    "carrot_poriyal": ("Carrot and cabbage with coconut (Nariyal ke saath pattagobhi aur gajar)", 0.85),
    "chai": ("Hot tea (Garam Chai)", 1.00),
    "chicken": ("Chicken curry", 0.85),
    "chicken_65": ("Chilli chicken", 0.80),
    "chicken_biryani": ("Chicken pulao", 0.80),
    "chole": ("Chickpeas curry (Safed channa curry)", 1.00),
    "coconut_chutney": ("Coconut chutney (Nariyal ki chutney)", 1.00),
    "dal": ("Mixed dal", 0.90),
    "dhokla": ("Dhokla", 1.00),
    "dosa": ("Plain dosa", 0.95),
    "dum_aloo": ("Dum aloo", 1.00),
    "eggs": ("Boiled egg (Ubla anda)", 0.95),
    "fish_curry": ("Fish curry (Machli curry)", 1.00),
    "ghevar": ("Ghevar", 1.00),
    "green_chutney": ("Green chutney", 1.00),
    "gulab_jamun": ("Gulab Jamun with khoya", 1.00),
    "idli": ("Idli", 1.00),
    "jalebi": ("Jalebi", 1.00),
    "kaara_chutney": ("Tomato chutney (Tamatar ki chutney)", 0.85),
    "kali": ("Maize porridge", 0.70),
    "kebab": ("Boti kebab", 0.90),
    "khandvi": ("Khandvi", 1.00),
    "kheer": ("Rice kheer (Chawal ki kheer)", 1.00),
    "koozh": ("Maize porridge", 0.70),
    "kulfi": ("Kulfi", 1.00),
    "lassi": ("Sweet Lassi (Meethi lassi)", 0.95),
    "lemon_rice": ("Lemon rice (Pulihora, Elumichai sadam, Chitranna)", 1.00),
    "medu_vada": ("Plain urad dal vada (Uzunne vada/Minapa garelu/Ulundu vadai/Medu vada)", 1.00),
    "modak": ("Semolina ladoo with coconut (Suji/Rava aur nariyal ke ladoo )", 0.70),
    "mushroom_biryani": ("Mushroom pulao", 0.80),
    "mutton_biryani": ("Mutton biryani/biriyani", 1.00),
    "mutton_curry": ("Mutton korma", 0.85),
    "nandu_masala": ("Nandu Kari (Crab masala)", 1.00),
    "nei_satham": ("Plain pulao", 0.80),
    "omelette": ("Plain omelette/omlet", 1.00),
    "onion_pakoda": ("Onion pakora/pakoda (Pyaaz ke pakode)", 1.00),
    "paal_kolukattai": ("Rice kheer (Chawal ki kheer)", 0.75),
    "palak_paneer": ("Spinach paneer (Palak paneer)", 1.00),
    "paneer_biryani": ("Paneer pulao", 0.80),
    "paratha": ("Plain parantha/paratha", 0.95),
    "parupu_vadai": ("Fermented bengal gram vada (Khameerikrit/Ufna hua channa dal ka vada)", 0.90),
    "pidi_kolukattai": ("Rice puttu (Ari puttu)", 0.75),
    "poha": ("Poha", 1.00),
    "poorna_kolukattai": ("Semolina ladoo with coconut (Suji/Rava aur nariyal ke ladoo )", 0.70),
    "prawn_thokku": ("Prawn curry (with coconut) (Jhinga curry)", 0.85),
    "puri": ("Poori", 1.00),
    "raita": ("Cucumber raita (Kheere ka raita)", 0.90),
    "rajma_curry": ("Kidney bean curry (Rajmah curry)", 1.00),
    "ras_malai": ("Rasmalai", 1.00),
    "rice": ("Boiled rice (Uble chawal)", 1.00),
    "roti": ("Chapati/Roti", 1.00),
    "saag": ("Sarson ka saag", 1.00),
    "salad": ("Tossed salad", 0.90),
    "sambar": ("Sambar", 1.00),
    "sambar_satham": ("Vegetable khichdi/khichri", 0.80),
    "samosa": ("Potato samosa (Aloo ka samosa)", 1.00),
    "shahi_paneer": ("Shahi paneer", 1.00),
    "thepla": ("Methi thepla", 0.95),
    "upma": ("Semolina upma (Suji/Rava upma)", 0.95),
    "veg_briyani": ("Vegetable biryani/biriyani", 1.00),
    "veg_pulao": ("Mixed vegetable pulao", 1.00),
    "ven_pongal": ("Plain khitchdi (Plain khichri/khichdi)", 0.75),
    # Legacy deployed-model label not present in the 72-class dataset.
    "vada_pav": ("Potato bonda (Aloo bonda)", 0.75),
    "white_rice": ("Boiled rice (Uble chawal)", 1.00),
}

MANUAL_BY_NORMALIZED_CLASS = {
    normalize_food_name(class_name): mapping
    for class_name, mapping in MANUAL_CLASS_MAPPINGS.items()
}


def load_dataset_class_names(dataset_yaml_path: Path) -> list[str]:
    """Load the simple YOLO data.yaml names list without requiring PyYAML."""
    if not dataset_yaml_path.exists():
        return []

    class_names: list[str] = []
    in_names = False

    for raw_line in dataset_yaml_path.read_text(encoding="utf-8").splitlines():
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

    return class_names


def load_model_class_names(model_class_path: Path) -> list[str]:
    if not model_class_path.exists():
        return []

    with model_class_path.open("r", encoding="utf-8") as handle:
        class_names = json.load(handle)

    if not isinstance(class_names, list):
        raise ValueError(f"Expected a class-name list in {model_class_path}")

    return [str(class_name) for class_name in class_names]


def load_yolo_class_names(project_root: Path) -> list[str]:
    dataset_path = project_root / "data" / "food_dataset" / "data.yaml"
    model_path = project_root / "models" / "class_names.json"

    sources = [
        ("dataset", dataset_path, load_dataset_class_names(dataset_path)),
        ("model", model_path, load_model_class_names(model_path)),
    ]

    class_names: list[str] = []
    seen: set[str] = set()

    for source_name, source_path, source_classes in sources:
        if source_classes:
            print(f"Loaded {len(source_classes)} YOLO classes from {source_path} ({source_name})")
        else:
            print(f"No YOLO classes loaded from {source_path} ({source_name})")

        for class_name in source_classes:
            if class_name not in seen:
                class_names.append(class_name)
                seen.add(class_name)

    return class_names


def resolve_db_food_name(target_name: str, db_foods: dict[str, str]) -> str | None:
    if target_name in db_foods:
        return target_name

    target_normalized = normalize_food_name(target_name)
    for db_name, db_normalized in db_foods.items():
        if db_normalized == target_normalized:
            return db_name

    return None


def resolve_class_mapping(
    yolo_class: str,
    db_foods: dict[str, str],
) -> tuple[str | None, float, str]:
    manual_mapping = MANUAL_BY_NORMALIZED_CLASS.get(normalize_food_name(yolo_class))
    if manual_mapping:
        target_name, score = manual_mapping
        resolved_name = resolve_db_food_name(target_name, db_foods)
        if resolved_name:
            return resolved_name, score, "manual"
        print(f"  WARNING: manual target not found for {yolo_class}: {target_name}")

    matched_name, score = find_best_match(yolo_class, list(db_foods.keys()))
    if matched_name and score >= MIN_FUZZY_MAPPING_SCORE:
        return matched_name, score, "fuzzy"

    return None, 0.0, "unmapped"


def main():
    try:
        project_root = Path(__file__).parent.parent.parent
        os.chdir(project_root)

        print("=== Data Foundation - merge_db.py ===")

        print("Step A: Loading INDB.xlsx from the 'Nutrient Data' sheet...")
        df = pd.read_excel("data/INDB.xlsx", sheet_name="Nutrient Data")
        print(f"INDB shape: {df.shape}")
        print(f"INDB columns: {df.columns.tolist()}")

        print("\nStep B: Verifying required nutrition columns...")
        required_columns = ["food_name", "energy_kcal", "protein_g", "carb_g", "fat_g"]
        available_columns = [col for col in required_columns if col in df.columns]

        if len(available_columns) != len(required_columns):
            print(f"ERROR: Missing columns. Required: {required_columns}")
            print(f"ERROR: Available: {available_columns}")
            return False

        print(f"All required columns found: {available_columns}")

        print("\nStep C: Cleaning and preparing data...")

        df_clean = df[required_columns].copy()
        df_clean = df_clean.rename(
            columns={
                "food_name": "name",
                "energy_kcal": "calories",
                "carb_g": "carbs_g",
            }
        )

        print("Normalizing food names for better matching...")
        df_clean["normalized_name"] = df_clean["name"].apply(normalize_food_name)
        df_clean["source"] = "INDB"
        df_clean["source_url"] = ""
        df_clean["source_notes"] = "Imported from data/INDB.xlsx Nutrient Data sheet."

        initial_count = len(df_clean)
        df_clean = df_clean.drop_duplicates(subset=["normalized_name"], keep="first")
        dedup_count = len(df_clean)
        if initial_count != dedup_count:
            print(f"Removed {initial_count - dedup_count} duplicate foods by normalized name")

        for col in ["calories", "protein_g", "carbs_g", "fat_g"]:
            df_clean[col] = pd.to_numeric(df_clean[col], errors="coerce")

        initial_count = len(df_clean)
        df_clean = df_clean.dropna(subset=["calories", "protein_g", "carbs_g", "fat_g"])
        final_count = len(df_clean)

        print(f"Filtered from {initial_count} to {final_count} food items with complete nutrition data")

        print("\nAdding verified supplemental nutrition rows missing from INDB...")
        supplemental_df = pd.DataFrame(SUPPLEMENTAL_NUTRITION_ROWS)
        supplemental_df["normalized_name"] = supplemental_df["name"].apply(normalize_food_name)
        df_clean = pd.concat([df_clean, supplemental_df], ignore_index=True)
        df_clean = df_clean.drop_duplicates(subset=["normalized_name"], keep="first")
        print(f"Added {len(supplemental_df)} supplemental rows; total foods now {len(df_clean)}")

        print("\nStep D: YOLO-relevant foods found:")
        yolo_keywords = sorted(
            {
                token
                for class_name in MANUAL_CLASS_MAPPINGS
                for token in class_name.split("_")
                if len(token) >= 3
            }
        )

        yolo_foods = []
        for _, row in df_clean.iterrows():
            food_name = str(row["name"]).lower()
            if any(keyword in food_name for keyword in yolo_keywords):
                yolo_foods.append(
                    {
                        "name": row["name"],
                        "calories": row["calories"],
                        "protein_g": row["protein_g"],
                        "carbs_g": row["carbs_g"],
                        "fat_g": row["fat_g"],
                    }
                )

        print(f"Found {len(yolo_foods)} YOLO-relevant foods:")
        for food in yolo_foods[:10]:
            print(
                f"  {food['name']:40} "
                f"{food['calories']:3.0f} cal, "
                f"{food['protein_g']:4.1f}g P, "
                f"{food['carbs_g']:4.1f}g C, "
                f"{food['fat_g']:4.1f}g F"
            )
        if len(yolo_foods) > 10:
            print(f"  ... and {len(yolo_foods) - 10} more")

        print("\nStep E: Creating SQLite database...")

        if os.path.exists("data/nutrition.db"):
            os.remove("data/nutrition.db")
            print("Removed existing nutrition.db")

        conn = sqlite3.connect("data/nutrition.db", check_same_thread=False)
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE indb_foods (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                normalized_name TEXT NOT NULL,
                calories REAL,
                protein_g REAL,
                carbs_g REAL,
                fat_g REAL,
                source TEXT NOT NULL DEFAULT 'INDB',
                source_url TEXT,
                source_notes TEXT
            )
            """
        )

        cursor.execute("CREATE INDEX idx_normalized ON indb_foods(normalized_name)")

        df_insert = df_clean[
            [
                "name",
                "normalized_name",
                "calories",
                "protein_g",
                "carbs_g",
                "fat_g",
                "source",
                "source_url",
                "source_notes",
            ]
        ]
        df_insert.to_sql("indb_foods", conn, if_exists="append", index=False)

        print("\nCreating YOLO class mappings...")
        yolo_classes = load_yolo_class_names(project_root)
        dataset_classes = load_dataset_class_names(project_root / "data" / "food_dataset" / "data.yaml")

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS yolo_mappings (
                yolo_class TEXT PRIMARY KEY,
                matched_food_name TEXT,
                match_score REAL,
                FOREIGN KEY (matched_food_name) REFERENCES indb_foods(name)
            )
            """
        )

        cursor.execute("SELECT name, normalized_name FROM indb_foods")
        db_foods = {row[0]: row[1] for row in cursor.fetchall()}

        mapped_count = 0
        method_counts = {"manual": 0, "fuzzy": 0, "unmapped": 0}
        mapped_classes: set[str] = set()
        unmapped_classes: list[str] = []

        for yolo_class in yolo_classes:
            matched_name, score, method = resolve_class_mapping(yolo_class, db_foods)
            method_counts[method] += 1

            if matched_name:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO yolo_mappings (yolo_class, matched_food_name, match_score)
                    VALUES (?, ?, ?)
                    """,
                    (yolo_class, matched_name, score),
                )
                mapped_count += 1
                mapped_classes.add(yolo_class)
                print(f"  OK [{method:6}] {yolo_class} -> {matched_name} (score: {score:.2f})")
            else:
                unmapped_classes.append(yolo_class)
                print(f"  -- [unmapped] {yolo_class} -> No safe INDB match")

        print(f"\nMapped {mapped_count}/{len(yolo_classes)} YOLO classes to database foods")
        print(f"Mapping methods: manual={method_counts['manual']}, fuzzy={method_counts['fuzzy']}, unmapped={method_counts['unmapped']}")
        if dataset_classes:
            dataset_unmapped = [class_name for class_name in dataset_classes if class_name not in mapped_classes]
            print(f"Dataset class coverage: {len(dataset_classes) - len(dataset_unmapped)}/{len(dataset_classes)}")
            if dataset_unmapped:
                print(f"Dataset classes without safe INDB rows: {', '.join(dataset_unmapped)}")
        if unmapped_classes:
            print(f"Unmapped classes: {', '.join(unmapped_classes)}")

        cursor.execute("SELECT COUNT(*) FROM indb_foods")
        count = cursor.fetchone()[0]
        print(f"Inserted {count} food items into indb_foods")

        cursor.execute("SELECT name, normalized_name, calories, protein_g, carbs_g, fat_g, source FROM indb_foods LIMIT 10")
        sample = cursor.fetchall()
        print("\nSample data from database:")
        for row in sample:
            print(f"  {row[0]:35} | {row[1]:25} | {row[2]:3.0f} cal | {row[6]}")

        cursor.execute("SELECT calories, protein_g, carbs_g, fat_g FROM indb_foods")
        all_data = cursor.fetchall()

        if all_data:
            calories = [row[0] for row in all_data]
            proteins = [row[1] for row in all_data]
            carbs = [row[2] for row in all_data]
            fats = [row[3] for row in all_data]

            print("\nNutrition Statistics (per 100g):")
            print(f"Calories: min={min(calories):.0f}, max={max(calories):.0f}, avg={sum(calories)/len(calories):.0f}")
            print(f"Protein:  min={min(proteins):.1f}, max={max(proteins):.1f}, avg={sum(proteins)/len(proteins):.1f}")
            print(f"Carbs:    min={min(carbs):.1f}, max={max(carbs):.1f}, avg={sum(carbs)/len(carbs):.1f}")
            print(f"Fat:      min={min(fats):.1f}, max={max(fats):.1f}, avg={sum(fats)/len(fats):.1f}")

        conn.commit()
        conn.close()

        print("\nmerge_db.py completed successfully")
        print("Database created: data/nutrition.db")
        print(f"Table: indb_foods with {count} rows")
        print(f"Table: yolo_mappings with {mapped_count} rows")
        print(f"Found {len(yolo_foods)} YOLO-relevant foods")

        return True

    except Exception as e:
        print(f"ERROR in merge_db.py: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
