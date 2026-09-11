"""Reproducible, read-only evidence audit. Writes reports, never datasets or SQLite.

Exact byte/pixel duplicates establish overlap, not independence: absence of these
duplicates cannot rule out crops, recompression, shared subjects or source leakage.
No Torch import, training, provider calls, or new nutrition ground truth.
"""
from __future__ import annotations

import argparse
import asyncio
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
import csv
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import subprocess
import sys

from PIL import Image, ImageOps
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.services.nutrition_service import NutritionService
from backend.utils.food_normalizer import normalize_food_name

SPLITS = ('train', 'valid', 'test')
IMAGE_SUFFIXES = {'.jpg', '.jpeg', '.png', '.webp'}


def sha256(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def inspect_image(task):
    path, dataset, class_count, pixels = task
    split = path.relative_to(dataset).parts[0]
    label = dataset / split / 'labels' / (path.stem + '.txt')
    row = {'path': path.relative_to(dataset).as_posix(), 'split': split, 'sha256': sha256(path),
           'label_sha256': sha256(label) if label.is_file() else None, 'classes': [], 'issues': []}
    if not label.is_file():
        row['issues'].append('missing_label')
    else:
        for number, line in enumerate(label.read_text(encoding='utf-8').splitlines(), 1):
            if not line.strip():
                continue
            try:
                fields = line.split()
                if len(fields) != 5:
                    raise ValueError('expected five YOLO detection fields')
                category = int(fields[0])
                coords = [float(value) for value in fields[1:]]
                if not 0 <= category < class_count or not all(math.isfinite(v) for v in coords):
                    raise ValueError('invalid class or non-finite coordinate')
                x, y, width, height = coords
                if not (0 <= x <= 1 and 0 <= y <= 1 and 0 < width <= 1 and 0 < height <= 1):
                    raise ValueError('invalid normalized box')
                row['classes'].append(category)
            except ValueError:
                row['issues'].append(f'invalid_label_line:{number}')
    try:
        with Image.open(path) as source:
            row['dimensions'] = list(source.size)
            if pixels:
                with ImageOps.exif_transpose(source) as oriented, oriented.convert('RGB') as rgb:
                    digest = hashlib.sha256(f'{rgb.width}:{rgb.height}:RGB:'.encode())
                    digest.update(rgb.tobytes())
                    row['pixel_sha256'] = digest.hexdigest()
            else:
                source.verify()
    except (OSError, ValueError, Image.DecompressionBombError):
        row['issues'].append('decode_error')
    return row


def duplicate_summary(rows, key):
    groups = defaultdict(list)
    for row in rows:
        if row.get(key):
            groups[row[key]].append(row)
    cross = [group for group in groups.values() if len({r['split'] for r in group}) > 1]
    pairs = {}
    for left, right in [('train', 'valid'), ('train', 'test'), ('valid', 'test')]:
        shared = [group for group in cross if {left, right} <= {r['split'] for r in group}]
        pairs[f'{left}:{right}'] = {'shared_groups': len(shared),
                                   'affected_images': sum(sum(r['split'] in {left, right} for r in g) for g in shared)}
    return {'cross_split_groups': len(cross), 'affected_images': sum(len(g) for g in cross),
            'pairs': pairs, 'examples': [[r['path'] for r in g] for g in cross[:20]]}


def audit_dataset(dataset, pixels=True, manifest=None):
    config = yaml.safe_load((dataset / 'data.yaml').read_text(encoding='utf-8'))
    names = config['names']
    if isinstance(names, dict):
        names = [names[key] for key in sorted(names, key=int)]
    if config.get('nc', len(names)) != len(names):
        raise ValueError('Dataset class count disagrees with names')
    paths = sorted(path for split in SPLITS for path in (dataset / split / 'images').iterdir()
                   if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES)
    rows = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        for index, row in enumerate(executor.map(inspect_image, ((p, dataset, len(names), pixels) for p in paths)), 1):
            rows.append(row)
            if index % 5000 == 0:
                print(f'Audited {index}/{len(paths)} images', flush=True)
    fingerprint = hashlib.sha256()
    for row in rows:
        fingerprint.update(json.dumps({key: row[key] for key in ('path', 'sha256', 'label_sha256')}, sort_keys=True).encode())
        fingerprint.update(b'\n')
    if manifest:
        manifest.parent.mkdir(parents=True, exist_ok=True)
        with manifest.open('w', encoding='utf-8') as stream:
            for row in rows:
                stream.write(json.dumps(row, sort_keys=True) + '\n')
    splits = {}
    for split in SPLITS:
        selected = [r for r in rows if r['split'] == split]
        instances = Counter(c for row in selected for c in row['classes'])
        stems = {Path(row['path']).stem for row in selected}
        orphan_labels = [p.name for p in (dataset / split / 'labels').glob('*.txt') if p.stem not in stems]
        splits[split] = {'images': len(selected), 'instances': sum(instances.values()),
                         'empty_labels': sum(not r['classes'] and not r['issues'] for r in selected),
                         'issue_images': sum(bool(r['issues']) for r in selected),
                         'orphan_labels': len(orphan_labels), 'orphan_examples': orphan_labels[:10],
                         'instances_per_class': {name: instances[index] for index, name in enumerate(names)}}
    return {'class_count': len(names), 'image_count': len(rows), 'manifest_sha256': fingerprint.hexdigest(),
            'splits': splits, 'byte_duplicates': duplicate_summary(rows, 'sha256'),
            'pixel_duplicates': duplicate_summary(rows, 'pixel_sha256') if pixels else None,
            'issue_examples': [r for r in rows if r['issues']][:20],
            'limitations': 'No near-duplicate, source-identity, semantic-annotation or clinical validation.'}, names


async def audit_nutrition(database, names):
    with sqlite3.connect(database.resolve().as_uri() + '?mode=ro', uri=True) as db:
        db.row_factory = sqlite3.Row
        foods = [dict(row) for row in db.execute('SELECT name, normalized_name, calories, protein_g, carbs_g, fat_g, source, source_url FROM indb_foods ORDER BY name')]
        mappings = [dict(row) for row in db.execute('SELECT yolo_class, matched_food_name, match_score FROM yolo_mappings')]
    full = NutritionService(database)
    automatic = NutritionService(database)
    await full.initialize()
    await automatic.initialize()
    automatic._yolo_mappings.clear()  # Ablation in this instance only; SQLite stays read-only.
    normalized = {row['normalized_name']: row['name'] for row in foods}
    comparisons = []
    for label in names:
        mapped = await full.get_nutrition_for_food(label)
        fallback = await automatic.get_nutrition_for_food(label)
        comparisons.append({'class': label, 'normalized_exact': normalized.get(normalize_food_name(label)),
                            'automatic_without_precomputed': fallback['display_name'] if fallback else None,
                            'current_mapping': mapped['display_name'] if mapped else None})
    current = [row for row in mappings if row['yolo_class'] in names]
    records_by_name = {row['name']: row for row in foods}
    invalid_macros = []
    for mapping in current:
        food = records_by_name.get(mapping['matched_food_name'])
        if not food or any(not isinstance(food[key], (int, float)) or not math.isfinite(food[key]) or food[key] < 0
                           for key in ('calories', 'protein_g', 'carbs_g', 'fat_g')):
            invalid_macros.append(mapping['yolo_class'])
    return {'database_sha256': sha256(database), 'food_rows': len(foods), 'mapping_rows': len(mappings),
            'sources': dict(Counter(row['source'] or 'unspecified' for row in foods)),
            'dataset_precomputed_mappings': len(current), 'invalid_macro_classes': invalid_macros,
            'review_score_below_0_9_or_missing': sum(r['match_score'] is None or r['match_score'] < .9 for r in current),
            'supplemental_records': [row for row in foods if (row['source'] or '').startswith('Supplemental:')],
            'coverage_not_accuracy': {key: sum(r[key] is not None for r in comparisons) for key in ('normalized_exact', 'automatic_without_precomputed', 'current_mapping')},
            'comparisons': comparisons,
            'limitations': 'Current mappings are implementation choices, NOT independent ground truth. Coverage is not correctness; no clinical/recipe equivalence claim.'}


def audit_training(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        rows = [{key.strip(): value.strip() for key, value in row.items()} for row in csv.DictReader(stream)]
    return {'sha256': sha256(path), 'rows': len(rows),
            'epochs_unique': len({row['epoch'] for row in rows}),
            'best_validation_map50': max(rows, key=lambda r: float(r['metrics/mAP50(B)'])),
            'best_validation_map50_95': max(rows, key=lambda r: float(r['metrics/mAP50-95(B)'])),
            'limitations': 'Training validation CSV is not an independent held-out test evaluation.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', type=Path, default=ROOT / 'data/food_dataset')
    parser.add_argument('--output', type=Path, default=ROOT / 'research/evidence/audit.json')
    parser.add_argument('--manifest', type=Path, default=ROOT / '.deployment/research/split-manifest.jsonl')
    parser.add_argument('--skip-pixels', action='store_true')
    args = parser.parse_args()
    dataset, names = audit_dataset(args.dataset, not args.skip_pixels, args.manifest)
    report = {'schema_version': 1, 'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'audit_script_sha256': sha256(Path(__file__)), 'dataset': dataset,
              'nutrition': asyncio.run(audit_nutrition(ROOT / 'data/nutrition.db', names)),
              'training': audit_training(ROOT / 'merge_results/merged_results_1_to_100.csv'),
              'model_sha256': sha256(ROOT / 'results_after_discontinuation/yolo11s_indian_food_best.pt')}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'report': str(args.output), 'images': dataset['image_count'],
                      'cross_split_byte_groups': dataset['byte_duplicates']['cross_split_groups'],
                      'cross_split_pixel_groups': dataset['pixel_duplicates']['cross_split_groups'] if dataset['pixel_duplicates'] else None,
                      'nutrition_coverage': report['nutrition']['coverage_not_accuracy']}, indent=2), flush=True)


if __name__ == '__main__':
    main()
