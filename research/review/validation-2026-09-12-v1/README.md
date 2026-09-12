# Independent mapping review packet, version 2

Status: **not reviewed and not scored**. These templates contain no judgments, reviewer identities, or claims of clinical validity. The original version-1 template and scorer are unchanged.

## What this review can establish

The question is whether a database recipe row is defensible for a clearly defined detector food class. This is not a review of photographed-meal ingredients, measured portions, clinical dietary targets, or advice suitability. Database import fidelity and coverage do not answer this question.

The packet freezes the database, workbook, class list, builder and local catalog using SHA-256 fingerprints. The validation baseline additionally fingerprints the runtime implementation. All 72 canonical classes require review, including classes with high developer-assigned mapping scores.

## Materials and blinding

Give reviewers `packet.json`, an assigned blank reference template, and the full local nutrition catalog:

`.deployment/research/validation-2026-09-12-v1/review/nutrition-catalog.json`

The catalog lists all 1,010 rows and their source metadata, but contains no algorithm predictions, mapping scores, or heuristic VERIFIED flags. It remains outside tracked public artifacts because upstream redistribution rights are not established. Providing catalog access to reviewers must respect the original sources' permissions.

Do **not** provide `mapping-predictions.json`, the legacy mapping-review outputs, or the production mapping table until the independent references have been completed and fingerprinted. A reviewer who has already seen the answers must not attest to being blinded. Self-attestation is necessary but is not proof of qualification or independence.

## Review procedure

1. Confirm that two reviewers have relevant food-composition and Indian-food expertise and are independent of the developer-selected mappings. Medical review of condition rules requires separately appropriate qualifications.
2. Agree and freeze a plain-language scope for every class before independent row choices. Use the same frozen `class_definition` text in both references. Do not define ambiguous classes by copying the current application's chosen database row.
3. Each reviewer independently fills their own template. Use a pseudonymous reviewer ID, relevant qualifications, completion timestamp, and the two truthful blinding/independence attestations. Reviewer identity verification and any sharing consent are handled outside this public packet.
4. For every class provide a status, traceable sources or catalog/source-record locations, and a reasoned explanation:
   - `accepted`: one or more database names are defensible under the frozen class definition. Names must exactly match the frozen database catalog.
   - `unsupported`: review is complete and no catalog row is defensible. The acceptable-name list must be empty.
   - `indeterminate`: class scope, recipe variation, or evidence is too ambiguous to decide. The acceptable-name list must be empty; explain what is missing. This is not an incorrect prediction or a correct abstention.
5. Save the completed references as new files, preserving both originals and their SHA-256 hashes. Do not overwrite the blank templates.
6. A third qualified adjudicator resolves disagreements in status, acceptable rows, or class-definition text. Copy the completed review hashes into a new adjudication document and include exactly the disagreement classes. Retaining `indeterminate` is permitted; consensus must not be manufactured.
7. Only then reveal and score the frozen predictions. Reviewers must not alter references after seeing model or mapping outcomes without documenting a new review version and its reason.

An accepted class-level correspondence still does not establish that an uploaded meal follows that recipe, that its nutrient values are clinically correct, or that a recommendation is medically appropriate.

## Scoring

Run from the repository root after real references have been completed:

```powershell
.\.venv\Scripts\python.exe scripts/score_mapping_reference.py `
  --packet research/review/validation-2026-09-12-v1/packet.json `
  --review-a <completed-reference-a.json> `
  --review-b <completed-reference-b.json> `
  --adjudication <completed-adjudication.json> `
  --predictions .deployment/research/validation-2026-09-12-v1/mapping-predictions.json `
  --output <new-results-file.json>
```

Omit `--adjudication` only if there are no disagreements. Output creation is exclusive: existing reports are never replaced. Blank/pending reviews, stale input hashes, repeated reviewer IDs, invalid database names, missing evidence, and unresolved disagreements are rejected.

The scorer reports per-class outcomes, raw lookup coverage, correct/wrong matches, correct abstentions, missed supported matches, and indeterminate counts. Decision agreement and matched precision exclude indeterminate classes with explicit denominators; a zero denominator returns null. The entire frozen vocabulary is a finite census, so the tool does not manufacture population confidence intervals or treat three predictions for the same class as independent samples.

The current automatic-without-precomputed predictions are pinned to `PYTHONHASHSEED=0`. The offline validation found cross-seed row-choice changes for six canonical classes in this ablation. Scoring one frozen execution must not be presented as a determinism guarantee or generalized accuracy for every possible runtime execution.
