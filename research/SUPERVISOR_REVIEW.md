# Supervisor review package — 12 September 2026

The subsequent full existing-evidence audit is documented in [VALIDATION_REPORT.md](VALIDATION_REPORT.md), with fresh dataset scans, independent arithmetic, recommendation/browser checks, per-page PDF review and a claim ledger. That report supersedes this earlier editorial-pass verification summary. The updated PDFs contain these additional results; read the full paper first.

## Recommendation

**Ready to circulate for supervisor feedback; not represented as ready for external submission.** The full manuscript is the primary review document. The shorter version presents the same study, not a second experiment or an independently publishable contribution.

- [Full manuscript PDF](../Research_Paper_Journal/main.pdf) and [editable LaTeX](../Research_Paper_Journal/main.tex).
- [Short companion PDF](../Research_Paper_Conference/main.pdf) and [editable LaTeX](../Research_Paper_Conference/main.tex).
- [Evidence and next-study gates](READINESS.md).

The project name is preserved, with the subtitle **“A System and Reproducibility Audit.”** This framing reports what the available artifacts can support: an implemented application, a dataset-integrity audit, candidate source-family recovery, lookup-availability measurements, and software-contract verification. It does not claim a novel detector, independent benchmark superiority, image-measured food mass, clinical efficacy, or demonstrated user benefit.

No application behavior, dietary policy, model weights, nutrition rows, dataset labels, or live deployment was changed by this manuscript revision. No retraining, participant study, provider evaluation, external submission, or paid service was started.

## What was reviewed

The review cross-checked both existing drafts against backend and frontend source, tests, policy, SQLite lookup behavior, historical notebook/CSV outputs, recorded full-export and grouping reports, local dataset metadata, and primary reference sources. [Review identity](evidence/manuscript-review.json) records the inspected base commit and hashes of the historical notebook and supporting reports. These are review-time identities, not retroactive proof of the files used during historical training.

The earlier full dataset scans were inspected, not rerun as a new experiment during this editing pass. Their recorded hashes and limitations remain visible. Primary-source citation checking is not an exhaustive systematic literature review, plagiarism certification, or guarantee of novelty. Online access was not available for every dataset version: the five version URLs are supported by local export metadata, not all independently retrieved online.

## Principal corrections

| Issue | Evidence-backed treatment in the new drafts |
| --- | --- |
| Historical accuracy presented too strongly | Validation/test metrics appear only as historical observations in an appendix. Exact overlap across old partitions prevents calling the test independently held out; the amount of inflation is unknown. |
| Reassignment confused with a new benchmark | Candidate groups, quarantine, and assignment methods are described explicitly. The current checkpoint was not retrained on the candidates, so their construction does not validate its accuracy. |
| Nutrition coverage confused with correctness | The 19/72, 55/72, and 72/72 results measure lookup availability under three implementations, not nutritional correctness or an accuracy ablation. |
| Portions confused with image measurements | The equations use user-entered grams and per-100-g row values. Unknown nutrition remains marked incomplete; an unsaved scan never enters daily consumption. |
| Recommendation inputs overstated | The browser sends included per-100-g records, goal, and context. Groq receives the name/energy subset, not all macros, portion weights, calorie targets, or journal history. Local templates do not select advice from nutrient numbers. |
| Health labels implied expert approval | An “Adjusted for…” badge reflects a successful matching backend context. It is not a medical-quality assessment. Existing consumption-assuming/suitability language in some fallback templates is disclosed as a limitation, not silently fixed. |
| Matching algorithm inaccurately described | The actual normalized-name/containment chain and thresholds replace edit-distance claims. Ambiguous set-derived alias fallbacks are not guaranteed to be deterministic across processes; canonical precomputed mappings bypass them. |
| Unsupported theory and evidence | The invented optimization objective, unmeasured ablations, and unsupported benefit/novelty claims were removed. Prospective experiments are clearly labeled as proposed work. |
| Weak provenance and citation detail | The verified pinned INDB artifact, its article and corrigendum, source versions, software citation, and supplemental nutrition sources are distinguished. Identity, attribution, permission, and clinical correctness are separate questions. |

The new full paper follows four research questions: archived dataset integrity, candidate grouping and its limits, nutrition-lookup availability, and verified application invariants versus unmeasured outcomes. Methods explain the unit of analysis, exact identities, heuristic family links, quarantine propagation, assignment objectives, missingness arithmetic, and rounding. Threats to validity and the proposed next protocol are explicit.

## Key numbers and their limits

- The archived export contains **48,693 image records and 72 classes**: 36,852 training, 5,922 validation, and 5,919 test images. Exported records are not necessarily distinct original photographs.
- Both byte and oriented-pixel checks found **138 cross-partition groups affecting 276 images**. Pair-specific group counts are 63 train–validation, 56 train–test, and 19 validation–test. These are group counts, not all pairs or a measured accuracy effect.
- Strict checks flag **65 images**: 51/7/7 across the three partitions. Accepted instance counts are 56,287/8,805/8,868; the historical evaluator counted differently. Syntactically valid boxes are not necessarily semantically correct annotations.
- Source reconstruction links **5,548 candidate family groups across the old partitions** and quarantines **11,002 image records** in 9,274 groups. These family links are heuristic, not 5,548 visually confirmed shared originals. Quarantine is a manifest status; no files were deleted.
- The candidate train/validation/test partitions contain **26,384/5,655/5,652 images**, with all 72 classes represented. Representation alone does not establish adequate independent support or a valid benchmark. Two full reads produced matching outputs in the same environment, not independent replication.
- The database has **1,010 rows and 103 mappings**, including legacy labels. All 72 current labels have precomputed mappings; **21** have a score below 0.9 or no score. Those scores are heuristics, not reference-review judgments.
- Historical notebook test mAP50 is approximately **0.820**. It is not newly measured, not a clean held-out claim, and not evidence of CPU web latency. Matching current/archive checkpoint bytes cannot establish the evaluated checkpoint's identity at the earlier execution time, which was not hashed in the notebook.

Numerical audit values in both papers are generated from [audit.json](evidence/audit.json) and [grouped-split-v1.json](evidence/grouped-split-v1.json); a drift check rejects stale generated files. Neither these checks nor the rewritten prose converts incomplete evidence into ground truth.

## Citation and attribution review

Both bibliographies now contain the same focused 22 cited entries, including the explicitly labeled September 2026 FKG validation preprint added in the subsequent audit. Missing bibliographic details were corrected using primary records where available; uncited tutorial material was removed rather than used to inflate the reference list.

- Im2Calories is an ICCV 2015 conference paper, not a journal article. Its prior diary/nutrition pipeline prevents claiming that simple integration is novel here. [CVF record](https://openaccess.thecvf.com/content_iccv_2015/html/Meyers_Im2Calories_Towards_an_ICCV_2015_paper.html).
- Nutrition5k has measured component-weight/nutrition supervision, unlike user-entered gram assumptions. Its published scope and pagination were corrected. [CVF record](https://openaccess.thecvf.com/content/CVPR2021/html/Thames_Nutrition5k_Towards_Automatic_Nutritional_Understanding_of_Generic_Food_CVPR_2021_paper.html).
- The Indian Thali paper is acknowledged as prior integrated multi-dish work; its results are not substituted for a matched baseline. [Author-hosted paper](https://adityaarun1.github.io/assets/files/icvgip25/thali/Thali_ICVGIP2025_main.pdf).
- The INDB article, pinned workbook, and subsequent corrigendum are separate references. The corrigendum corrects food-composition source attribution; it is not a correction or endorsement of this application's mappings. [Original article](https://doi.org/10.1016/j.cdnut.2024.103790), [corrigendum](https://doi.org/10.1016/j.cdnut.2025.107450).
- YOLO11 is cited through Ultralytics' software documentation, which states that there is no formal YOLO11 research paper. [Official documentation](https://docs.ultralytics.com/models/yolo11/).
- The old `synergistic_frameworks_2025` entry lacked an identifiable author, venue, DOI, or URL and could not be verified in the searches performed. It was removed; this does not establish that no similarly named work exists.
- Supplemental nutrition values were checked against their named product/recipe pages. Product-specific Bhakarwadi and recipe-specific estimates must not be generalized into measurements of every similarly named dish or medical suitability.

## What still needs a human decision or new evidence

1. **Scope and contribution.** Ask the supervisor whether the system/evidence-audit case study is the right framing, or whether the next study should focus on independently reviewed mapping quality. Neither route requires more interface features before feedback.
2. **Independent data protocol.** Review candidate family links, remaining transformed duplicates, representative selection, quarantine reasons, and annotations. Freeze a reviewed manifest before model selection, then retrain appropriately or obtain genuinely untouched external evaluation data. Reassigning images alone cannot independently evaluate the developed checkpoint.
3. **Nutrition reference review.** Have suitably qualified independent reviewers assess all 72 labels without seeing current predictions/scores. Use the new [version-2 packet](review/validation-2026-09-12-v1/README.md), with accepted alternatives, reviewed unsupported cases and explicitly indeterminate cases. Preserve both initial judgments and separate adjudication. The original version-1 format remains unchanged; neither scorer can prove qualifications or independence. The 72 labels remain a discovery set if used to tune rules.
4. **Advice and usability claims.** Existing tests verify context handling, errors, fallbacks, arithmetic, and storage behavior. Claims of safe advice, reduced effort, or dietary benefit need separate prespecified assessment. Check institutional requirements before participant or patient-data collection.
5. **Authors and disclosures.** Confirm author order, affiliations, corresponding author, contributions, funding, competing interests, and the factual AI-assistance disclosure. The current names are provisional; no consent or endorsement is inferred from existing files.
6. **Rights and artifact access.** Review dataset/image, model, derived database, and other third-party reuse terms separately. The INDB workbook identity is verified, but that is not a license grant. Full manifests are local and absent from both PDFs and ordinary public checkouts; package them separately only when permitted. See [third-party notices](../THIRD_PARTY_NOTICES.md).
7. **External venue later.** Once scope and evidence are agreed, select a suitable venue and check its current author instructions, charges, and disclosure rules. The two formats here are for feedback, not proof of venue compliance or two separate submissions.

## Reproducible document checks

From the repository root, with Python and an installed TeX/BibTeX environment:

```text
python scripts/generate_paper_evidence.py --check
python scripts/test_paper_evidence.py
python scripts/check_manuscripts.py
python scripts/test_manuscripts.py
python scripts/test_publication.py
python scripts/build_papers.py --refresh-pdfs
```

Use the repository virtual environment where available. Ruff checks the development scripts. The manuscript scanner checks literal inputs, bibliography keys, reference targets, environment nesting, abstract length, obsolete placeholders, review-artifact identity, and generated-number drift. It is intentionally not a complete TeX parser or scholarly validator.

Builds run in `.deployment/research/conference/` and `.deployment/research/journal/`. MiKTeX automatic installation is disabled; required packages must already be installed. Both documents must compile before the script starts refreshing the tracked PDFs. Inspect the final logs and rendered pages as well as automated checks. GitHub Actions includes the offline checks; this local revision does not claim a new remote CI result or automatically submit/deploy anything.

Earlier editorial-pass verification on 12 September 2026 passed: 15 manuscript-checker tests, 5 evidence-generator tests, 10 existing research-tool tests, generated-number and four-file identity checks, Ruff and `git diff --check`. Its intermediate PDFs were 16/5 pages. The subsequent [full validation report](VALIDATION_REPORT.md) and [PDF checklist](evidence/validation-2026-09-12-v1/pdf-review.json) supersede those intermediate counts and limited checks: the full frontend/browser/backend suites and fresh dataset scans have now run, with application source still unchanged.

## Suggested message to the supervisor

> Please review the attached full draft, “AI-Based Food Recognition with Nutrition-Aware Recommendations: A System and Reproducibility Audit.” It separates the implemented application and measured audit findings from historical detector results and proposed evaluation. The audit identified cross-partition duplicates and unresolved mapping-validity questions, so I have not presented the historical score as independent generalization. I would appreciate your guidance on the contribution framing, the next independent evaluation/reference-review protocol, and authorship and reuse approvals. The shorter companion is included only as an alternative presentation of the same study.
