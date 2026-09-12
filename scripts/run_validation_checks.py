"""Run allowlisted offline checks and preserve per-attempt receipts and local logs."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
NPM = shutil.which('npm.cmd' if os.name == 'nt' else 'npm') or 'npm'
RUFF = str(Path(sys.executable).with_name('ruff.exe' if os.name == 'nt' else 'ruff'))
CHECKS = {
    'backend-lint': [RUFF, 'check', 'backend'],
    'contracts': [sys.executable, 'scripts/generate_contracts.py', '--check'],
    'backend-deployment': [sys.executable, 'scripts/test_deployment.py'],
    'backend-architecture': [sys.executable, 'scripts/test_architecture.py'],
    'research-tools': [sys.executable, 'scripts/test_publication.py'],
    'paper-numbers': [sys.executable, 'scripts/generate_paper_evidence.py', '--check'],
    'paper-tests': [sys.executable, 'scripts/test_paper_evidence.py'],
    'manuscripts': [sys.executable, 'scripts/check_manuscripts.py'],
    'manuscript-tests': [sys.executable, 'scripts/test_manuscripts.py'],
    'provenance': [sys.executable, 'scripts/verify_nutrition_provenance.py'],
    'frontend-lint': [NPM, '--prefix', 'frontend', 'run', 'lint'],
    'frontend-unit': [NPM, '--prefix', 'frontend', 'run', 'test:unit'],
    'frontend-build': [NPM, '--prefix', 'frontend', 'run', 'build'],
    'frontend-types': [NPM, '--prefix', 'frontend', 'run', 'typecheck'],
    'browser': [NPM, '--prefix', 'frontend', 'run', 'test:browser'],
    'validation-tools': [sys.executable, 'scripts/test_validation_tools.py'],
    'dataset-validator': [sys.executable, 'scripts/test_validate_dataset_training.py'],
    'nutrition-validator': [sys.executable, 'scripts/test_validate_nutrition_evidence.py'],
    'mapping-reference': [sys.executable, 'scripts/test_score_mapping_reference.py'],
    'recommendation-validator': [sys.executable, 'scripts/test_recommendation_evidence.py'],
    'arithmetic-oracle': ['node', '--import', './frontend/node_modules/tsx/dist/loader.mjs', 'scripts/test_nutrition_oracle.mjs', '--self-test'],
    'validation-numbers': [sys.executable, 'scripts/check_validation_numbers.py', '--check'],
    'number-validator': [sys.executable, 'scripts/test_validation_numbers.py'],
    'claim-validator': [sys.executable, 'scripts/test_claim_ledger.py'],
    'claims': [sys.executable, 'scripts/validate_paper_claims.py', '--run-id', 'validation-2026-09-12-v1', '--output-name', 'claims-final.json', '--check'],
    'claim-reviews': [sys.executable, 'scripts/check_claim_reviews.py', '--check'],
    'claim-review-validator': [sys.executable, 'scripts/test_claim_reviews.py'],
    'pdf-freshness': [sys.executable, 'scripts/record_validation_documents.py', '--check'],
    'validation-lint': [RUFF, 'check', *[f'scripts/{name}.py' for name in (
        'start_validation', 'run_validation_checks', 'seal_validation', 'test_validation_tools',
        'validate_paper_claims', 'test_claim_ledger', 'check_validation_numbers', 'test_validation_numbers',
        'validate_dataset_training', 'record_dataset_visual_review', 'test_validate_dataset_training',
        'validate_nutrition_evidence', 'test_validate_nutrition_evidence', 'score_mapping_reference',
        'test_score_mapping_reference', 'validate_recommendation_evidence', 'test_recommendation_evidence',
        'check_claim_reviews', 'test_claim_reviews', 'record_claim_corrections', 'record_validation_documents')]],
}


def file_digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--checks', nargs='+', choices=CHECKS, required=True)
    args = parser.parse_args()
    if not args.run_id.startswith('validation-') or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.run_id):
        parser.error('Invalid run identifier')
    local = ROOT / '.deployment/research' / args.run_id / 'checks'
    reports = ROOT / 'research/evidence' / args.run_id / 'checks'
    baseline = reports.parent / 'baseline.json'
    if not baseline.is_file():
        parser.error('Freeze the baseline first')
    local.mkdir(parents=True, exist_ok=True)
    reports.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update(APP_ENV='test', GROQ_API_KEY='', OPENAI_API_KEY='', OLLAMA_HOST='',
               NEXT_TELEMETRY_DISABLED='1', YOLO_AUTOINSTALL='false', PYTHONIOENCODING='utf-8')
    failed = False
    for name in args.checks:
        attempt = 1
        while (reports / f'{name}-{attempt}.json').exists() or (local / f'{name}-{attempt}.log').exists():
            attempt += 1
        command = CHECKS[name]
        log = local / f'{name}-{attempt}.log'
        started = datetime.now(timezone.utc).isoformat()
        before = time.monotonic()
        print(f'Starting {name} (attempt {attempt})', flush=True)
        with log.open('x', encoding='utf-8') as stream:
            result = subprocess.run(command, cwd=ROOT, env=env, stdout=stream, stderr=subprocess.STDOUT, check=False)
        # Only explicitly relevant code/lock identities, never environment contents.
        paths = [ROOT / part for part in command[1:] if (ROOT / part).is_file()]
        paths += [ROOT / name for name in ('pyproject.toml', 'uv.lock', 'frontend/package-lock.json')]
        receipt = {'schema_version': 1, 'check': name, 'attempt': attempt,
                   'started_at_utc': started, 'duration_seconds': round(time.monotonic() - before, 3),
                   'exit_code': result.returncode, 'status': 'passed' if result.returncode == 0 else 'failed',
                   'command': [Path(command[0]).name, *command[1:]],
                   'inputs': [{'path': p.relative_to(ROOT).as_posix(), 'sha256': file_digest(p)} for p in paths],
                   'local_log': log.relative_to(ROOT).as_posix(), 'log_sha256': file_digest(log),
                   'network_policy': 'Provider credentials disabled; mocked suites only. No scientific/clinical approval implied.'}
        with (reports / f'{name}-{attempt}.json').open('x', encoding='utf-8', newline='\n') as stream:
            json.dump(receipt, stream, indent=2)
            stream.write('\n')
        print(f'{name}: {receipt["status"]} ({receipt["duration_seconds"]}s)', flush=True)
        if result.returncode:
            failed = True
            print(log.read_text(encoding='utf-8', errors='replace')[-3000:].replace(str(ROOT), '<repo>'), flush=True)
    return int(failed)


if __name__ == '__main__':
    raise SystemExit(main())
