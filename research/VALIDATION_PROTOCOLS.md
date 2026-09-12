# Approval-gated follow-up protocols

These protocols accompany the existing-evidence audit. They are **not authorization to execute new experiments**. No reviewer judgments, participant consent, resource approval, or clinical effectiveness is assumed. Keep production weights, database, dietary policy and deployment unchanged.

## 1. Independent mapping and policy review

Use the versioned packet under `research/review/validation-2026-09-12-v1/`. Freeze the database, class definitions, recipe catalog, candidate outputs and reviewer rubric before review. The catalog must contain source records without model predictions or mapping scores. Keep the predictions with the coordinator until initial assessments are locked.

Two suitably qualified independent reviewers should assess all 72 current labels, allowing multiple acceptable records, reviewed unsupported labels and a separate indeterminate outcome. Reviewers must record evidence and any preparation assumptions. An empty accepted set must not stand for uncertainty. Preserve both original assessments and use a separate adjudication record for disagreements. The coordinator confirms reviewer suitability and blinding; a completed JSON form cannot prove either.

Report current/exact/automatic lookup availability separately from correct matches, wrong matches, correct abstentions, missed supported cases, unresolved classes and disagreement. Report the denominator for each result. The fixed 72-label set is a discovery census, not an independent population sample or a confirmatory tuning set. Do not attach population confidence claims without a defined sampling design.

Assess numeric health modifiers, goal calorie boundaries and recommendation templates separately. Correct transcription and arithmetic do not establish safe dietary rules. Do not collect private medical histories for this review packet; use the application's synthetic context identifiers only.

**Release gate:** qualified judgments, evidence and adjudication available; reference/data/prediction identities match; no unresolved class is silently scored as unsupported. Otherwise retain the awaiting-review status.

## 2. Independent detector evaluation

The default follow-up is an external test of the fixed checkpoint on genuinely untouched, appropriately permitted source images. It is not evaluation on a rearrangement of development data.

Before inference, the supervisor must approve the target population, acquisition and rights process, independent source-family unit, label definitions, original/representative policy, annotation rubric, class and background coverage, and sample-size rationale. Review all selected evaluation annotations, independently adjudicate disputed cases, and use an independently checked quality-control sample. Keep any feasibility pilot outside the final test set.

Freeze the manifest, class order, model hash, package locks, preprocessing, evaluation implementation, confidence floor, NMS IoU, maximum detections and metric matching rules. Evaluate low-confidence AP separately from precision/recall at the application's 0.25 confidence and 0.45 NMS IoU settings. Store raw predictions and reference hashes so scores can be recomputed without another inference run.

Report per-class image **and independent-family** support, precision/recall/AP, aggregate metrics, missed detections, and separately defined background/out-of-vocabulary false positives. Do not label absence of a detection as a verified negative without reference review. If population uncertainty is justified, resample independent source families and retain paired units for model comparisons. No hyperparameter or threshold tuning on the held-out results.

**Resource gate:** documented data access, reviewer availability, permitted image/model transfer, available hardware, and a fixed no-paid-services time/compute ceiling must be approved before running. If untouched data cannot be obtained, retain the audit-case-study scope rather than replacing it with the candidate split.

Retraining is a separate decision. It requires a reviewed grouped split, appropriate initialization rather than resuming the developed checkpoint, frozen checkpoint-selection criterion, matched baseline and training budget, prespecified seeds, and recorded package/configuration hashes. Augmentation or architecture superiority requires the corresponding matched comparison; it is not implied by an old checkpoint filename.

## 3. Optional recommendation-content pilot

Default: zero live provider calls. After explicit authorization, use synthetic inputs only and the existing free-tier Groq provider; no paid alternative and no automatic retries.

- Primary set: 36 calls, one per combination of four goals and nine contexts. Distribute the six fixed offline food scenarios evenly in a saved manifest before execution.
- Repeat set: 12 calls maximum, three repeats of the preselected Maintenance cases for `none`, `diabetic`, `hypertension` and `kidney_disease`. These keys exist in the inspected policy; protocol freezing must reject policy drift rather than silently substitute cases.
- Hard cap: 48 outbound attempts across the entire pilot, not per retry/run. Persist the attempt counter before each call. Stop on authentication or quota errors. A resumption must use the existing attempt record, not reset the budget.
- Record synthetic case IDs, input/prompt/model/config hashes, date, returned source/context, response text, latency, usage when exposed, and all failures. Never record credentials or actual user health information.
- Keep AI outputs and deterministic fallbacks for qualified blinded review where feasible. Assess source fidelity, relevance, unsupported nutrient/portion claims, assumed consumption, overgeneralization and medical-suitability assertions. Structural text rules are triage, not expert scoring.

**Reporting gate:** call accounting and limitations complete; describe this as a small descriptive pilot. Even favorable judgments do not demonstrate general clinical safety or effectiveness.

The [qualified-review rubric and blank per-output form](review/validation-2026-09-12-v1/RECOMMENDATION_RUBRIC.md) define relevance, factual support, context appropriateness, overgeneralization and medical-suitability judgments, including explicit indeterminate states and preserved disagreements. They can be used for the already recorded offline fallback outputs without any live calls.

## 4. Optional deployment measurements

Do not create or promote a deployment during the existing-evidence audit. A later approved preview must retain its deployment ID, exact source/release manifest, build logs, package identities, and measured function bundle bytes.

Use a fixed permitted image suite for one/multiple dishes, empty results, orientation and input boundaries. Separate preprocessing, first-request, warm-request, inference and provider timing. Schedule three explicitly identified first-instance/first-deployment observations and 20 warm scans within rate and free-tier quotas. Save every observation and failure; report median and range rather than a service guarantee.

Call a measurement a cold start only with evidence linking the request to an uninitialized instance. A preceding health request does not establish that the subsequent scan reaches the same instance. Label process high-water memory as process peak, not isolated per-request use. Retain acceptance targets of bundle below 5 GB, observed peak below 1.6 GB, and analysis below 120 seconds, with units and measurement scope stated. Missing telemetry is an unverified gate, not a passing estimate.

Verify static pages independently of lazy model loading, API contracts, processed-image alignment, request IDs, cache headers, secret absence in public assets, and journal reload persistence. These images remain smoke-test fixtures, not a scientific detector benchmark. No production promotion is part of this protocol.

## 5. Human outcomes, authors and permissions

No participant study is needed to report the implementation and artifact audit. Claims of reduced logging effort, improved usability, adherence or health benefit require a distinct supervisor-approved study with defined population/outcomes, consent, data handling and applicable institutional review. Do not backfill a study from browser regression results.

Before external submission, confirm every author's role and consent, affiliations, correspondence, funding/conflicts, factual AI-assistance disclosure, access to supplementary artifacts, and dataset/model/database reuse permissions. The journal and conference-style documents describe one study; they are not two independent submissions. Select a venue and check its current instructions and mandatory costs only after the scope and evidence gates are agreed.
