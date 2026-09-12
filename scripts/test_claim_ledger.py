"""Synthetic tests of index coverage and honest evidence boundaries, not science."""

import tempfile
import unittest
from pathlib import Path

from validate_paper_claims import (
    atomic_units,
    balanced_commands,
    blocks,
    file_identities,
    numeric_definitions,
    occurrence_review,
    write_ledger,
)


class ClaimLedgerTests(unittest.TestCase):
    def test_abstract_sentences_and_inline_math_are_separate_with_spans(self):
        source = '\n'.join([r'\begin{abstract}', r'First assertion. $x=1.2$ is a formula.', r'\end{abstract}'])
        units = atomic_units(blocks(source)[0])
        self.assertEqual([unit['unit_type'] for unit in units], ['abstract_sentence', 'abstract_sentence', 'inline_math'])
        self.assertEqual(units[0]['text'], 'First assertion.')
        self.assertEqual(units[1]['text'], '$x=1.2$ is a formula.')
        for unit in units:
            span = unit['span']
            self.assertEqual(span['start_line'], 2)
            self.assertEqual(span['end_line'], 2)
            self.assertEqual(source.splitlines()[1][span['start_column'] - 1:span['end_column']], unit['text'])

    def test_list_items_and_multisentence_items_are_not_one_opaque_list(self):
        source = '\n'.join([r'\section{Introduction}', r'\begin{enumerate}',
                            r'\item First research question? A boundary.', r'\item Second research question?', r'\end{enumerate}'])
        units = atomic_units(blocks(source)[0])
        self.assertEqual(len(units), 3)
        self.assertTrue(all(unit['unit_type'] == 'list_item' for unit in units))
        self.assertEqual([unit['span']['start_line'] for unit in units], [3, 3, 4])

    def test_nested_caption_table_rows_and_container_are_preserved(self):
        source = '\n'.join([r'\section{Results}', r'\subsection{RQ1: Export integrity}',
                            r'\begin{table}', r'\caption{Count for \AuditClasses{} labels, not \emph{accuracy}.}',
                            r'\begin{tabular}{lr}', r'Split & Images\\', r'Train & \AuditImages\\',
                            r'\end{tabular}', r'\end{table}'])
        units = atomic_units(blocks(source)[0])
        self.assertEqual([unit['unit_type'] for unit in units], ['table', 'caption', 'table_row', 'table_row'])
        self.assertEqual(units[1]['text'], r'Count for \AuditClasses{} labels, not \emph{accuracy}.')
        self.assertEqual(units[1]['span']['start_line'], 4)
        self.assertIn(r'\begin{tabular}', units[0]['text'])
        with self.assertRaises(ValueError):
            list(balanced_commands(r'\caption{missing', 'caption'))

    def test_mixed_sections_get_explicit_primary_overrides(self):
        def review(text, section='Implemented System', subsection='Nutrition, grams, and saved history'):
            return occurrence_review(section, subsection, {'text': text, 'unit_type': 'prose_sentence'})
        journal = review('Only explicitly saved meals contribute to daily totals.')
        self.assertEqual(journal['claim_set_id'], 'JOURNAL')
        self.assertIn('ARITHMETIC', journal['claim_set_ids'])
        self.assertEqual(review('The offline builder prioritizes developer mappings.')['claim_set_id'], 'NUTRITION')
        proposed = review('Before new detector claims, review group links.', 'Limitations and Evaluation Plan', '')
        self.assertEqual(proposed['claim_set_id'], 'PROPOSED')
        approval = review('Authors must verify the paper and confirm authorship.', 'Availability and Review Transparency', '')
        self.assertEqual(approval['claim_set_id'], 'APPROVAL')
        tests = review('Backend/contract tests examine arithmetic.', 'Audit Methods', 'Lookup comparison and software tests')
        self.assertEqual(tests['claim_set_id'], 'TESTS')

    def test_shared_concepts_are_navigation_not_individual_or_clinical_approval(self):
        one = occurrence_review('Introduction', '', {'text': 'Only explicitly saved meals contribute.', 'unit_type': 'prose_sentence'})
        two = occurrence_review('Results', 'RQ4: Implemented invariants', {'text': 'Saved-only totals passed tests.', 'unit_type': 'prose_sentence'})
        self.assertIn('CONCEPT:journal.saved-only-totals', set(one['shared_concept_ids']) & set(two['shared_concept_ids']))
        self.assertEqual(one['individual_review_status'], 'not_individually_adjudicated')
        self.assertNotEqual(one['disposition'], 'Reproduced')
        clinical = occurrence_review('Implemented System', 'Advice context is not clinical validation', {'text': r'$p_c=50$', 'unit_type': 'inline_math'})
        self.assertEqual(clinical['claim_set_id'], 'ARITHMETIC')
        self.assertEqual(clinical['clinical_review_status'], 'pending_qualified_review')
        historic = occurrence_review('Historical Scores, Not a Clean Benchmark', '', {'text': 'Independent evaluation would require retraining.', 'unit_type': 'prose_sentence'})
        self.assertEqual(historic['disposition'], 'Historical only')

    def test_macro_values_and_content_hashes_detect_changes(self):
        macros = numeric_definitions(r'\newcommand{\AuditImages}{12,345}\newcommand{\CoverageExactPercent}{25.00}')
        self.assertEqual(macros, {'AuditImages': '12,345', 'CoverageExactPercent': '25.00'})
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / 'evidence.json'
            path.write_text('{"status":"pass"}', encoding='utf-8')
            first, missing = file_identities(root, ['evidence.json', 'missing.json'])
            self.assertEqual(missing, ['missing.json'])
            path.write_text('{"status":"fail"}', encoding='utf-8')
            second, _ = file_identities(root, ['evidence.json'])
            self.assertNotEqual(first[0]['sha256'], second[0]['sha256'])

    def test_invalid_evidence_never_creates_a_ledger_and_existing_is_not_replaced(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'claims.json'
            with self.assertRaisesRegex(ValueError, 'Missing claim evidence'):
                write_ledger(path, {'structural_errors': ['Missing claim evidence files: missing.json']})
            self.assertFalse(path.exists())
            write_ledger(path, {'structural_errors': []})
            original = path.read_bytes()
            with self.assertRaises(FileExistsError):
                write_ledger(path, {'structural_errors': [], 'changed': True})
            self.assertEqual(path.read_bytes(), original)


if __name__ == '__main__':
    unittest.main()
