# AI Food Recognition with Nutrition-Aware Recommendations
## AGENTS.md — Project Directive for Cascade

> This file is the single source of truth for the entire project.
> Read this fully before executing any phase.

---

## 1. Project Goal

Build a full-stack web MVP that:
- Recognises an Indian food item from an uploaded image
- Estimates portion mass using monocular depth + plate anchor
- Fetches real nutrition values from INDB / IFCT databases
- Generates a personalised LLM-based meal recommendation

---

## 2. Final Architecture

```
Image Upload
   ↓
YOLOv8n-seg → food_label + bounding_box + mask
   ↓
Depth Anything V2 Metric → depth_map + plate_anchor → estimated_mass_g
   ↓
INDB lookup → macros (scaled by estimated mass)
   ↓
Groq LLM → 1-day compensatory meal plan JSON
```

---

## 3. Final Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14, App Router, Tailwind CSS, Zustand |
| Backend | FastAPI, Python 3.12.7, Uvicorn |
| Vision | YOLOv8n-seg (single model only) |
| Depth | Depth Anything V2 Metric Indoor Small (HuggingFace) |
| Database | SQLite only |
| LLM | Groq API → OpenAI → Ollama llama3.1:8b |

---

## 4. Data Rules

- **INDB.xlsx** — primary nutrition source for all prepared Indian dishes
- **NIN_fct.xlsx** — fallback for raw or ingredient-level foods only
- **food_label_map.json** — maps every YOLO class to:
  `{ "indb_name": "", "source": "indb|usda", "density": float, "serving_g": int }`
- If no INDB match found: return `food_not_found: true`, never crash

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
  "mask_base64": "...",
  "estimated_mass_g": 180,
  "mass_confidence_band_g": 40,
  "mass_source": "depth_plate_anchor",
  "plate_anchor_used": true,
  "macros": {
    "calories": 274,
    "protein_g": 12.2,
    "carbs_g": 22.1,
    "fat_g": 14.0
  },
  "nutrition_source": "INDB",
  "food_not_found": false
}
```

### POST /api/override-mass
```json
{ "food_label": "dal_makhani", "mass_g": 220 }
```

### POST /api/generate-meal-plan
```json
{
  "food_label": "dal_makhani",
  "mass_g": 180,
  "macros": { "calories": 274, "protein_g": 12.2, "carbs_g": 22.1, "fat_g": 14.0 },
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
│       │   ├── MassDisplay.tsx
│       │   ├── MealRecommendations.tsx
│       │   └── UserProfileForm.tsx
│       └── store/
│           └── foodStore.ts
├── backend/
│   ├── main.py
│   ├── api/
│   │   ├── analyze_food.py
│   │   ├── override_mass.py
│   │   └── generate_meal_plan.py
│   ├── services/
│   │   ├── vision_service.py
│   │   ├── nutrition_service.py
│   │   ├── depth_service.py
│   │   └── llm_service.py
│   └── scripts/
│       ├── merge_db.py
│       ├── build_label_map.py
│       ├── train_yolo_seg.py
│       └── validate_mass.py
├── data/
│   ├── nutrition.db
│   ├── food_label_map.json
│   ├── INDB.xlsx
│   ├── NIN_fct.xlsx
│   └── indianfoodnet_yolo/
├── models/
│   ├── yolov8_indian_seg.pt
│   ├── yolov8n-seg.pt
│   └── class_names.json
├── notebooks/
│   ├── 01_explore_indb.ipynb
│   ├── 02_train_yolo.ipynb
│   └── 03_validate_mass.ipynb
└── tests/
    ├── test_phase0.py
    ├── test_phase1.py
    ├── test_phase2.py
    ├── test_phase3.py
    ├── test_phase4.py
    └── test_phase5.py
```

---

## 7. .env File

```env
# LLM
GROQ_API_KEY=
OPENAI_API_KEY=
OLLAMA_HOST=http://localhost:11434

# Model (switch to yolov8_indian_seg.pt after training)
YOLO_MODEL_PATH=models/yolov8n-seg.pt

# Depth
DEPTH_ENABLED=true
PLATE_DIAMETER_CM=26
MAE_FRACTION=0.25

# Server
RATE_LIMIT_PER_MINUTE=5
```

---

## 8. Core Technical Rules

1. ONE YOLOv8n-seg model only — never add EfficientNet, FastSAM, or a separate classifier
2. All PyTorch inference → `asyncio.run_in_executor` — never block FastAPI event loop
3. SQLite → always `check_same_thread=False`
4. Canvas bounding box → scale with `scaleX = displayWidth / img_width` before drawing
5. Resize all uploads to max 1024px before inference
6. Use Zustand for ALL frontend state — no Redux, no prop drilling
7. Never import a component in page.tsx before that component file is fully written
8. App Router ONLY — never create a `pages/` directory
9. After creating new components, clear cache: `Remove-Item -Recurse -Force .next`
10. Each phase is a self-contained mini-project — fully demo-ready before next phase

---

## 9. Phase Overview

| Phase | Mini-Project Title | Demo-Ready Output |
|---|---|---|
| Phase 0 | Data Foundation | nutrition.db + food_label_map.json + train script ready |
| Phase 1 | Working Food Recognition MVP | Upload image → see real food label + nutrition |
| Phase 2 | Detection Overlay MVP | Bounding box drawn over food in image |
| Phase 3 | Segmentation MVP | Mask overlay + toggle on detected food |
| Phase 4 | Portion & Mass Estimation MVP | Estimated mass + manual override + recalculated macros |
| Phase 5 | NutriGen Meal Planner MVP | Personalised breakfast/lunch/dinner cards |
| Phase 6 | Polish & Demo Readiness | Mobile layout + error toasts + validation metrics |

---

## 10. Phase Execution Prompts

---

### PHASE 0 — Data Foundation (Mini-Project 0)

**Goal:** Prepare all data and model training pipeline before app development.

**Stop condition:** `python tests\test_phase0.py` passes with zero errors.

**Prompt:**
```
Execute Phase 0 — Data Foundation mini-project.

1. backend/scripts/merge_db.py
   - Read data/INDB.xlsx (sheet 0) + data/NIN_fct.xlsx
   - Print column names before processing
   - Create data/nutrition.db with two tables:
     indb_recipes: id, name, calories, protein_g, carbs_g, fat_g (per 100g)
     ifct_ingredients: id, name, calories, protein_g, carbs_g, fat_g (per 100g)
   - SQLite: check_same_thread=False
   - All macro values stored as per-100g floats

2. data/food_label_map.json — 30 Indian food classes:
   biryani, butter_chicken, chapati, chole_bhature, dal_makhani, dal_tadka,
   dosa, gulab_jamun, idli, jalebi, kadai_paneer, kathi_roll, kheer, kulfi,
   masala_dosa, medu_vada, naan, pakoda, palak_paneer, paneer_butter_masala,
   pav_bhaji, poha, puri, rasgulla, ras_malai, samosa, shahi_paneer,
   uttapam, vada_pav, momos
   Each entry: { "indb_name": "", "source": "indb|usda", "density": float, "serving_g": int }
   momos → source: "usda", indb_name: null

3. notebooks/02_train_yolo.ipynb — training notebook with cells:
   Cell 1: GPU check + imports
   Cell 2: YOLO training (data=data/indianfoodnet_yolo/data.yaml,
           epochs=60, imgsz=640, batch=8, patience=15, device=0,
           workers=2, amp=True, save_period=10)
   Cell 3: Copy best.pt → models/yolov8_indian_seg.pt
   Cell 4: Save class names → models/class_names.json
   Cell 5: Plot training loss curves inline

4. backend/scripts/train_yolo_seg.py — same logic as notebook but as .py
   for running from terminal: python backend\scripts\train_yolo_seg.py

5. tests/test_phase0.py — verify:
   - All required files exist (nutrition.db, food_label_map.json, INDB.xlsx, NIN_fct.xlsx)
   - nutrition.db has indb_recipes and ifct_ingredients tables with rows
   - food_label_map.json is valid JSON with 30 entries
   - models/ folder exists

Run: python tests\test_phase0.py
Stop after test passes with zero errors.
```

---

### PHASE 1 — Working Food Recognition MVP (Mini-Project 1)

**Goal:** Upload an image → get real Indian food label + real nutrition values displayed in UI.

**Stop condition:** `/api/health` returns `model_loaded: true` AND UI renders at `localhost:3000`.

**Prompt:**
```
Execute Phase 1 — Working Food Recognition mini-project.

Backend:
- backend/main.py:
  FastAPI with CORS for http://localhost:3000
  slowapi rate limiter: 5 req/min on /api/analyze-food
  ThreadPoolExecutor max_workers=2
  Load YOLO from os.getenv("YOLO_MODEL_PATH", "models/yolov8n-seg.pt") at startup
  Load data/nutrition.db and data/food_label_map.json at startup
  Warm-up pass on dummy black image after model loads
  GET /api/health → {"status":"ok","model_loaded":true,"phase":"1",...}

- backend/services/vision_service.py:
  _resize_image(image_bytes) → PIL Image max 1024px
  _run_yolo(image_bytes) → food_label, confidence, bounding_box,
    mask_base64 (null Phase 1), img_width, img_height
  If confidence < 0.3: return food_label="unknown", confidence=0.0
  All sync. Async wrappers use run_in_executor.

- backend/services/nutrition_service.py:
  get_macros(food_label, mass_g) → macros dict
  Lookup food_label_map.json → query indb_recipes → scale by mass_g/100
  Return food_not_found: true if no match (never crash)

- backend/api/analyze_food.py:
  POST /api/analyze-food — full API contract from section 5
  mass = serving_g from food_label_map.json (default in Phase 1)
  Input validation: reject >10MB (413), reject non-images (400)

Frontend:
- frontend/src/store/foodStore.ts:
  Zustand fields: imageFile, imageUrl, result, isLoading, error, userProfile

- frontend/src/components/ImageUpload.tsx:
  Drag-and-drop + click to upload. Shows image preview after selection.

- frontend/src/components/NutritionLabel.tsx:
  Displays: calories, protein_g, carbs_g, fat_g in a clean label card

- frontend/src/components/ResultsPanel.tsx:
  Shows: display_name, confidence badge, NutritionLabel,
  mass with "default serving" label

- frontend/src/app/layout.tsx:
  Minimal — html + body + children with Tailwind base class only

- frontend/src/app/page.tsx:
  Two-panel layout: left=image upload, right=ResultsPanel
  On upload: POST to /api/analyze-food → store in Zustand → render results
  Loading state: "Detecting... → Classifying... → Looking up nutrition..."

Write tests/test_phase1.py to verify API response shape.
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
- Update vision_service.py to return real bounding_box [x1,y1,x2,y2]
  from YOLOv8 result. Return img_width and img_height.

Frontend:
- components/ImageOverlay.tsx:
  Image inside <div style={{position:"relative"}}>
  Absolutely positioned <canvas> overlay on top
  CRITICAL: scaleX = canvas.offsetWidth / img_width
            scaleY = canvas.offsetHeight / img_height
  Draw 2px teal bounding box scaled to display size
  Food label text drawn above the box
- Replace plain <img> in page.tsx with <ImageOverlay>
- Show "YOLO Detected" badge when confidence > 0.3

Write tests/test_phase2.py.
Stop after bounding box renders at correct position on the food.
```

---

### PHASE 3 — Segmentation MVP (Mini-Project 3)

**Goal:** Highlight the exact food region with a mask overlay and toggle control.

**Stop condition:** Mask renders correctly over food region, toggle shows/hides it.

**Prompt:**
```
Execute Phase 3 — Segmentation mini-project.

Backend (vision_service.py):
- Extract mask: results[0].masks.data[0].cpu().numpy() → binary uint8 array
- Resize to img_width x img_height using cv2.resize
- Encode as PNG → base64 string → return as mask_base64
- If masks is None: return mask_base64: null (never crash)

Frontend (ImageOverlay.tsx):
- When mask_base64 present: decode and draw as semi-transparent
  teal overlay using drawImage with globalAlpha=0.35
- Add "Show Mask / Hide Mask" toggle button
- Bounding box must be drawn on top of mask layer

Write tests/test_phase3.py.
Stop after mask toggle works correctly on a real food image.
```

---

### PHASE 4 — Portion & Mass Estimation MVP (Mini-Project 4)

**Goal:** Replace fixed serving size with depth-estimated mass. Manual override recalculates macros live.

**Stop condition:** Override input updates displayed macros in real-time.

**Prompt:**
```
Execute Phase 4 — Portion and Mass Estimation mini-project.

Backend (backend/services/depth_service.py):
- Lazy-load model on first call (not startup — model is 300MB+):
  AutoModelForDepthEstimation.from_pretrained(
    "depth-anything/Depth-Anything-V2-Metric-Indoor-Small-hf")
  Warm up after first load with dummy image.

- _detect_plate_scale(img_np) → float | None:
  cv2.HoughCircles on grayscale blurred image → largest circle
  Return plate_diameter_px / PLATE_DIAMETER_CM (from .env, default 26)
  Return None if no circle found

- _estimate_mass(image_bytes, mask_base64, food_label) → dict:
  1. Get depth map (metres) from Depth Anything V2
  2. Resize mask to depth map size
  3. scale = _detect_plate_scale() or img_width/40.0
  4. ref_depth = median depth of non-food pixels in lower 2/3 of image
  5. h_p_cm = clip(ref_depth - depth[mask], 0) * 100
  6. pixel_area_cm2 = (1/scale)^2
  7. volume_cm3 = sum(h_p_cm * pixel_area_cm2)
  8. density = food_label_map[food_label]["density"]
  9. mass_g = clamp(volume_cm3 * density, 20, 800)
  10. band = mass_g * MAE_FRACTION (from .env, default 0.25)
  Return: estimated_mass_g, mass_confidence_band_g, mass_source, plate_anchor_used

- Add POST /api/override-mass endpoint

Frontend:
- components/MassDisplay.tsx:
  Shows "~185g ± 40g" with source badge (depth_plate_anchor / default_serving)
  Tooltip: "Accuracy improves with a visible plate rim"
  If plate_anchor_used=false: show warning "Plate not detected — estimate may vary"
- Manual mass override input → POST /api/override-mass → update macros in Zustand live
- ResultsPanel uses MassDisplay instead of plain mass text

Write tests/test_phase4.py.
Stop after override input correctly updates displayed macros.
```

---

### PHASE 5 — NutriGen Meal Planner MVP (Mini-Project 5)

**Goal:** Generate personalised Indian meal recommendations using LLM based on detected food + user profile.

**Stop condition:** Breakfast/Lunch/Dinner cards render with real LLM data.

**Prompt:**
```
Execute Phase 5 — NutriGen Meal Planner mini-project.

Backend (backend/services/llm_service.py):
- Detect provider at startup: GROQ_API_KEY → OPENAI_API_KEY → ollama
- Log active provider on startup

- System prompt (exact):
  "You are NutriGen, a certified Indian dietitian.
  Respond ONLY with valid JSON. No markdown. No explanation.
  Format: {breakfast:{name,description,calories,protein_g},
           lunch:{same}, dinner:{same}, tip:string}
  Suggest common Indian home-cooked dishes only."

- _extract_json(text): use re.search(r\'\{[\s\S]*\}\', text)
  to extract JSON even if LLM wraps in markdown
- Retry once if JSON parse fails
- Return hardcoded fallback plan if retry also fails:
  breakfast=poha, lunch=dal rice, dinner=roti sabzi

- Add POST /api/generate-meal-plan endpoint

Frontend:
- components/UserProfileForm.tsx:
  Slide-in drawer. Fields: age, weight_kg,
  goal (weight_loss/muscle_gain/maintenance), allergies
  Save to Zustand userProfile on submit

- "Generate Meal Plan" button — visible only after food analysis completes

- components/MealRecommendations.tsx:
  Three cards: Breakfast, Lunch, Dinner
  Each card: name, description, calories, protein_g
  Tip shown at bottom in muted text
  Loading skeleton while LLM responds (not blank — show shimmer)

Write tests/test_phase5.py.
Stop after meal cards render with real LLM data.
```

---

### PHASE 6 — Polish & Demo Readiness (Mini-Project 6)

**Goal:** Make the project demo-safe, mobile-ready, and report-ready with validation metrics.

**Stop condition:** All toasts work, layout is clean at 375px, git status is clean.

**Prompt:**
```
Execute Phase 6 — Polish and Demo Readiness mini-project.

Backend:
- Add X-Request-ID header logging on every request
- notebooks/03_validate_mass.ipynb:
  Cell 1: Load CSV (columns: image_path, actual_mass_g)
  Cell 2: Run full pipeline on each image
  Cell 3: Compute MAE, RMSE, MAPE — print results
  Cell 4: Plot predicted vs actual mass scatter chart inline
  Cell 5: Save results.csv

Frontend:
- Shimmer skeleton for ResultsPanel while /api/analyze-food loads
- Shimmer skeleton for MealRecommendations while LLM responds
- Error toasts for exactly these cases:
  "No food detected — try better lighting and a clear view of the dish"
  "Plate not detected — using default scale, mass may vary"
  "Food not found in nutrition database"
  "Meal plan generation failed — showing default plan"
- Single column layout at < 768px, meal cards stack vertically
- Test at 375px width (iPhone SE) — verify no overflow
- Remove ALL console.log statements
- Remove ALL debug/temp UI elements

Final checks:
- Run git status → verify .gitignore covers all large/secret files
- Run python tests\test_phase0.py through test_phase5.py — all must pass
- Start both servers and do a full end-to-end demo run

Stop after all toasts work, mobile layout is clean, and git status is clean.
```

---

## 11. YOLO Training Quick Reference

```
Dataset:    data/indianfoodnet_yolo/data.yaml  (from Roboflow IndianFoodNet)
Script:     python backend\scripts\train_yolo_seg.py
Notebook:   notebooks/02_train_yolo.ipynb
GPU:        RTX 3050 Laptop (4GB VRAM)
Settings:   batch=8, amp=True, workers=2, epochs=60
Time:       ~3-4 hours
Output:     models/yolov8_indian_seg.pt + models/class_names.json
After:      Update .env → YOLO_MODEL_PATH=models/yolov8_indian_seg.pt
Monitor:    nvidia-smi -l 3 (in separate terminal)
```

---

## 12. When Cascade Drifts Off-Plan

```
Stop. Re-read @AGENTS.md [Phase X section].
You added [wrong thing]. Revert [filename] to follow AGENTS.md exactly.
```
