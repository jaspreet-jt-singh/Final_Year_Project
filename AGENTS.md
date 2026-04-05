# AI Food Recognition with Nutrition-Aware Recommendations
## AGENTS.md — Project Directive for Cascade

> This file is the single source of truth for the entire project.
> Read this fully before executing any phase.

---

## 1. Project Goal

Build a full-stack web MVP that:
- Recognises an Indian food item from an uploaded image using a detection model
- Fetches real nutrition values from INDB database using per-100g values
- Generates a personalised LLM-based meal recommendation

---

## 2. Final Architecture

```
Image Upload
   ↓
YOLOv8n (detection) → food_label + bounding_box + confidence
   ↓
SQLite DB lookup (INDB only) → macros per 100g
   ↓
Groq LLM → 1-day compensatory meal plan JSON
```

---

## 3. Final Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14, App Router, Tailwind CSS, Zustand |
| Backend | FastAPI, Python 3.12.7, Uvicorn |
| Vision | YOLOv8n (detection only — no segmentation) |
| Database | SQLite only |
| LLM | Groq API (llama-3.3-70b-versatile) → OpenAI → Ollama llama3.1:8b |

---

## 4. Data Rules

- **INDB.xlsx** — sole nutrition source; 1,014 composite Indian recipes, per-100g values
- **NIN_fct.xlsx** — intentionally NOT imported into the DB. It covers 528 raw
  ingredients only (uncooked rice, wheat flour, raw dal). All 30 YOLO food classes
  are composite prepared dishes — NIN_fct provides zero useful fallback and is excluded.
- **No food_label_map.json** — the SQLite DB is the single source of truth
- All macros are returned **per 100g** exactly as stored in the DB — no serving size scaling

### Column Mapping (INDB raw → DB schema)
The actual column names in INDB.xlsx differ from standard naming — `merge_db.py`
must rename them explicitly on import:

| INDB.xlsx column | DB column name |
|---|---|
| `energy_kcal` | `calories` |
| `carb_g` | `carbs_g` |
| `protein_g` | `protein_g` |
| `fat_g` | `fat_g` |

### Label Normalisation
- YOLO labels (snake_case) are normalised to title case before DB lookup:
  `"dal_makhani"` → `"Dal Makhani"` via `label.replace("_", " ").title()`
- DB lookup uses `WHERE LOWER(name) = LOWER(?)` for capitalisation safety

### Known Missing Foods
These 3 YOLO classes are absent from INDB and have no valid fallback:
`kathi_roll`, `vada_pav`, `momos` — they will always return `food_not_found: true`.
The Phase 4 error toast handles this gracefully in the UI.

### Scaling Path (future, not current scope)
When serving sizes are needed later, add a `serving_g INTEGER` column directly
to the `indb_recipes` table and populate via a migration script (INDB.xlsx already
stores per-serving values — the data is available). The DB stays the single source
of truth — no config files are introduced.

---

## 5. API Contract

### GET /api/health
```json
{
  "status": "ok",
  "model_loaded": true,
  "phase": "1",
  "description": "AI Food Recognition - Phase 1 MVP"
}
```

### POST /api/analyze-food
Input: multipart/form-data image (max 10MB)

Output:
```json
{
  "food_label": "dal_makhani",
  "display_name": "Dal Makhani",
  "confidence": 0.91,
  "bounding_box": [40, 60, 320, 300],
  "img_width": 640,
  "img_height": 480,
  "macros": {
    "calories": 152,
    "protein_g": 6.8,
    "carbs_g": 12.3,
    "fat_g": 7.8
  },
  "macros_unit": "per_100g",
  "nutrition_source": "INDB",
  "food_not_found": false
}
```

> `macros_unit` is always `"per_100g"`.
> `nutrition_source` is always `"INDB"` — there is no IFCT fallback.
> The frontend must display a "per 100g" label with every macro value.

### POST /api/generate-meal-plan
```json
{
  "food_label": "dal_makhani",
  "macros": { "calories": 152, "protein_g": 6.8, "carbs_g": 12.3, "fat_g": 7.8 },
  "macros_unit": "per_100g",
  "profile": { "age": 22, "weight_kg": 72, "goal": "muscle_gain", "allergies": "none" }
}
```

---

## 6. Directory Structure

```
project-root/
├── AGENTS.md
├── .env
├── .gitignore
├── requirements.txt
├── frontend/
│   ├── package.json
│   └── src/
│       ├── app/
│       │   ├── page.tsx
│       │   └── layout.tsx
│       ├── components/
│       │   ├── ImageUpload.tsx
│       │   ├── ImageOverlay.tsx
│       │   ├── ResultsPanel.tsx
│       │   ├── NutritionLabel.tsx
│       │   ├── MealRecommendations.tsx
│       │   └── UserProfileForm.tsx
│       └── store/
│           └── foodStore.ts
├── backend/
│   ├── main.py
│   ├── api/
│   │   ├── analyze_food.py
│   │   └── generate_meal_plan.py
│   ├── services/
│   │   ├── vision_service.py
│   │   ├── nutrition_service.py
│   │   └── llm_service.py
│   └── scripts/
│       ├── merge_db.py
│       └── train_yolo_det.py
├── data/
│   ├── nutrition.db
│   ├── INDB.xlsx          ← only source imported into nutrition.db
│   ├── NIN_fct.xlsx       ← kept for reference only, never imported
│   └── indianfoodnet_yolo/
├── models/
│   ├── yolov8n_indian.pt
│   ├── yolov8n.pt
│   └── class_names.json
├── notebooks/
│   ├── 01_explore_indb.ipynb
│   └── 02_train_yolo.ipynb
└── tests/
    ├── test_phase0.py
    ├── test_phase1.py
    ├── test_phase2.py
    ├── test_phase3.py
    └── test_phase4.py
```

> `food_label_map.json` and `build_label_map.py` are intentionally absent.
> `NIN_fct.xlsx` is present in data/ for reference but never read by any script.

---

## 7. .env File

```env
# LLM
GROQ_API_KEY=
OPENAI_API_KEY=
OLLAMA_HOST=http://localhost:11434

# Model (switch to yolov8n_indian.pt after training)
YOLO_MODEL_PATH=models/yolov8n.pt

# Server
RATE_LIMIT_PER_MINUTE=5
```

---

## 8. Core Technical Rules

1. ONE YOLOv8n detection model only — never use seg, EfficientNet, FastSAM, or a separate classifier
2. All PyTorch inference → `asyncio.run_in_executor` — never block FastAPI event loop
3. SQLite → always `check_same_thread=False`
4. Canvas bounding box → scale with `scaleX = displayWidth / img_width` before drawing
5. Resize all uploads to max 1024px before inference
6. Use Zustand for ALL frontend state — no Redux, no prop drilling
7. Never import a component in page.tsx before that component file is fully written
8. App Router ONLY — never create a `pages/` directory
9. After creating new components, clear cache: `Remove-Item -Recurse -Force .next`
10. Each phase is a self-contained mini-project — fully demo-ready before next phase
11. Add `'use client'` to every component that uses Zustand hooks, event handlers
    (onClick, onChange), or browser APIs — never add it to layout.tsx or page.tsx
12. SQLite is the single source of truth — never introduce config JSON files for data lookup
13. All macros are per 100g — no serving size scaling in any service or endpoint
14. YOLO label normalisation lives only in `nutrition_service.py` — no other file touches it
15. NIN_fct.xlsx is never read or imported — only INDB.xlsx feeds nutrition.db
16. The only valid DB table is `indb_recipes` — there is no `ifct_ingredients` table

---

## 9. Phase Overview

| Phase | Mini-Project Title | Demo-Ready Output |
|---|---|---|
| Phase 0 | Data Foundation | nutrition.db (INDB only) + train script ready |
| Phase 1 | Working Food Recognition MVP | Upload image → see real food label + nutrition |
| Phase 2 | Detection Overlay MVP | Bounding box drawn over food in image |
| Phase 3 | NutriGen Meal Planner MVP | Personalised breakfast/lunch/dinner cards |
| Phase 4 | Polish & Demo Readiness | Mobile layout + error toasts + clean git |

---

## 10. Phase Execution Prompts

---

### PHASE 0 — Data Foundation (Mini-Project 0)

**Goal:** Build nutrition.db from INDB.xlsx only and prepare the YOLO training pipeline.

**Stop condition:** `python tests\test_phase0.py` passes with zero errors.

**Prompt:**
```
Execute Phase 0 — Data Foundation mini-project.

1. backend/scripts/merge_db.py

   SOURCE: data/INDB.xlsx (sheet 0) — only this file is imported. Never read NIN_fct.xlsx.

   Step A — Inspect and print raw columns:
     df = pd.read_excel("data/INDB.xlsx", sheet_name=0)
     print("INDB shape:", df.shape)
     print("INDB columns:", df.columns.tolist())
     # This output must be reviewed before proceeding to confirm actual column names.

   Step B — Rename columns to match DB schema (INDB actual → standard name):
     rename_map = {
         "energy_kcal": "calories",
         "carb_g":      "carbs_g",
         "protein_g":   "protein_g",   # already correct
         "fat_g":       "fat_g",        # already correct
     }
     df = df.rename(columns=rename_map)
     # If the actual INDB column names differ from above, adjust rename_map
     # to match what Step A printed — never hardcode blindly.

   Step C — Normalise recipe names to title case:
     df["name"] = df["name"].str.strip().str.title()

   Step D — Print all recipe names for manual verification:
     print("\n=== ALL INDB RECIPE NAMES ===")
     for name in sorted(df["name"].tolist()):
         print(name)
     # Review this list to confirm YOLO class names will match after normalisation.
     # Look specifically for: Biryani, Butter Chicken, Chole Bhature, Dal Makhani,
     # Dal Tadka, Dosa, Kadai Paneer, Masala Dosa, Naan, Pakoda, Paneer Butter Masala,
     # Palak Paneer, Pav Bhaji, Samosa, Shahi Paneer, Uttapam, and all 30 YOLO classes.

   Step E — Create data/nutrition.db with ONE table only:
     indb_recipes:
       id       INTEGER PRIMARY KEY AUTOINCREMENT,
       name     TEXT UNIQUE NOT NULL,
       calories REAL,
       protein_g REAL,
       carbs_g  REAL,
       fat_g    REAL
     (all values per 100g as-is from INDB — no scaling)

     Insert only rows where all four macro columns are non-null.
     SQLite: check_same_thread=False.
     Print row count after insert: print(f"Inserted {n} recipes into indb_recipes")

   DO NOT create ifct_ingredients table. NIN_fct.xlsx is never read.

2. notebooks/02_train_yolo.ipynb — training notebook with cells:
   Cell 1: GPU check + imports
   Cell 2: YOLO detection training (task=detect,
           data=data/indianfoodnet_yolo/data.yaml,
           epochs=60, imgsz=640, batch=8, patience=15, device=0,
           workers=2, amp=True, save_period=10)
   Cell 3: Copy best.pt → models/yolov8n_indian.pt
   Cell 4: Save class names → models/class_names.json
   Cell 5: Plot training loss curves inline

3. backend/scripts/train_yolo_det.py — same logic as notebook but as .py
   for running from terminal: python backend\scripts\train_yolo_det.py

4. tests/test_phase0.py — verify:
   - data/INDB.xlsx exists
   - data/nutrition.db exists
   - nutrition.db has table indb_recipes with > 0 rows
   - indb_recipes has columns: id, name, calories, protein_g, carbs_g, fat_g
   - nutrition.db does NOT have a table named ifct_ingredients (assert absence)
   - No food_label_map.json exists anywhere in the repo (assert absence)
   - models/ folder exists

Run: python tests\test_phase0.py
Stop after test passes with zero errors.
```

---

### PHASE 1 — Working Food Recognition MVP (Mini-Project 1)

**Goal:** Upload an image → get real Indian food label + real per-100g nutrition values displayed in UI.

**Stop condition:** `/api/health` returns `model_loaded: true` AND UI renders at `localhost:3000`.

**Prompt:**
```
Execute Phase 1 — Working Food Recognition mini-project.

Backend:
- backend/main.py:
  FastAPI with CORS for http://localhost:3000
  slowapi rate limiter: 5 req/min on /api/analyze-food
  ThreadPoolExecutor max_workers=2
  Load YOLOv8n from os.getenv("YOLO_MODEL_PATH", "models/yolov8n.pt") at startup
  Load data/nutrition.db at startup (no JSON files, no NIN_fct)
  Warm-up pass on dummy black image after model loads
  GET /api/health → {"status":"ok","model_loaded":true,"phase":"1",...}

- backend/services/vision_service.py:
  _resize_image(image_bytes) → PIL Image max 1024px
  _run_yolo(image_bytes) → food_label, confidence, bounding_box [x1,y1,x2,y2],
    img_width, img_height
  Use model(image)[0].boxes — detection results only, no masks
  If confidence < 0.3: return food_label="unknown", confidence=0.0
  All sync. Async wrappers use run_in_executor.

- backend/services/nutrition_service.py:
  _normalize_label(food_label: str) -> str:
    return food_label.replace("_", " ").title()
    # "dal_makhani" → "Dal Makhani"

  get_macros(food_label: str) -> dict:
    display_name = _normalize_label(food_label)

    # Query indb_recipes — single source, no fallback table
    row = db.execute(
        """SELECT calories, protein_g, carbs_g, fat_g
           FROM indb_recipes
           WHERE LOWER(name) = LOWER(?)""",
        (display_name,)
    ).fetchone()

    if row:
        return {
            **dict(row),
            "nutrition_source": "INDB",
            "macros_unit": "per_100g",
            "food_not_found": False
        }

    # Not found in INDB — no further fallback
    logger.warning(f"Food not found in INDB: {food_label} (normalised: {display_name})")
    return {"food_not_found": True, "macros_unit": "per_100g"}

  No ifct_ingredients query. No USDA. No JSON mapping. No serving size scaling.

- backend/api/analyze_food.py:
  POST /api/analyze-food — full API contract from section 5
  Input validation: reject >10MB (413), reject non-images (400)

Frontend:
- frontend/src/store/foodStore.ts:
  Zustand fields: imageFile, imageUrl, result, isLoading, error, userProfile

  Use persist middleware for userProfile ONLY:
  import { create } from 'zustand'
  import { persist } from 'zustand/middleware'

  const useFoodStore = create(
    persist(
      (set) => ({
        imageFile: null,
        imageUrl: null,
        result: null,
        isLoading: false,
        error: null,
        userProfile: null,
        setImageFile: (file) => set({ imageFile: file }),
        setImageUrl: (url) => set({ imageUrl: url }),
        setResult: (result) => set({ result }),
        setIsLoading: (v) => set({ isLoading: v }),
        setError: (e) => set({ error: e }),
        setUserProfile: (profile) => set({ userProfile: profile }),
      }),
      {
        name: "nutrigen-user-profile",
        partialize: (state) => ({ userProfile: state.userProfile }),
      }
    )
  )

- frontend/src/components/ImageUpload.tsx: (add 'use client')
  Drag-and-drop + click to upload. Shows image preview after selection.

- frontend/src/components/NutritionLabel.tsx: (add 'use client')
  Displays: calories, protein_g, carbs_g, fat_g
  Always show "per 100g" label beneath every macro value — never omit this

- frontend/src/components/ResultsPanel.tsx: (add 'use client')
  Shows: display_name, confidence badge, NutritionLabel
  Show "per 100g" subtitle under the nutrition section heading

- frontend/src/app/layout.tsx:
  Minimal — html + body + children with Tailwind base class only
  Do NOT add 'use client' here.

- frontend/src/app/page.tsx:
  Two-panel layout: left=image upload, right=ResultsPanel
  On upload: POST to /api/analyze-food → store in Zustand → render results
  Loading state: "Detecting... → Classifying... → Looking up nutrition..."

Write tests/test_phase1.py to verify:
- API response contains macros_unit: "per_100g"
- API response contains nutrition_source: "INDB" (never "IFCT")
- food_not_found: true is returned for unknown labels
Stop after health check passes AND upload UI renders at localhost:3000.
```

---

### PHASE 2 — Detection Overlay MVP (Mini-Project 2)

**Goal:** Show the detected food location visually with a bounding box drawn over the image.

**Stop condition:** Bounding box renders at correct position on the food in the image.

**Prompt:**
```
Execute Phase 2 — Detection Overlay mini-project.

Backend:
- vision_service.py already returns bounding_box [x1,y1,x2,y2],
  img_width, img_height from Phase 1. No backend changes needed.

Frontend:
- components/ImageOverlay.tsx: (add 'use client')
  Image inside <div style={{position:"relative"}}>
  Absolutely positioned <canvas> overlay on top
  CRITICAL: scaleX = canvas.offsetWidth / img_width
            scaleY = canvas.offsetHeight / img_height
  Draw 2px teal bounding box scaled to display size
  Food label text drawn above the box in teal
  No mask drawing — detection only
- Replace plain <img> in page.tsx with <ImageOverlay>
- Show "YOLO Detected" badge when confidence > 0.3

Write tests/test_phase2.py.
Stop after bounding box renders at correct position on the food.
```

---

### PHASE 3 — NutriGen Meal Planner MVP (Mini-Project 3)

**Goal:** Generate personalised Indian meal recommendations using LLM based on detected food + user profile.

**Stop condition:** Breakfast/Lunch/Dinner cards render with real LLM data.

**Prompt:**
```
Execute Phase 3 — NutriGen Meal Planner mini-project.

Backend (backend/services/llm_service.py):
- Detect provider at startup: GROQ_API_KEY → OPENAI_API_KEY → ollama
- Log active provider on startup
- Groq model: llama-3.3-70b-versatile
- Ollama model: llama3.1:8b

- System prompt (exact):
  "You are NutriGen, a certified Indian dietitian.
  The nutrition values provided are per 100g.
  Respond ONLY with valid JSON. No markdown. No explanation.
  Format: {breakfast:{name,description,calories,protein_g},
           lunch:{same}, dinner:{same}, tip:string}
  Suggest common Indian home-cooked dishes only."

- _extract_json(text): use re.search(r'\{[\s\S]*\}', text)
  to extract JSON even if LLM wraps in markdown
- Retry once if JSON parse fails
- Return hardcoded fallback plan if retry also fails:
  breakfast=poha, lunch=dal rice, dinner=roti sabzi

- Add POST /api/generate-meal-plan endpoint

Frontend:
- components/UserProfileForm.tsx: (add 'use client')
  Slide-in drawer. Fields: age, weight_kg,
  goal (weight_loss/muscle_gain/maintenance), allergies
  Save to Zustand userProfile on submit
  Profile auto-populates on next visit via Zustand persist (localStorage)

- "Generate Meal Plan" button — visible only after food analysis completes

- components/MealRecommendations.tsx: (add 'use client')
  Three cards: Breakfast, Lunch, Dinner
  Each card: name, description, calories, protein_g
  Tip shown at bottom in muted text
  Loading skeleton while LLM responds (not blank — show shimmer)

Write tests/test_phase3.py.
Stop after meal cards render with real LLM data.
```

---

### PHASE 4 — Polish & Demo Readiness (Mini-Project 4)

**Goal:** Make the project demo-safe, mobile-ready, and report-ready.

**Stop condition:** All toasts work, layout is clean at 375px, git status is clean.

**Prompt:**
```
Execute Phase 4 — Polish and Demo Readiness mini-project.

Backend:
- Add X-Request-ID header logging on every request

Frontend:
- Shimmer skeleton for ResultsPanel while /api/analyze-food loads
- Shimmer skeleton for MealRecommendations while LLM responds
- Error toasts for exactly these cases:
  "No food detected — try better lighting and a clear view of the dish"
  "Food not found in nutrition database"
  "Meal plan generation failed — showing default plan"
- Single column layout at < 768px, meal cards stack vertically
- Test at 375px width (iPhone SE) — verify no overflow
- Remove ALL console.log statements
- Remove ALL debug/temp UI elements

Final checks:
- Run git status → verify .gitignore covers all large/secret files
- Confirm no food_label_map.json exists anywhere in the repo
- Confirm no ifct_ingredients table exists in nutrition.db
- Run python tests\test_phase0.py through test_phase3.py — all must pass
- Start both servers and do a full end-to-end demo run

Stop after all toasts work, mobile layout is clean, and git status is clean.
```

---

## 11. YOLO Training Quick Reference

```
Task:       Detection (not segmentation)
Dataset:    data/indianfoodnet_yolo/data.yaml  (from Roboflow IndianFoodNet)
Script:     python backend\scripts\train_yolo_det.py
Notebook:   notebooks/02_train_yolo.ipynb
GPU:        RTX 3050 Laptop (4GB VRAM)
Settings:   task=detect, batch=8, amp=True, workers=2, epochs=60
Time:       ~2-3 hours (faster than seg)
Output:     models/yolov8n_indian.pt + models/class_names.json
After:      Update .env → YOLO_MODEL_PATH=models/yolov8n_indian.pt
Monitor:    nvidia-smi -l 3 (in separate terminal)
```

---

## 12. When Cascade Drifts Off-Plan

```
Stop. Re-read @AGENTS.md [Phase X section].
You added [wrong thing]. Revert [filename] to follow AGENTS.md exactly.
```
