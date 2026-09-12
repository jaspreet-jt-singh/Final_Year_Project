"""Record completed page-by-page layout review and check source/PDF freshness."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
RUN = 'validation-2026-09-12-v1'
REPORTS = ROOT / 'research/evidence' / RUN
NOTES = [
    'Title, authors, abstract, keywords, scope and opening related work legible; columns fit margins.',
    'Workflow branches/caption, equations 1-2, gram/missingness/storage and context text legible without overlap; excluded-item clarification visible.',
    'Tables I-II and source/grouping/result text aligned; direct label-conflict clarification fits columns.',
    'Table III, validation follow-up, limitations, conclusion and narrowed repository availability statement legible.',
    'Disclosure, historical appendix and all 22 bibliography entries complete and readable; URL wrapping remains within columns.',
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    target = REPORTS / 'pdf-review.json'
    if args.check:
        report = json.loads(target.read_text(encoding='utf-8'))
        for document in report['documents']:
            for record in [document['pdf'], *document['sources']]:
                if sha(ROOT / record['path']) != record['sha256']:
                    raise SystemExit(f'Document/review freshness mismatch: {record["path"]}')
        print('Both source/PDF identities match the 23-page review; no scholarly approval implied.')
        return
    journal = json.loads((REPORTS / 'pdf-journal-final-review.json').read_text(encoding='utf-8'))
    if journal['pdf']['sha256'] != sha(ROOT / 'Research_Paper_Journal/main.pdf'):
        raise SystemExit('Journal visual review is stale')
    if sorted(row['page'] for row in journal['page_reviews']) != list(range(1, 19)):
        raise SystemExit('Journal page coverage is incomplete')
    documents = []
    for kind, pages in (('Journal', 18), ('Conference', 5)):
        directory = ROOT / f'Research_Paper_{kind}'
        log = ROOT / '.deployment/research' / kind.lower() / 'main.log'
        content = log.read_text(encoding='utf-8', errors='replace')
        if re.search(r'Overfull|undefined|Rerun to get cross-references', content):
            raise SystemExit(f'Unresolved final build warnings: {kind}')
        if f'({pages} pages,' not in content:
            raise SystemExit(f'Unexpected PDF page count: {kind}')
        pdf = directory / 'main.pdf'
        sources = [directory / name for name in ('main.tex', 'bibliography/references.bib', 'generated/evidence.tex')]
        documents.append({
            'kind': kind, 'pdf': {'path': pdf.relative_to(ROOT).as_posix(), 'sha256': sha(pdf), 'bytes': pdf.stat().st_size, 'pages': pages},
            'sources': [{'path': path.relative_to(ROOT).as_posix(), 'sha256': sha(path)} for path in sources],
            'build_log': {'path': log.relative_to(ROOT).as_posix(), 'sha256': sha(log), 'engine': content.splitlines()[0]},
            'page_reviews': journal['page_reviews'] if kind == 'Journal' else [
                {'page': i, 'observation': note, 'result': 'pass_visual_layout',
                 'render': f'final-conference-{i}.png'} for i, note in enumerate(NOTES, 1)],
        })
    report = {'schema_version': 1, 'run_id': RUN, 'reviewed_at_utc': datetime.now(timezone.utc).isoformat(),
              'reviewer_role': 'AI-assisted visual artifact/layout review, not qualified scholarly or nutrition approval.',
              'build_command': ['python', 'scripts/build_papers.py', '--refresh-pdfs'],
              'render_command_template': 'pdftoppm -r 100 -png <paper>/main.pdf <ignored-final-render-prefix>',
              'render_location': f'.deployment/research/{RUN}/pdf-review',
              'method': 'Every final rendered page opened individually via view_image; layout, equations, captions, diagrams, references and appendices checked. No collage or generated replacement figures.',
              'documents': documents, 'total_pages_reviewed': 23,
              'minor_findings': journal.get('minor_findings', []),
              'build_attempt_note': 'One intermediate journal build had an overfull inline path. Original documents/indexes preserved locally; final emergency-stretch formatting removed overflow without changing substantive claim units.',
              'status': 'all_pages_reviewed_no_blocking_layout_defect_observed'}
    with target.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    print('Recorded all 23 final pages with source/PDF identities.')


if __name__ == '__main__':
    main()
