"""Index reviewed claim sets and check documentary consistency, not scholarly truth.

The assessments below apply to bounded claim sets, not automatically to every
indexed sentence. Literal prose/abstract sentences, list items, captions, tables,
diagrams and math receive source spans and shared exact/curated concept IDs.
This is not a full TeX parser, individual scholarly adjudication or clinical review.
"""

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

from check_manuscripts import check_document, command_arguments, strip_comments

ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS = ('Journal', 'Conference')
FINAL_BROWSER = 'browser-extended-attempt4.json'

# Explicit review decisions; substantive evidence is linked separately in the report.
REVIEWS = {
    'SCOPE': ('Supported with limitations', 'Engineering/audit case study, not detector novelty or a clinical intervention.', ['dataset-inspection.json', 'nutrition-validation.json', 'recommendations.json']),
    'CITATIONS': ('Supported with limitations', 'Primary-source attribution checked; cached/failed retrieval and preprint status are explicit. No systematic-review or global novelty certificate.', ['citation-review.json']),
    'INFERENCE': ('Supported with limitations', 'Source/configuration and mocked API tests support the operating contract, not independent accuracy or a new live deployment measurement.', ['checks/backend-deployment-1.json', 'checks/backend-architecture-1.json', 'deployment-evidence.json']),
    'NUTRITION': ('Supported with limitations', 'Workbook/import reconciliation and fixed-database lookup checks are separate from unresolved recipe equivalence.', ['nutrition-validation.json', 'citation-review.json']),
    'ARITHMETIC': ('Supported with limitations', 'Independent arithmetic results and recorded discrepancies bound the numerical description; policy correctness remains unreviewed.', ['arithmetic-validation.json']),
    'JOURNAL': ('Supported with limitations', 'Saved-only totals and storage behavior are software properties; no measured consumption or user-benefit evidence.', ['checks/frontend-unit-1.json', 'checks/browser-1.json', FINAL_BROWSER]),
    'ADVICE': ('Supported with limitations', 'Mocked transport/context checks and fallback triage do not assess medical suitability or clinical efficacy.', ['recommendations.json', 'checks/browser-1.json', FINAL_BROWSER]),
    'DATASET': ('Reproduced', 'Fresh full census and independent aggregation validate recorded membership/counts, not original-photo independence or semantic annotation truth.', ['dataset-inspection.json', 'dataset-audit-command.json']),
    'GROUPING': ('Supported with limitations', 'Fresh grouping/assignment reproduction checks known identities; heuristic ancestry and perceptual candidates require review.', ['dataset-inspection.json', 'dataset-grouped-command.json']),
    'MAPPING': ('Supported with limitations', 'Availability is reproduced over the fixed vocabulary. Independent correct-match judgments are not available.', ['nutrition-validation.json']),
    'TESTS': ('Supported with limitations', 'Recorded local suites support enumerated scenarios only. Windows test environment differs from the locked Linux deployment.', ['checks/backend-deployment-1.json', 'checks/backend-architecture-1.json', 'checks/frontend-unit-1.json', 'checks/browser-1.json', FINAL_BROWSER]),
    'LIMITS': ('Supported with limitations', 'These statements delimit evidence; they do not estimate unknown error, safety, or benefit rates.', ['dataset-inspection.json', 'nutrition-validation.json', 'recommendations.json']),
    'PROPOSED': ('Proposed', 'Expert review, independent evaluation, retraining, live pilots and participant studies remain behind separate approval/resource gates.', []),
    'ACCESS': ('Supported with limitations', 'Pinned application source and tracked summaries are distinguished from uncommitted validation tooling and ignored full manifests. No license grant.', ['baseline.json']),
    'APPROVAL': ('Awaiting qualified review/approval', 'Author consent, rights, clinical judgments and any institutional-review decisions must come from the appropriate people.', []),
    'HISTORY': ('Historical only', 'CSV/notebook transcription is checked, but execution-time model/data identity and final-model predictions are insufficient for independent AP recomputation.', ['training-results.json']),
    'VERSIONS': ('Supported with limitations', 'Artifact hashes and production lockfile settings are distinct from the local validation environment and current hosting state.', ['baseline.json', 'training-results.json', 'deployment-evidence.json']),
    'VALIDATION': ('Supported with limitations', 'Additional source reconciliation, independent arithmetic calculations and mocked provider tests are completed implementation/audit evidence, not clinical or independent detector validation.', ['nutrition-validation.json', 'arithmetic-validation.json', 'recommendations.json', 'training-results.json', FINAL_BROWSER]),
}

# Explicit editorial navigation anchors. Matching an anchor relates propositions;
# it does not decide their truth, direction, completeness, or equivalence.
CONCEPTS = (
    ('journal.saved-only-totals', 'JOURNAL', r'explicitly saved|saved-only|unsaved scan|only saved meals'),
    ('journal.storage-privacy', 'JOURNAL', r'version-1|browser (?:storage|history|journal)|persisted journal|health selections and photos'),
    ('journal.storage-failure', 'JOURNAL', r'corrupt|unsupported storage|storage fail|saving fails|saving is paused'),
    ('journal.identity-and-day', 'JOURNAL', r'draft identity|original (?:timestamp|date)|local midnight|focus/visibility|new drafts?'),
    ('nutrition.missing-is-not-zero', 'ARITHMETIC', r'unknown nutrients|known subtotal|missingness|unavailable row|not assumed to equal zero'),
    ('nutrition.estimated-grams', 'ARITHMETIC', r'user-estimated (?:grams|weight)|weights? default|25 to 1,000|per-100-g.*(?:vector|values)'),
    ('mapping.availability-not-correctness', 'MAPPING', r'availability|lookup covers|lookup is available|correct(?:ness| match)|recipe equivalence'),
    ('mapping.fallback-order', 'NUTRITION', r'containment|alias variations|variation order|hash seeds|precomputed mappings'),
    ('advice.context-consistency', 'ADVICE', r'echoed (?:health key|context)|context.*(?:hides|matching)|changing context|superseded requests|late (?:responses|results)|out-of-order'),
    ('advice.limited-inputs', 'ADVICE', r'(?:prompt|endpoint|advice request|neither stage).*(?:receives|retains|contain|grams|per-100-g)'),
    ('advice.provider-and-fallback', 'ADVICE', r'groq|local (?:fallback|templates)|provider (?:capacity|timeout)|sdk/mock'),
    ('dataset.exact-overlap', 'DATASET', r'\\AuditDuplicate|cross-partition groups|exact (?:overlap|identit|duplicate)'),
    ('dataset.candidate-lineage', 'GROUPING', r'candidate (?:lineage|group|partition)|filename famil|quarantine|\\Candidate'),
    ('detector.operating-contract', 'INFERENCE', r'confidence.*0\.25|image size 640|processed image|decoded pixels|analysis budget|worker'),
    ('scope.clinical-evidence-unresolved', 'APPROVAL', r'not clinical validation|not a safety guarantee|clinically (?:safe|validated)|clinical (?:safety|efficacy|validity)|qualified.*review'),
    ('scope.independent-detector-evidence', 'PROPOSED', r'independent (?:detector|accuracy|evaluation)|untouched external|retrain|new detector claims'),
)

PRIMARY_OVERRIDES = (
    ('author-or-permission-approval', 'APPROVAL', r'^(?:authors must|authorship,|the author list|the authors must)|(?:permissions|rights|author).*remain.*(?:confirm|decision)|institutional-review'),
    ('prospective-protocol', 'PROPOSED', r'^(?:before new detector claims|for mapping correctness|freeze the database|review candidate group|qualified reviewers|evaluate recommendation content|a usability or longitudinal study|report per-class|use uncertainty procedures)'),
    ('saved-journal-operation', 'JOURNAL', r'^(?:only explicitly saved|an unsaved scan|saving updates|starting a new scan|new scans|the current day|day selection|version-1 browser|unsupported or corrupt storage|corrupt or unsupported storage)'),
    ('software-test-description', 'TESTS', r'^(?:backend/contract tests|backend unit/contract tests|desktop and 360|passing these scenarios|recorded checks passed|the recorded source-revision checks)'),
    ('lookup-implementation', 'NUTRITION', r'^(?:sqlite contains|the offline builder|runtime (?:first|uses)|the local workbook|offline construction)'),
    ('prospective-packet-implemented', 'VALIDATION', r'^(?:a new version-2 packet|the new version-2 packet|the current scorer|the preserved version-1 template)'),
)


def category(section, subsection):
    title = f'{section} / {subsection}'.lower()
    if 'validation follow-up' in title:
        return 'VALIDATION'
    if 'purpose of' in title or 'transparency and author' in title:
        return 'APPROVAL'
    if 'historical' in title:
        return 'HISTORY'
    if 'implementation snapshot' in title:
        return 'VERSIONS'
    if 'availability and review' in title or 'data, code' in title:
        return 'ACCESS'
    if 'prospective' in title:
        return 'PROPOSED'
    if 'interpretation' in title or 'limitations and evaluation plan' in title:
        return 'LIMITS'
    if 'related work' in title:
        return 'CITATIONS'
    if any(word in title for word in ('abstract', 'introduction', 'conclusion', 'keywords')):
        return 'SCOPE'
    if 'rq1' in title or 'artifacts and unit' in title or 'scope and strict' in title or 'exact identities' in title:
        return 'DATASET'
    if 'candidate' in title or 'rq2' in title:
        return 'GROUPING'
    if 'lookup availability' in title or 'lookup comparison' in title or 'rq3' in title:
        return 'MAPPING'
    if 'software verification' in title or 'rq4' in title:
        return 'TESTS'
    if 'goals and health' in title or 'advice context' in title:
        return 'ADVICE'
    if 'portion estimates' in title or 'nutrition, grams' in title:
        return 'ARITHMETIC'
    if 'nutrition lookup' in title:
        return 'NUTRITION'
    if 'scope and inference' in title or 'detection and processed' in title:
        return 'INFERENCE'
    raise ValueError(f'Unreviewed section: {section}/{subsection}')


def blocks(text):
    """Literal manuscript blocks; not a full TeX expansion engine."""
    lines = strip_comments(text).splitlines()
    section, subsection = 'Preamble', ''
    buffer, start = [], 0
    environment = None
    result = []

    def flush():
        if buffer:
            raw = '\n'.join(buffer).strip()
            if raw and section != 'Preamble':
                first = buffer[0]
                result.append({'line': start, 'end_line': start + len(buffer) - 1,
                               'start_column': len(first) - len(first.lstrip()) + 1,
                               'section': section, 'subsection': subsection, 'text': raw,
                               'block_type': environment.rstrip('*') if environment else 'prose'})
            buffer.clear()

    for number, line in enumerate(lines, 1):
        stripped = line.strip()
        heading = re.fullmatch(r'\\(subsection|section)\*?\{(.*)\}', stripped)
        if heading and not environment:
            flush()
            if heading[1] == 'section':
                section, subsection = heading[2], ''
            else:
                subsection = heading[2]
            continue
        opening = re.match(r'\\begin\{(abstract|IEEEkeywords|figure\*?|table\*?|equation\*?|align\*?|enumerate|itemize|quote|center)\}', stripped)
        if opening and not environment:
            flush()
            environment = opening[1]
            if environment in ('abstract', 'IEEEkeywords'):
                section, subsection = environment, ''
        if environment:
            if not buffer:
                start = number
            buffer.append(line)
            if f'\\end{{{environment}}}' in stripped:
                flush()
                environment = None
            continue
        if not stripped:
            flush()
        elif stripped.startswith(('\\linenumbers', '\\modulolinenumbers', '\\appendices', '\\bibliograph', '\\end{document}')):
            flush()
        else:
            if not buffer:
                start = number
            buffer.append(line)
    flush()
    return result


def balanced_commands(text, name):
    """Content offsets of literal braced commands, including nested TeX braces."""
    pattern = rf'\\{name}(?![A-Za-z])(?:\s*\[[^\]]*\])?\s*\{{'
    for match in re.finditer(pattern, text):
        depth = 1
        start = match.end()
        index = start
        while index < len(text) and depth:
            escaped = index > 0 and text[index - 1] == '\\'
            if text[index] == '{' and not escaped:
                depth += 1
            elif text[index] == '}' and not escaped:
                depth -= 1
            index += 1
        if depth:
            raise ValueError(f'Unclosed literal \\{name} argument')
        yield start, index - 1


def sentence_ranges(text, start=0, end=None):
    """Bounded literal sentence segmentation; punctuation inside math is masked."""
    end = len(text) if end is None else end
    mask = list(text)
    for match in re.finditer(r'(?<!\\)\$(?!\$).*?(?<!\\)\$', text, re.S):
        mask[match.start():match.end()] = ['_'] * (match.end() - match.start())
    masked = ''.join(mask)
    cursor = start
    for match in re.finditer(r'[.!?](?=\s+[^\s])', masked[start:end]):
        stop = start + match.end()
        # Decimal/version punctuation is never a boundary; common prose abbreviations
        # need an explicit exception in this intentionally small grammar.
        previous = text[max(cursor, stop - 5):stop].lower()
        if previous.endswith(('e.g.', 'i.e.', ' et al.', 'fig.', 'eq.')):
            continue
        yield cursor, stop
        cursor = stop
    if text[cursor:end].strip():
        yield cursor, end


def atomic_units(block):
    """Return intentionally overlapping containers/captions/inline-math spans."""
    raw = block['text']
    kind = block['block_type']
    ranges = []
    if kind in ('figure', 'table', 'equation', 'align'):
        ranges.append((0, len(raw), {'figure': 'diagram', 'table': 'table', 'equation': 'display_math', 'align': 'display_math'}[kind]))
        if kind in ('figure', 'table'):
            ranges += [(start, end, 'caption') for start, end in balanced_commands(raw, 'caption')]
        if kind == 'table':
            # Retain headers and data rows separately; the table container preserves
            # alignment specifications, rules and every literal cell as well.
            table_body = re.search(r'\\begin\{tabularx?\}', raw)
            table_end = re.search(r'\\end\{tabularx?\}', raw)
            if table_body and table_end:
                for match in re.finditer(r'[^\n]*&[^\n]*\\\\', raw[table_body.end():table_end.start()]):
                    ranges.append((table_body.end() + match.start(), table_body.end() + match.end(), 'table_row'))
    else:
        opening = re.match(r'\\begin\{[^}]+\}(?:\[[^\]]*\])?', raw)
        closing = re.search(r'\\end\{[^}]+\}\s*$', raw)
        start = opening.end() if opening else 0
        end = closing.start() if closing else len(raw)
        if kind in ('enumerate', 'itemize'):
            items = list(re.finditer(r'\\item(?:\[[^\]]*\])?\s*', raw[start:end]))
            if not items:
                raise ValueError('List has no literal items')
            for index, item in enumerate(items):
                item_start = start + item.end()
                item_end = start + items[index + 1].start() if index + 1 < len(items) else end
                ranges += [(a, b, 'list_item') for a, b in sentence_ranges(raw, item_start, item_end)]
        elif kind == 'IEEEkeywords':
            ranges.append((start, end, 'keywords'))
        else:
            unit_kind = {'abstract': 'abstract_sentence', 'center': 'front_matter', 'quote': 'quote'}.get(kind, 'prose_sentence')
            ranges += [(a, b, unit_kind) for a, b in sentence_ranges(raw, start, end)]
    # Inline math is independently locatable, even when inside a sentence/table.
    ranges += [(match.start(), match.end(), 'inline_math') for match in re.finditer(r'(?<!\\)\$(?!\$).*?(?<!\\)\$', raw, re.S)]
    units = []
    for start, end, unit_kind in ranges:
        start += len(raw[start:end]) - len(raw[start:end].lstrip())
        end -= len(raw[start:end]) - len(raw[start:end].rstrip())
        if start >= end:
            continue
        prefix = raw[:start]
        ending = raw[:end]
        line = block['line'] + prefix.count('\n')
        column = len(prefix.rsplit('\n', 1)[-1]) + (block['start_column'] if '\n' not in prefix else 1)
        end_line = block['line'] + ending.count('\n')
        end_column = len(ending.rsplit('\n', 1)[-1]) + (block['start_column'] - 1 if '\n' not in ending else 0)
        units.append({'text': raw[start:end], 'unit_type': unit_kind,
                      'span': {'start_line': line, 'start_column': column, 'end_line': end_line, 'end_column': end_column},
                      'block_type': kind, 'block_start_line': block['line'], 'block_end_line': block['end_line']})
    return units


def navigation_text(text):
    # Strip formatting commands, not their contents, for curated textual anchors.
    text = re.sub(r'\\(?:emph|textbf|texttt|code|path)\{([^{}]*)\}', r'\1', text)
    return ' '.join(text.split())


def occurrence_review(section, subsection, unit):
    primary = category(section, subsection)
    section_category = primary
    text = navigation_text(unit['text'])
    applied = None
    # Historical claims stay historical even when they discuss future evidence.
    if primary != 'HISTORY':
        if unit['unit_type'] in ('display_math', 'inline_math') and primary == 'ADVICE':
            primary, applied = 'ARITHMETIC', 'policy-math-is-arithmetic-not-clinical-validation'
        elif unit['unit_type'] == 'front_matter':
            primary, applied = 'APPROVAL', 'supervisor-review-front-matter'
        else:
            for name, target, pattern in PRIMARY_OVERRIDES:
                if re.search(pattern, text, re.I):
                    primary, applied = target, name
                    break
    concepts = [identifier for identifier, _, pattern in CONCEPTS if re.search(pattern, text, re.I)]
    tags = {primary, section_category} | {tag for _, tag, pattern in CONCEPTS if re.search(pattern, text, re.I)}
    if primary == 'HISTORY':
        tags.add('HISTORY')
    assessment, note, _ = REVIEWS[primary]
    # Section-level judgments are not silently upgraded to individual decisions.
    disposition = assessment if primary in ('PROPOSED', 'APPROVAL', 'HISTORY') else 'Indexed; claim-set assessment only'
    return {'claim_set_id': primary, 'claim_set_ids': sorted(tags), 'primary_override': applied,
            'shared_concept_ids': [f'CONCEPT:{key}' for key in concepts],
            'claim_set_disposition': assessment, 'disposition': disposition,
            'assessment': note, 'individual_review_status': 'not_individually_adjudicated',
            'clinical_review_status': 'pending_qualified_review' if section_category == 'ADVICE' or re.search(r'clinical|medical|diabet|health.context|dietary|prescri|suitabil|appropriat', text, re.I) else 'not_assessed_by_this_index'}


def numeric_definitions(text):
    return dict(re.findall(r'\\(?:newcommand|renewcommand|providecommand)\*?\{\\([A-Za-z]+)\}\{([0-9][0-9,. ]*)\}', text))


def file_identities(root, paths):
    result, missing = [], []
    for name in sorted(set(paths)):
        path = root / name
        if not path.is_file():
            missing.append(name)
        else:
            data = path.read_bytes()
            result.append({'path': name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
    return result, missing


def build_ledger(root, run_id):
    reports = root / 'research/evidence' / run_id
    occurrences = []
    bibliographies = []
    errors = []
    sources = ['scripts/validate_paper_claims.py']
    definitions_by_document = {}
    coverage = {}
    for kind in DOCUMENTS:
        document = root / f'Research_Paper_{kind}/main.tex'
        text = document.read_text(encoding='utf-8')
        errors.extend(check_document(document).errors)
        bibliography_path = document.parent / 'bibliography/references.bib'
        generated_path = document.parent / 'generated/evidence.tex'
        sources += [path.relative_to(root).as_posix() for path in (document, bibliography_path, generated_path)]
        definitions = numeric_definitions(generated_path.read_text(encoding='utf-8'))
        definitions_by_document[kind] = definitions
        bib = bibliography_path.read_text(encoding='utf-8')
        bibliographies.append(bib)
        entries = set(re.findall(r'@\w+\s*\{\s*([^,]+),', strip_comments(bib)))
        cited = {key.strip() for group in command_arguments(strip_comments(text), 'cite') for key in group.split(',')}
        if entries != cited:
            errors.append(f'{kind}: missing/unused bibliography keys: {sorted(entries ^ cited)}')
        document_blocks = blocks(text)
        document_units = []
        for block in document_blocks:
            units = atomic_units(block)
            for ordinal, unit in enumerate(units, 1):
                review = occurrence_review(block['section'], block['subsection'], unit)
                evidence = sorted({name for tag in review['claim_set_ids'] for name in REVIEWS[tag][2]})
                normalized = ' '.join(unit['text'].split())
                identifier = hashlib.sha256(normalized.encode()).hexdigest()
                numeric_macros = sorted(set(re.findall(r'\\((?:Audit|Candidate|Coverage|Nutrition|Mapping)[A-Za-z]+)', unit['text'])))
                missing_macros = set(numeric_macros) - definitions.keys()
                if missing_macros:
                    errors.append(f'{kind}: unresolved numeric macros: {sorted(missing_macros)}')
                labels = command_arguments(block['text'], 'label')
                anchors = [f'{block["block_type"].upper()}:{label}' for label in labels] if block['block_type'] in ('table', 'figure', 'equation', 'align') else []
                occurrence = {**review, **unit,
                              'canonical_claim_ids': [f'EXACT:{identifier}', *review['shared_concept_ids']],
                              'shared_block_anchors': anchors,
                              'occurrence_id': f'{kind[0]}-{block["line"]}-{ordinal}',
                              'path': document.relative_to(root).as_posix(), 'line': unit['span']['start_line'],
                              'section': block['section'], 'subsection': block['subsection'],
                              'text_sha256': hashlib.sha256(unit['text'].encode()).hexdigest(),
                              'numeric_literals': re.findall(r'(?<![A-Za-z])\d+(?:[.,]\d+)*', unit['text']),
                              'numeric_macros': numeric_macros,
                              'expanded_numeric_macros': {name: definitions.get(name) for name in numeric_macros},
                              'evidence': [f'research/evidence/{run_id}/{item}' for item in evidence]}
                occurrences.append(occurrence)
                document_units.append(occurrence)
        coverage[kind] = {'literal_blocks': len(document_blocks), 'units_by_type': dict(Counter(unit['unit_type'] for unit in document_units)),
                          'indexed_block_spans': [{'start_line': block['line'], 'end_line': block['end_line'], 'block_type': block['block_type']} for block in document_blocks],
                          'excluded': 'Author/title/package preamble, section headings and bibliography/line-number commands are metadata, not adjudicated claims.',
                          'overlap': 'Table/diagram containers overlap their captions/cells/inline math by design; counts are index units, not independent empirical claims.'}
    if bibliographies[0] != bibliographies[1]:
        errors.append('Bibliographies differ between papers')
    if definitions_by_document['Journal'] != definitions_by_document['Conference']:
        errors.append('Expanded generated numeric definitions differ between papers')
    citation_path = reports / 'citation-review.json'
    if citation_path.is_file():
        citation_report = json.loads(citation_path.read_text(encoding='utf-8'))
        reviewed_keys = {item['key'] for item in citation_report['entries']}
        if entries != reviewed_keys:
            errors.append(f'Citation review missing/extra keys: {sorted(entries ^ reviewed_keys)}')
    evidence_paths = {path for claim in occurrences for path in claim['evidence']}
    evidence_identity, missing = file_identities(root, evidence_paths)
    if missing:
        errors.append(f'Missing claim evidence files: {missing}')
    source_identity, missing_sources = file_identities(root, sources)
    if missing_sources:
        errors.append(f'Missing source files: {missing_sources}')
    # A deliberately historical/unverified deployment report is valid boundary
    # evidence; passing test receipts, on the other hand, must actually pass.
    for identity in evidence_identity:
        name = identity['path']
        if '/checks/' in name or name.endswith(FINAL_BROWSER):
            receipt = json.loads((root / name).read_text(encoding='utf-8'))
            if receipt.get('status') not in ('pass', 'passed') or receipt.get('exit_code', 0) != 0:
                errors.append(f'Claim links a non-passing selected test receipt: {name}')
    return {'schema_version': 2, 'run_id': run_id,
            'granularity': 'Literal prose and abstract sentences, list-item sentences, captions, table rows, whole tables/diagrams/display math and inline math, with exact source spans. Limited grammar, not arbitrary TeX expansion or complete semantic atomization.',
            'assessment_method': 'Explicit bounded claim-set editorial assessments; per-occurrence routing/anchors aid review but do not individually adjudicate truth. Test success is never promoted to scientific or clinical approval.',
            'concept_method': 'EXACT IDs normalize whitespace only. Curated CONCEPT IDs connect related propositions, not necessarily equivalent wording or truth. Shared TeX labels are block anchors, not semantic proofs.',
            'source_identities': source_identity, 'evidence_identities': evidence_identity,
            'numeric_definitions': definitions_by_document, 'coverage': coverage,
            'claims': occurrences, 'counts': dict(Counter(item['disposition'] for item in occurrences)),
            'structural_errors': errors}


def check_ledger(root, ledger):
    regenerated = build_ledger(root, ledger['run_id'])
    for key in ('schema_version', 'claims', 'counts', 'structural_errors', 'source_identities', 'evidence_identities', 'numeric_definitions', 'coverage'):
        if regenerated[key] != ledger[key]:
            raise ValueError('Manuscript/review ledger drift; review the changed claims before refreshing')
    if ledger['structural_errors']:
        raise ValueError(str(ledger['structural_errors']))
    return len(ledger['claims'])


def write_ledger(path, report):
    """Check missing/failed evidence and structural issues before creating output."""
    if report['structural_errors']:
        raise ValueError(str(report['structural_errors']))
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(report, stream, indent=2, ensure_ascii=False)
        stream.write('\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--output-name', default='claims.json')
    args = parser.parse_args()
    if not re.fullmatch(r'validation-[a-z0-9-]+', args.run_id):
        parser.error('Invalid run ID')
    if not re.fullmatch(r'claims(?:-[a-z0-9-]+)?\.json', args.output_name):
        parser.error('Invalid ledger filename')
    path = ROOT / 'research/evidence' / args.run_id / args.output_name
    if args.check:
        count = check_ledger(ROOT, json.loads(path.read_text(encoding='utf-8')))
        print(f'Claim ledger verified: {count}')
        return
    report = build_ledger(ROOT, args.run_id)
    report['reviewed_at_utc'] = datetime.now(timezone.utc).isoformat()
    write_ledger(path, report)
    print(f'Indexed {len(report["claims"])} claim occurrences; no clinical/submission approval implied')


if __name__ == '__main__':
    main()
