"""Offline structural checks for the two supervisor-review LaTeX manuscripts.

This deliberately limited scanner does not execute TeX or validate references'
contents, scholarly claims, clinical suitability, authorship, or permissions.
It supports the literal commands used in these manuscripts, not arbitrary TeX
macro expansion. Generated numeric macros are expanded for approximate abstract
word counts. Files are only read; missing or stale artifacts are never repaired.
"""

import argparse
from collections import Counter
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
import re

import generate_paper_evidence

ROOT = Path(__file__).resolve().parents[1]
MANUSCRIPTS = tuple(Path(f"Research_Paper_{kind}/main.tex") for kind in ("Journal", "Conference"))
REVIEW_IDENTITY = Path("research/evidence/manuscript-review.json")
LIMITATION = (
    "Structural consistency only: NOT scholarly, clinical, authorship, permission, "
    "or submission approval. No network, providers, or TeX execution."
)


@dataclass
class CheckResult:
    document: Path
    abstract_words: int | None
    errors: list[str]


def strip_comments(text):
    """Remove unescaped percent comments while preserving escaped percentages."""
    cleaned = []
    for line in text.splitlines():
        for index, character in enumerate(line):
            if character != "%":
                continue
            before = index - 1
            while before >= 0 and line[before] == "\\":
                before -= 1
            if (index - before - 1) % 2 == 0:
                line = line[:index]
                break
        cleaned.append(line)
    return "\n".join(cleaned)


def command_arguments(text, names):
    pattern = rf"\\(?:{names})\*?(?![A-Za-z])(?:\s*\[[^\]]*\])*\s*\{{([^{{}}]*)\}}"
    return re.findall(pattern, text)


def abstract_word_count(source):
    """Count approximate prose words after expanding literal numeric macros."""
    abstracts = re.findall(r"\\begin\s*\{abstract\}(.*?)\\end\s*\{abstract\}", source, re.S)
    if len(abstracts) != 1:
        return None
    macros = dict(re.findall(
        r"\\(?:newcommand|renewcommand|providecommand)\*?\s*\{\\([A-Za-z]+)\}"
        r"\s*\{([0-9][0-9,.\s]*)\}", source,
    ))
    abstract = re.sub(
        r"\\([A-Za-z]+)(?:\{\})?",
        lambda match: macros.get(match[1], match[0]),
        abstracts[0],
    )
    abstract = re.sub(r"\\cite\w*\*?(?:\s*\[[^\]]*\])*\s*\{[^{}]*\}", " ", abstract)
    abstract = re.sub(r"\\[A-Za-z]+\*?", " ", abstract)
    # Keep thousands, decimal numbers, contractions and hyphenated words intact.
    return len(re.findall(r"[A-Za-z0-9]+(?:[.,'’\-][A-Za-z0-9]+)*", abstract))


def check_text(source, bibliographies):
    """Check already-expanded literal source against named bibliography texts."""
    source = strip_comments(source)
    errors = []
    entries = []
    for name, text in bibliographies.items():
        cleaned = strip_comments(text)
        for kind, key in re.findall(r"@([A-Za-z]+)\s*[({]\s*([^\s,{}()]+)\s*,", cleaned):
            if kind.lower() not in {"comment", "preamble", "string"}:
                entries.append(key)
        if re.search(r"\b[A-Za-z0-9_:-]*placeholder[A-Za-z0-9_:-]*\b", cleaned, re.I):
            errors.append(f"Placeholder BibTeX marker in {name}")
    keys = set(entries)
    for key, count in sorted(Counter(entries).items()):
        if count > 1:
            errors.append(f"Duplicate bibliography key: {key}")
    for argument in command_arguments(source, "cite|citet|citep|citealp|citeauthor|citeyear|nocite"):
        for key in (part.strip() for part in argument.split(",")):
            if key and key != "*" and key not in keys:
                errors.append(f"Missing bibliography key: {key}")

    labels = command_arguments(source, "label")
    for label, count in sorted(Counter(labels).items()):
        if count > 1:
            errors.append(f"Duplicate label: {label}")
    for argument in command_arguments(source, "ref|eqref|pageref|autoref|cref|Cref"):
        for label in (part.strip() for part in argument.split(",")):
            if label not in labels:
                errors.append(f"Missing reference target: {label}")

    stack = []
    for command, environment in re.findall(r"\\(begin|end)\s*\{([^{}]+)\}", source):
        if command == "begin":
            stack.append(environment)
        elif not stack:
            errors.append(f"Unexpected environment end: {environment}")
        elif stack[-1] != environment:
            errors.append(f"Mismatched environment end: expected {stack[-1]}, found {environment}")
        else:
            stack.pop()
    errors.extend(f"Unclosed environment: {environment}" for environment in reversed(stack))

    if re.search(r"\[(?:student|your|author)\s+email\]|your[._-]?email@", source, re.I):
        errors.append("Placeholder author email in manuscript")
    if re.search(r"\b[A-Za-z0-9_:-]*placeholder[A-Za-z0-9_:-]*\b", source, re.I):
        errors.append("Placeholder manuscript/BibTeX marker in source")
    words = abstract_word_count(source)
    if words is None:
        errors.append("Require exactly one complete abstract environment")
    elif not 150 <= words <= 250:
        errors.append(f"Abstract has approximately {words} words; require 150-250")
    return words, list(dict.fromkeys(errors))


def check_document(document):
    """Expand literal input/include files and read bibliography dependencies."""
    document = Path(document).resolve()
    base = document.parent
    errors = []

    def expand(path, ancestors):
        path = path.resolve()
        if path in ancestors:
            errors.append(f"Recursive input cycle: {path.name}")
            return ""
        try:
            text = strip_comments(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError) as exc:
            errors.append(f"Missing or unreadable input: {path} ({type(exc).__name__})")
            return ""

        def replace(match):
            target = base / match[1].strip()
            if not target.suffix:
                target = target.with_suffix(".tex")
            return expand(target, (*ancestors, path))

        return re.sub(r"\\(?:input|include)\s*\{([^{}]+)\}", replace, text)

    source = expand(document, ())
    bibliographies = {}
    arguments = command_arguments(source, "bibliography")
    if not arguments:
        errors.append("No bibliography declaration found")
    for argument in arguments:
        for name in (part.strip() for part in argument.split(",")):
            path = base / name
            if not path.suffix:
                path = path.with_suffix(".bib")
            try:
                bibliographies[str(path)] = path.read_text(encoding="utf-8")
            except (OSError, UnicodeError) as exc:
                errors.append(f"Missing or unreadable bibliography: {path} ({type(exc).__name__})")
    words, text_errors = check_text(source, bibliographies)
    return CheckResult(document, words, errors + text_errors)


def check_review_identity(root):
    """Verify review-time file identity, not historical execution or correctness."""
    root = Path(root).resolve()
    report = json.loads((root / REVIEW_IDENTITY).read_text(encoding="utf-8"))
    if not isinstance(report, dict) or type(report.get("schema_version")) is not int or report["schema_version"] != 1:
        raise ValueError("Review identity requires schema_version 1")
    records = report.get("files")
    if not isinstance(records, list) or not records:
        raise ValueError("Review identity requires a nonempty files list")
    checked_paths = set()
    files = []
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("Each review identity file must be an object")
        name, expected = record.get("path"), record.get("sha256")
        if not isinstance(name, str) or not name or any(character in name for character in "\\:\0"):
            raise ValueError("Unsafe review identity path: require a relative POSIX file path")
        relative = PurePosixPath(name)
        if (relative.is_absolute() or PureWindowsPath(name).drive
                or any(part in {"", ".", ".."} for part in name.split("/"))):
            raise ValueError(f"Unsafe review identity path: {name}")
        resolved = (root / relative).resolve()
        if not resolved.is_relative_to(root):
            raise ValueError(f"Review identity path escapes repository root: {name}")
        if resolved in checked_paths:
            raise ValueError(f"Duplicate review identity path: {name}")
        checked_paths.add(resolved)
        if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise ValueError(f"Invalid canonical SHA-256 for review identity: {name}")
        files.append((name, resolved, expected))
    for name, path, expected in files:
        try:
            with path.open("rb") as stream:
                actual = hashlib.file_digest(stream, "sha256").hexdigest()
        except OSError as exc:
            raise ValueError(f"Missing or unreadable review identity file: {name}") from exc
        if actual != expected:
            raise ValueError(f"Review identity hash drift: {name}")
    return len(files)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="Repository root; default is this checkout")
    args = parser.parse_args(argv)
    print(LIMITATION)
    failed = False
    try:
        generate_paper_evidence.generate(root=args.root, check=True)
    except (OSError, ValueError) as exc:
        print(f"FAIL generated numeric evidence: {exc}")
        failed = True
    try:
        checked = check_review_identity(args.root)
        print(f"PASS review-time artifact identity: {checked} files; not historical execution proof")
    except (OSError, ValueError) as exc:
        print(f"FAIL review-time artifact identity: {exc}")
        failed = True
    for relative in MANUSCRIPTS:
        result = check_document(args.root / relative)
        print(f"{'FAIL' if result.errors else 'PASS'} {relative.as_posix()}: "
              f"approximately {result.abstract_words} abstract words")
        for error in result.errors:
            print(f"  - {error}")
        failed |= bool(result.errors)
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
