# AI Food Recognition — Cascade Rules
## .windsurf/rules/project.md

---
trigger: always_on
---

> These rules are enforced in EVERY Cascade session.
> Full project plan is in AGENTS.md at project root — read it before starting any phase.

---

## OS & Environment

- OS: Windows 11, PowerShell terminal
- Python: 3.12.7 via `.venv` (NOT conda — ignore the (base) prefix)
- Node.js: v22.x LTS
- Package manager: npm (not yarn, not pnpm)
- GPU: NVIDIA RTX 3050 Laptop, 4GB VRAM, CUDA 12.7
- PyTorch build: cu124

Activate venv before any Python command:
```
.venv\Scripts\activate
```

---

## PowerShell Command Rules

- `python -c` multiline is **STRICTLY FORBIDDEN** — no exceptions, ever
- Never use `/usr/bin/env` — does not exist on Windows
- Never use `&&` to chain commands — use semicolons: `cd backend; python app.py`
- Never use `python3` — use `python`
- Never use `export VAR=value` — use `$env:VAR = "value"`
- Never use `rm -rf` — use `Remove-Item -Recurse -Force`
- Never use `./script.sh` — use `.\script.ps1` or `python script.py`
- Always write test/debug code to a `.py` file and run it

---

## Working Directory Rules

```
Backend commands  → cd G:\Projects\Final_Year_Project\backend
Frontend commands → cd G:\Projects\Final_Year_Project\frontend
Test commands     → cd G:\Projects\Final_Year_Project
```

- NEVER run `npm` from project root — `package.json` is in `/frontend`
- NEVER run `uvicorn` from project root — `main.py` is in `/backend`

---

## Server Start Commands

```
Tab 1 (Backend):  cd backend; uvicorn main:app --host 0.0.0.0 --port 8000 --reload
Tab 2 (Frontend): cd frontend; npm run dev
Tab 3 (Tests):    cd G:\Projects\Final_Year_Project
```

- NEVER start FastAPI with `python main.py`
- Backend: http://localhost:8000
- Frontend: http://localhost:3000
- When a server starts it stays running — open a NEW terminal tab to continue

---

## Non-Interactive Command Rules

- `npx create-next-app`: ALWAYS add `--yes` flag
- `npm init`: ALWAYS use `npm init -y`
- Any CLI that prompts questions: find `--yes`/`--force` flag first

### Long-running commands (NOT stuck — do not interrupt)

| Command | Expected wait |
|---|---|
| `npx create-next-app` | 2–3 minutes |
| `pip install torch` | 5–10 minutes |
| YOLOv8 first inference | 30–60 seconds |
| `npm install` | 1–2 minutes |
| YOLO training | 3–4 hours |

---

## Test & Debug File Rules

- ALL test files go in: `tests/` at project root only
- Naming: `tests/test_phase0.py`, `tests/test_phase1.py`, etc.
- Run from project root: `python tests\test_phaseX.py`
- NEVER place test files in `backend/` or `frontend/`
- NEVER run tests from inside `backend/` or `frontend/`

---

## Notebook Rules

- ALL `.ipynb` files go in: `notebooks/` folder only
- Use `.ipynb` for: training, data exploration, validation charts
- NEVER use `.ipynb` for: FastAPI services, API routes, frontend, tests
- FastAPI backend MUST be `.py` files — cannot import from notebooks

---

## API Testing (Windows)

```powershell
# GET — clean, no security warning
Invoke-RestMethod -Uri http://localhost:8000/api/health -Method GET

# curl with warning suppressed
curl -UseBasicParsing http://localhost:8000/api/health
```

---

## Vision Model Rules

- ONE YOLOv8n-seg model only
- NEVER add: EfficientNet, FastSAM, separate classifier, second detector
- Model path via env: `os.getenv("YOLO_MODEL_PATH", "models/yolov8n-seg.pt")`
- All PyTorch inference → `asyncio.run_in_executor` (never block event loop)
- Resize all uploads to max 1024px before inference
- SQLite → always `check_same_thread=False`

---

## YOLO Training Rules (Local GPU)

- batch=8, amp=True, workers=2, device=0 (MANDATORY for 4GB VRAM)
- Training script: `python backend\scripts\train_yolo_seg.py`
- Training notebook: `notebooks/02_train_yolo.ipynb`
- Monitor: `nvidia-smi -l 3` in separate terminal
- Output: `models/yolov8_indian_seg.pt` + `models/class_names.json`
- After training: update `.env` → `YOLO_MODEL_PATH=models/yolov8_indian_seg.pt`

---

## Frontend Rules (Next.js App Router)

- App Router ONLY — NEVER create a `pages/` directory
- Required files:
  `frontend/src/app/page.tsx`    ← homepage (must exist)
  `frontend/src/app/layout.tsx`  ← root layout (must exist, keep minimal)
- If 404 persists after fixing `page.tsx` → bug is always in `layout.tsx`
- After creating new components → clear cache: `Remove-Item -Recurse -Force .next`
- Never import a component before that file is fully written
- Zustand for ALL state — no Redux, no prop drilling
- Canvas bbox → ALWAYS scale: `scaleX = canvas.offsetWidth / img_width`

---

## Git & .gitignore Rules

- ALWAYS update `.gitignore` after creating new sensitive files
- After every phase: run `git status` — verify no secrets or large files staged
- NEVER commit `.env`

`.gitignore` must always contain:
```gitignore
.venv/
__pycache__/
*.pyc
.env
.env.local
models/*.pt
models/*.pth
models/*.onnx
data/*.db
data/*.xlsx
data/*.csv
frontend/.next/
frontend/node_modules/
*.log
logs/
models/runs/
.DS_Store
Thumbs.db
```

---

## Phase Execution Rule

- Execute STRICTLY phase by phase
- Each phase is a self-contained mini-project
- Stop at the defined stop condition for each phase
- Do NOT start the next phase without explicit approval
- Full phase prompts are in AGENTS.md section 10

---

## If You Drift Off-Plan

The user will say: "Stop. Re-read @AGENTS.md [Phase X]."
Immediately revert the incorrect change and follow AGENTS.md exactly.
