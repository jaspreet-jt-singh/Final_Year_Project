# AI Food Recognition with Nutrition-Aware Recommendations

[Live educational demo](https://food-recognition-nutrition.vercel.app)

Scan a food photo, review estimated portions, and explicitly save a meal to your browser-only journal. The app detects supported Indian foods, looks up database nutrition per 100 g, and offers general goal/health-context guidance. It does not measure food weight or provide medically validated dietary advice.

## What is implemented

- CPU YOLO detection with unchanged production checkpoint, confidence settings and class mappings.
- User-estimated portions (25–1,000 g), exclusions, saved-only daily totals, editing and deletion/undo.
- Version-1 local journal with validation, unavailable-storage handling and local-day rollover.
- Async Groq recommendations with timeout, bounded concurrency and local fallback; context-matching diabetes/BP labels.
- Typed API contracts, generated policy, runtime validation, request IDs, and automated unit/browser checks.
- One Vercel application: static frontend and lazy Python inference. No paid provider fallback in production.

## Privacy and limitations

Processed photos go to the application backend for inference; the application does not deliberately store uploads. Included food names, per-100-g nutrition estimates, the goal and optional health context go to Groq for AI guidance. Photos, user-selected gram amounts and saved history do not go to Groq. Vercel/Groq have their own request-processing and retention policies. Health selections and photos are not persisted in the journal; goals and meals remain in localStorage and can be lost when browser data is cleared.

Nutrition varies with recipes and preparation. Some database matches are substitutes and five records come from supplemental sources. Source labels/links and matching cautions are shown for new scans. Earlier journal entries retain their original source strings. Model confidence is not nutrition accuracy. Health labels identify the context used, not clinical validation. No claims of global quota control, unlimited availability or guaranteed medical suitability are made.

## Local development

The deployment/CI lock targets Linux x86-64, Python 3.12 and Node 24. On Linux (or WSL), from the repository root:

```sh
uv sync --frozen
npm ci --prefix frontend
uv run uvicorn backend.main:app --reload
```

In another terminal, run `npm --prefix frontend run dev`. Local frontend requests use `http://localhost:8000`; production uses same-origin `/api/*`. The tracked nutrition database and production checkpoint are required. Keep optional `GROQ_API_KEY` in the backend environment or root `.env`, never a `NEXT_PUBLIC_*` variable. With no key, local guidance falls back without a provider call. Native Windows uses an appropriately provisioned environment; the Linux-only lock is not advertised as a native Windows install recipe.

## Verification

```sh
uv pip install -r scripts/requirements-dev.txt
uv run python scripts/generate_contracts.py --check
uv run python scripts/test_deployment.py
uv run python scripts/test_architecture.py
uv run python scripts/test_publication.py
npm --prefix frontend run lint
npm --prefix frontend run test:unit
npm --prefix frontend run build
npm --prefix frontend run typecheck
npm --prefix frontend exec -- playwright install --with-deps chromium
npm --prefix frontend run test:browser
```

CI never needs provider credentials or live AI calls. It includes synthetic source-grouping tests and an offline check of the pinned INDB workbook. The full research audit and candidate split preparation are separate from CI because source images are not in the runtime release.

For research preparation, run `python scripts/audit_publication.py`, then `python scripts/prepare_research_split.py --output .deployment/research/my-reviewed-candidate`. The second command verifies the audited files, groups known source families and quarantines unresolved records in a new manifest; it never rewrites the dataset or trains a model. See the limitations before using it for experiments. Verify the original workbook with `python scripts/verify_nutrition_provenance.py --online`.

## Publication and reuse

See [research readiness and next steps](research/READINESS.md), [venue shortlist](research/VENUES.md), [third-party provenance](THIRD_PARTY_NOTICES.md), and [deployment instructions](DEPLOYMENT.md). The manuscripts are working drafts, not evidence of acceptance or clinical validation. Do not redistribute the merged image dataset or assume unrestricted model/database reuse until the outstanding rights checks are resolved. No new license grant is implied by this README.
