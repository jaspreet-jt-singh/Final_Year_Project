# Research Paper

This folder contains an IEEE conference-style LaTeX research paper for:

**Nutrition-Aware Indian Food Recognition Using YOLO11s and Conservative Class-to-Database Mapping**

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
- `figures/`: prototype, class verification, and YOLO11s result figures

## Before Submission

Update the author email in `main.tex`.

Two bibliography entries remain marked as placeholders because the repository does not contain official citation metadata for the local INDB spreadsheet or the exact source dataset URLs.
