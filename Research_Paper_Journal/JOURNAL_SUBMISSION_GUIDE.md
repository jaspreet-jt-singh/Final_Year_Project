# Supervisor Review and Submission Preparation

The current manuscripts are supervisor-review drafts of **AI-Based Food Recognition with Nutrition-Aware Recommendations: A System and Reproducibility Audit**. They are not approved external submissions, and no venue has been selected.

Use [SUPERVISOR_REVIEW.md](../research/SUPERVISOR_REVIEW.md) for the review package and requested decisions, and [READINESS.md](../research/READINESS.md) for recorded evidence and remaining gates.

## Which version to review

[The full draft](main.pdf) is the primary manuscript. It uses a one-column, 12-point IEEEtran layout, 1.5-spaced text, and real `lineno` line numbering for review. [The short companion](../Research_Paper_Conference/main.pdf) presents the same study in a compact conference-style layout.

These are alternative presentations, not independent studies. Do not treat their different layouts or lengths as evidence of distinct contributions. Decide with the supervisors which version and article type to develop for one external submission; assess any later reuse or extension against the selected venue's policies.

The use of IEEEtran does not select an IEEE venue or establish universal journal formatting requirements. Page limits, abstract length, anonymization, article type, references, figures, supplementary files, and final templates must be checked against the actual venue once selected.

## What the drafts establish

The completed work documents the implemented application, an export-integrity audit, candidate source-family reconstruction with quarantine, and a lookup-availability comparison. It separates these observations from archived detector metrics and proposed experiments.

The INDB workbook is byte-identical to the original authors' pinned public artifact. Its publication and citation correction are identified. Five supplemental nutrient records have source attribution and checked per-100-g transcription. None of these checks establishes that every photographed recipe matches its database row, that entered grams were consumed, or that the advice is clinically appropriate.

The historical partitions contain exact overlap; the broader filename-family links are heuristic. Reassignment cannot retrospectively make the existing checkpoint's evaluation independent. Availability for all current labels is not mapping accuracy.

## Supervisor decisions and evidence gates

1. Agree the research claim and article scope. A reproducibility case study should be assessed on its documented methods, findings, and limitations, not presented as a new detector or clinical intervention.
2. Approve the next independent-evaluation protocol. Before making new detector-generalization claims, review group links, representative selection, quarantined records, annotations, and source permissions; freeze the evaluation design and record the checkpoint, environment, and selection rules. Appropriately retrained models or genuinely untouched external data are needed for the proposed independent evaluation.
3. Arrange qualified nutrition-mapping review. Freeze the database and predictions, define acceptable recipe equivalence and ambiguous/unsupported labels, retain independent initial judgments, and document adjudication. Do not copy developer mappings into the reference set or substitute lookup coverage for correctness.
4. Assess advice separately. Context-label consistency is a software property. Clinical appropriateness, unsupported assertions, inherited fallback wording, and user benefit require their own qualified review or study design before those benefits are claimed.
5. Match experiments to claims. Matched model baselines, augmentation ablations, nutrient-error measurements, or user studies are required when their corresponding comparative or outcome claims are made; they are not already completed evidence.

## Rights, authors, and disclosures

Confirm dataset, checkpoint, derived-database, and any reused figure permissions with the relevant owners and institutional guidance. Export-level license labels and source URLs do not by themselves resolve the image-rights caveats recorded in some source READMEs. No new license or blanket permission is granted by these drafts.

Confirm the author list/order, affiliations, corresponding author and contact details, contributions, acknowledgments, funding, and competing interests. Add identifiers such as ORCID only when verified and required. Do not invent missing declarations or describe an institutional review as approved when it has not occurred.

The drafts disclose AI-assisted inspection and editing. Authors must verify the resulting text, references, calculations, and provenance, and adapt the disclosure to the selected venue's requirements. Any proposed participant or clinical study needs its own consent, data-handling, and institutional-review assessment; none is claimed as completed here.

## Artifact package

Keep the manuscript sources, PDFs, focused bibliography, tracked generated numeric files, and the relevant audit reports together. The public source revision and full hashes in the evidence identify the inspected artifacts.

The full per-image and grouped-assignment manifests remain under `.deployment/research/` locally; a public repository checkout or PDF does not include them. Determine what may be supplied for artifact review and package permitted materials explicitly. State access restrictions honestly rather than promising unrestricted reproducibility.

Historical assets in `figures/` are preserved but unused by the current drafts. Do not reintroduce old screenshots or evaluation plots as current evidence without checking their origin, meaning, and permissions.

## Reproducible checks and PDF refresh

From the repository root:

```bash
python scripts/generate_paper_evidence.py --check
python scripts/check_manuscripts.py
python scripts/build_papers.py --refresh-pdfs
```

- The generated-evidence check reads recorded audit reports and detects drift in tracked numeric macros. It does not regenerate evidence or validate its scientific interpretation.
- The manuscript checker checks literal structure, citations, references, and related consistency constraints. It is not peer review, clinical validation, authorship verification, or permission approval.
- Building requires installed `pdflatex`, `bibtex`, and the packages referenced by the sources. No TeX/package installer is invoked, and MiKTeX automatic package installation is disabled.
- Intermediate files are isolated under `.deployment/research/`. The refresh option replaces both tracked PDFs only after both documents compile successfully. Without the option, tracked PDFs remain unchanged.

After building, inspect both PDFs for clipped text, unreadable labels, broken links, unresolved citations, float placement, and consistency between abstract, methods, results, and conclusion. Automated success is not a substitute for reading the output.

## Final external-submission gate

Select a venue only after agreeing the contribution and evidence status with the supervisors. Check its current official scope, article types, review model, required files, author/disclosure rules, reuse policy, and any mandatory costs before committing to submission.

Complete the agreed evidence and approval gates, update the availability statement, apply the venue's actual template, obtain every author's final approval, and submit only the approved version. No claim of acceptance, cost-free publication, or venue readiness is made by this guide.
