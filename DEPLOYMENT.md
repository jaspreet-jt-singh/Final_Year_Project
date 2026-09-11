# Free Vercel deployment

One Hobby project serves the exported website from the CDN and FastAPI through
the native Python runtime. No container registry or paid storage is used.
Large Python functions are a beta feature; a successful Linux preview is a
release requirement, not something the local Windows checks establish.

## Project settings

- Framework: FastAPI. Root directory: repository root. Node: 24.x. Python: 3.12.
- Fluid Compute enabled. Region: Mumbai (`bom1`).
- Environment variables for Preview and Production:
  - `VERCEL_SUPPORT_LARGE_FUNCTIONS=1`
  - `VERCEL_FASTAPI_STATIC_CDN=1` (required by the deployed Python builder)
  - `APP_ENV=production`
  - `YOLO_MODEL_PATH=results_after_discontinuation/yolo11s_indian_food_best.pt`
  - `RATE_LIMIT_PER_MINUTE=10`
  - `GROQ_API_KEY`: enter privately as a backend environment variable.
  - `GROQ_MODEL=openai/gpt-oss-20b`: available to the existing key on Groq;
    the former Llama model is no longer available to this account.
- Leave `NEXT_PUBLIC_API_BASE_URL` unset so the website uses same-origin APIs.
- Use Groq's free tier. Do not configure a paid provider or upgrade Vercel.

Vercel installs from `pyproject.toml` and `uv.lock`. The build hook runs a clean
frontend install and static export, then copies it to root `web/`. FastAPI mounts
this directory, and explicit static CDN collection promotes it during the build.
Root HTML and assets are served by the CDN, independently of model readiness.
`static.cdn=true` handles CORS middleware and `static.exclude=true` omits the
frontend files from the Python bundle. The build excludes frontend dependencies from the Python
function. The research `requirements.txt` is not part of a release.

## Verify and prepare

From the repository root on Windows:

```powershell
.\.venv\Scripts\python.exe scripts/test_deployment.py
npm.cmd --prefix frontend run lint
npm.cmd --prefix frontend run build
npm.cmd --prefix frontend run typecheck
.\.venv\Scripts\python.exe scripts/prepare_vercel_release.py --commit
```

The last command prints a small `.deployment/release-*` directory and creates
or fast-forwards the local `vercel-live` branch. It does not switch branches,
modify the research index, push, or copy `.env`. `release-manifest.json` records
the source commit and exact SHA-256 digest of every deployed file, including
any implementation edits not yet committed to the source branch.

Connect `vercel-live` from the existing GitHub repository and choose it as the
production branch. For the initial release, deploy the printed directory with
`npx.cmd vercel` to create a preview before pushing the production branch.
Configure the environment variables above, then redeploy the preview.

## Release gates

- Linux import succeeds with the locked CPU wheels and headless OpenCV.
- Actual Python function bundle is below 5 GB; peak process memory below 1.6 GB.
- Homepage and static assets load without loading YOLO. `/api/health` shows
  `model_status=not_loaded` until the first analysis.
- A cold analysis finishes within 120 seconds. Run single-food, multidish,
  no-food, rotated-photo, invalid-upload and concurrent-upload checks.
- Compare CPU detections to the original model using the same confidence and
  IoU settings. Confirm overlay coordinates match the processed preview.
- Groq succeeds with the private key; timeout/quota failures produce three
  local fallback recommendations. No paid provider is attempted in production.
- API error responses are visible to the user. No localhost URLs or secrets
  appear in exported HTML/JS. `/api/*` responses are not cached.

After these checks, promote the preview and push `vercel-live` for subsequent
Git-connected deployments. Keep the last successful deployment for rollback.
If any gate fails, keep the site unpromoted and report the actual failure.

## Runtime behavior

YOLO imports and loads in a dedicated thread on the first scan. One analysis
runs and one can wait per instance; further scans receive 503 with Retry-After.
HTTP cancellation does not free a worker slot before inference actually stops.
Rate limits are per instance, not a global quota or spending control. Hobby
usage limits and Groq free quotas still apply; this is a personal demo and
does not promise unlimited traffic or constant readiness.

For local development, start `python -m uvicorn backend.main:app --reload` from
the repository root, and `npm.cmd --prefix frontend run dev` in another terminal.
The frontend uses localhost:8000 only in development. Existing local `.env`
settings are preserved. Runtime tests do not invoke Groq or paid services.
