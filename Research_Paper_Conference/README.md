# Research Paper

This folder contains an IEEE conference-style LaTeX research paper for:

**AI-Based Food Recognition with Nutrition-Aware Recommendations**

The paper is intentionally compressed for a conference format. It focuses on the implemented project: YOLO-based Indian food detection, conservative nutrition mapping, macro calculation, serving adjustment, and nutrition-aware recommendations.

## Build

Run from this folder:

```bash
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

## Files

- `main.tex`: paper source
- `main.pdf`: compiled paper after build
- `bibliography/references.bib`: BibTeX references
- `figures/`: prototype and YOLO11s result figures

## Before Submission

Update the author email in `main.tex`.

Two bibliography entries remain marked as placeholders because the repository does not contain official citation metadata for the local INDB spreadsheet or the exact source dataset URLs.
