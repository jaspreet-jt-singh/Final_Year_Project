"""Synthetic offline structural-checker tests; no research data or TeX runs."""

from contextlib import redirect_stdout
import hashlib
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from check_manuscripts import (
    MANUSCRIPTS, REVIEW_IDENTITY, abstract_word_count, check_document,
    check_review_identity, check_text, main, strip_comments,
)


def manuscript(body="", abstract=None):
    abstract = abstract if abstract is not None else " ".join(["word"] * 180)
    return ("\\documentclass{article}\n\\begin{document}\n\\begin{abstract}\n"
            + abstract + "\n\\end{abstract}\n" + body
            + "\n\\bibliography{references}\n\\end{document}\n")


BIB = {"references.bib": "@article{known, title={A synthetic reference}, year={2026}}"}


def review_fixture(root):
    path = root / "artifact.txt"
    content = b"Synthetic review artifact\n"
    path.write_bytes(content)
    report = {"schema_version": 1, "files": [{
        "path": "artifact.txt", "sha256": hashlib.sha256(content).hexdigest(),
    }]}
    (root / REVIEW_IDENTITY).parent.mkdir(parents=True, exist_ok=True)
    (root / REVIEW_IDENTITY).write_text(json.dumps(report), encoding="utf-8")
    return report


class ManuscriptTests(unittest.TestCase):
    def test_passing_document_and_commented_bad_commands(self):
        source = manuscript(r"\section{Method}\label{sec:method} See \ref{sec:method} \cite[p. 1]{known}."
                            + "\n% \\cite{missing} \\label{sec:method} \\end{bad}\n")
        self.assertEqual(check_text(source, BIB), (180, []))

    def test_percent_comments_respect_escaping(self):
        self.assertEqual(strip_comments(r"26\% is shown % not this"), r"26\% is shown ")
        self.assertEqual(strip_comments(r"end\\% comment"), "end\\\\")

    def test_missing_and_duplicate_bibliography_keys(self):
        source = manuscript(r"\cite{known, absent} \citep[see][p. 2]{also_absent}")
        bibliography = {**BIB, "second.bib": "@book{known, title={Duplicate}}"}
        errors = check_text(source, bibliography)[1]
        self.assertIn("Missing bibliography key: absent", errors)
        self.assertIn("Missing bibliography key: also_absent", errors)
        self.assertIn("Duplicate bibliography key: known", errors)

    def test_missing_references_and_duplicate_labels(self):
        source = manuscript(r"\label{x}\label{x}\ref{absent}\eqref{equation}")
        errors = check_text(source, BIB)[1]
        self.assertIn("Duplicate label: x", errors)
        self.assertIn("Missing reference target: absent", errors)
        self.assertIn("Missing reference target: equation", errors)

    def test_misnested_and_unclosed_environments_fail(self):
        source = manuscript(r"\begin{table}\begin{tabular}\end{table}\end{tabular}")
        errors = check_text(source, BIB)[1]
        self.assertTrue(any("Mismatched environment end" in error for error in errors))
        self.assertTrue(any("Unclosed environment" in error for error in errors))
        self.assertTrue(any("Unexpected environment end" in error
                            for error in check_text(r"\end{unexpected}", BIB)[1]))

    def test_numeric_macro_expansion_and_abstract_boundaries(self):
        source = r"\newcommand{\ImageCount}{48,693}" + manuscript(abstract=r"\ImageCount{} " + "word " * 149)
        self.assertEqual(abstract_word_count(source), 150)
        self.assertEqual(check_text(source, BIB)[1], [])
        self.assertEqual(check_text(manuscript(abstract="word " * 250), BIB)[1], [])
        for length in (149, 251):
            self.assertTrue(any("require 150-250" in error
                                for error in check_text(manuscript(abstract="word " * length), BIB)[1]))
        duplicate = manuscript() + r"\begin{abstract}Second abstract\end{abstract}"
        self.assertIn("Require exactly one complete abstract environment", check_text(duplicate, BIB)[1])

    def test_placeholder_email_and_bibtex_marker_fail(self):
        errors = check_text(manuscript("Email: [student email] \\cite{indb_placeholder}"),
                            {"references.bib": "@misc{indb_placeholder, title={Pending}}"})[1]
        self.assertIn("Placeholder author email in manuscript", errors)
        self.assertTrue(any("Placeholder BibTeX marker" in error for error in errors))

    def test_literal_inputs_resolve_and_missing_files_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "main.tex"
            (root / "generated").mkdir()
            (root / "generated/evidence.tex").write_text(r"\newcommand{\ImageCount}{48,693}", encoding="utf-8")
            (root / "references.bib").write_text(BIB["references.bib"], encoding="utf-8")
            path.write_text(r"\input{generated/evidence}" + manuscript(
                r"\cite{known}", abstract=r"\ImageCount{} " + "word " * 149), encoding="utf-8")
            result = check_document(path)
            self.assertEqual((result.abstract_words, result.errors), (150, []))
            path.write_text(r"\input{generated/missing.tex}" + manuscript(), encoding="utf-8")
            self.assertTrue(any("Missing or unreadable input" in error for error in check_document(path).errors))
            path.write_text(r"\input{main}" + manuscript(), encoding="utf-8")
            self.assertTrue(any("Recursive input cycle" in error for error in check_document(path).errors))

    def test_missing_bibliography_is_an_error(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "main.tex"
            path.write_text(manuscript(r"\cite{known}"), encoding="utf-8")
            self.assertTrue(any("Missing or unreadable bibliography" in error
                                for error in check_document(path).errors))

    def test_cli_checks_numeric_drift_read_only_and_reports_limits(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            review_fixture(root)
            for relative in MANUSCRIPTS:
                path = root / relative
                path.parent.mkdir()
                path.write_text(manuscript(r"\cite{known}"), encoding="utf-8")
                (path.parent / "references.bib").write_text(BIB["references.bib"], encoding="utf-8")
            output = StringIO()
            with patch("check_manuscripts.generate_paper_evidence.generate") as generate, redirect_stdout(output):
                self.assertEqual(main(["--root", str(root)]), 0)
                generate.assert_called_once_with(root=root, check=True)
            self.assertIn("NOT scholarly, clinical", output.getvalue())
            with patch("check_manuscripts.generate_paper_evidence.generate", side_effect=ValueError("drift")), \
                    redirect_stdout(StringIO()):
                self.assertEqual(main(["--root", str(root)]), 1)


class ReviewIdentityTests(unittest.TestCase):
    def test_valid_manifest_and_current_bytes_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            review_fixture(root)
            self.assertEqual(check_review_identity(root), 1)
            (root / "artifact.txt").write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "hash drift"):
                check_review_identity(root)

    def test_missing_listed_file_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = review_fixture(root)
            report["files"][0]["path"] = "missing.txt"
            (root / REVIEW_IDENTITY).write_text(json.dumps(report), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Missing or unreadable"):
                check_review_identity(root)

    def test_unsafe_paths_rejected_portably(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = review_fixture(root)
            for name in ("../outside", "/absolute", "C:/absolute", "C:relative", "a/../artifact.txt",
                         "a\\..\\outside", "//server/share", "./artifact.txt", "a//b", "file:stream"):
                with self.subTest(path=name):
                    report["files"][0]["path"] = name
                    (root / REVIEW_IDENTITY).write_text(json.dumps(report), encoding="utf-8")
                    with self.assertRaisesRegex(ValueError, "Unsafe review identity path"):
                        check_review_identity(root)

    def test_duplicate_paths_schema_and_noncanonical_digests_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = review_fixture(root)
            report["files"].append(dict(report["files"][0]))
            (root / REVIEW_IDENTITY).write_text(json.dumps(report), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Duplicate review identity path"):
                check_review_identity(root)
            for version in (2, True, "1"):
                report = review_fixture(root)
                report["schema_version"] = version
                (root / REVIEW_IDENTITY).write_text(json.dumps(report), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "schema_version 1"):
                    check_review_identity(root)
            for digest in ("A" * 64, "a" * 63, "z" * 64, None):
                report = review_fixture(root)
                report["files"][0]["sha256"] = digest
                (root / REVIEW_IDENTITY).write_text(json.dumps(report), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "canonical SHA-256"):
                    check_review_identity(root)

    def test_resolved_symlink_escape_rejected_before_hashing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            review_fixture(root)
            original_resolve = Path.resolve

            def resolve(path, *args, **kwargs):
                if path.name == "artifact.txt":
                    return root.parent / "outside.txt"
                return original_resolve(path, *args, **kwargs)

            # Portable simulation: Windows hosts need extra privileges for real symlinks.
            with patch.object(Path, "resolve", resolve):
                with self.assertRaisesRegex(ValueError, "escapes repository root"):
                    check_review_identity(root)


if __name__ == "__main__":
    unittest.main()
