"""Seal an existing-evidence audit without changing historical inputs or runtime files."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
EDITABLE = ('scripts/', 'research/', 'Research_Paper_Journal/', 'Research_Paper_Conference/', '.github/')


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def verify_baseline(root, baseline):
    protected, backups, errors = [], [], []
    for entry in baseline['files']:
        relative = entry['path']
        if not relative.startswith(EDITABLE):
            path = root / relative
            actual = digest(path) if path.is_file() else None
            protected.append({'path': relative, 'sha256': actual, 'unchanged': actual == entry['sha256']})
            if actual != entry['sha256']:
                errors.append(f'Protected input changed/missing: {relative}')
        if entry.get('local_snapshot'):
            path = root / entry['local_snapshot']
            okay = path.is_file() and digest(path) == entry['sha256']
            backups.append({'path': relative, 'snapshot_matches': okay})
            if not okay:
                errors.append(f'Baseline backup mismatch: {relative}')
    return protected, backups, errors


def inventory(root, run_id):
    paths = set()
    for directory in ('scripts', f'research/evidence/{run_id}', f'research/review/{run_id}',
                      'Research_Paper_Journal', 'Research_Paper_Conference'):
        for path in (root / directory).rglob('*'):
            if path.is_file() and path.suffix in {'.py', '.mjs', '.md', '.json', '.tex', '.bib', '.pdf'}:
                if '__pycache__' not in path.parts and path.name != 'validation-manifest.json':
                    paths.add(path)
    for name in ('research/VALIDATION_REPORT.md', 'research/VALIDATION_PROTOCOLS.md',
                 'research/READINESS.md', 'research/SUPERVISOR_REVIEW.md', '.github/workflows/quality.yml'):
        paths.add(root / name)
    return [{'path': path.relative_to(root).as_posix(), 'sha256': digest(path), 'bytes': path.stat().st_size}
            for path in sorted(paths)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if not re.fullmatch(r'validation-[a-z0-9-]+', args.run_id):
        parser.error('Invalid run identifier')
    reports = ROOT / 'research/evidence' / args.run_id
    target = reports / 'validation-manifest.json'
    if args.check:
        manifest = json.loads(target.read_text(encoding='utf-8'))
        errors = [entry['path'] for entry in manifest['artifacts']
                  if not (ROOT / entry['path']).is_file() or digest(ROOT / entry['path']) != entry['sha256']]
        if errors:
            raise SystemExit('Sealed artifacts changed: ' + ', '.join(errors))
        print(f"Sealed artifact hashes match ({len(manifest['artifacts'])}); not a scientific endorsement.")
        return
    if target.exists():
        parser.error('Seal already exists; preserve it and create a new run for later revisions')
    baseline = json.loads((reports / 'baseline.json').read_text(encoding='utf-8'))
    protected, backups, errors = verify_baseline(ROOT, baseline)
    for name in ('claims-final.json', 'claim-review-coverage.json', 'claim-corrections.json', 'numeric-checks.json', 'findings.json', 'pdf-review.json',
                 'dataset-inspection.json', 'training-results.json', 'nutrition-validation.json',
                 'arithmetic-validation.json', 'recommendations.json', 'citation-review.json'):
        if not (reports / name).is_file():
            errors.append(f'Missing required report: {name}')
    latest_checks = {}
    for path in sorted((reports / 'checks').glob('*.json')):
        receipt = json.loads(path.read_text(encoding='utf-8'))
        if receipt['attempt'] > latest_checks.get(receipt['check'], {}).get('attempt', 0):
            latest_checks[receipt['check']] = receipt
    errors.extend(f'Latest check failed: {name}' for name, receipt in latest_checks.items()
                  if receipt['status'] != 'passed')
    if not latest_checks:
        errors.append('No recorded offline checks')
    if errors:
        raise SystemExit('\n'.join(errors))
    manifest = {
        'schema_version': 1, 'run_id': args.run_id,
        'sealed_at_utc': datetime.now(timezone.utc).isoformat(),
        'source_commit': baseline['source_commit'],
        'current_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'identity_note': 'Uncommitted documents and tooling are identified by content hashes, not by the base commit alone.',
        'command': ['python', 'scripts/seal_validation.py', '--run-id', args.run_id],
        'baseline_sha256': digest(reports / 'baseline.json'),
        'protected_inputs': protected, 'verified_local_backups': backups,
        'latest_offline_checks': {name: {'attempt': value['attempt'], 'status': value['status']}
                                  for name, value in latest_checks.items()},
        'artifacts': inventory(ROOT, args.run_id),
        'decisions': {
            'supervisor_review': 'Ready with recorded limitations and unresolved findings.',
            'scientific_scope': 'Only the explicitly bounded audit-case-study claims are supported; see claim dispositions.',
            'external_submission': 'Not approved: author/rights decisions, independent review and venue assessment remain.',
            'new_experiments': 'Protocols prepared only; separate approval required.',
        },
        'boundary': 'Hash integrity and passing software checks do not establish mapping correctness, independent detector accuracy or clinical effectiveness.',
    }
    with target.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(manifest, stream, indent=2)
        stream.write('\n')
    print(json.dumps({'protected_unchanged': len(protected), 'verified_backups': len(backups),
                      'sealed_artifacts': len(manifest['artifacts'])}))


if __name__ == '__main__':
    main()
