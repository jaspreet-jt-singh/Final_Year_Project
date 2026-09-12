"""Check individual-review coverage and evidence identity, never clinical correctness."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN = 'validation-2026-09-12-v1'
DISPOSITIONS = {'Reproduced', 'Supported with limitations', 'Historical only', 'Proposed',
                'Unsupported or contradicted', 'Awaiting qualified review/approval'}
REVIEWS = ('claim-review-001-220.json', 'claim-review-221-440.json', 'claim-review-441-635.json')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(root):
    directory = root / 'research/evidence' / RUN
    ledger_path = directory / 'claims.json'
    ledger = json.loads(ledger_path.read_text(encoding='utf-8'))
    expected = {row['occurrence_id'] for row in ledger['claims']}
    reviewed, identities, errors = [], [], []
    for name in REVIEWS:
        path = directory / name
        report = json.loads(path.read_text(encoding='utf-8'))
        identities.append({'path': path.relative_to(root).as_posix(), 'sha256': digest(path)})
        if report['ledger_sha256'] != digest(ledger_path):
            errors.append(f'Stale source ledger: {name}')
        for row in report['claims']:
            if row['disposition'] not in DISPOSITIONS:
                errors.append(f'Unknown disposition: {row["occurrence_id"]}')
            if not row.get('rationale'):
                errors.append(f'Missing rationale: {row["occurrence_id"]}')
            reviewed.append(row)
    ids = [row['occurrence_id'] for row in reviewed]
    if set(ids) != expected or len(ids) != len(expected):
        errors.append('Individual reviews must cover every indexed occurrence exactly once')
    final_path = directory / 'claims-final.json'
    final = json.loads(final_path.read_text(encoding='utf-8'))
    changes = json.loads((directory / 'claim-corrections.json').read_text(encoding='utf-8'))
    if changes['initial_ledger_sha256'] != digest(ledger_path) or changes['final_ledger_sha256'] != digest(final_path):
        errors.append('Stale correction linkage')
    original_by_id = {row['occurrence_id']: row for row in ledger['claims']}
    final_by_id = {row['occurrence_id']: row for row in final['claims']}
    if original_by_id.keys() != final_by_id.keys():
        errors.append('Final occurrence identities need reconciliation')
    changed_ids = {key for key in original_by_id if key not in final_by_id or
                   original_by_id[key]['text_sha256'] != final_by_id[key]['text_sha256']}
    corrections = {row['occurrence_id']: row for row in changes['corrections']}
    if changed_ids != corrections.keys():
        errors.append('Every changed literal unit requires an explicit correction disposition')
    for key, row in corrections.items():
        if (row['before_text_sha256'] != original_by_id[key]['text_sha256'] or
                row['after_text_sha256'] != final_by_id[key]['text_sha256'] or
                row['disposition'] not in DISPOSITIONS):
            errors.append(f'Invalid correction identity/disposition: {key}')
    final_reviews = []
    for row in reviewed:
        selected = corrections.get(row['occurrence_id'], row)
        final_reviews.append({'occurrence_id': row['occurrence_id'], 'disposition': selected['disposition'],
                              'rationale': selected['rationale'],
                              'corrected_after_initial_review': row['occurrence_id'] in corrections})
    return {'schema_version': 1, 'run_id': RUN, 'ledger_sha256': digest(ledger_path),
            'final_ledger_sha256': digest(final_path),
            'review_receipts': identities, 'indexed_units': len(expected), 'reviewed_units': len(reviewed),
            'dispositions': dict(sorted(Counter(row['disposition'] for row in reviewed).items())),
            'final_dispositions': dict(sorted(Counter(row['disposition'] for row in final_reviews).items())),
            'final_reviews': final_reviews,
            'correction_candidates': [{'occurrence_id': row['occurrence_id'],
                                      'required_correction': row['required_correction']}
                                     for row in reviewed if row.get('required_correction')],
            'errors': errors, 'status': 'pass' if not errors else 'fail',
            'boundary': 'AI-assisted artifact review and complete indexing are not qualified nutrition review or external submission approval.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    report = check(ROOT)
    if report['errors']:
        raise SystemExit('\n'.join(report['errors']))
    if not args.check:
        target = ROOT / 'research/evidence' / RUN / 'claim-review-coverage.json'
        with target.open('x', encoding='utf-8', newline='\n') as stream:
            json.dump(report, stream, indent=2)
            stream.write('\n')
    print(json.dumps({'status': report['status'], 'reviewed_units': report['reviewed_units'],
                      'correction_candidates': len(report['correction_candidates']),
                      'dispositions': report['dispositions']}))


if __name__ == '__main__':
    main()
