# IEEE Transactions Initial Review Draft

This folder contains an IEEE Transactions-style initial-review LaTeX manuscript for:

**AI-Based Food Recognition with Nutrition-Aware Recommendations**

## Build

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
