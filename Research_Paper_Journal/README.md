# IEEE Transactions Initial Review Draft

This folder contains an IEEE Transactions-style initial-review LaTeX manuscript for:

**Nutrition-Aware Indian Food Recognition With YOLO11s and Conservative Nutrition Mapping**

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
- `bibliography/references.bib`: BibTeX references copied from the conference paper
- `figures/`: standalone figure assets used by the journal manuscript
- `JOURNAL_SUBMISSION_GUIDE.md`: IEEE journal formatting, review-readiness, and pre-submission checklist

## Before Submission

Update author email details, ORCID details if required, target-journal page/figure requirements, placeholder bibliography entries for the local INDB spreadsheet and exact source dataset URLs, and detector-family benchmark/ablation rows before journal submission.
