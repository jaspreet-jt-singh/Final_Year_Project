# Short Supervisor-Review Companion

This folder contains the short conference-style companion to **AI-Based Food Recognition with Nutrition-Aware Recommendations: A System and Reproducibility Audit**.

Read [the PDF](main.pdf) for a compact overview. The [full journal-format draft](../Research_Paper_Journal/main.pdf) is the primary supervisor-review manuscript and contains the detailed methods, implementation caveats, historical evidence, and prospective evaluation protocol.

Both drafts describe the same study. They are not separate experiments or two independent publication claims. No conference or journal has been selected, and the current layout is not a venue-compliance certificate.

See [supervisor review notes](../research/SUPERVISOR_REVIEW.md) and [research readiness](../research/READINESS.md) before using results externally. The audit distinguishes exact overlap from heuristic source-family links, lookup availability from correctness, and tested software behavior from clinical or user benefit.

## Files

- [main.tex](main.tex): short manuscript source in a two-column IEEEtran conference-style layout.
- [main.pdf](main.pdf): compiled review copy.
- [bibliography/references.bib](bibliography/references.bib): the same focused reference set as the primary draft.
- [generated/evidence.tex](generated/evidence.tex): tracked generated numeric macros; do not edit by hand.
- `figures/`: preserved historical assets, not used by the current manuscript. The current workflow diagram is drawn in LaTeX.

## Check and build

Run from the repository root:

```bash
python scripts/generate_paper_evidence.py --check
python scripts/check_manuscripts.py
python scripts/build_papers.py --refresh-pdfs
```

The checks detect generated-number drift and structural/reference problems; they do not certify scholarly validity or submission readiness. Building requires installed `pdflatex`, `bibtex`, and the source packages. The script does not install TeX or packages, and disables MiKTeX automatic package installation.

Build outputs are isolated under `.deployment/research/`; both tracked PDFs are refreshed only after both manuscripts compile successfully. Omit `--refresh-pdfs` to retain the tracked PDFs unchanged.

## Review boundaries

The nutrition workbook's byte identity and citation have been verified, while permissions and independent correctness review remain separate questions. Historical detector metrics are not clean independent generalization estimates. The grouped candidate split is review-only and no new detector evaluation or clinical study is claimed.

Follow the [primary draft's preparation guide](../Research_Paper_Journal/JOURNAL_SUBMISSION_GUIDE.md) for evidence, author/disclosure, permission, and venue decisions before any external submission.
