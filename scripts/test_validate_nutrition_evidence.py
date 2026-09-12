"""Synthetic tests for the independent nutrition/arithmetic validator."""

from fractions import Fraction
from pathlib import Path
import sqlite3
import tempfile
import unittest
import zipfile

from validate_nutrition_evidence import (
    expected_import, goal_oracle, independent_normalize, literal_from_builder,
    read_database, reconcile, round_rational, workbook_records,
)


class NutritionEvidenceTests(unittest.TestCase):
    def test_independent_name_cleanup(self):
        self.assertEqual(independent_normalize("Fish_Curry (Machli curry)"), "fishcurry")
        self.assertEqual(independent_normalize(" Aloo-Gobi "), "aloogobi")
        self.assertEqual(independent_normalize(None), "")

    def test_import_deduplicates_before_missing_filter_and_keeps_supplements(self):
        rows = [
            {"excel_row": 2, "food_name": "Food (one)", "energy_kcal": None, "protein_g": "1", "carb_g": "2", "fat_g": "3"},
            {"excel_row": 3, "food_name": "Food (two)", "energy_kcal": "20", "protein_g": "1", "carb_g": "2", "fat_g": "3"},
            {"excel_row": 4, "food_name": "Other", "energy_kcal": "25.5", "protein_g": "1.25", "carb_g": "2", "fat_g": "3"},
        ]
        expected, omitted = expected_import(rows, [{"name": "Supplement", "calories": 3, "protein_g": 0, "carbs_g": 0, "fat_g": 0}])
        self.assertEqual([row["name"] for row in expected], ["Other", "Supplement"])
        self.assertEqual([row["reason"] for row in omitted], ["missing_or_nonnumeric_macro", "duplicate_normalized_name"])
        self.assertEqual(expected[0]["calories"], 25.5)

    def test_reconciliation_detects_missing_extra_metadata_and_numeric_changes(self):
        expected = [{"name": "Food", "calories": 10, "protein_g": 1, "carbs_g": 2, "fat_g": 3,
                     "normalized_name": "food", "source": "INDB", "source_url": "", "source_notes": "note"}]
        actual = [dict(expected[0])]
        self.assertEqual(reconcile(expected, actual), [])
        actual[0]["calories"] = 99
        actual[0]["source"] = "wrong"
        self.assertEqual({row["field"] for row in reconcile(expected, actual)}, {"calories", "source"})
        self.assertEqual(reconcile(expected, [])[0]["kind"], "missing_database_row")
        self.assertEqual(reconcile([], actual)[0]["kind"], "unexpected_database_row")

    def test_builder_literals_are_read_without_executing_module(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "builder.py"
            path.write_text("raise RuntimeError('must not execute')\nROWS: list = [{'name': 'test'}]\n", encoding="utf-8")
            self.assertEqual(literal_from_builder(path, "ROWS"), [{"name": "test"}])
            with self.assertRaisesRegex(ValueError, "literal missing"):
                literal_from_builder(path, "OTHER")

    def test_stdlib_workbook_reader_resolves_shared_inline_and_numeric_cells(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "book.xlsx"
            namespace = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
            headers = ["food_name", "energy_kcal", "protein_g", "carb_g", "fat_g"]
            cells = ''.join(f'<c r="{letter}1" t="inlineStr"><is><t>{name}</t></is></c>' for letter, name in zip("ABCDE", headers))
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("xl/workbook.xml", f'<workbook xmlns="{namespace}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Nutrient Data" r:id="r1"/></sheets></workbook>')
                archive.writestr("xl/_rels/workbook.xml.rels", '<Relationships><Relationship Id="r1" Target="worksheets/sheet1.xml"/></Relationships>')
                archive.writestr("xl/sharedStrings.xml", f'<sst xmlns="{namespace}"><si><t>Food</t></si></sst>')
                archive.writestr("xl/worksheets/sheet1.xml", f'<worksheet xmlns="{namespace}"><sheetData><row r="1">{cells}</row><row r="2"><c r="A2" t="s"><v>0</v></c><c r="B2"><v>42.5</v></c></row></sheetData></worksheet>')
            self.assertEqual(list(workbook_records(path)), [{"food_name": "Food", "energy_kcal": "42.5", "excel_row": 2}])

    def test_database_reader_requires_existing_read_only_database(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing.sqlite"
            with self.assertRaises(sqlite3.OperationalError):
                read_database(path)
            self.assertFalse(path.exists())

    def test_exact_rounding_and_goal_oracle(self):
        for fraction, expected in ((Fraction(5, 2), 2), (Fraction(7, 2), 4), (Fraction(9, 2), 4), (Fraction(451, 100), 5)):
            self.assertEqual(round_rational(fraction), expected)
        policy = {"goals": {"endurance": {"carbs_percent": 55, "protein_percent": 20, "fat_percent": 20}},
                  "modifiers": {"none": {"carbs": 1, "protein": 1, "fat": 1}}}
        self.assertEqual(goal_oracle(policy, "endurance", "none", 2000), {
            "carbs_percent": 58, "protein_percent": 21, "fat_percent": 21,
            "carbs_g": 290, "protein_g": 105, "fat_g": 47})


if __name__ == "__main__":
    unittest.main()
