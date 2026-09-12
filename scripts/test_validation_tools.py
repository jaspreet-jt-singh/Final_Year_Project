"""Synthetic checks for validation provenance and literal claim indexing."""

from pathlib import Path
import tempfile
import unittest

from start_validation import inputs
from seal_validation import digest, verify_baseline
from validate_paper_claims import blocks, category


class ValidationToolTests(unittest.TestCase):
    def test_snapshot_excludes_dependencies_secrets_and_old_run_reports(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = ['frontend/lib/meal.ts', 'backend/settings.py', 'frontend/node_modules/a.json',
                     'frontend/.next/cache.json', 'backend/.env',
                     'research/evidence/validation-old/private.json', 'research/READINESS.md']
            for name in paths:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('{}', encoding='utf-8')
            actual = {path.relative_to(root).as_posix() for path in inputs(root)}
            self.assertEqual(actual, {'frontend/lib/meal.ts', 'backend/settings.py', 'research/READINESS.md'})

    def test_claim_blocks_preserve_math_and_ignore_comments(self):
        source = '\n'.join([r'\documentclass{article}', r'\begin{abstract}', 'The scope.',
                            r'\end{abstract}', r'\section{Introduction}', 'First sentence. Second sentence.',
                            '', r'\begin{equation}', 'a=1', r'\end{equation}',
                            '% excluded', r'\subsection{Detail}', 'Last sentence.'])
        result = blocks(source)
        self.assertEqual(len(result), 4)
        self.assertEqual(result[0]['section'], 'abstract')
        self.assertIn('a=1', result[2]['text'])
        self.assertEqual(result[3]['subsection'], 'Detail')
        self.assertFalse(any('excluded' in block['text'] for block in result))

    def test_unknown_sections_require_an_explicit_review_decision(self):
        with self.assertRaises(ValueError):
            category('New unreviewed claim', '')

    def test_historical_and_prospective_claims_are_not_promoted(self):
        self.assertEqual(category('Historical Detector Evidence', ''), 'HISTORY')
        self.assertEqual(category('Prospective Evaluation for Supervisor Approval', 'Independent mapping assessment'), 'PROPOSED')

    def test_seal_detects_runtime_changes_and_checks_preserved_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'backend').mkdir()
            runtime = root / 'backend/app.py'
            runtime.write_text('original', encoding='utf-8')
            snapshot = root / 'saved.tex'
            snapshot.write_text('original manuscript', encoding='utf-8')
            baseline = {'files': [
                {'path': 'backend/app.py', 'sha256': digest(runtime)},
                {'path': 'Research_Paper_Journal/main.tex', 'sha256': digest(snapshot), 'local_snapshot': 'saved.tex'},
            ]}
            protected, backups, errors = verify_baseline(root, baseline)
            self.assertFalse(errors)
            self.assertTrue(protected[0]['unchanged'])
            self.assertTrue(backups[0]['snapshot_matches'])
            runtime.write_text('changed', encoding='utf-8')
            snapshot.write_text('changed backup', encoding='utf-8')
            self.assertEqual(len(verify_baseline(root, baseline)[2]), 2)


if __name__ == '__main__':
    unittest.main()
