# Existing-evidence validation report

Run: `validation-2026-09-12-v1`, 12 September 2026. Audience: supervisor review. The full paper is primary; the shorter paper is a companion, not a second experiment.

## Decision

**Ready for supervisor review with explicit limitations.** The implementation and narrowly stated audit/transcription/arithmetic results are supported to the extent recorded below. **Not certified for external submission, independent detector accuracy, mapping correctness, medical suitability, or user benefit.** New experiments and qualified review remain separate gates.

- [Full paper PDF](../Research_Paper_Journal/main.pdf) · [source](../Research_Paper_Journal/main.tex).
- [Short companion PDF](../Research_Paper_Conference/main.pdf) · [source](../Research_Paper_Conference/main.tex).
- [Final claim/evidence index](evidence/validation-2026-09-12-v1/claims-final.json), [individual claim dispositions](evidence/validation-2026-09-12-v1/claim-review-coverage.json), [recorded corrections](evidence/validation-2026-09-12-v1/claim-corrections.json), [discrepancy register](evidence/validation-2026-09-12-v1/findings.json), [sealed manifest](evidence/validation-2026-09-12-v1/validation-manifest.json).
- [Blank independent-review packet](review/validation-2026-09-12-v1/README.md), [approval-gated protocols](VALIDATION_PROTOCOLS.md).

No production code, API, dietary policy, database, model weights, original images/annotations, or deployment was changed. There were no detector experiments, live provider calls, participant studies, retraining, submissions, or paid services. Generated build/cache cleanup is recorded separately and excludes research evidence and rollback snapshots.

## Reproducibility and preservation

The [baseline](evidence/validation-2026-09-12-v1/baseline.json) identifies commit `0a4edfa92818945ccd7f16b023299c847c745f0d` **and 148 current file hashes**, including uncommitted documents, PDFs, scripts, locks, database, workbook, notebooks, training outputs and checkpoints. The commit alone does not identify this revised package. Editable baseline copies are preserved locally under `.deployment/research/validation-2026-09-12-v1/baseline/`; new full manifests and detailed outputs use that separate run directory, never historical output paths.

The local audit used Windows 11, Python 3.12.7 and the recorded environment. This is not a new Linux/Vercel verification. Torch was not loaded for training or inference. Run receipts identify commands, timestamps, elapsed durations, inputs, software and failures. Reports contain aggregate data and fingerprints, not photos, credentials or personal reviewer identities. Source-account path segments were redacted. Local-only manifests/catalogs require separate access and permission review; a public checkout does not contain all reproduction inputs.

## Findings by workstream

| Workstream | Observed outcome | Essential qualification |
| --- | --- | --- |
| Dataset census and grouping | Fresh scans reproduce 48,693 records, 72 classes, 138 byte/pixel cross-partition groups, and previous dataset/source/assignment identities. | These records are not 48,693 independent originals; overlap does not quantify score inflation. |
| Annotation integrity | 65 zero-area flags: 45 zero-width and 20 zero-height; 47 affected images have no accepted instances. All 65 originals viewed individually. | AI-assisted visual/numerical inspection is not qualified semantic approval or proof of valid negatives. |
| Identical-pixel label disagreement | 104 groups/209 images: 69 box differences with unchanged class multiset, 35 changed class/instance multisets; none only formatting/order. | Numeric disagreement does not decide which annotation is correct. |
| Additional geometry | 3,794 rows in 3,346 images cross image edges at tolerance `1e-6`. | Additional review flags, not automatic invalidation; originals unchanged. |
| Candidate independence | Minimum class-specific group support is 43/9/11; 11,002 records remain quarantined. A 2,020-record perceptual screen queues 16 candidate pairs. | Candidate grouping is not benchmark approval; crop/mirror/rotation probes were missed, and all queued ancestry judgments remain pending. |
| Training history | 55+45 CSV rows reconstruct 100 consecutive epochs exactly; notebook cells and full-precision historical metrics extracted. | Timer resets at resume; execution-time final checkpoint identity and matching raw final predictions are unavailable. Metrics remain historical only. |
| Nutrition transcription | 1,014 workbook rows minus 9 deduplications plus 5 supplemental records reconcile to 1,010 database rows. All 4,040 nutrient comparisons agree at `1e-9` absolute tolerance. | Import/source consistency is not recipe equivalence, measured meal composition or medical endorsement. |
| Mapping behavior | Availability reproduces 19/72, 55/72 and 72/72. Eight seeds × 181 labels × two methods reveal 30 changing method/label pairs. Current canonical mappings stay stable. | Six canonical classes change only without precomputed mappings; no independent wrong-match rate exists. |
| Arithmetic | 2,880 frontend portion cases/11,520 values pass. 162,036 goal cases in each implementation pass independent rational oracles. | Maximum portion deviation is about `9.095e-13`; policy's clinical basis is not tested. Backend/browser calorie boundaries differ and remain unchanged. |
| Recommendations | 216 offline scenarios and 16 real SDK mocked-transport cases pass; timeouts, zero retries, errors, saturation, cancellation and cleanup exercised. | No live AI outputs or medical-quality scores. Templates can imply consumption/suitability and ignore nutrient values or goals. |
| Browser behavior | All 36 goal/context combinations, stale/out-of-order responses, retries, missing context, all-excluded foods, unknown totals, reload and local-date scenarios pass alongside existing suites. | Finite mocked tests, not a usability study. Health badges identify response context, not expert endorsement. |
| Deployment | Existing local receipts and configuration inspected, no live deployment touched. | Current 5 GB bundle, 1.6 GB peak and 120-second cold-analysis acceptance are not established by these artifacts. |

Detailed receipts: [dataset](evidence/validation-2026-09-12-v1/dataset-inspection.json), [65-image review](evidence/validation-2026-09-12-v1/dataset-visual-review.json), [perceptual limitations](evidence/validation-2026-09-12-v1/dataset-perceptual-review.json), [training](evidence/validation-2026-09-12-v1/training-results.json), [nutrition](evidence/validation-2026-09-12-v1/nutrition-validation.json), [arithmetic](evidence/validation-2026-09-12-v1/arithmetic-validation.json), [recommendations](evidence/validation-2026-09-12-v1/recommendations.json), [final expanded browser run](evidence/validation-2026-09-12-v1/browser-extended-attempt4.json), [deployment evidence limits](evidence/validation-2026-09-12-v1/deployment-evidence.json).

The perceptual queue is bounded review preparation: 1,360,132 eligible comparisons at dHash distance at most six. Twelve originals were probed **per transform**: 12/12 recovered for each JPEG and resize transform; 0/12 for each crop, mirror and rotation transform. These are synthetic known-lineage checks, not calibrated sensitivity/precision on real duplicates or a detector experiment.

The first source's README advertises 9,290 images while the actual local inventory contains 9,053; the source table reports the counted local records, not an invented resolution of that metadata discrepancy. Nutrient energy-versus-4/4/9 residuals are recorded as investigation flags, not automatic transcription errors. The [qualified recommendation/policy rubric](review/validation-2026-09-12-v1/RECOMMENDATION_RUBRIC.md) remains blank and separates concerns from indeterminate judgments.

## Section-by-section corrections

The title/abstract/contributions now describe a system and reproducibility audit. Abstract numbers are linked to aggregate evidence, not novel detector performance. The introduction and related work acknowledge prior integrated nutrition systems, distinguish preprints, and avoid unmatched published-score baselines. Twenty-two focused citations were checked against primary records with unavailable/direct/cached access recorded in the [citation audit](evidence/validation-2026-09-12-v1/citation-review.json); this is not an exhaustive systematic review or novelty certification.

Methods trace image processing, matching, recommendation payload/prompt, browser-only storage and runtime protections to frozen code. Equations distinguish known subtotals, missingness, exclusions and saved-only consumption. Results separate reproduced counts/calculations from historical notebook metrics. The full paper records resume-timer resets, legacy-notebook mismatch, application-versus-AP settings, and timing boundaries. Discussion and conclusion retain unresolved lineage, annotation, recipe, portion, recommendation, sampling and rights limitations. Both versions report the new audit findings and retain the same essential qualifications.

The ledger indexes 635 literal manuscript units, including overlapping table/math/container units, with shared IDs, locations, evidence and limits; these are not 635 independent experimental claims. Each indexed unit receives a separate AI-assisted artifact-review disposition. Eleven resulting wording corrections clarify retained excluded-item records, saved known totals, configured deployment, earlier versus controlled hash seeds, generic versus observed label differences, and unverified public access. The original index, individual reviews and pre-correction PDFs are preserved; the final coverage report applies the recorded corrections. Automated indexing/drift checks are not a complete semantic theorem prover or qualified expert assessment. Quantitative assertions also receive 234 [scoped independent number checks](evidence/validation-2026-09-12-v1/numeric-checks.json), rerun after the corrections. Every rendered page is reviewed separately in the [PDF checklist](evidence/validation-2026-09-12-v1/pdf-review.json).

## Verification and failed attempts

Recorded local checks pass: frontend lint, unit tests, build and types; backend lint, deployment/architecture tests; OpenAPI/policy drift; nutrition provenance; manuscript structure/bibliography/generated evidence; existing research tests; new synthetic audit/scorer/oracle tests; and all four mocked browser scripts. Existing regressions include rotated images/aligned boxes, invalid/oversized uploads, timeout/busy/rate-limit handling, empty results, fallback, journal storage failures, save/update/delete/undo, midnight/focus behavior, mobile width and keyboard controls. See individual [command receipts](evidence/validation-2026-09-12-v1/checks/) rather than combining heterogeneous assertions into a scientific-validation score.

Two initial extended-browser attempts failed because of harness selectors and a wrongly mocked route prefix. Both are preserved; corrected attempt 3 and strengthened pending-cancellation attempt 4 passed. An initial wrong Python-interpreter attempt is also disclosed in the recommendation validator receipt. These were tooling failures, not hidden production fixes. The final shared browser runner also executes the new CI mode without frozen/private artifacts.

GitHub Actions now includes deterministic offline validators and mocked browser coverage. Heavy dataset scans, workbook access beyond existing provenance checks, full scientific arithmetic runs, provider credentials/live calls, model inference, and new experiments are not introduced into ordinary CI. These are **local passing results and CI configuration**, not a newly observed remote GitHub check run; no push is part of this audit.

## Unavailable evidence and external decisions

1. Qualified blinded mapping judgments for all 72 classes; qualified advice/health-policy review. Blank templates support acceptable alternatives, reviewed unsupported classes, indeterminate cases and preserved adjudication. They contain no fabricated reference answers.
2. Reviewed untouched evaluation data, annotations, source-family relationships and permissions. Candidate repartitioning cannot repair historical checkpoint exposure retrospectively.
3. Evaluation-time checkpoint hashes, a fully traceable 72-class initial execution and matching raw final predictions/settings. Available notebook numbers cannot fill these gaps.
4. Identified current preview deployment measurements, actual installed Linux bundle identity, cold-instance observations and concurrency memory traces.
5. Representative usability/health outcomes, study protocol and applicable institutional review.
6. Confirmed author order/affiliations/contributions, funding/conflicts/AI assistance, artifact rights and external venue requirements.

These are explicit pending items, not passing checks. [Prepared protocols](VALIDATION_PROTOCOLS.md) define approval gates for independent review, untouched detector evaluation/retraining, an optional at-most-48-call synthetic recommendation pilot, identified preview measurements and human research. None was executed automatically.

## Reuse and handoff

For deterministic local/CI checks, use the repository virtual environment and locked frontend dependencies. Run the checks listed in `.github/workflows/quality.yml`; source/PDF generation uses `python scripts/build_papers.py --refresh-pdfs` with installed TeX/BibTeX. Full audits require locally available permitted inputs and a **new** `validation-...` run ID; preserve this run. Do not invoke dataset construction or fixed-output historical evaluation scripts as a validation shortcut.

Ask the supervisor to assess the audit-case-study framing and prioritize independent data/mapping review. More interface features are not the missing evidence. Supervisor readiness, support within this limited study, and readiness for external submission remain three separate decisions.
