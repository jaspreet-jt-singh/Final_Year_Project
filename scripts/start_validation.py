"""Freeze allowlisted research inputs before validation; no runtime/data edits."""

import argparse
from datetime import datetime, timezone
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SKIP = {'node_modules', '.next', 'out', '__pycache__', '.git'}
SUFFIXES = {'.py', '.ts', '.tsx', '.mjs', '.json', '.toml', '.lock', '.yaml', '.yml',
            '.csv', '.tex', '.bib', '.md', '.pdf', '.ipynb'}


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def inputs(root):
    selected = set()
    for directory in ('backend', 'frontend', 'scripts', 'research', 'notebooks',
                      'Research_Paper_Journal', 'Research_Paper_Conference', 'tests/contracts'):
        for path in (root / directory).rglob('*'):
            relative = path.relative_to(root)
            if (path.is_file() and path.suffix in SUFFIXES and not (set(relative.parts) & SKIP)
                    and not any(part.startswith('validation-') for part in relative.parts)
                    and not path.name.startswith('.env')):
                selected.add(path)
    for name in ('pyproject.toml', 'uv.lock', 'requirements.txt', 'package.json',
                 'vercel.json', 'THIRD_PARTY_NOTICES.md', '.github/workflows/quality.yml',
                 'data/food_dataset/data.yaml', 'data/INDB.xlsx', 'data/nutrition.db',
                 'models/best.pt', 'results_after_discontinuation/yolo11s_indian_food_best.pt',
                 'results_after_discontinuation/yolo11s_indian_food_last.pt',
                 'merge_results/merged_results_1_to_100.csv'):
        path = root / name
        if path.is_file():
            selected.add(path)
    for directory in ('results_before_discontinuation', 'results_after_discontinuation', 'merge_results'):
        for path in (root / directory).rglob('*'):
            if path.is_file() and path.suffix in {'.csv', '.yaml', '.json', '.pt'}:
                selected.add(path)
    return sorted(selected)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    if not args.run_id.startswith('validation-') or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.run_id):
        parser.error('Use a lowercase validation- run identifier')
    local = ROOT / '.deployment/research' / args.run_id
    reports = ROOT / 'research/evidence' / args.run_id
    if local.exists() or reports.exists():
        parser.error('Run already exists; choose a fresh identifier')
    local.mkdir(parents=True)
    reports.mkdir(parents=True)
    records = []
    for path in inputs(ROOT):
        relative = path.relative_to(ROOT)
        record = {'path': relative.as_posix(), 'sha256': digest(path), 'bytes': path.stat().st_size}
        # Preserve editable documents and tooling locally, not research images or weights.
        if relative.parts[0] in {'Research_Paper_Journal', 'Research_Paper_Conference', 'research', 'scripts'}:
            target = local / 'baseline' / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
            record['local_snapshot'] = target.relative_to(ROOT).as_posix()
        records.append(record)
    packages = {}
    for name in ('pillow', 'numpy', 'pandas', 'openpyxl', 'torch', 'torchvision',
                 'ultralytics', 'ultralytics-opencv-headless', 'fastapi', 'groq', 'httpx', 'ruff'):
        try:
            packages[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            packages[name] = None
    manifest = {
        'schema_version': 1, 'run_id': args.run_id,
        'started_at_utc': datetime.now(timezone.utc).isoformat(),
        'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'snapshot_scope': 'Current worktree, including uncommitted files; source commit alone does not identify this snapshot.',
        'environment': {'python': sys.version.split()[0], 'system': platform.system(),
                        'release': platform.release(), 'architecture': platform.machine(),
                        'processor': platform.processor(), 'logical_cpus': os.cpu_count(), 'packages': packages},
        'command': ['python', 'scripts/start_validation.py', '--run-id', args.run_id],
        'files': records,
        'boundaries': ['No model inference, retraining, live providers, deployment or clinical review.',
                       'Full manifests and local document backups are not distributed in these reports.',
                       'No environment values, credentials, uploaded images or reviewer identities collected.'],
    }
    with (reports / 'baseline.json').open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(manifest, stream, indent=2)
        stream.write('\n')
    print(json.dumps({'run_id': args.run_id, 'files': len(records), 'baseline': str(reports.relative_to(ROOT) / 'baseline.json')}))


if __name__ == '__main__':
    main()
