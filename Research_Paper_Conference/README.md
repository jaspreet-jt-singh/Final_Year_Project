# Research Paper

**Submission blocked (2026-09-12):** the new full dataset audit found 138 identical-image groups spanning splits and 65 annotation-flagged images. Read `../research/READINESS.md` before using historical performance claims. The source and rebuilt PDF include an audit notice.

This folder contains an IEEE conference-style LaTeX research paper for:

**AI-Based Food Recognition with Nutrition-Aware Recommendations**

The paper is intentionally compressed for a conference format. It focuses on the implemented project: YOLO-based Indian food detection, conservative nutrition mapping, macro calculation, serving adjustment, and nutrition-aware recommendations.

## Build

Preferred from the repository root: `python scripts/build_papers.py --refresh-pdfs`. It isolates build artifacts and refreshes both draft PDFs only after successful compilation. MiKTeX automatic package installation is disabled.

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

The five source-dataset versions/URLs have been recovered from local export metadata and cited. The INDB workbook citation remains explicitly unresolved; a related journal article alone does not establish the local file's version or reuse terms.
