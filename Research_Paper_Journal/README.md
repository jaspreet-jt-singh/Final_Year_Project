# Full Supervisor-Review Draft

This is the primary review manuscript for **AI-Based Food Recognition with Nutrition-Aware Recommendations: A System and Reproducibility Audit**.

Start with [the PDF](main.pdf), [supervisor review notes](../research/SUPERVISOR_REVIEW.md), and [research readiness](../research/READINESS.md). The manuscript separates completed application/audit work, historical detector observations, and proposed independent evaluation. It is prepared for supervisor feedback, not approved for external submission.

The [conference-style companion](../Research_Paper_Conference/main.pdf) is a shorter presentation of the same study, not a separate experiment or an independently publishable second contribution. No venue has been selected.

## Files and layout

- [main.tex](main.tex): primary manuscript source, using a one-column, 12-point IEEEtran review layout with 1.5-spaced text and actual `lineno` line numbering.
- [main.pdf](main.pdf): compiled review copy.
- [bibliography/references.bib](bibliography/references.bib): focused, checked references shared with the short companion.
- [generated/evidence.tex](generated/evidence.tex): tracked numeric macros generated from recorded audit evidence; do not edit by hand.
- `figures/`: preserved historical assets, not used by the current manuscript. Its workflow diagram is drawn directly in LaTeX.
- [JOURNAL_SUBMISSION_GUIDE.md](JOURNAL_SUBMISSION_GUIDE.md): review and submission-preparation gates.

This layout is a local review choice, not a claim of compliance with a particular journal's requirements.

## Check and build

From the repository root:

```bash
python scripts/generate_paper_evidence.py --check
python scripts/check_manuscripts.py
python scripts/build_papers.py --refresh-pdfs
```

The first command checks generated-number drift without rewriting files. The second checks manuscript structure and reference consistency; neither validates scientific claims, reviewer independence, clinical suitability, or permissions.

Building requires an installed TeX distribution, `pdflatex`, `bibtex`, and the packages used by the sources. The script does not install them; MiKTeX automatic package installation is disabled. Build artifacts are isolated under `.deployment/research/`. Both tracked PDFs are refreshed only after both documents compile successfully. Omit `--refresh-pdfs` to build without replacing the tracked PDFs.

## Before external submission

The INDB workbook's identity and source citation are verified; this does not establish nutrient correctness or all reuse permissions. A candidate grouped partition does not independently evaluate the existing checkpoint, and lookup availability is not mapping accuracy.

Use the [supervisor review notes](../research/SUPERVISOR_REVIEW.md) to agree the paper's claim scope and evaluation protocol. Independent evaluation/review, asset rights, author details, disclosures, and venue-specific requirements still need the decisions described in [the submission guide](JOURNAL_SUBMISSION_GUIDE.md).
