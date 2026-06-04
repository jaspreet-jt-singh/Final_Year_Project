#!/usr/bin/env python3
"""Build a merged YOLO master dataset excluding SOHL with safe multilabel stratified splitting.

Pipeline:
1. Load DS1, DS2, DS3, DS4, DS6 only.
2. Normalize labels with unique canonical classes.
3. Create a new global split (70/15/15) using multilabel iterative stratification.
4. Fall back safely if rare-label stratification fails.
5. Export original images with names like train0001-shahi_paneer.jpg.
6. Augment TRAIN only to improve class balance.
7. Keep VALID and TEST untouched.
8. Write per-class counts before and after train augmentation.
"""

from __future__ import annotations

import math
import random
import shutil
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import yaml
from PIL import Image, ImageEnhance, ImageOps
from iterstrat.ml_stratifiers import MultilabelStratifiedShuffleSplit

DATA_ROOT = Path("data")
OUTPUT_DIR = DATA_ROOT / "master_dataset"
LOG_PATH = OUTPUT_DIR / "build_log.txt"
COUNTS_CSV = OUTPUT_DIR / "split_class_counts_before_after.csv"

DATASETS = [
    "Indian food detection.v1i.yolov11",
    "indian food.v6i.yolov11",
    "Indian_food.v2-indianfood-7.yolov11",
    "indianfoodnet_yolo",
    "south indian food detection.v19i.yolov11",
]

TRAIN_RATIO = 0.70
VALID_RATIO = 0.15
TEST_RATIO = 0.15
RANDOM_SEED = 42
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}

CLASS_MAP = {
    "Bhatura": "bhatura",
    "BhindiMasala": "bhindi_masala",
    "Biryani": "biryani",
    "Chole": "chole",
    "ShahiPaneer": "shahi_paneer",
    "chicken": "chicken",
    "dal": "dal",
    "dhokla": "dhokla",
    "gulab_jamun": "gulab_jamun",
    "idli": "idli",
    "jalebi": "jalebi",
    "modak": "modak",
    "palak_paneer": "palak_paneer",
    "poha": "poha",
    "rice": "rice",
    "roti": "roti",
    "samosa": "samosa",
    "aloo gobhi": "aloo_gobi",
    "aloo sabji": "aloo_masala",
    "bhakarwadi": "bhakarwadi",
    "bhakri": "bhakri",
    "bhindi": "bhindi_masala",
    "coconut chutney": "coconut_chutney",
    "daal": "dal",
    "dosa": "dosa",
    "eggs": "eggs",
    "khandvi": "khandvi",
    "medu vada": "medu_vada",
    "omelette": "omelette",
    "paratha": "paratha",
    "puri": "puri",
    "rajma": "rajma_curry",
    "roti phulka": "roti",
    "saag": "saag",
    "salad": "salad",
    "sambhar": "sambar",
    "thepla": "thepla",
    "upma": "upma",
    "varan": "dal",
    "veg-pulao": "veg_pulao",
    "yellow dhokla": "dhokla",
    "yogurt": "raita",
    "besan_cheela": "besan_cheela",
    "AlooGobi": "aloo_gobi",
    "AlooMasala": "aloo_masala",
    "Chai": "chai",
    "CoconutChutney": "coconut_chutney",
    "Dal": "dal",
    "Dosa": "dosa",
    "DumAloo": "dum_aloo",
    "FishCurry": "fish_curry",
    "Ghevar": "ghevar",
    "GreenChutney": "green_chutney",
    "GulabJamun": "gulab_jamun",
    "Idli": "idli",
    "Jalebi": "jalebi",
    "Kebab": "kebab",
    "Kheer": "kheer",
    "Kulfi": "kulfi",
    "Lassi": "lassi",
    "MuttonCurry": "mutton_curry",
    "OnionPakoda": "onion_pakoda",
    "PalakPaneer": "palak_paneer",
    "Poha": "poha",
    "RajmaCurry": "rajma_curry",
    "RasMalai": "ras_malai",
    "Samosa": "samosa",
    "WhiteRice": "rice",
    "appam": "appam",
    "beetroot poriyal": "beetroot_poriyal",
    "boiled egg": "eggs",
    "carrot poriyal": "carrot_poriyal",
    "chicken 65": "chicken_65",
    "chicken briyani": "chicken_biryani",
    "idly": "idli",
    "kaara chutney": "kaara_chutney",
    "kali": "kali",
    "koozh": "koozh",
    "lemon satham": "lemon_rice",
    "medu vadai": "medu_vada",
    "mushroom briyani": "mushroom_biryani",
    "mutton briyani": "mutton_biryani",
    "nandu masala": "nandu_masala",
    "nei satham": "nei_satham",
    "paal kolukattai": "paal_kolukattai",
    "paneer briyani": "paneer_biryani",
    "paneer masala": "shahi_paneer",
    "parupu vadai": "parupu_vadai",
    "pidi kolukattai": "pidi_kolukattai",
    "poorna kolukattai": "poorna_kolukattai",
    "prawn thokku": "prawn_thokku",
    "puthina chutney": "green_chutney",
    "sambar": "sambar",
    "sambar satham": "sambar_satham",
    "satham": "rice",
    "thengai chutney": "coconut_chutney",
    "veg briyani": "veg_briyani",
    "ven pongal": "ven_pongal",
}

@dataclass(frozen=True)
class Sample:
    image_path: Path
    dataset: str
    annotations: tuple[tuple[str, tuple[float, float, float, float]], ...]

def clean_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)

def image_files(directory: Path) -> list[Path]:
    if not directory.exists():
        return []
    return sorted(
        p for p in directory.iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES
    )

def load_class_names(dataset_path: Path) -> list[str] | None:
    yaml_files = sorted(dataset_path.glob("*.yaml")) + sorted(dataset_path.glob("*.yml"))
    if not yaml_files:
        return None
    with yaml_files[0].open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    names = data.get("names")
    if isinstance(names, list):
        return [str(v) for v in names]
    if isinstance(names, dict):
        return [str(names[k]) for k in sorted(names, key=lambda x: int(x))]
    return None

def canonical_class(name: str) -> str:
    mapped = CLASS_MAP.get(name, name)
    mapped = mapped.strip().lower().replace("-", "_").replace(" ", "_")
    while "__" in mapped:
        mapped = mapped.replace("__", "_")
    return mapped

def parse_label(label_path: Path, class_names: list[str]):
    anns = []
    if not label_path.exists() or label_path.stat().st_size == 0:
        return tuple()
    with label_path.open("r", encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            parts = line.strip().split()
            if len(parts) < 5:
                continue
            try:
                cid = int(float(parts[0]))
                bbox = tuple(float(v) for v in parts[1:5])
            except ValueError:
                continue
            if not (0 <= cid < len(class_names)):
                continue
            if any(not math.isfinite(v) for v in bbox):
                continue
            anns.append((canonical_class(class_names[cid]), bbox))
    return tuple(anns)

def collect_samples() -> list[Sample]:
    samples = []
    for dataset in DATASETS:
        dataset_path = DATA_ROOT / dataset
        if not dataset_path.exists():
            continue
        class_names = load_class_names(dataset_path)
        if not class_names:
            continue

        found_structured = False
        for split in ("train", "valid", "test"):
            image_dir = dataset_path / split / "images"
            label_dir = dataset_path / split / "labels"
            files = image_files(image_dir)
            if files:
                found_structured = True
            for image_path in files:
                label_path = label_dir / f"{image_path.stem}.txt"
                anns = parse_label(label_path, class_names)
                if anns:
                    samples.append(Sample(image_path, dataset, anns))

        if not found_structured:
            image_dir = dataset_path / "images"
            label_dir = dataset_path / "labels"
            for image_path in image_files(image_dir):
                label_path = label_dir / f"{image_path.stem}.txt"
                anns = parse_label(label_path, class_names)
                if anns:
                    samples.append(Sample(image_path, dataset, anns))
    return samples

def dominant_class(sample: Sample) -> str:
    counts = Counter(c for c, _ in sample.annotations)
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]

def build_multilabel_matrix(samples: list[Sample], class_names: list[str]) -> np.ndarray:
    class_to_idx = {cls: i for i, cls in enumerate(class_names)}
    y = np.zeros((len(samples), len(class_names)), dtype=int)
    for row_idx, sample in enumerate(samples):
        present = {cls for cls, _ in sample.annotations}
        for cls in present:
            y[row_idx, class_to_idx[cls]] = 1
    return y

def random_fallback_split(samples: list[Sample]):
    samples = samples[:]
    random.shuffle(samples)
    n = len(samples)
    n_train = int(round(n * TRAIN_RATIO))
    n_valid = int(round(n * VALID_RATIO))
    if n_train + n_valid > n:
        n_valid = max(0, n - n_train)
    return {
        "train": samples[:n_train],
        "valid": samples[n_train:n_train + n_valid],
        "test": samples[n_train + n_valid:],
    }

def split_samples(samples: list[Sample], class_names: list[str]):
    if len(samples) < 3:
        return random_fallback_split(samples)

    y = build_multilabel_matrix(samples, class_names)
    X = np.arange(len(samples)).reshape(-1, 1)

    try:
        outer = MultilabelStratifiedShuffleSplit(
            n_splits=1,
            test_size=(VALID_RATIO + TEST_RATIO),
            random_state=RANDOM_SEED,
        )
        train_idx, temp_idx = next(outer.split(X, y))

        temp_samples = [samples[i] for i in temp_idx]
        temp_y = y[temp_idx]
        X_temp = np.arange(len(temp_samples)).reshape(-1, 1)

        if len(temp_samples) < 2:
            return {
                "train": [samples[i] for i in train_idx],
                "valid": temp_samples,
                "test": [],
            }

        inner = MultilabelStratifiedShuffleSplit(
            n_splits=1,
            test_size=(TEST_RATIO / (VALID_RATIO + TEST_RATIO)),
            random_state=RANDOM_SEED,
        )
        valid_rel_idx, test_rel_idx = next(inner.split(X_temp, temp_y))

        split_map = {
            "train": [samples[i] for i in train_idx],
            "valid": [temp_samples[i] for i in valid_rel_idx],
            "test": [temp_samples[i] for i in test_rel_idx],
        }

        if len(split_map["train"]) == 0 or len(split_map["valid"]) == 0:
            return random_fallback_split(samples)

        for split in split_map:
            random.shuffle(split_map[split])

        return split_map

    except ValueError:
        return random_fallback_split(samples)

def write_label(path: Path, annotations, class_to_id):
    with path.open("w", encoding="utf-8") as handle:
        for cls, bbox in annotations:
            x, y, w, h = (max(0.0, min(1.0, v)) for v in bbox)
            handle.write(f"{class_to_id[cls]} {x:.6f} {y:.6f} {w:.6f} {h:.6f}\n")

def class_image_counts(samples: list[Sample]) -> Counter:
    counts = Counter()
    for sample in samples:
        present = {c for c, _ in sample.annotations}
        for cls in present:
            counts[cls] += 1
    return counts

def class_annotation_counts(samples: list[Sample]) -> Counter:
    counts = Counter()
    for sample in samples:
        counts.update(c for c, _ in sample.annotations)
    return counts

def export_original_split(split_name: str, samples: list[Sample], class_to_id: dict[str, int]):
    image_dir = OUTPUT_DIR / split_name / "images"
    label_dir = OUTPUT_DIR / split_name / "labels"
    image_dir.mkdir(parents=True, exist_ok=True)
    label_dir.mkdir(parents=True, exist_ok=True)

    exported = []
    for idx, sample in enumerate(samples, start=1):
        tag = dominant_class(sample)
        ext = sample.image_path.suffix.lower()
        out_name = f"{split_name}{idx:04d}-{tag}{ext}"
        out_image = image_dir / out_name
        out_label = label_dir / f"{Path(out_name).stem}.txt"

        shutil.copy2(sample.image_path, out_image)
        write_label(out_label, sample.annotations, class_to_id)
        exported.append(Sample(out_image, sample.dataset, sample.annotations))
    return exported

def augment_one(sample: Sample, out_image: Path):
    image = Image.open(sample.image_path).convert("RGB")
    annotations = sample.annotations

    if random.random() < 0.5:
        image = ImageOps.mirror(image)
        annotations = tuple((c, (1.0 - b[0], b[1], b[2], b[3])) for c, b in annotations)

    image = ImageEnhance.Brightness(image).enhance(random.uniform(0.9, 1.1))
    image = ImageEnhance.Contrast(image).enhance(random.uniform(0.9, 1.1))
    image.save(out_image, quality=95)
    image.close()
    return annotations

def augment_train_only(train_samples: list[Sample], class_to_id: dict[str, int]):
    image_dir = OUTPUT_DIR / "train" / "images"
    label_dir = OUTPUT_DIR / "train" / "labels"

    ann_counts = class_annotation_counts(train_samples)
    target = max(ann_counts.values()) if ann_counts else 0

    by_class = defaultdict(list)
    for sample in train_samples:
        present = {c for c, _ in sample.annotations}
        for cls in present:
            by_class[cls].append(sample)

    augmented = []
    next_index = len(train_samples) + 1

    for cls in sorted(class_to_id):
        pool = by_class.get(cls, [])
        while pool and ann_counts[cls] < target:
            source = random.choice(pool)
            tag = dominant_class(source)
            out_name = f"train{next_index:04d}-{tag}.jpg"
            out_image = image_dir / out_name
            out_label = label_dir / f"train{next_index:04d}-{tag}.txt"

            annotations = augment_one(source, out_image)
            write_label(out_label, annotations, class_to_id)

            new_sample = Sample(out_image, "augmented", annotations)
            augmented.append(new_sample)
            ann_counts.update(c for c, _ in annotations)
            next_index += 1

    return train_samples + augmented, target

def write_yaml(class_names: list[str]) -> None:
    data = {
        "path": str(OUTPUT_DIR.resolve()),
        "train": "train/images",
        "val": "valid/images",
        "test": "test/images",
        "nc": len(class_names),
        "names": class_names,
    }
    with (OUTPUT_DIR / "data.yaml").open("w", encoding="utf-8") as handle:
        yaml.safe_dump(data, handle, sort_keys=False)

def write_counts_csv(class_names, before, after):
    with COUNTS_CSV.open("w", encoding="utf-8") as handle:
        handle.write(
            "class_name,"
            "train_images_before,train_images_after,train_annotations_before,train_annotations_after,"
            "valid_images_before,valid_images_after,valid_annotations_before,valid_annotations_after,"
            "test_images_before,test_images_after,test_annotations_before,test_annotations_after\n"
        )
        for cls in class_names:
            handle.write(
                f"{cls},"
                f"{before['train']['images'][cls]},{after['train']['images'][cls]},{before['train']['annotations'][cls]},{after['train']['annotations'][cls]},"
                f"{before['valid']['images'][cls]},{after['valid']['images'][cls]},{before['valid']['annotations'][cls]},{after['valid']['annotations'][cls]},"
                f"{before['test']['images'][cls]},{after['test']['images'][cls]},{before['test']['annotations'][cls]},{after['test']['annotations'][cls]}\n"
            )

def main():
    if abs(TRAIN_RATIO + VALID_RATIO + TEST_RATIO - 1.0) > 1e-9:
        raise ValueError("Split ratios must sum to 1.0")

    random.seed(RANDOM_SEED)
    np.random.seed(RANDOM_SEED)

    clean_dir(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    raw_samples = collect_samples()
    if not raw_samples:
        raise RuntimeError("No annotated YOLO samples found.")

    class_names = sorted({c for s in raw_samples for c, _ in s.annotations})
    class_to_id = {c: i for i, c in enumerate(class_names)}

    split_map = split_samples(raw_samples, class_names)

    before = {
        split: {
            "images": class_image_counts(split_map[split]),
            "annotations": class_annotation_counts(split_map[split]),
        }
        for split in ("train", "valid", "test")
    }

    exported = {
        split: export_original_split(split, split_map[split], class_to_id)
        for split in ("train", "valid", "test")
    }

    exported["train"], train_target = augment_train_only(exported["train"], class_to_id)

    after = {
        split: {
            "images": class_image_counts(exported[split]),
            "annotations": class_annotation_counts(exported[split]),
        }
        for split in ("train", "valid", "test")
    }

    write_yaml(class_names)
    write_counts_csv(class_names, before, after)

    with LOG_PATH.open("w", encoding="utf-8") as handle:
        handle.write("Merged dataset build complete\n")
        handle.write(f"Total classes: {len(class_names)}\n")
        handle.write(f"Universal split ratio: {TRAIN_RATIO:.2f}/{VALID_RATIO:.2f}/{TEST_RATIO:.2f}\n")
        handle.write(f"Train augmentation target annotations per class: {train_target}\n\n")
        for split in ("train", "valid", "test"):
            handle.write(f"[{split}]\n")
            for cls in class_names:
                handle.write(
                    f"{cls}: before_images={before[split]['images'][cls]}, after_images={after[split]['images'][cls]}, "
                    f"before_annotations={before[split]['annotations'][cls]}, after_annotations={after[split]['annotations'][cls]}\n"
                )
            handle.write("\n")

if __name__ == "__main__":
    main()