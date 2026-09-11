"""Prepare a review-only, source-grouped split manifest; never mutate datasets.

No training, model evaluation, uploads or license grants. Unknown lineage and
annotation conflicts are quarantined, not silently repaired. A new partition
cannot turn an already-trained checkpoint into an independent evaluation.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess

import yaml

from audit_publication import IMAGE_SUFFIXES, ROOT, SPLITS, inspect_image, sha256

SOURCE_DIRS = (
    'Indian food detection.v1i.yolov11',
    'indian food.v6i.yolov11',
    'Indian_food.v2-indianfood-7.yolov11',
    'indianfoodnet_yolo',
    'south indian food detection.v19i.yolov11',
)
RATIOS = {'train': .7, 'valid': .15, 'test': .15}


def family_key(source, filename):
    """Conservative within-export identity, not a verified original-photo ID.

    Roboflow export variants share a prefix before .rf.<32 hex digits>.
    Generic names in unrelated exports must NOT be joined by name alone.
    Nested export markers use the earliest marker to retain ancestor variants.
    Unrecognized naming is unresolved, not assumed to identify a unique original.
    """
    match = re.search(r'\.rf\.[0-9a-f]{32}(?=[._]|$)', filename, flags=re.I)
    return f'{source}/{filename[:match.start()].casefold()}' if match else None


def fingerprint(rows):
    digest = hashlib.sha256()
    for row in sorted(rows, key=lambda row: row['path']):
        digest.update(json.dumps({key: row[key] for key in ('path', 'sha256', 'label_sha256')}, sort_keys=True).encode())
        digest.update(b'\n')
    return digest.hexdigest()


def load_verified_manifest(manifest, dataset, expected_fingerprint, class_count):
    """Recompute current labels and pixels; stale or incomplete input fails closed."""
    rows = [json.loads(line) for line in manifest.read_text(encoding='utf-8').splitlines() if line.strip()]
    paths = [row['path'] for row in rows]
    if len(set(paths)) != len(paths):
        raise ValueError('Duplicate paths in input manifest')
    for path in paths:
        relative = PurePosixPath(path)
        if relative.is_absolute() or '..' in relative.parts or len(relative.parts) != 3:
            raise ValueError('Unsafe dataset path in manifest')
        if relative.parts[0] not in SPLITS or relative.parts[1] != 'images':
            raise ValueError('Unexpected dataset path in manifest')
        if not (dataset / path).resolve().is_relative_to(dataset.resolve()):
            raise ValueError('Dataset path escapes its root')
    actual = {path.relative_to(dataset).as_posix() for split in SPLITS
              for path in (dataset / split / 'images').iterdir()
              if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES}
    if actual != set(paths) or fingerprint(rows) != expected_fingerprint:
        raise ValueError('Manifest membership/fingerprint differs from recorded audit; audit again')
    current = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        tasks = ((dataset / row['path'], dataset, class_count, True) for row in rows)
        for index, (old, new) in enumerate(zip(rows, executor.map(inspect_image, tasks)), 1):
            if old != new:
                raise ValueError(f'Dataset or audit changed: {old["path"]}; audit again')
            current.append(new)
            if index % 5000 == 0:
                print(f'Verified export {index}/{len(rows)}', flush=True)
    return sorted(current, key=lambda row: row['path'])


def source_record(task):
    path, source, data_root = task
    return {'path': path.relative_to(data_root).as_posix(), 'sha256': sha256(path),
            'family': family_key(source, path.name)}


def inventory_sources(data_root):
    records, metadata = [], []
    with ThreadPoolExecutor(max_workers=4) as executor:
        for source in SOURCE_DIRS:
            directory = data_root / source
            config = directory / 'data.yaml'
            if not config.is_file():
                raise ValueError(f'Missing source export: {source}')
            paths = sorted(path for folder in ('train/images', 'valid/images', 'test/images', 'images')
                           for path in (directory / folder).glob('*')
                           if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES)
            if not paths:
                raise ValueError(f'Empty source export: {source}')
            result = list(executor.map(source_record, ((path, source, data_root) for path in paths)))
            records.extend(result)
            metadata.append({'source': source, 'images': len(result),
                             'recognized_family_images': sum(r['family'] is not None for r in result),
                             'yaml_sha256': sha256(config),
                             'declared_metadata': yaml.safe_load(config.read_text(encoding='utf-8')).get('roboflow')})
            print(f'Indexed {source}: {len(result)} images', flush=True)
    return records, metadata


class Groups:
    def __init__(self, count):
        self.parent = list(range(count))

    def find(self, index):
        while self.parent[index] != index:
            self.parent[index] = self.parent[self.parent[index]]
            index = self.parent[index]
        return index

    def join(self, left, right):
        left, right = self.find(left), self.find(right)
        self.parent[max(left, right)] = min(left, right)


def build_components(rows, sources):
    """Union exported pixels/bytes and source families, including transitive links.

    Source-only images participate too: an unused identical source image can
    establish that two source families are related.
    """
    rows = sorted(rows, key=lambda row: row['path'])
    sources = sorted(sources, key=lambda row: row['path'])
    combined = rows + sources
    groups, seen = Groups(len(combined)), {}
    for index, row in enumerate(combined):
        for kind in ('sha256', 'pixel_sha256', 'family'):
            if row.get(kind):
                token = (kind, row[kind])
                if token in seen:
                    groups.join(index, seen[token])
                else:
                    seen[token] = index
    members, origins = defaultdict(list), defaultdict(list)
    for index, row in enumerate(combined):
        (members if index < len(rows) else origins)[groups.find(index)].append(row)
    components = []
    for root, exports in members.items():
        source_rows = origins[root]
        families = sorted({row['family'] for row in source_rows if row['family']})
        reasons = set()
        if not families:
            reasons.add('unresolved_source_lineage')
        if any(row['family'] is None for row in source_rows):
            reasons.add('unrecognized_source_family')
        if any(row['issues'] for row in exports):
            reasons.add('annotation_or_decode_issue')
        if any(not row['classes'] for row in exports):
            reasons.add('no_accepted_annotations')
        pixels = defaultdict(set)
        for row in exports:
            if row.get('pixel_sha256'):
                pixels[row['pixel_sha256']].add(row['label_sha256'])
        if any(len(labels) > 1 for labels in pixels.values()):
            # Includes order/rounding-only differences: reviewer must adjudicate.
            reasons.add('identical_pixels_different_labels')
        group_id = hashlib.sha256('\n'.join(row['path'] for row in exports).encode()).hexdigest()
        components.append({'group_id': group_id, 'rows': exports, 'source_families': families,
                           'source_paths': [row['path'] for row in source_rows],
                           'reasons': sorted(reasons)})
    return components


def assign_components(components, seed=42):
    """Deterministic group-level greedy balancing; no sample-level fallback.

    Optimize squared deviations from image and per-class image targets. Report
    absent classes rather than violating group boundaries to fill partitions.
    """
    eligible = [group for group in components if not group['reasons']]
    counts = {group['group_id']: Counter(c for row in group['rows'] for c in set(row['classes']))
              for group in eligible}
    total_classes = sum(counts.values(), Counter())
    total = sum(len(group['rows']) for group in eligible)
    used, used_classes = Counter(), {split: Counter() for split in SPLITS}

    def tie(value):
        return hashlib.sha256(f'{seed}:{value}'.encode()).hexdigest()

    def priority(group):
        rarest = min(total_classes[c] for c in counts[group['group_id']])
        return (rarest, -len(group['rows']), tie(group['group_id']))

    for group in sorted(eligible, key=priority):
        size, classes = len(group['rows']), counts[group['group_id']]

        def cost(split):
            ratio = RATIOS[split]
            target = total * ratio
            delta = ((used[split] + size - target) ** 2 - (used[split] - target) ** 2) / max(target, 1)
            for category, count in classes.items():
                target = total_classes[category] * ratio
                before = used_classes[split][category]
                delta += ((before + count - target) ** 2 - (before - target) ** 2) / max(target, 1)
            return delta, tie(f'{group["group_id"]}:{split}')

        split = min(SPLITS, key=cost)
        group['candidate_split'] = split
        used[split] += size
        used_classes[split].update(classes)
    for group in components:
        if group['reasons']:
            group['candidate_split'] = None
    return components


def validate_assignments(components):
    seen, paths = {}, set()
    for group in components:
        split = group['candidate_split']
        if (split is None) != bool(group['reasons']) or split not in (*SPLITS, None):
            raise ValueError('Quarantine/partition inconsistency')
        for row in group['rows']:
            if row['path'] in paths:
                raise ValueError('Repeated exported path')
            paths.add(row['path'])
        for kind, values in (
            ('family', group['source_families']),
            ('byte', [row['sha256'] for row in group['rows']]),
            ('pixel', [row.get('pixel_sha256') for row in group['rows']]),
        ):
            for value in filter(None, values):
                token = (kind, value)
                if token in seen and seen[token] != group['group_id']:
                    raise ValueError('Known related images assigned to different groups')
                seen[token] = group['group_id']


def summarize(components, names):
    splits = {}
    for split in SPLITS:
        selected = [group for group in components if group['candidate_split'] == split]
        rows = [row for group in selected for row in group['rows']]
        counts = Counter(c for row in rows for c in set(row['classes']))
        splits[split] = {'groups': len(selected), 'images': len(rows),
                         'unique_pixels': len({row['pixel_sha256'] for row in rows}),
                         'images_per_class': {name: counts[index] for index, name in enumerate(names)},
                         'missing_classes': [name for index, name in enumerate(names) if not counts[index]]}
    quarantined = [group for group in components if group['reasons']]
    return {'total_groups': len(components), 'splits': splits,
            'quarantined_groups': len(quarantined),
            'quarantined_images': sum(len(group['rows']) for group in quarantined),
            'quarantine_images_by_reason_nonexclusive': dict(Counter(
                reason for group in quarantined for _ in group['rows'] for reason in group['reasons'])),
            'source_family_groups_spanning_old_splits': sum(
                bool(group['source_families']) and len({row['split'] for row in group['rows']}) > 1
                for group in components),
            'known_group_overlap_across_candidate_splits': 0}


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', type=Path, default=ROOT / 'data/food_dataset')
    parser.add_argument('--manifest', type=Path, default=ROOT / '.deployment/research/split-manifest.jsonl')
    parser.add_argument('--audit', type=Path, default=ROOT / 'research/evidence/audit.json')
    parser.add_argument('--output', type=Path, default=ROOT / '.deployment/research/grouped-v1')
    parser.add_argument('--seed', type=int, default=42)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Output already exists; use a new versioned directory (never overwritten)')
    audit = json.loads(args.audit.read_text(encoding='utf-8'))
    config = yaml.safe_load((args.dataset / 'data.yaml').read_text(encoding='utf-8'))
    names = config['names']
    if isinstance(names, dict):
        names = [names[key] for key in sorted(names, key=int)]
    audited_names = list(audit['dataset']['splits']['train']['instances_per_class'])
    if len(names) != audit['dataset']['class_count'] or names != audited_names:
        raise ValueError('Class configuration differs from audit')
    rows = load_verified_manifest(args.manifest, args.dataset, audit['dataset']['manifest_sha256'], len(names))
    sources, metadata = inventory_sources(args.dataset.parent)
    components = assign_components(build_components(rows, sources), args.seed)
    validate_assignments(components)
    args.output.mkdir(parents=True, exist_ok=False)
    write_json(args.output / 'source-inventory.json', sources)
    with (args.output / 'assignments.jsonl').open('x', encoding='utf-8') as stream:
        for group in sorted(components, key=lambda group: group['group_id']):
            stream.write(json.dumps(group, sort_keys=True) + '\n')
    report = {
        'schema_version': 1, 'status': 'review_only_not_a_benchmark',
        'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'script_sha256': sha256(Path(__file__)), 'audit_sha256': sha256(args.audit),
        'input_manifest_sha256': sha256(args.manifest),
        'dataset_fingerprint': fingerprint(rows), 'seed': args.seed, 'target_ratios': RATIOS,
        'class_names': names, 'data_yaml_sha256': sha256(args.dataset / 'data.yaml'),
        'source_inventory_sha256': sha256(args.output / 'source-inventory.json'),
        'assignments_sha256': sha256(args.output / 'assignments.jsonl'),
        'sources': metadata, **summarize(components, names),
        'limitations': [
            'Filename families are conservative heuristics, not verified original identities.',
            'No exhaustive cross-source near-duplicate, crop, recompression or semantic-label review.',
            'Upstream augmented variants remain within groups, including validation/test candidates.',
            'Exact duplicate pixels are counted, not silently deleted; finalize representative policy before evaluation.',
            'Unmatched locally augmented images are quarantined; do not infer their ancestry from class names.',
            'All partitions have been seen in prior development; existing checkpoint metrics remain historical.',
            'Review lineage, annotations, representative selection and asset rights before freezing a benchmark.',
            'Retrain from an appropriate initialization or obtain untouched external data for independent evaluation.',
        ],
    }
    write_json(args.output / 'summary.json', report)
    print(json.dumps({key: report[key] for key in ('status', 'total_groups', 'quarantined_images',
                                                  'source_family_groups_spanning_old_splits')}, indent=2))
    print(f'Review-only artifacts: {args.output}', flush=True)


if __name__ == '__main__':
    main()
