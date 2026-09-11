"""Small synthetic evidence-audit regressions; no research images or providers."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image

from audit_publication import audit_dataset, duplicate_summary
from evaluate_mapping_review import evaluate


class AuditTests(unittest.TestCase):
    def test_release_refuses_dirty_source(self):
        from prepare_vercel_release import prepare
        with patch('prepare_vercel_release.git', return_value=' M backend/main.py'):
            with self.assertRaisesRegex(RuntimeError, 'exact clean source commit'):
                prepare()

    def test_review_is_required_and_abstentions_are_not_wrong_matches(self):
        candidates = [{'class': 'food', 'normalized_exact': None, 'automatic_without_precomputed': 'wrong', 'current_mapping': 'right'}]
        with self.assertRaises(ValueError):
            evaluate(candidates, [{'class': 'food', 'acceptable_database_names_json': '["right"]'}])
        review = [{'class': 'food', 'acceptable_database_names_json': '["right"]', 'reviewer': 'independent-test', 'evidence': 'synthetic fixture'}]
        results = evaluate(candidates, review)
        self.assertEqual(results['normalized_exact']['missed_supported'], 1)
        self.assertEqual(results['automatic_without_precomputed']['wrong_match'], 1)
        self.assertEqual(results['current_mapping']['correct_match'], 1)
        review[0]['acceptable_database_names_json'] = '[]'
        self.assertEqual(evaluate(candidates, review)['normalized_exact']['correct_abstention'], 1)

    def test_pair_counts_are_groups_not_cartesian_pairs(self):
        rows = [{'path': str(i), 'split': split, 'hash': 'same'} for i, split in enumerate(['train', 'train', 'test'])]
        result = duplicate_summary(rows, 'hash')
        self.assertEqual(result['cross_split_groups'], 1)
        self.assertEqual(result['pairs']['train:test'], {'shared_groups': 1, 'affected_images': 3})

    def test_byte_and_decoded_duplicates_and_invalid_labels(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'data.yaml').write_text('nc: 1\nnames: [food]\n', encoding='utf-8')
            for split in ('train', 'valid', 'test'):
                (root / split / 'images').mkdir(parents=True)
                (root / split / 'labels').mkdir()
            with Image.new('RGB', (10, 10), 'red') as image:
                image.save(root / 'train/images/a.png', compress_level=0)
                image.save(root / 'test/images/b.png', compress_level=9)
            (root / 'valid/images/c.png').write_bytes((root / 'train/images/a.png').read_bytes())
            (root / 'train/labels/a.txt').write_text('0 0.5 0.5 1 1\n', encoding='utf-8')
            (root / 'valid/labels/c.txt').write_text('5 nan 0.5 1 1\n', encoding='utf-8')
            result, _ = audit_dataset(root)
            self.assertEqual(result['image_count'], 3)
            self.assertEqual(result['byte_duplicates']['pairs']['train:test']['shared_groups'], 0)
            self.assertEqual(result['pixel_duplicates']['pairs']['train:test']['shared_groups'], 1)
            self.assertEqual(result['splits']['test']['issue_images'], 1)
            self.assertEqual(result['splits']['valid']['issue_images'], 1)
            self.assertEqual(result['splits']['train']['instances'], 1)


if __name__ == '__main__':
    unittest.main()
