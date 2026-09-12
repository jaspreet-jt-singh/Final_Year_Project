"""Preserve artifact-review corrections between the initial and final claim indexes."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / 'research/evidence/validation-2026-09-12-v1'
RULES = {
    'J-69-1': ('deployment_scope', 'vercel.json'),
    'J-69-4': ('deployment_scope', 'baseline.json'),
    'J-130-5': ('consumption_scope', 'frontend/lib/meals.ts'),
    'J-207-3': ('hash_seed_scope', 'nutrition-validation.json'),
    'J-132-1': ('storage', 'frontend/lib/meals.ts'),
    'C-88-5': ('storage', 'frontend/lib/meals.ts'),
    'J-190-2': ('label_conflicts', 'dataset-inspection.json'),
    'C-108-2': ('label_conflicts', 'dataset-inspection.json'),
    'J-331-2': ('availability', 'baseline.json'),
    'J-353-1': ('availability', 'baseline.json'),
    'C-197-2': ('availability', 'baseline.json'),
}
REASONS = {
    'deployment_scope': 'The inspected configuration/current checkpoint identifies an implementation artifact, not a verified live deployment.',
    'consumption_scope': 'The arithmetic is the saved known subtotal, not independently measured consumption.',
    'hash_seed_scope': 'The older availability receipt omitted a hash seed; the new eight-seed sweep records all seeds explicitly.',
    'storage': 'saveDraft retains all draft items with included flags; exclusion affects totals, not removal from stored records.',
    'label_conflicts': 'The generic byte-inequality limitation must be distinguished from this run: zero direct groups were formatting/order-only.',
    'availability': 'The checkout commit is verified locally; the exact public revision URL fetch failed with a cache miss. A failed fetch does not prove public unavailability or establish public availability.',
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    old_path, new_path = DIRECTORY / 'claims.json', DIRECTORY / 'claims-final.json'
    old = {row['occurrence_id']: row for row in json.loads(old_path.read_text(encoding='utf-8'))['claims']}
    new = {row['occurrence_id']: row for row in json.loads(new_path.read_text(encoding='utf-8'))['claims']}
    if old.keys() != new.keys():
        raise SystemExit('Occurrence identity changed; manual reconciliation required')
    changes = {key for key in old if old[key]['text_sha256'] != new[key]['text_sha256']}
    if changes != RULES.keys():
        raise SystemExit('Unexpected manuscript changes; extend the explicit review decisions first')
    rows = []
    for key, (reason, evidence) in RULES.items():
        path = ROOT / evidence if '/' in evidence or evidence == 'vercel.json' else DIRECTORY / evidence
        rows.append({'occurrence_id': key, 'before': old[key]['text'], 'after': new[key]['text'],
                     'before_text_sha256': old[key]['text_sha256'], 'after_text_sha256': new[key]['text_sha256'],
                     'disposition': 'Supported with limitations', 'rationale': REASONS[reason],
                     'evidence': {'path': path.relative_to(ROOT).as_posix(), 'sha256': sha(path)},
                     'limitation': 'Artifact/source-access statement only; no independent nutritional or clinical approval.',
                     'resolution': 'Corrected in both manuscripts where applicable; initial evidence index and pre-correction PDFs retained.'})
    report = {'schema_version': 1, 'run_id': 'validation-2026-09-12-v1',
              'initial_ledger_sha256': sha(old_path), 'final_ledger_sha256': sha(new_path),
              'reviewer_role': 'AI artifact reviewer; corrections based on code, recorded results and explicitly failed source access.',
              'public_access_probe': {'url': 'https://github.com/jaspreet-jt-singh/Final_Year_Project/tree/0a4edfa92818945ccd7f16b023299c847c745f0d',
                                      'date': '2026-09-12', 'method': 'Primary GitHub page via web open',
                                      'result': 'Failed to fetch: Cache miss; access not established.'},
              'unchanged_literal_units': len(old) - len(rows), 'corrections': rows}
    with (DIRECTORY / 'claim-corrections.json').open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    print(f'Recorded {len(rows)} corrections; preserved {len(old)} original review units')


if __name__ == '__main__':
    main()
