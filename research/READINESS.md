# Publication readiness — 2026-09-12

## Decision

The application can remain an educational demo. The manuscripts are **not ready for external submission**. More UI features will not resolve the experimental-validity and provenance gaps below. The production model, dataset, nutrition rows and clinical rules have not been changed. No retraining, paper submission, paid compute or publication fee has been incurred.

## Measured evidence

Reproduce with `python scripts/audit_publication.py`. It reads all images/labels and opens SQLite read-only. [Audit results](evidence/audit.json) record model, database, script, training CSV and split-manifest SHA-256 fingerprints. The complete per-file manifest is generated locally at `.deployment/research/split-manifest.jsonl`, outside the app bundle. `source_commit` identifies the base commit at audit time; the script hash identifies the actual new audit code, which was uncommitted when run.

| Check | Result | Interpretation |
| --- | --- | --- |
| Images / classes | 48,693 / 72 | Existing image counts reproduced |
| Train / validation / test images | 36,852 / 5,922 / 5,919 | Actual files read |
| Identical cross-split groups | 138 groups, 276 images | Both byte SHA-256 and oriented RGB pixel hashing detect overlap |
| Train–validation / train–test / validation–test | 63 / 56 / 19 groups | Not independent; metric inflation magnitude is unknown |
| Strict annotation flags | 51 train, 7 validation, 7 test images | Requires inspection; examples include zero-width boxes |
| Strict accepted instances | 56,287 / 8,805 / 8,868 | Excludes flagged lines; not a replacement for original evaluator counts |
| Nutrition rows / mappings | 1,010 / 103 | 72 canonical classes have precomputed mappings |
| Mappings below 0.9 or missing score | 21 | Heuristic review flag, not an independently assessed error rate |
| Coverage: exact normalized / no precomputed mappings / current | 19/72 / 55/72 / 72/72 | Lookup availability, **not accuracy** |
| Training CSV | 100 rows; best validation mAP50 at epoch 78 | Historical training result, not newly evaluated test performance |

Example overlap: `test/images/test0134-bhindi_masala.jpg` and `train/images/train16477-bhindi_masala.jpg`. No images were removed. The full local manifest supports reconstructing all groups. Near-duplicate crops, transforms, recompression and shared original-source identity were not exhaustively tested; these exact duplicates are a lower bound on overlap concerns.

Historical test mAP50 of approximately 0.820 is retained as a previously reported result, not proof of clean held-out generalization. Similar validation/test scores do not rule out leakage. Source README files describe augmentation already present in several downloads, while the builder pools source partitions and splits sample indices without source-family grouping. Additional training-only augmentation does not undo those upstream relationships.

## Candidate contribution and experiment protocol

### Implemented recovery tooling

`python scripts/prepare_research_split.py` now reconstructs candidate lineage against all five local source exports. It re-reads image bytes, decoded pixels and labels against the original audit manifest, rejects stale/incomplete input, joins exact-byte/pixel matches and within-export Roboflow filename families transitively, and assigns whole groups deterministically. Unknown lineage, strict annotation issues, empty accepted annotations and identical-pixel/different-label conflicts quarantine the entire related group. No dataset, checkpoint or database is edited or removed. Existing output directories are never overwritten.

[Grouped candidate evidence](evidence/grouped-split-v1.json) records the parameters and hashes. The full local source inventory and assignments are in `.deployment/research/grouped-v1-verified/`; `grouped-v1/` preserves the first run. Reproduction must use a fresh `--output` path. These local artifacts are not included in website releases.

Two independent full reads produced identical source-inventory and assignment SHA-256 hashes. The verified run also checks class-name ordering against the audit. The report's source commit identifies the base checkout and its script hash identifies the exact preparation code, added in this change. Ten synthetic research-tool tests pass, as do backend, frontend and browser regressions; both revised PDFs compile. These checks establish software reproducibility, not independent benchmark validity.

| Candidate partition | Images | Groups | Classes represented |
| --- | ---: | ---: | ---: |
| Train | 26,384 | 10,251 | 72 |
| Validation | 5,655 | 2,203 | 72 |
| Test | 5,652 | 2,205 | 72 |
| Quarantine | 11,002 | 9,274 | Not assigned |

There are **5,548 candidate source-family groups spanning the old partitions**. This is a heuristic grouping result, not 5,548 visually verified duplicate originals. The candidate assignment has zero cross-partition overlap for known groups, exact bytes and exact oriented pixels. Upstream augmented variants and within-group duplicates remain; different-name crops/recompression across sources can still escape grouping. The new split is **review-only**, not a benchmark or a validation of the existing checkpoint. Review original/representative selection and label conflicts before freezing any experiment. Quarantine is a manifest status, not deletion.

The INDB workbook provenance gap is resolved: it is byte-identical to the authors' pinned public artifact. [Provenance evidence](evidence/nutrition-provenance.json) and an offline/online checker now exist. Reuse terms still need owner review; no clinical correctness is inferred from identity.

Both paper abstracts and conclusions now describe an application/evidence audit rather than claim clean detector generalization or safe mappings. Runtime descriptions distinguish the offline mapping threshold from the more permissive preserved runtime fallbacks, gram estimates from measurements, and recommendation inputs from journal totals.

### Work still requiring evidence or approval

Hypothesis: **a provenance-preserving reviewed mapping layer reduces inappropriate Indian-food-to-nutrition matches while exposing unsupported/approximate cases, compared with name-only retrieval**. This is not a verified novelty or medical claim. Runtime fallback thresholds are preserved, not certified as sufficiently conservative.

1. Have a suitably qualified independent reviewer complete [mapping_review.csv](mapping_review.csv) using food-composition evidence, without copying current mapping outputs/scores as answers. Accepted database names are a JSON list; `[]` means no acceptable record was found after review. Every row needs reviewer identity and evidence. Adjudicate ambiguous cases and preserve original judgments.
2. Run `python scripts/evaluate_mapping_review.py --review research/mapping_review.csv`. It refuses incomplete reviews. Compare correct/wrong matches, correct abstentions and missed supported cases for normalized exact, automatic lookup without precomputed mappings, and current mapping. These 72 classes are a discovery set, not an untouched tuning benchmark. Freeze methods before review and use a separately specified challenge set for later tuning/confirmatory claims.
3. Review the newly reconstructed source-to-export lineage and candidate grouped manifest, including near duplicates, representative selection, annotation flags and conflicting labels. Freeze a reviewed version without replacing the old dataset. Simply reassigning or filtering images does not make the existing checkpoint independently evaluated. Retrain on clean partitions or obtain a genuinely untouched external test set; confirm the protocol and compute resources first.
4. Compare the existing architecture with one justified lightweight baseline under the same new split, input size and training budget. Report per-class results and CPU runtime. Run an augmentation ablation only if claiming augmentation benefit. Do not invent missing measurements or call old, differently trained checkpoints fair baselines.
5. Existing recommendation tests establish context handling, timeout and fallback behavior, not medical quality. Claims of advice quality require independent qualified assessment and a defined rubric. Do not begin patient-data collection or a human-subject study without checking institutional review requirements.

## Submission gate

- Both LaTeX drafts receive a blocking audit notice and updated application description; historical tables/figures remain historical. Rebuild PDFs with the notice before circulation.
- Remove unsupported claims of independent originals. Resolve annotation flags and explain strict-audit/evaluator count differences.
- The INDB placeholder has been replaced with the verified, pinned workbook citation. Resolve its reuse terms separately; artifact identity is not a license grant.
- Historical `VERIFIED` mapping labels describe heuristic checks, not clinical or recipe equivalence. Retain the 21 review flags.
- Runtime descriptions now reflect grams, saved-only daily totals, session-only health context and Groq-to-local fallback. Historical screenshots remain explicitly historical; replace them after choosing the final submission scope. Advice receives per-100-g values, not portion weights/history or calorie targets.
- Confirm authors, email/ORCID, affiliations and consent. Follow the chosen publisher's AI-assistance disclosure rules, describing actual assistance without inventing author contributions.
- Resolve [asset rights](../THIRD_PARTY_NOTICES.md), finish evidence, and then choose a [venue](VENUES.md) with the supervisors. None has been selected or contacted.

The next research step is independent reference review and a source-grouped evaluation protocol. Accounts, automatic portion estimation and charts are not prerequisites.
