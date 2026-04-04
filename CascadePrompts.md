# Phase-Wise Cascade Prompts
## Copy-paste these exactly — one phase at a time

---

## HOW TO USE

1. Open Windsurf → New Cascade chat
2. Always send the SESSION START prompt first (once per new chat)
3. Send the EXECUTE prompt for the current phase
4. Wait for Cascade to finish completely
5. Send the VALIDATE prompt — fix any issues before moving on
6. Only after validation passes → move to next phase

---

## SESSION START
> Send this as your VERY FIRST message in every new Cascade chat

```
Read AGENTS.md and .windsurf/rules/project.md before doing anything.

Confirm you have read both by answering:
1. What is the current phase?
2. What is the stop condition for this phase?
3. What is the ONE vision model being used?

Do not write any code until I give the phase execution prompt.
```

---

---

# PHASE 0 — Data Foundation

---

## PHASE 0 — EXECUTE

```
Execute Phase 0 — Data Foundation mini-project from AGENTS.md.

Create the following files in this exact order:

STEP 1 — backend/scripts/merge_db.py
- Read data/INDB.xlsx (sheet 0) with pandas. Print ALL column names first before doing anything else.
- Read data/NIN_fct.xlsx the same way. Print its column names.
- Create data/nutrition.db with SQLite (check_same_thread=False) with two tables:
    indb_recipes:      id INTEGER PRIMARY KEY, name TEXT, calories REAL, protein_g REAL, carbs_g REAL, fat_g REAL
    ifct_ingredients:  id INTEGER PRIMARY KEY, name TEXT, calories REAL, protein_g REAL, carbs_g REAL, fat_g REAL
- All values stored as per-100g floats. Normalize column names before inserting.
- Print row counts for both tables after inserting.

STEP 2 — data/food_label_map.json
Create this file with exactly 30 entries:
biryani, butter_chicken, chapati, chole_bhature, dal_makhani, dal_tadka,
dosa, gulab_jamun, idli, jalebi, kadai_paneer, kathi_roll, kheer, kulfi,
masala_dosa, medu_vada, naan, pakoda, palak_paneer, paneer_butter_masala,
pav_bhaji, poha, puri, rasgulla, ras_malai, samosa, shahi_paneer,
uttapam, vada_pav, momos
Each entry must have:
{ "indb_name": "...", "source": "indb", "density": <float>, "serving_g": <int> }
momos: source="usda", indb_name=null

STEP 3 — notebooks/02_train_yolo.ipynb
Create a Jupyter notebook with 5 cells:
Cell 1: import torch, print cuda available, print GPU name
Cell 2: pip install ultralytics, train YOLOv8n-seg:
  data=data/indianfoodnet_yolo/data.yaml, epochs=60, imgsz=640,
  batch=8, patience=15, device=0, workers=2, amp=True, save_period=10
Cell 3: copy runs best.pt → models/yolov8_indian_seg.pt
Cell 4: read data.yaml, save class names → models/class_names.json, print them
Cell 5: plot training loss curve using results.csv

STEP 4 — backend/scripts/train_yolo_seg.py
Same training logic as notebook but as a standalone .py script.
Auto-detects VRAM and sets batch size. Uses amp=True always.
Saves best.pt to models/yolov8_indian_seg.pt automatically.

STEP 5 — .gitignore
Create/update .gitignore with all required entries from AGENTS.md section 13.

STEP 6 — tests/test_phase0.py
Write to tests/ folder. Verify:
- data/food_label_map.json exists and has 30 entries
- data/nutrition.db exists, has indb_recipes and ifct_ingredients tables, both have rows
- data/INDB.xlsx exists
- data/NIN_fct.xlsx exists
- models/ folder exists
Print PASS or FAIL with details for each check.

Do NOT use python -c commands. Write files and run them.
Stop after creating all files. Do NOT run training yet.
```

---

## PHASE 0 — VALIDATE

```
Run Phase 0 validation.

STEP 1 — Run merge_db.py to build the database:
python backend\scripts\merge_db.py

STEP 2 — Run the test file:
python tests\test_phase0.py

STEP 3 — Run this verification script (write to tests/verify_phase0_quick.py first):
- Open data/nutrition.db
- Print the first 3 rows of indb_recipes
- Print the first 3 rows of ifct_ingredients
- Print all 30 keys from food_label_map.json

Expected result: All checks PASS, rows visible in both tables.
Fix anything that shows FAIL before I approve Phase 1.
```

---

---

# PHASE 1 — Working Food Recognition MVP

---

## PHASE 1 — EXECUTE

```
Execute Phase 1 — Working Food Recognition mini-project from AGENTS.md.

BACKEND — create in this order:

1. backend/services/nutrition_service.py
   - get_macros(food_label, mass_g) → dict with calories, protein_g, carbs_g, fat_g, nutrition_source, food_not_found
   - Load food_label_map.json → query indb_recipes in nutrition.db → scale macros by mass_g/100
   - If not found: return food_not_found=True with zero macros (never raise exception)
   - SQLite: check_same_thread=False

2. backend/services/vision_service.py
   - _resize_image(image_bytes) → PIL Image, max 1024px on longest side
   - _run_yolo(image_bytes) → dict:
       food_label, display_name, confidence, bounding_box [x1,y1,x2,y2],
       img_width, img_height, mask_base64=None (Phase 1)
   - Load YOLO from os.getenv("YOLO_MODEL_PATH", "models/yolov8n-seg.pt")
   - If confidence < 0.3: return food_label="unknown", confidence=0.0, bounding_box=None
   - All sync functions. Async wrappers use loop.run_in_executor.

3. backend/api/analyze_food.py
   - POST /api/analyze-food
   - Input: multipart/form-data image file
   - Validate: reject >10MB (413), reject non-image MIME types (400)
   - Call vision_service → nutrition_service
   - estimated_mass_g = serving_g from food_label_map (default in Phase 1)
   - Return full API contract from AGENTS.md section 5

4. backend/main.py
   - FastAPI app with CORS origins=["http://localhost:3000"]
   - slowapi Limiter: 5 req/min on /api/analyze-food
   - ThreadPoolExecutor(max_workers=2) stored in app.state
   - Load YOLO model at startup using vision_service
   - Warm-up pass: run inference on 10x10 black numpy array at startup
   - Load nutrition.db and food_label_map.json at startup
   - Include router from analyze_food.py
   - GET /api/health → {"status":"ok","model_loaded":true,"phase":"1","description":"AI Food Recognition - Phase 1 MVP"}

5. requirements.txt — all dependencies needed to run the backend

FRONTEND — create in this order:

1. frontend/src/store/foodStore.ts
   Zustand store with fields:
   imageFile: File | null
   imageUrl: string | null
   result: AnalyzeFoodResponse | null
   isLoading: boolean
   error: string | null
   userProfile: UserProfile | null
   Actions: setImage, setResult, setLoading, setError, setUserProfile, reset

2. frontend/src/components/NutritionLabel.tsx
   Props: macros object from API response
   Display: Calories (large), Protein / Carbs / Fat in a clean grid
   Show "per estimated serving" subtitle

3. frontend/src/components/ResultsPanel.tsx
   Props: result from Zustand store
   Display: display_name (large), confidence % badge (teal if >0.7, yellow if >0.3, red otherwise),
   "Default serving: Xg" mass label, NutritionLabel component,
   nutrition_source badge (INDB or IFCT)

4. frontend/src/components/ImageUpload.tsx
   Drag-and-drop zone + click to browse
   Shows image preview after selection using URL.createObjectURL
   On file select: update Zustand imageFile and imageUrl
   On upload button click: POST multipart/form-data to http://localhost:8000/api/analyze-food
   Shows loading steps in sequence: "Detecting..." → "Classifying..." → "Looking up nutrition..."

5. frontend/src/app/layout.tsx
   Minimal: html lang="en" + body with Tailwind className="min-h-screen bg-gray-950 text-white" + {children}

6. frontend/src/app/page.tsx
   Two-panel layout (side by side on desktop):
   Left panel: ImageUpload component
   Right panel: ResultsPanel (shown only when result exists in Zustand)
   Page title: "NutriVision — AI Food Recognition"

7. Install dependencies: npm install zustand in frontend/

Write tests/test_phase1.py:
- Send a real image to POST /api/analyze-food
- Verify response has all required fields from AGENTS.md API contract
- Print PASS/FAIL for each field

Stop after:
1. cd backend; uvicorn main:app --reload → /api/health returns model_loaded: true
2. cd frontend; npm run dev → UI renders at localhost:3000 with upload working
```

---

## PHASE 1 — VALIDATE

```
Validate Phase 1 is fully working.

STEP 1 — Backend health check (run in new terminal):
Invoke-RestMethod -Uri http://localhost:8000/api/health -Method GET
Expected: model_loaded=true

STEP 2 — Run API test (make sure backend is running first):
python tests\test_phase1.py

STEP 3 — Manual UI test:
- Open http://localhost:3000
- Upload any food image (use a photo from your phone or download one)
- Verify: food name appears, confidence badge shows, calories/protein/carbs/fat display
- Verify: no console errors in browser DevTools (F12)

STEP 4 — Edge case test (write to tests/test_phase1_edge.py):
- Send a non-image file → should return 400
- Send an empty request → should return 422
- Send a valid image of a random object (not food) → should return food_label="unknown"

Fix any failures before approving Phase 2.
```

---

---

# PHASE 2 — Detection Overlay MVP

---

## PHASE 2 — EXECUTE

```
Execute Phase 2 — Detection Overlay mini-project from AGENTS.md.

BACKEND changes only in vision_service.py:
- Return real bounding_box [x1,y1,x2,y2] from YOLOv8 detection result
  Use: results[0].boxes.xyxy[0].cpu().numpy().tolist()
- Return real img_width and img_height of the resized image
- If no detection: bounding_box=None, img_width and img_height still returned

FRONTEND — create/update:

1. frontend/src/components/ImageOverlay.tsx (NEW component)
   Props: imageUrl, boundingBox [x1,y1,x2,y2] | null, imgWidth, imgHeight, foodLabel, confidence
   Structure:
   - Outer <div> with position:relative, inline-block
   - <img> fills the div, ref=imgRef
   - <canvas> absolutely positioned on top, same size as rendered image
   - useEffect: when props change → clear canvas → draw bounding box
   CRITICAL scaling (MUST implement exactly):
     const scaleX = canvas.offsetWidth / imgWidth
     const scaleY = canvas.offsetHeight / imgHeight
     const x1 = boundingBox[0] * scaleX
     const y1 = boundingBox[1] * scaleY
     const x2 = boundingBox[2] * scaleX
     const y2 = boundingBox[3] * scaleY
   Draw: 2px teal (#14b8a6) rectangle
   Draw: food label text above the box in white on teal background
   Show "YOLO Detected" green badge below image if confidence > 0.3
   Show "No food detected" grey badge if confidence < 0.3

2. Update frontend/src/app/page.tsx:
   Replace plain <img> with <ImageOverlay> component
   Pass result fields from Zustand store as props

Write tests/test_phase2.py:
- Call API with a real food image
- Verify bounding_box is a list of 4 numbers
- Verify img_width and img_height are non-zero integers

Stop after bounding box renders at correct position on the uploaded food image.
```

---

## PHASE 2 — VALIDATE

```
Validate Phase 2 bounding box overlay.

STEP 1 — API test:
python tests\test_phase2.py

STEP 2 — Visual test:
- Upload a food image at localhost:3000
- Verify: green box appears on the food (not on the background)
- Verify: food label text shows above the box
- Resize the browser window — verify box stays on the food (scaling works)

STEP 3 — Write tests/test_phase2_scaling.py:
- Load the same image at two different canvas sizes
- Verify scaled coordinates land inside the image dimensions
- Print PASS/FAIL

Fix all scaling issues before approving Phase 3.
```

---

---

# PHASE 3 — Segmentation MVP

---

## PHASE 3 — EXECUTE

```
Execute Phase 3 — Segmentation mini-project from AGENTS.md.

BACKEND changes in vision_service.py:
- Extract segmentation mask from YOLOv8-seg results:
  raw_mask = results[0].masks.data[0].cpu().numpy()  → float32 binary mask
  Resize to (img_height, img_width) using cv2.resize with INTER_NEAREST
  Convert to uint8: (raw_mask * 255).astype(np.uint8)
  Encode to PNG bytes using cv2.imencode(".png", mask_array)
  Encode to base64 string: base64.b64encode(png_bytes).decode("utf-8")
  Return as mask_base64 in API response
- If results[0].masks is None: return mask_base64=None (never crash, never raise)

FRONTEND changes in ImageOverlay.tsx:
- Add prop: maskBase64: string | null
- Add state: showMask: boolean (default true)
- When maskBase64 present:
  Decode base64 → create Image object → draw on canvas BEFORE bounding box
  Use ctx.globalAlpha = 0.35 for the mask layer
  Use teal color overlay (#14b8a6) — draw mask then restore globalAlpha to 1.0
  Draw bounding box ON TOP of mask (after mask drawn)
- Add toggle button below the image: "Hide Mask" / "Show Mask"
  Clicking toggles showMask state → re-draws canvas

Update page.tsx to pass maskBase64 from Zustand result to ImageOverlay.

Write tests/test_phase3.py:
- Call API with food image
- Verify mask_base64 is a non-empty string
- Decode base64 → verify it is valid PNG bytes

Stop after mask renders over food and toggle button works.
```

---

## PHASE 3 — VALIDATE

```
Validate Phase 3 segmentation mask.

STEP 1:
python tests\test_phase3.py

STEP 2 — Visual test:
- Upload a food image
- Verify: teal semi-transparent mask covers the food region
- Verify: bounding box is visible on top of the mask
- Click "Hide Mask" → mask disappears, box remains
- Click "Show Mask" → mask reappears

STEP 3 — Edge case:
- Upload an image with no food (blank wall, etc.)
- Verify: app does NOT crash. Shows "No food detected" badge.
- mask_base64 should be null, no canvas errors in DevTools (F12)

Fix any crashes or visual glitches before approving Phase 4.
```

---

---

# PHASE 4 — Portion & Mass Estimation MVP

---

## PHASE 4 — EXECUTE

```
Execute Phase 4 — Portion and Mass Estimation mini-project from AGENTS.md.

BACKEND — create backend/services/depth_service.py:

Imports needed: torch, transformers (AutoModelForDepthEstimation, AutoImageProcessor),
                numpy, cv2, base64, PIL, os, re

CLASS DepthService:
  __init__: model=None, processor=None (lazy load — do NOT load at import time)

  _load_model():
    Load "depth-anything/Depth-Anything-V2-Metric-Indoor-Small-hf" from HuggingFace
    Set to eval mode. Run warm-up on dummy image. Log "Depth model loaded."

  _detect_plate_scale(img_np) → float | None:
    Convert to grayscale → GaussianBlur(21,21)
    cv2.HoughCircles(method=HOUGH_GRADIENT, dp=1.2, minDist=50,
                     param1=50, param2=30, minRadius=30, maxRadius=300)
    If circles found: return largest circle diameter / float(os.getenv("PLATE_DIAMETER_CM", 26))
    Return None if no circles

  estimate_mass(image_bytes, mask_base64, food_label) → dict:
    1. Lazy-load model on first call
    2. Decode image_bytes → PIL RGB
    3. Run depth inference → depth_map numpy array (metres)
    4. Resize depth_map to image size
    5. Decode mask_base64 → binary numpy mask, resize to depth_map size
    6. scale = _detect_plate_scale(img_np) OR (img_width / 40.0) as fallback
    7. plate_anchor_used = (scale from plate detection, not fallback)
    8. ref_depth = np.median(depth_map[lower 2/3 of image where mask==0])
    9. h_p_cm = np.clip(ref_depth - depth_map[mask > 0], 0, None) * 100
    10. pixel_area_cm2 = (1.0 / scale) ** 2
    11. volume_cm3 = float(np.sum(h_p_cm) * pixel_area_cm2)
    12. density = food_label_map.get(food_label, {}).get("density", 0.9)
    13. mass_g = float(np.clip(volume_cm3 * density, 20, 800))
    14. mae_fraction = float(os.getenv("MAE_FRACTION", 0.25))
    15. band = round(mass_g * mae_fraction)
    Return: {estimated_mass_g, mass_confidence_band_g, mass_source="depth_plate_anchor", plate_anchor_used}

Update backend/api/analyze_food.py:
- After getting mask from vision_service → call depth_service.estimate_mass
- Use returned estimated_mass_g for nutrition lookup (replaces serving_g default)
- Add all depth fields to API response

Add backend/api/override_mass.py:
- POST /api/override-mass
- Input: { food_label: str, mass_g: float }
- Returns: recalculated macros for given food_label at given mass_g

Register override_mass router in main.py

FRONTEND:

1. frontend/src/components/MassDisplay.tsx (NEW)
   Props: estimatedMassG, massConfidenceBandG, massSource, plateAnchorUsed
   Display: "~185g ± 40g" in large text
   Source badge: "Depth + Plate Anchor" (teal) or "Default Serving" (grey)
   If plateAnchorUsed=false: yellow warning banner "Plate not detected — estimate may vary"
   Tooltip on hover: "Accuracy improves with a visible plate rim in frame"

2. frontend/src/components/ResultsPanel.tsx — update:
   Replace old mass label with <MassDisplay> component
   Add manual override input below MassDisplay:
     Number input field + "Recalculate" button
     On click: POST /api/override-mass → update macros in Zustand store
     Show "Manually adjusted" badge when override is active

Write tests/test_phase4.py:
- Call /api/analyze-food with a food image
- Verify estimated_mass_g is between 20 and 800
- Verify mass_confidence_band_g is non-zero
- Call /api/override-mass with food_label and mass_g=200
- Verify returned macros are correctly scaled

Stop after override input updates displayed macros in real-time.
```

---

## PHASE 4 — VALIDATE

```
Validate Phase 4 mass estimation.

STEP 1:
python tests\test_phase4.py

STEP 2 — Visual test:
- Upload a food photo where a plate or bowl is visible
- Verify: mass shows as "~Xg ± Yg" (not "default serving")
- Verify: "Depth + Plate Anchor" badge appears in teal
- Type a different mass in the override field → click Recalculate
- Verify: calories and macros update immediately to reflect new mass

STEP 3 — No-plate test:
- Upload a food image with NO visible plate
- Verify: yellow warning "Plate not detected" appears
- Verify: mass is still shown (fallback scale used, not crashed)

STEP 4 — Depth model load test (write tests/test_phase4_depth.py):
- Time the first call to /api/analyze-food (lazy load)
- Time the second call (model already loaded)
- Verify second call is significantly faster
- Print both times

Fix any crashes before approving Phase 5.
```

---

---

# PHASE 5 — NutriGen Meal Planner MVP

---

## PHASE 5 — EXECUTE

```
Execute Phase 5 — NutriGen Meal Planner mini-project from AGENTS.md.

BACKEND — create backend/services/llm_service.py:

CLASS LLMService:
  __init__:
    Detect provider on init:
      if GROQ_API_KEY in env → use groq (log "LLM provider: Groq")
      elif OPENAI_API_KEY in env → use openai (log "LLM provider: OpenAI")
      else → use ollama at OLLAMA_HOST (log "LLM provider: Ollama")

  SYSTEM_PROMPT = """You are NutriGen, a certified Indian dietitian.
Respond ONLY with valid JSON. No markdown. No explanation. No preamble.
Exact format required:
{
  "breakfast": {"name": "", "description": "", "calories": 0, "protein_g": 0},
  "lunch":     {"name": "", "description": "", "calories": 0, "protein_g": 0},
  "dinner":    {"name": "", "description": "", "calories": 0, "protein_g": 0},
  "tip": ""
}
Suggest common Indian home-cooked dishes only. No exotic or restaurant dishes."""

  _extract_json(text) → dict | None:
    Use re.search(r'\{[\s\S]*\}', text) to find JSON block
    Parse and return dict. Return None if parse fails.

  FALLBACK_PLAN = {
    "breakfast": {"name": "Poha", "description": "Light flattened rice with vegetables", "calories": 250, "protein_g": 5},
    "lunch":     {"name": "Dal Rice", "description": "Yellow dal with steamed rice", "calories": 450, "protein_g": 18},
    "dinner":    {"name": "Roti Sabzi", "description": "Whole wheat roti with seasonal vegetable curry", "calories": 380, "protein_g": 12},
    "tip": "Stay hydrated and eat your meals at consistent times daily."
  }

  generate_meal_plan(food_label, mass_g, macros, profile) → dict:
    Build user prompt with food eaten + macros + profile constraints
    Call LLM with system_prompt + user_prompt
    Try _extract_json on response
    If fails: retry once with stricter prompt
    If retry fails: return FALLBACK_PLAN
    Return parsed plan

Create backend/api/generate_meal_plan.py:
- POST /api/generate-meal-plan
- Input: food_label, mass_g, macros dict, profile dict
- Call llm_service.generate_meal_plan
- Return plan JSON directly

Register in main.py

FRONTEND:

1. frontend/src/components/UserProfileForm.tsx (NEW)
   Slide-in drawer (fixed right side, toggled by button)
   Fields:
     Age: number input (min 10, max 100)
     Weight (kg): number input (min 20, max 200)
     Goal: select → weight_loss / muscle_gain / maintenance
     Allergies: text input (placeholder: "e.g. dairy, nuts")
   Save button: updates Zustand userProfile, closes drawer
   Show saved profile summary if already set

2. frontend/src/components/MealRecommendations.tsx (NEW)
   Props: mealPlan object | null, isLoading boolean
   Loading state: show 3 shimmer skeleton cards
   Loaded state: three cards side by side (stack on mobile):
     Each card: meal type header (Breakfast/Lunch/Dinner),
     dish name (bold), description (muted), calories chip, protein chip
   Bottom section: "NutriGen Tip" in italic muted text
   Small "Powered by NutriGen AI" footer text

3. Update frontend/src/app/page.tsx:
   Add "Profile Settings" button (top right) → toggles UserProfileForm drawer
   Add "Generate Meal Plan" button below ResultsPanel
     Only visible when result exists in Zustand
     Disabled if userProfile is not set (show tooltip "Set your profile first")
   On click: POST /api/generate-meal-plan → show MealRecommendations below results
   Add mealPlan and isMealLoading fields to Zustand store

Write tests/test_phase5.py:
- POST /api/generate-meal-plan with sample food + macros + profile
- Verify response has breakfast, lunch, dinner, tip keys
- Verify each meal has name, description, calories, protein_g

Stop after meal plan cards render with real LLM data.
```

---

## PHASE 5 — VALIDATE

```
Validate Phase 5 meal planner.

STEP 1:
python tests\test_phase5.py

STEP 2 — Visual test:
- Open Profile Settings → fill in age, weight, goal, allergies → Save
- Upload a food image → wait for analysis
- Click "Generate Meal Plan"
- Verify: 3 cards appear with real dish names (not fallback poha/dal/roti)
- Verify: tip text appears at bottom

STEP 3 — Fallback test (write tests/test_phase5_fallback.py):
- Temporarily set GROQ_API_KEY to an invalid value in .env
- Restart backend
- Call /api/generate-meal-plan
- Verify: fallback plan returns (poha, dal rice, roti sabzi) — no crash
- Restore real GROQ_API_KEY

STEP 4 — Profile disabled test:
- Clear userProfile from Zustand (refresh page)
- Verify: "Generate Meal Plan" button is disabled or shows tooltip

Fix all issues before approving Phase 6.
```

---

---

# PHASE 6 — Polish & Demo Readiness

---

## PHASE 6 — EXECUTE

```
Execute Phase 6 — Polish and Demo Readiness mini-project from AGENTS.md.

BACKEND:
1. Add X-Request-ID middleware in main.py:
   Generate UUID for each request, add as response header X-Request-ID
   Log: f"[{request_id}] {method} {path} → {status_code}"

2. notebooks/03_validate_mass.ipynb — validation notebook:
   Cell 1: imports, load food_label_map.json
   Cell 2: read validation CSV (columns: image_path, actual_mass_g, food_label)
   Cell 3: for each row → call depth_service.estimate_mass → collect predicted mass
   Cell 4: compute MAE, RMSE, MAPE → print results table
   Cell 5: scatter plot (predicted vs actual) using matplotlib inline
   Cell 6: save results to data/validation_results.csv

FRONTEND:

1. Loading skeletons:
   ResultsPanel: show shimmer skeleton while isLoading=true in Zustand
   MealRecommendations: show 3 shimmer skeleton cards while isMealLoading=true
   Skeleton style: animate-pulse bg-gray-700 rounded blocks

2. Error toast system:
   Install: npm install react-hot-toast in frontend/
   Add <Toaster> to layout.tsx
   Show toasts for exactly these cases:
     food_not_found=true → "Food not found in nutrition database"
     confidence < 0.3 → "No food detected — try better lighting and a clear view of the dish"
     plateAnchorUsed=false → "Plate not detected — using default scale, mass may vary"
     /api/generate-meal-plan uses fallback → "Meal plan generation failed — showing default plan"
     network error → "Connection failed — make sure the backend is running"

3. Mobile layout:
   page.tsx: flex-col on mobile (< 768px), flex-row on desktop
   MealRecommendations cards: grid-cols-1 on mobile, grid-cols-3 on desktop
   All text readable at 375px width — no horizontal overflow
   Add <meta name="viewport" content="width=device-width, initial-scale=1"> in layout.tsx if missing

4. Final cleanup:
   Remove ALL console.log statements from all .tsx files
   Remove ALL debug inputs, hardcoded test values, TODO comments
   Verify all Tailwind classes are valid (no typos)

5. Update .gitignore — final check, must include all items from AGENTS.md

Write tests/test_phase6.py:
- Verify X-Request-ID header present in all API responses
- Verify /api/analyze-food returns 413 for >10MB file
- Verify /api/analyze-food returns 400 for non-image file
- All previous tests still pass

Stop after all toasts work, layout is clean at 375px, git status is clean.
```

---

## PHASE 6 — VALIDATE

```
Validate Phase 6 — Final demo readiness check.

STEP 1 — Run all tests:
python tests\test_phase0.py
python tests\test_phase1.py
python tests\test_phase2.py
python tests\test_phase3.py
python tests\test_phase4.py
python tests\test_phase5.py
python tests\test_phase6.py
All must print PASS. Fix any FAIL before proceeding.

STEP 2 — Visual demo run:
1. Start backend: cd backend; uvicorn main:app --reload
2. Start frontend: cd frontend; npm run dev
3. Open http://localhost:3000 on mobile view in Chrome DevTools (375px width)
4. Upload a food image → verify full flow works on mobile:
   - Upload visible
   - Bounding box draws correctly
   - Nutrition shows
   - Skeleton shows during load
5. Trigger each error toast manually and verify they appear

STEP 3 — Git status check:
git status
Verify NOTHING sensitive is staged or tracked:
- No .env
- No .venv/
- No models/*.pt
- No data/*.db or data/*.xlsx

STEP 4 — Final report:
Create a file docs/phase6_metrics.md with:
- MAE, RMSE, MAPE from validation notebook
- Phase completion summary
- Known limitations

Project is demo-ready after all steps pass.
```

---

---

## RECOVERY PROMPT
> Use this if Cascade goes off-plan at any point

```
Stop immediately. You have deviated from AGENTS.md.

You did: [describe what went wrong]
You should have done: [describe correct behavior from AGENTS.md]

Re-read @AGENTS.md Phase [X] now.
Revert [filename] to match AGENTS.md exactly.
Do not add anything not specified in AGENTS.md.
```

---

## QUICK REFERENCE

| Phase | Execute goal | Validate command |
|---|---|---|
| 0 | Build DB + label map + training script | `python tests\test_phase0.py` |
| 1 | Upload → real food name + nutrition in UI | `python tests\test_phase1.py` |
| 2 | Bounding box drawn over food | `python tests\test_phase2.py` |
| 3 | Mask overlay + toggle | `python tests\test_phase3.py` |
| 4 | Mass estimation + override | `python tests\test_phase4.py` |
| 5 | Meal plan cards from LLM | `python tests\test_phase5.py` |
| 6 | Toasts + mobile + clean git | `python tests\test_phase6.py` |
