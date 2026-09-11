# IEEE Transactions Initial Review Draft

**Submission blocked (2026-09-12):** the new full dataset audit found 138 identical-image groups spanning splits and 65 annotation-flagged images. Read `../research/READINESS.md` before using historical performance claims. No target journal has been selected. The source and rebuilt PDF include an audit notice.

This folder contains an IEEE Transactions-style initial-review LaTeX manuscript for:

**AI-Based Food Recognition with Nutrition-Aware Recommendations**

## Build

Preferred from the repository root: `python scripts/build_papers.py --refresh-pdfs`. This isolates build artifacts and refreshes both PDFs only after successful compilation. MiKTeX automatic package installation is disabled.

Run from this folder:

```bash
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

## Files

- `main.tex`: initial-review manuscript source using `IEEEtran` 12-point, one-column, double-spaced draft mode with line numbers
- `bibliography/references.bib`: BibTeX references for food recognition, Indian-food datasets, nutrition databases, recommendation systems, and implementation frameworks
- `figures/`: standalone figure assets used by the journal manuscript
- `JOURNAL_SUBMISSION_GUIDE.md`: IEEE journal formatting, review-readiness, and pre-submission checklist

## Before Submission

Update author email details, ORCID details if required, target-journal page/figure requirements, exact source dataset URLs and access dates, and detector-family benchmark/ablation rows before journal submission.
