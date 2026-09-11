"""Small synthetic evidence-audit regressions; no research images or providers."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image

from audit_publication import audit_dataset, duplicate_summary
from evaluate_mapping_review import evaluate
from prepare_research_split import (
    assign_components, build_components, family_key, fingerprint,
    load_verified_manifest, validate_assignments,
)


def sample(path, digest, pixel=None, issues=None, label='label'):
    return {'path': path, 'split': path.split('/')[0], 'sha256': digest,
            'pixel_sha256': pixel or digest, 'label_sha256': label,
            'classes': [0], 'issues': issues or []}


class GroupedSplitTests(unittest.TestCase):
    def test_family_names_are_scoped_and_nested_variants_stay_related(self):
        name = '001_jpg.rf.' + 'a' * 32 + '.jpg'
        self.assertEqual(family_key('source', name), 'source/001_jpg')
        self.assertNotEqual(family_key('other', name), family_key('source', name))
        nested = name[:-4] + '.rf.' + 'b' * 32 + '.jpg'
        self.assertEqual(family_key('source', nested), family_key('source', name))
        self.assertIsNone(family_key('source', 'untraceable.jpg'))

    def test_source_only_bridge_and_pixels_join_transitively(self):
        rows = [sample('train/images/a.jpg', 'a'), sample('test/images/b.jpg', 'b'),
                sample('valid/images/c.jpg', 'c', pixel='b')]
        sources = [
            {'path': 's1/a', 'sha256': 'a', 'family': 's1/family'},
            {'path': 's1/bridge', 'sha256': 'bridge', 'family': 's1/family'},
            {'path': 's2/bridge', 'sha256': 'bridge', 'family': 's2/family'},
            {'path': 's2/b', 'sha256': 'b', 'family': 's2/family'},
        ]
        groups = assign_components(build_components(rows, sources))
        self.assertEqual(len(groups), 1)
        self.assertEqual(len(groups[0]['rows']), 3)
        self.assertEqual(groups[0]['reasons'], [])
        validate_assignments(groups)

    def test_quarantine_propagates_to_family_and_conflicts(self):
        rows = [sample('train/images/a.jpg', 'a'),
                sample('test/images/b.jpg', 'b', issues=['invalid_label_line:1']),
                sample('test/images/c.jpg', 'c'),
                sample('train/images/d.jpg', 'd', pixel='c', label='conflict'),
                sample('valid/images/unknown.jpg', 'unknown')]
        sources = [{'path': value, 'sha256': value, 'family': family}
                   for value, family in [('a', 'one'), ('b', 'one'), ('c', 'two')]]
        groups = assign_components(build_components(rows, sources))
        self.assertEqual(len(groups), 3)
        self.assertTrue(all(group['candidate_split'] is None for group in groups))
        self.assertEqual({reason for group in groups for reason in group['reasons']}, {
            'annotation_or_decode_issue', 'identical_pixels_different_labels', 'unresolved_source_lineage'})
        validate_assignments(groups)

    def test_assignments_are_reproducible_under_reordered_inputs(self):
        rows = [sample(f'train/images/{i}.jpg', str(i)) for i in range(100)]
        sources = [{'path': str(i), 'sha256': str(i), 'family': f'family-{i // 2}'} for i in range(100)]
        first = assign_components(build_components(rows, sources))
        second = assign_components(build_components(rows[::-1], sources[::-1]))
        self.assertEqual(first, second)
        self.assertEqual({g['candidate_split'] for g in first}, {'train', 'valid', 'test'})
        validate_assignments(first)
        duplicate = dict(first[0], group_id='different')
        with self.assertRaisesRegex(ValueError, 'Repeated exported path'):
            validate_assignments(first + [duplicate])

    def test_stale_manifest_and_path_traversal_are_rejected(self):
        import json
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rows = [sample('../escape/a.jpg', 'a')]
            manifest = root / 'manifest.jsonl'
            manifest.write_text(json.dumps(rows[0]), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'Unsafe dataset path'):
                load_verified_manifest(manifest, root, fingerprint(rows), 1)
            for split in ('train', 'valid', 'test'):
                (root / split / 'images').mkdir(parents=True)
            rows = [sample('train/images/a.jpg', 'a')]
            manifest.write_text(json.dumps(rows[0]), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'membership/fingerprint'):
                load_verified_manifest(manifest, root, fingerprint(rows), 1)


class AuditTests(unittest.TestCase):
    def test_pinned_workbook_provenance_detects_changes(self):
        import hashlib
        from verify_nutrition_provenance import REPOSITORY, verify
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'fixture.xlsx'
            content = b'synthetic workbook content'
            path.write_bytes(content)
            digest = hashlib.sha256(content).hexdigest()
            revision = 'a' * 40
            evidence = {'local_sha256': digest, 'upstream_sha256': digest, 'bytes': len(content),
                        'comparison': 'byte_identical', 'upstream_commit': revision,
                        'upstream_artifact': f'{REPOSITORY}{revision}/INDB.xlsx'}
            self.assertFalse(verify(evidence, path)['upstream_checked'])
            with patch('verify_nutrition_provenance.urllib.request.urlopen') as fetch:
                fetch.return_value.__enter__.return_value.read.return_value = content
                self.assertTrue(verify(evidence, path, online=True)['upstream_checked'])
            path.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'no longer matches'):
                verify(evidence, path)

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
