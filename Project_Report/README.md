# Final Year Project LaTeX Report

This folder contains the LaTeX source for the final year project report:

**AI-Based Food Recognition with Nutrition-Aware Recommendations**

## Structure

- `main.tex`: main LaTeX entry point
- `frontmatter/`: title page, certificate, declaration, acknowledgement, abstract, abbreviations
- `chapters/`: report chapters
- `appendices/`: mapping tables and API examples
- `figures/`: copied report figures and verification sheets
- `tables/`: supporting CSV artifacts
- `bibliography/references.bib`: BibTeX references

## Build

From this folder, run:

```bash
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

or:

```bash
latexmk -pdf main.tex
```

The LaTeX source includes portrait literature-review tables, generated
TikZ/PGFPlots diagrams, and project verification figures. If `pdflatex` is not
available on PATH, install MiKTeX or TeX Live and rerun the build sequence
above.

## Editable Metadata

These commands near the top of `main.tex` control the front matter:

- `\studentone`, `\enrollmentone`
- `\studenttwo`, `\enrollmenttwo`
- `\supervisor`
- `\cosupervisor`
- `\submissionmonth`

Some bibliography entries are provisional because the exact official citation metadata was not available in the repository.
