# IEEE Journal Submission Guide

This note records the journal-writing guidance used to revise `main.tex` and lists the remaining items to complete before external submission.

## Current Draft Mode

The current manuscript is formatted for an IEEE Transactions initial review phase:

- Single-column layout.
- 12-point IEEEtran draft class.
- Double-spaced body text.
- Running sequential line numbers in the left margin.
- Figures and tables placed inline near first mention using review-friendly float placement.
- Target review length: 30-45 pages in this draft format, which typically compresses substantially when converted to final two-column journal layout.

## IEEE Journal Prerequisites

- Use an IEEE journal article template. This folder uses `IEEEtran` in initial-review draft mode.
- Select one target journal before submission and check that journal's `Information for Authors`, aims and scope, article type, page limits, overlength charges, and required files.
- Submit the article to only one publication at a time.
- Confirm the corresponding author, author affiliations, country, email address, and ORCID requirements.
- Disclose funding and any prior conference presentation when applicable. If a conference version is later accepted, the journal version must be meaningfully extended and the prior presentation must be disclosed according to the target journal's policy.
- Verify authorship, citation ethics, originality, permissions for reused figures/data, and dataset/license restrictions.
- Prepare all source files, bibliography, figures, trained-model or supplementary files, and a clear data/code availability statement.

## Format Applied

- Title is concise and descriptive; avoid vague words such as "new" or "novel".
- Abstract is one paragraph and within the IEEE journal range of 150-250 words.
- Abbreviations are defined on first use in the abstract and body where practical.
- Keywords are compressed to five focused terms for discoverability.
- The paper follows the journal flow: introduction, related work, methodology/system, results, discussion, limitations, conclusion, acknowledgments, and references.
- Tables use IEEE-style captions and white page background by default.
- Figures are embedded as manuscript figures; final submission should use target-journal-approved formats and resolution.

## Detail vs. Compression

- Keep the main paper focused on the contribution, reproducible method, key quantitative results, and reviewer-relevant validation.
- Move excessive screenshots, full per-class results, extra prediction grids, and raw logs to supplementary material unless the target journal asks for them in the manuscript.
- Do not over-compress methodology. Reviewers should be able to understand dataset construction, split rules, training protocol, model selection, and evaluation metrics without reading the code first.
- Do compress implementation narration. Framework lists and frontend details should support the research claim, not dominate the paper.
- Page limits are journal-specific. For initial review, this draft targets readability first: single-column, double-spaced, line-numbered text with enough depth for reviewers to inspect the full project lifecycle.

## Initial Review Readiness

Before submission, check the manuscript as an editor or reviewer would:

- Scope: the work fits the selected journal's aims.
- Novelty: the contribution is clearly different from ordinary food classification or object detection.
- Validity: dataset creation, training protocol, model selection, and test evaluation are reproducible.
- Data: counts, metrics, mapping coverage, and nutrition sources are reported accurately.
- Clarity: abstract, introduction, figures, tables, and conclusion tell the same technical story.
- Compliance: ethics, originality, references, permissions, and target-journal file rules are satisfied.
- Advancement: the paper explains why conservative nutrition mapping improves regional food-recognition systems.
- Proof: detector metrics, held-out testing, nutrition coverage, macro verification, and clearly marked benchmark/ablation requirements are present.

## Remaining Before External Submission

- Replace `[student email]` with real author email details.
- Replace placeholder INDB and dataset bibliography entries with citable public records or official source documentation.
- Select the exact IEEE journal and verify article type, page limit, figure format, and any supplementary-material rules.
- Run same-split detector-family benchmarks and augmentation ablations before claiming complete Transactions-level proof.
- Add ORCID details if required by the submission system.
- Confirm whether the journal requires author biographies or photos.
- Run a final proofread for English, citation balance, figure readability, and table overflow.

## Official IEEE Sources Consulted

- IEEE Author Center Journals, "Structure Your Article": https://journals.ieeeauthorcenter.ieee.org/create-your-ieee-journal-article/create-the-text-of-your-article/structure-your-article/
- IEEE Author Center Journals, "Checklist for Creating Your Article": https://journals.ieeeauthorcenter.ieee.org/create-your-ieee-journal-article/authoring-tools-and-templates/checklist-for-creating-your-article/
- IEEE Author Center Journals, "The IEEE Article Submission Process": https://journals.ieeeauthorcenter.ieee.org/submit-your-article-for-peer-review/the-ieee-article-submission-process/
- IEEE Author Center Journals, "About the Peer Review Process": https://journals.ieeeauthorcenter.ieee.org/submit-your-article-for-peer-review/about-the-peer-review-process/
- IEEE Editorial Style Manual for Authors: https://journals.ieeeauthorcenter.ieee.org/wp-content/uploads/sites/7/IEEE-Editorial-Style-Manual-for-Authors.pdf
