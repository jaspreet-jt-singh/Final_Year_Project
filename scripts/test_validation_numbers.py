"""Synthetic, offline tests for the bounded manuscript number checker."""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from check_validation_numbers import (
    REPORT_DIR,
    Checks,
    check_supplements,
    integer,
    main,
    row_cells,
    run_checks,
    section,
    supplemental_literals,
    table,
    visible_tex,
)


class NumericChecksTests(unittest.TestCase):
    def test_integer_and_scoped_capture_reject_drift_and_duplicate_locations(self):
        self.assertEqual(integer("1,014"), 1014)
        self.assertEqual(integer("Eight"), 8)
        checks = Checks()
        checks.capture("right", "found 1,014 source rows", r"found ([0-9,]+) source rows", 1014, "fixture")
        checks.capture("wrong", "found 1,013 source rows", r"found ([0-9,]+) source rows", 1014, "fixture")
        checks.capture("duplicate", "found 1 found 1", r"found ([0-9]+)", 1, "fixture")
        checks.capture("missing", "unrelated 1,014", r"found ([0-9,]+) source rows", 1014, "fixture")
        self.assertEqual([row["status"] for row in checks.rows], ["pass", "fail", "fail", "fail"])

    def test_section_table_and_comments_are_scoped(self):
        text = visible_tex(
            "\\section{Other}\n999\n\\subsection{Validation follow-up}\n36 cases\n"
            "% 999 cases\n\\section{Next}\n999 cases\n"
            "\\begin{table}\n\\label{target}\nTrain & 51\\\\\n\\end{table}\n"
            "\\begin{table}\n\\label{other}\nTrain & 999\\\\\n\\end{table}\n"
        )
        self.assertEqual(section(text, "Validation follow-up").strip(), "36 cases")
        self.assertEqual(row_cells(table(text, "target"), "Train"), ["51"])
        self.assertEqual(visible_tex(r"50\% retained % comment"), "50\\% retained ")
        with self.assertRaises(ValueError):
            section(text + "\\section{Validation follow-up}", "Validation follow-up")

    def test_ast_never_executes_builder_and_rejects_non_literals(self):
        source = "raise RuntimeError('must never execute')\nSUPPLEMENTAL_NUTRITION_ROWS: list = [{'name': 'A'}]"
        self.assertEqual(supplemental_literals(source), [{"name": "A"}])
        with self.assertRaises(ValueError):
            supplemental_literals("SUPPLEMENTAL_NUTRITION_ROWS = load_values()")
        with self.assertRaises(ValueError):
            supplemental_literals("UNRELATED = []")

    def test_per100g_sources_do_not_accept_changed_value_or_missing_citation(self):
        row = {"name": "Synthetic", "source_url": "https://example.invalid/food", "source_notes": "Per 100 g",
               "calories": 100, "protein_g": 1, "carbs_g": 2, "fat_g": 3}
        citation = {"entries": [{"url": row["source_url"], "key": "synthetic", "status": "fixture",
                                 "per_100g": {key: row[key] for key in ("calories", "protein_g", "carbs_g", "fat_g")}}]}
        source = "SUPPLEMENTAL_NUTRITION_ROWS = " + repr([row])
        checks = Checks()
        check_supplements(checks, citation, source, 1)
        self.assertTrue(all(value["status"] == "pass" for value in checks.rows))
        citation["entries"][0]["per_100g"]["calories"] = 200
        checks = Checks()
        check_supplements(checks, citation, source, 1)
        self.assertTrue(any(value["status"] == "fail" for value in checks.rows))
        checks = Checks()
        check_supplements(checks, {"entries": []}, source, 1)
        self.assertTrue(any(value["status"] == "fail" for value in checks.rows))

    def test_missing_required_evidence_fails_without_writing(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            result = run_checks(root)
            self.assertEqual(result["status"], "fail")
            self.assertIn("FileNotFoundError", result["checks"][0]["observed"])
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(["--root", str(root), "--check"]), 1)
            self.assertEqual(list(root.iterdir()), [])

    def test_check_mode_is_read_only_and_generation_never_overwrites(self):
        passed = {"status": "pass", "summary": {"checks": 1, "failed": 0}, "checks": []}
        with tempfile.TemporaryDirectory() as folder, patch("check_validation_numbers.run_checks", return_value=passed):
            root = Path(folder)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(["--root", str(root), "--check"]), 0)
            self.assertEqual(list(root.iterdir()), [])
            output_dir = root / REPORT_DIR
            output_dir.mkdir(parents=True)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(["--root", str(root)]), 0)
            output = output_dir / "numeric-checks.json"
            before = output.read_bytes()
            self.assertEqual(json.loads(before), passed)
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(["--root", str(root)]), 1)
            self.assertEqual(output.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
