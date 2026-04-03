# AI Food Recognition with Nutrition-Aware Recommendations
**Final MVP Plan — College Project Version**

## 1. Project Goal

Build a full-stack web MVP that can:
- recognize an Indian food item from an uploaded image,
- estimate its portion and approximate mass,
- fetch nutrition values from a compatible nutrition database,
- and generate a simple personalized meal recommendation.

The project is designed so that **every phase is a working mini-project**, not a half-finished pipeline.

---

## 2. Final Design Choice

### Why a single model is better

This MVP will use **one YOLOv8-seg model** as the main vision model instead of separate classifier, detector, and segmentation models.

### Purpose of each function inside one YOLOv8-seg pipeline

A single YOLOv8-seg model gives:
- **classification** → food label,
- **detection** → bounding box,
- **segmentation** → food mask.

This is better for the MVP because:
- there is only **one model to train and load**,
- there is only **one inference pass**,
- there is **no label conflict** between different models,
- and debugging becomes much easier.

### Final architecture

```text
Image Upload
   ↓
YOLOv8-seg (food label + bbox + mask)
   ↓
Nutrition Lookup (INDB / IFCT fallback)
   ↓
Mass Estimation (mask + metric depth + plate reference)
   ↓
Meal Plan Generator (LLM)
```

---

## 3. Data Compatibility Rule

This is the most important rule in the whole project:

- **Image datasets contain prepared dishes** like biryani, dal makhani, dosa, samosa.
- **IFCT 2017 mainly represents ingredients/raw foods**, so it should not be the primary nutrition source for prepared dish images [web:13].
- **INDB includes standard Indian recipes and prepared foods**, and the GitHub repository exposes a directly readable `INDB.xlsx` file, which makes it the correct primary source for dish-level nutrition mapping [web:48][web:52].

### Final nutrition rule

- Use **INDB as the primary nutrition source** for detected dish labels [web:48][web:52].
- Use **IFCT/NIN ingredient tables only as fallback** for raw or simple items like rice, egg, banana, or similar ingredient-level foods [web:13].
- Use a **manual fallback entry** only for classes that do not exist in INDB.

---

## 4. Final Dataset Choice

### Vision dataset

Use **IndianFoodNet on Roboflow** as the primary training dataset for YOLO because it is already available as an Indian food object-detection dataset and is suitable for export in YOLO format [web:51].

### Nutrition datasets

Use:
- **INDB.xlsx** as the primary recipe-level nutrition source [web:52],
- **NIN / IFCT-based sheet** as fallback ingredient nutrition source [web:13][web:48].

### Why this combination works

This pair is compatible because:
- the image side is dish-oriented,
- and the nutrition side is also recipe-oriented through INDB [web:48][web:52].

---

## 5. Final Tech Stack

## Frontend
- Next.js
- React
- Tailwind CSS

## Backend
- FastAPI
- Python 3.10+

## Vision
- YOLOv8-seg for food recognition, detection, and segmentation
- Metric monocular depth model for portion estimation

## Database
- SQLite

## Recommendation
- Groq API as primary LLM
- OpenAI or Ollama as fallback

---

## 6. Core Project Principle

### Every phase must be a complete mini-project

Each phase must:
1. have a working backend,
2. be connected to the frontend,
3. show visible output in the UI,
4. and be demo-ready on its own.

Do **not** move to the next phase unless the current one is fully working.

---

## 7. Project Phases

## Phase 0 — Data Foundation

### Goal
Prepare all data and mappings before app development begins.

### Tasks
- Download the Indian food detection dataset from Roboflow and export it in YOLO format [web:51].
- Download `INDB.xlsx` from the Indian Nutrient Databank repository [web:52].
- Prepare IFCT/NIN fallback data from the available nutrient tables [web:13][web:48].
- Create `food_label_map.json` that maps each image label to:
  - display name,
  - INDB recipe name,
  - fallback source,
  - density value,
  - default serving size.

### Output
A verified data layer with:
- `nutrition.db`
- `food_label_map.json`
- cleaned image dataset
- train/val split

### Mini-project result
At the end of Phase 0, the project has **real Indian image classes and real nutrition mappings** ready for development.

---

## Phase 1 — Working Food Recognition MVP

### Goal
Upload an image and get a **real Indian food label** plus **real nutrition values**.

### Backend tasks
- Initialize FastAPI.
- Add `/api/health`.
- Add `/api/analyze-food`.
- Load the trained YOLOv8-seg model.
- Run inference on uploaded image.
- Return:
  - `food_label`
  - `display_name`
  - `confidence`
  - `estimated_mass_g` using default serving size
  - `macros`
  - `nutrition_source`

### Frontend tasks
- Build drag-and-drop upload component.
- Show uploaded image.
- Show result panel with:
  - food name,
  - confidence,
  - calories,
  - protein,
  - carbs,
  - fat.

### Mini-project result
A user uploads a food image and sees a real predicted Indian dish and real nutrition data.

---

## Phase 2 — Detection Overlay MVP

### Goal
Show the detected food location visually.

### Backend tasks
- Return bounding box from YOLOv8-seg.
- Return original image width and height.

### Frontend tasks
- Add canvas overlay.
- Draw bounding box on the image.
- Correctly scale box coordinates from original image size to displayed image size.

### Mini-project result
The app now works as a food-recognition tool with a visible detection box.

---

## Phase 3 — Segmentation MVP

### Goal
Show the exact food region instead of only a box.

### Backend tasks
- Return segmentation mask from YOLOv8-seg.
- Encode mask as base64 PNG.

### Frontend tasks
- Overlay the semi-transparent mask on top of the image.
- Add toggle: show/hide mask.

### Mini-project result
The app now works as a visual food-analysis tool with dish highlighting.

---

## Phase 4 — Portion and Mass Estimation MVP

### Goal
Replace fixed serving size with estimated mass.

### Backend tasks
- Add metric depth inference.
- Use the segmentation mask to isolate only the food region.
- Use a visible plate/bowl reference to estimate scale.
- Compute approximate food volume.
- Convert volume to mass using density from `food_label_map.json`.
- Recalculate macros based on estimated mass.
- Add `/api/override-mass` for manual correction.

### Frontend tasks
- Show estimated mass like:
  - `Estimated mass: 185g ± 40g`
- Add manual mass override field.
- Recalculate displayed macros immediately after override.

### Mini-project result
The app now behaves like a portion-aware nutrition estimator.

---

## Phase 5 — Meal Recommendation MVP

### Goal
Generate a simple personalized diet suggestion based on detected food and user profile.

### Backend tasks
- Add `/api/generate-meal-plan`.
- Use:
  - detected food,
  - estimated mass,
  - calculated macros,
  - user profile.
- Ask the LLM for strict JSON output only.

### Frontend tasks
- Add profile form:
  - age
  - weight
  - goal
  - allergies
- Show breakfast, lunch, dinner recommendations.

### Mini-project result
The app now becomes a nutrition assistant, not just a recognizer.

---

## Phase 6 — Polish and Validation

### Goal
Make the project demo-safe and report-ready.

### Backend tasks
- Run validation on a small manually weighed set.
- Compute MAE for mass estimation.
- Add file validation and better error handling.
- Add logs and request tracing.

### Frontend tasks
- Add loading skeletons.
- Add error toasts.
- Improve mobile responsiveness.
- Remove debug UI.

### Mini-project result
A final-year project that is clean enough for viva/demo and strong enough for documentation.

---

## 8. Final API Design

## `GET /api/health`
Returns:
```json
{
  "status": "ok"
}
```

## `POST /api/analyze-food`
Returns:
```json
{
  "food_label": "dal_makhani",
  "display_name": "Dal Makhani",
  "confidence": 0.91,
  "bounding_box":,[1][2]
  "mask_base64": "....",
  "estimated_mass_g": 180,
  "mass_confidence_band_g": 40,
  "mass_source": "depth_plate_anchor",
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

## `POST /api/override-mass`
Input:
```json
{
  "food_label": "dal_makhani",
  "mass_g": 220
}
```

## `POST /api/generate-meal-plan`
Input:
```json
{
  "food_label": "dal_makhani",
  "mass_g": 180,
  "macros": {
    "calories": 274,
    "protein_g": 12.2,
    "carbs_g": 22.1,
    "fat_g": 14.0
  },
  "profile": {
    "age": 22,
    "weight_kg": 72,
    "goal": "muscle_gain",
    "allergies": "none"
  }
}
```

---

## 9. Final Directory Structure

```text
project-root/
├── frontend/
│   ├── components/
│   │   ├── ImageUpload.tsx
│   │   ├── ImageOverlay.tsx
│   │   ├── ResultsPanel.tsx
│   │   ├── NutritionLabel.tsx
│   │   ├── MassDisplay.tsx
│   │   ├── MealRecommendations.tsx
│   │   └── UserProfileForm.tsx
│   ├── store/
│   │   └── foodStore.ts
│   └── pages/
│       └── index.tsx
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
│   └── IFCT_fallback.xlsx
├── models/
│   └── yolov8_indian_seg.pt
├── .env
└── requirements.txt
```

---

## 10. Final `.env`

```env
GROQ_API_KEY=
OPENAI_API_KEY=
OLLAMA_HOST=http://localhost:11434

PLATE_DIAMETER_CM=26
MAE_FRACTION=0.25
RATE_LIMIT_PER_MINUTE=5
DEPTH_ENABLED=true
```

---

## 11. Final `requirements.txt`

```txt
fastapi
uvicorn[standard]
slowapi
python-multipart
torch
ultralytics
transformers
opencv-python-headless
pillow
numpy
pandas
openpyxl
sqlalchemy
aiosqlite
python-dotenv
httpx
groq
openai
```

---

## 12. Final Recommendation

For the **best college MVP with minimum errors**, keep the project strictly like this:

- **one YOLOv8-seg model** for recognition + bbox + mask,
- **INDB as the primary nutrition source** [web:48][web:52],
- **IFCT only as fallback** [web:13],
- **SQLite only**,
- **real Indian labels from the beginning**,
- and **each phase fully demoable before moving forward**.

This gives the cleanest possible MVP with the least engineering complexity.