"""Verify the pinned workbook fingerprint; optional public upstream comparison.

No local artifact is downloaded/replaced. This verifies identity, not licenses
or nutritional correctness. Default mode is offline and suitable for CI.
"""
import argparse
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = 'https://raw.githubusercontent.com/lindsayjaacks/Indian-Nutrient-Databank-INDB-/'


def verify(evidence, workbook, online=False):
    content = workbook.read_bytes()
    digest = hashlib.sha256(content).hexdigest()
    if evidence['comparison'] != 'byte_identical':
        raise ValueError('Evidence does not assert a byte-identity comparison')
    if digest != evidence['local_sha256'] or digest != evidence['upstream_sha256']:
        raise ValueError('Workbook no longer matches the pinned provenance evidence')
    if len(content) != evidence['bytes']:
        raise ValueError('Workbook size differs from evidence')
    commit = evidence['upstream_commit']
    if len(commit) != 40 or any(c not in '0123456789abcdef' for c in commit):
        raise ValueError('Upstream commit must be immutable')
    expected_url = f'{REPOSITORY}{commit}/INDB.xlsx'
    if evidence['upstream_artifact'] != expected_url:
        raise ValueError('Unexpected upstream artifact')
    if online:
        with urllib.request.urlopen(expected_url, timeout=30) as response:
            # Bounded memory even if the upstream response changes unexpectedly.
            remote = response.read(len(content) + 1)
        if remote != content:
            raise ValueError('Public upstream artifact differs from the local workbook')
    return {'sha256': digest, 'bytes': len(content), 'upstream_checked': online,
            'rights_or_nutritional_correctness_verified': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--online', action='store_true')
    args = parser.parse_args()
    evidence = json.loads((ROOT / 'research/evidence/nutrition-provenance.json').read_text(encoding='utf-8'))
    print(json.dumps(verify(evidence, ROOT / 'data/INDB.xlsx', args.online), indent=2))


if __name__ == '__main__':
    main()
