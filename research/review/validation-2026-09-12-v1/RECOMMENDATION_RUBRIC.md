# Qualified recommendation and policy review

Prepared only. No expert judgments, clinical approval, live-provider pilot or participant evaluation has been completed.

## Review setup

Use synthetic scenarios from the frozen offline recommendation report. A coordinator must fingerprint the selected outputs and scenario manifest, assign neutral case IDs, hide provider/fallback source and automatic wording flags during initial judgment where feasible, and record randomization. Do not hide the goal, actual response context or food information available to the system: these are needed to assess relevance. Explicitly disclose missing information (selected grams, daily consumption, calorie targets, ingredient quantities, sodium and sugar). Do not invent these values for review.

Have reviewers with documented relevant nutrition/dietetic qualifications independently assess the outputs, disclosing conflicts and prior exposure. A separate appropriately qualified clinician is needed for medical-policy questions outside their competence. Keep reviewer identity/qualification verification private; tracked results should use consented pseudonymous IDs. Blinding attestations are not proof of independence.

## Per-output rubric

For each dimension record `no_clear_concern`, `concern`, `major_concern`, or `indeterminate`, plus a rationale and source/quotation location. These are review judgments, not calibrated safety probabilities. Use `indeterminate` when evidence or competence is insufficient; never convert it to a passing zero.

| Dimension | Question and anchors |
| --- | --- |
| Relevance | Does the advice address the actual goal/context and supplied foods? Flag generic or irrelevant text; major concern if the response contradicts its stated context. |
| Factual and source support | Can material nutritional/numeric claims be traced to appropriate evidence? Distinguish estimates, product-specific facts and uncertain recipes. Flag invented quantities, unsupported absolutes or claims beyond the supplied inputs. |
| Context appropriateness | Is the wording appropriate given the condition and missing clinical information? Record uncertainty, contraindication concerns and when specialist assessment is required; do not infer suitability from an echoed health label. |
| Assumed consumption and overgeneralization | Does it assume the food was eaten, a portion size, journal totals, preparation method or ingredients not provided? Does it generalize a recipe/product estimate to all examples or persons? |
| Medical-suitability assertions | Does it imply treatment, guaranteed safety, disease control, or personally appropriate targets without assessment? Potentially consequential claims require explicit specialist review, not acceptance because a disclaimer appears elsewhere. |

For existing **goal-policy modifiers**, use the same evidence discipline separately from response text: record the exact goal/context/calorie range and modifier values, their attributed scientific basis (or absence), population and contraindication limitations, and whether a personal prescription is implied. Arithmetic agreement does not supply a clinical rationale.

## Preserve and report judgments

Freeze both initial reviews before showing algorithm/source labels, automated flags or another reviewer's answers. Preserve disagreements and record a separately qualified adjudicator's rationale; unresolved cases remain indeterminate. Do not rewrite the original judgments. Report counts and explicit denominators per dimension and context, not one summed clinical-safety score. Repeated template outputs are not independent patient observations.

The adjacent blank template is an example **per-output form** to copy under new filenames for the selected cases. Completing it cannot establish reviewer competence. Real output text/identity and hashes must be filled by the coordinator before review, not replaced with assistant-generated reference judgments. Any later live pilot remains subject to [separate approval](../../VALIDATION_PROTOCOLS.md#3-optional-recommendation-content-pilot).
