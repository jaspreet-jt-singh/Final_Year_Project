#!/usr/bin/env python3
"""
Create visual contact sheets for checking YOLO food class names against images.

The exported dataset filenames include the dominant canonical class
(`valid0001-idli.jpg`, for example). This script groups images by that suffix,
parses only the selected samples' YOLO labels for object crops, and writes page
images plus a CSV index. Validation/test samples are preferred before train
samples so the review mostly uses non-augmented images.
"""

from __future__ import annotations

import argparse
import csv
import math
import random
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".bmp", ".webp")
SPLIT_ORDER = ("valid", "test", "train")


@dataclass(frozen=True)
class Sample:
    class_id: int
    class_name: str
    split: str
    image_path: Path
    label_path: Path
    bbox: tuple[float, float, float, float] | None


def load_class_names(data_yaml: Path) -> list[str]:
    class_names: list[str] = []
    in_names = False

    for raw_line in data_yaml.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        if stripped == "names:":
            in_names = True
            continue

        if in_names and stripped.startswith("- "):
            class_names.append(stripped[2:].strip().strip("'\""))
        elif in_names and class_names:
            break

    return class_names


def class_from_image_stem(stem: str) -> str | None:
    if "-" not in stem:
        return None
    return stem.split("-", 1)[1]


def find_bbox_for_class(label_path: Path, class_id: int) -> tuple[float, float, float, float] | None:
    if not label_path.exists():
        return None

    for raw_line in label_path.read_text(encoding="utf-8").splitlines():
        parts = raw_line.strip().split()
        if len(parts) != 5:
            continue

        try:
            current_class_id = int(parts[0])
            bbox = tuple(float(value) for value in parts[1:5])
        except ValueError:
            continue

        if current_class_id == class_id:
            return bbox

    return None


def collect_samples(dataset_dir: Path, class_names: list[str]) -> dict[int, list[Sample]]:
    class_to_id = {class_name: class_id for class_id, class_name in enumerate(class_names)}
    samples_by_class = {class_id: [] for class_id in range(len(class_names))}

    for split in SPLIT_ORDER:
        images_dir = dataset_dir / split / "images"
        labels_dir = dataset_dir / split / "labels"
        if not images_dir.exists():
            continue

        image_paths = sorted(path for path in images_dir.iterdir() if path.suffix.lower() in IMAGE_EXTENSIONS)
        for image_path in image_paths:
            class_name = class_from_image_stem(image_path.stem)
            if class_name not in class_to_id:
                continue

            class_id = class_to_id[class_name]
            label_path = labels_dir / f"{image_path.stem}.txt"
            samples_by_class[class_id].append(
                Sample(
                    class_id=class_id,
                    class_name=class_name,
                    split=split,
                    image_path=image_path,
                    label_path=label_path,
                    bbox=None,
                )
            )

    return samples_by_class


def choose_samples(
    samples_by_class: dict[int, list[Sample]],
    samples_per_class: int,
    seed: int,
) -> dict[int, list[Sample]]:
    rng = random.Random(seed)
    chosen: dict[int, list[Sample]] = {}

    for class_id, samples in samples_by_class.items():
        if len(samples) <= samples_per_class:
            chosen[class_id] = samples
            continue

        chosen[class_id] = sorted(
            rng.sample(samples, samples_per_class),
            key=lambda sample: (SPLIT_ORDER.index(sample.split), sample.image_path.name),
        )

    return chosen


def load_font(size: int) -> ImageFont.ImageFont:
    for name in ("arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def crop_sample(sample: Sample, crop_size: int) -> Image.Image:
    image = Image.open(sample.image_path).convert("RGB")
    bbox = sample.bbox or find_bbox_for_class(sample.label_path, sample.class_id)
    if bbox is None:
        return ImageOps.contain(image, (crop_size, crop_size), Image.Resampling.LANCZOS)

    width, height = image.size
    x_center, y_center, box_width, box_height = bbox

    left = (x_center - box_width / 2) * width
    top = (y_center - box_height / 2) * height
    right = (x_center + box_width / 2) * width
    bottom = (y_center + box_height / 2) * height

    pad_x = (right - left) * 0.18
    pad_y = (bottom - top) * 0.18
    left = max(0, int(left - pad_x))
    top = max(0, int(top - pad_y))
    right = min(width, int(right + pad_x))
    bottom = min(height, int(bottom + pad_y))

    if right <= left or bottom <= top:
        crop = image
    else:
        crop = image.crop((left, top, right, bottom))

    return ImageOps.contain(crop, (crop_size, crop_size), Image.Resampling.LANCZOS)


def draw_text_fit(
    draw: ImageDraw.ImageDraw,
    position: tuple[int, int],
    text: str,
    font: ImageFont.ImageFont,
    fill: tuple[int, int, int],
    max_width: int,
) -> None:
    words = text.split()
    lines: list[str] = []
    current = ""

    for word in words:
        candidate = f"{current} {word}".strip()
        if draw.textbbox((0, 0), candidate, font=font)[2] <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word

    if current:
        lines.append(current)

    x, y = position
    for line in lines[:2]:
        draw.text((x, y), line, font=font, fill=fill)
        y += 16


def make_contact_sheets(
    chosen: dict[int, list[Sample]],
    class_names: list[str],
    output_dir: Path,
    samples_per_class: int,
    classes_per_page: int,
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    title_font = load_font(22)
    class_font = load_font(18)
    small_font = load_font(12)

    crop_size = 220
    cell_width = 260
    cell_height = 264
    row_title_height = 28
    row_height = row_title_height + cell_height + 18
    margin = 20
    header_height = 48
    page_width = margin * 2 + cell_width * samples_per_class
    page_count = math.ceil(len(class_names) / classes_per_page)
    sheet_paths: list[Path] = []

    for page_idx in range(page_count):
        start = page_idx * classes_per_page
        page_classes = list(enumerate(class_names[start : start + classes_per_page], start=start))
        page_height = header_height + margin + row_height * len(page_classes) + margin
        sheet = Image.new("RGB", (page_width, page_height), "white")
        draw = ImageDraw.Draw(sheet)

        draw.rectangle((0, 0, page_width, header_height), fill=(30, 41, 59))
        draw.text(
            (margin, 12),
            f"Food class visual verification - page {page_idx + 1}/{page_count}",
            font=title_font,
            fill="white",
        )

        y = header_height + margin
        for class_id, class_name in page_classes:
            selected_samples = chosen.get(class_id, [])
            draw.text(
                (margin, y),
                f"{class_id:02d}  {class_name}  ({len(selected_samples)} samples)",
                font=class_font,
                fill=(15, 23, 42),
            )

            cell_y = y + row_title_height
            for sample_idx in range(samples_per_class):
                cell_x = margin + sample_idx * cell_width
                draw.rectangle(
                    (cell_x, cell_y, cell_x + cell_width - 12, cell_y + cell_height),
                    outline=(203, 213, 225),
                    width=1,
                )

                if sample_idx >= len(selected_samples):
                    draw.text((cell_x + 12, cell_y + 96), "No sample", font=small_font, fill=(100, 116, 139))
                    continue

                sample = selected_samples[sample_idx]
                crop = crop_sample(sample, crop_size)
                crop_x = cell_x + (cell_width - 12 - crop.width) // 2
                crop_y = cell_y + 8
                sheet.paste(crop, (crop_x, crop_y))

                label_y = cell_y + crop_size + 14
                draw_text_fit(
                    draw,
                    (cell_x + 8, label_y),
                    f"{sample.split}: {sample.image_path.stem}",
                    small_font,
                    (51, 65, 85),
                    cell_width - 28,
                )

            y += row_height

        sheet_path = output_dir / f"class_verification_page_{page_idx + 1:02d}.jpg"
        sheet.save(sheet_path, quality=92)
        sheet_paths.append(sheet_path)

    return sheet_paths


def write_csv(chosen: dict[int, list[Sample]], output_path: Path) -> None:
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "class_id",
                "class_name",
                "split",
                "image_path",
                "label_path",
                "x_center",
                "y_center",
                "width",
                "height",
            ]
        )

        for class_id in sorted(chosen):
            for sample in chosen[class_id]:
                bbox = sample.bbox or find_bbox_for_class(sample.label_path, sample.class_id)
                writer.writerow(
                    [
                        sample.class_id,
                        sample.class_name,
                        sample.split,
                        sample.image_path.as_posix(),
                        sample.label_path.as_posix(),
                        *(bbox or ("", "", "", "")),
                    ]
                )


def write_summary(
    output_path: Path,
    class_names: list[str],
    samples_by_class: dict[int, list[Sample]],
    chosen: dict[int, list[Sample]],
    sheet_paths: list[Path],
) -> None:
    missing = [class_names[class_id] for class_id, samples in samples_by_class.items() if not samples]

    lines = [
        "# Food Class Visual Verification",
        "",
        f"Classes checked: {len(class_names)}",
        f"Classes with image samples: {len(class_names) - len(missing)}",
        f"Classes without image samples: {len(missing)}",
        "",
        "## Contact Sheets",
        "",
    ]

    for sheet_path in sheet_paths:
        lines.append(f"- `{sheet_path.as_posix()}`")

    lines.extend(
        [
            "",
            "## Sample Counts",
            "",
            "| Class ID | Class name | Available images | Displayed samples |",
            "|---:|---|---:|---:|",
        ]
    )

    for class_id, class_name in enumerate(class_names):
        lines.append(
            f"| {class_id} | `{class_name}` | "
            f"{len(samples_by_class.get(class_id, []))} | {len(chosen.get(class_id, []))} |"
        )

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-dir", type=Path, default=Path("data/food_dataset"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/food_dataset/class_verification"))
    parser.add_argument("--samples-per-class", type=int, default=4)
    parser.add_argument("--classes-per-page", type=int, default=9)
    parser.add_argument("--seed", type=int, default=20260606)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    data_yaml = args.dataset_dir / "data.yaml"
    class_names = load_class_names(data_yaml)
    if not class_names:
        raise SystemExit(f"No class names found in {data_yaml}")

    samples_by_class = collect_samples(args.dataset_dir, class_names)
    chosen = choose_samples(samples_by_class, args.samples_per_class, args.seed)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    sheet_paths = make_contact_sheets(
        chosen,
        class_names,
        args.output_dir,
        args.samples_per_class,
        args.classes_per_page,
    )
    write_csv(chosen, args.output_dir / "verification_samples.csv")
    write_summary(
        args.output_dir / "verification_summary.md",
        class_names,
        samples_by_class,
        chosen,
        sheet_paths,
    )

    classes_with_samples = sum(1 for samples in samples_by_class.values() if samples)
    print(f"Classes found in images: {classes_with_samples}/{len(class_names)}")
    print(f"Contact sheets written: {len(sheet_paths)}")
    print(f"Output directory: {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
