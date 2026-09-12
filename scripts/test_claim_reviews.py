"""Synthetic identity/coverage tests; no manuscripts, datasets or providers required."""

import json
from pathlib import Path
import tempfile
import unittest

from check_claim_reviews import RUN, REVIEWS, check, digest


class ClaimReviewTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.directory = self.root / 'research/evidence' / RUN
        self.directory.mkdir(parents=True)
        self.write('claims.json', {'claims': [{'occurrence_id': 'J-1-1', 'text_sha256': 'before'}]})
        self.write('claims-final.json', {'claims': [{'occurrence_id': 'J-1-1', 'text_sha256': 'after'}]})
        self.hash = digest(self.directory / 'claims.json')
        self.row = {'occurrence_id': 'J-1-1', 'disposition': 'Unsupported or contradicted',
                    'rationale': 'Synthetic claim lacked evidence.', 'required_correction': 'Narrow the claim.'}
        for index, name in enumerate(REVIEWS):
            self.write(name, {'ledger_sha256': self.hash, 'claims': [self.row] if index == 0 else []})
        self.write('claim-corrections.json', {
            'initial_ledger_sha256': self.hash,
            'final_ledger_sha256': digest(self.directory / 'claims-final.json'),
            'corrections': [{'occurrence_id': 'J-1-1', 'before_text_sha256': 'before', 'after_text_sha256': 'after',
                             'disposition': 'Supported with limitations', 'rationale': 'Now narrowed.'}],
        })

    def write(self, name, value):
        (self.directory / name).write_text(json.dumps(value), encoding='utf-8')

    def test_every_unit_reviewed_and_corrected_disposition_separate(self):
        report = check(self.root)
        self.assertEqual(report['errors'], [])
        self.assertEqual(report['dispositions'], {'Unsupported or contradicted': 1})
        self.assertEqual(report['final_dispositions'], {'Supported with limitations': 1})

    def test_duplicate_review_rejected(self):
        self.write(REVIEWS[1], {'ledger_sha256': self.hash, 'claims': [self.row]})
        self.assertTrue(any('exactly once' in error for error in check(self.root)['errors']))

    def test_missing_rationale_unknown_disposition_and_stale_hash_rejected(self):
        self.write(REVIEWS[0], {'ledger_sha256': 'stale', 'claims': [dict(self.row, rationale='', disposition='Clinically validated')]})
        self.assertEqual(len(check(self.root)['errors']), 3)

    def test_unrecorded_literal_change_rejected(self):
        self.write('claim-corrections.json', {'initial_ledger_sha256': self.hash,
                   'final_ledger_sha256': digest(self.directory / 'claims-final.json'), 'corrections': []})
        self.assertTrue(any('changed literal' in error for error in check(self.root)['errors']))


if __name__ == '__main__':
    unittest.main()
