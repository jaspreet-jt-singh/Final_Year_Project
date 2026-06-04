# Project Status - AI-Based Food Recognition with Nutrition-Aware Recommendations

Document date: 2026-06-05  
Project type: Final year full-stack AI application  
Implementation status: Local full-stack prototype implemented

## Executive Summary

This project implements an AI-based food recognition system focused on Indian food items. The application accepts a food image, detects visible food items with a YOLO object detection model, maps detected food labels to nutrition records from the Indian Nutrient Database, calculates calorie and macronutrient values, and generates personalized dietary guidance based on the user's daily goal and health condition.

The repository contains a working FastAPI backend, a Next.js frontend, a SQLite nutrition database, YOLO model weights, a merged 72-class YOLO dataset, dataset build scripts, validation scripts, screenshots, demo media, and presentation assets.

## Implemented Deliverables

| Area | Implemented output |
|---|---|
| Dataset engineering | Five YOLO-format Indian food datasets merged into one canonical 72-class dataset at `data/food_dataset/` |
| Dataset normalization | Raw class variants normalized into stable canonical names such as `aloo_gobi`, `coconut_chutney`, `lemon_rice`, and `ven_pongal` |
| Dataset splitting | Universal train/validation/test split created with a 70/15/15 target ratio |
| Train augmentation | Train-only image augmentation applied for underrepresented classes |
| Model inference | YOLO inference service implemented through `backend/services/vision_service.py` |
| Nutrition lookup | SQLite-backed nutrition lookup implemented through `backend/services/nutrition_service.py` |
| Food name matching | Alias, normalization, partial match, and fuzzy match pipeline implemented |
| API layer | FastAPI routes implemented for health, food analysis, nutrition validation, macro calculation, goals, health conditions, and recommendations |
| Recommendation engine | Goal-aware and health-condition-aware recommendation service implemented with Groq, OpenAI, Ollama, and rule-based fallback |
| Frontend application | Next.js 14 app implemented with upload, results, bounding boxes, macro tracking, serving adjustment, and dietary guidance |
| Demo assets | Screenshots, demo video, and presentation files included in `screenshots/` and `presentations/` |

## System Architecture

```text
User image upload
  -> Next.js frontend
  -> FastAPI /api/analyze-food
  -> VisionService YOLO inference
  -> NutritionService SQLite lookup
  -> API response with detections, boxes, confidence, and macros
  -> ResultsPanel UI with nutrition totals and serving controls
  -> /api/recommendations
  -> RecommendationService LLM or fallback guidance
```

The application is separated into four main layers:

| Layer | Responsibility | Main files |
|---|---|---|
| Data layer | Raw datasets, merged YOLO dataset, INDB nutrition database | `data/`, `scripts/build_master_dataset.py`, `data/nutrition.db` |
| AI layer | YOLO model loading, warm-up, image detection, bounding box extraction | `backend/services/vision_service.py`, `models/yolo11s_indian.pt` |
| Backend layer | API endpoints, service orchestration, validation, rate limiting | `backend/main.py`, `backend/services/` |
| Frontend layer | User interface, image upload, results display, macro tracking, recommendations | `frontend/app/page.tsx`, `frontend/components/` |

## Implementation Phases

| Phase | Implemented work |
|---|---|
| Phase 0 - Data foundation | INDB nutrition file and SQLite nutrition database included; database schema verified by scripts |
| Phase 1 - Food recognition MVP | FastAPI backend, YOLO detection service, nutrition lookup service, and image upload endpoint implemented |
| Phase 2 - Detection visualization | Bounding box data returned by backend and rendered in the frontend results view |
| Phase 3 - Nutrition-aware personalization | Daily goals, calorie targets, macro calculation, health conditions, and dietary recommendations implemented |
| Dataset expansion | Merged 72-class YOLO dataset generated with train-only augmentation and export artifacts |

## Dataset - Merged YOLO Food Dataset

### Source Datasets

Five YOLO-format datasets were used as the source for the merged food dataset.

| # | Source dataset | Listed classes | Train images | Valid images | Test images | Total images |
|---|---|---:|---:|---:|---:|---:|
| 1 | `Indian food detection.v1i.yolov11` | 17 | 7,547 | 1,053 | 453 | 9,053 |
| 2 | `indian food.v6i.yolov11` | 29 | 8,088 | 213 | 105 | 8,406 |
| 3 | `Indian_food.v2-indianfood-7.yolov11` | 7 | 1,698 | 159 | 92 | 1,949 |
| 4 | `indianfoodnet_yolo` | 30+ | 11,387 | 1,073 | 576 | 13,036 |
| 5 | `south indian food detection.v19i.yolov11` | 31 | 6,478 | 1,294 | 581 | 8,353 |
| Total | Combined sources | 114+ raw labels with overlap | 35,198 | 3,792 | 1,807 | 40,797 |

The raw class count is higher than the final class count because many food names appear in multiple spellings or formats. Examples include `AlooGobi`, `aloo gobhi`, and `aloo_gobi`; `Idli` and `idly`; `WhiteRice`, `rice`, and `satham`.

### Dataset Build Script

Main script: `scripts/build_master_dataset.py`

The dataset build script implements the complete merge pipeline:

1. Scans each source dataset for YOLO split folders and label files.
2. Loads source class names from dataset YAML files.
3. Parses YOLO labels in normalized `class x y w h` format.
4. Converts raw labels into canonical snake_case food names.
5. Builds a multi-label representation for images containing more than one food class.
6. Creates train, validation, and test splits using `MultilabelStratifiedShuffleSplit`.
7. Falls back to deterministic random splitting for rare-label edge cases.
8. Exports image files and YOLO label files into a unified dataset structure.
9. Applies augmentation only to training images.
10. Writes `data.yaml`, `build_log.txt`, and `split_class_counts_before_after.csv`.

### Canonical Label Handling

The merge pipeline converts inconsistent source labels into 72 canonical labels. This keeps the model training data stable even when source datasets use different naming styles.

Examples:

| Raw variants | Canonical class |
|---|---|
| `AlooGobi`, `aloo gobhi`, `aloo_gobi` | `aloo_gobi` |
| `CoconutChutney`, `thengai chutney`, `coconut chutney` | `coconut_chutney` |
| `Idli`, `idly` | `idli` |
| `WhiteRice`, `rice`, `satham` | `rice` |
| `lemon satham` | `lemon_rice` |
| `medu vadai`, `medu vada` | `medu_vada` |

### Generated Dataset Summary

Generated dataset path: `data/food_dataset/`

| Property | Value |
|---|---:|
| Canonical classes | 72 |
| Train images | 36,852 |
| Train labels | 36,852 |
| Validation images | 5,922 |
| Validation labels | 5,922 |
| Test images | 5,919 |
| Test labels | 5,919 |
| Total exported image-label pairs | 48,693 |
| Split target ratio | 70/15/15 |
| Validation augmentation | None |
| Test augmentation | None |

### Generated Dataset Artifacts

| File | Purpose |
|---|---|
| `data/food_dataset/data.yaml` | YOLO dataset configuration with path, split folders, class count, and class names |
| `data/food_dataset/build_log.txt` | Build summary, augmentation targets, and per-class before/after counts |
| `data/food_dataset/split_class_counts_before_after.csv` | Machine-readable per-class counts for train, validation, and test splits |
| `data/food_dataset/train/images/` | Training images |
| `data/food_dataset/train/labels/` | Training YOLO labels |
| `data/food_dataset/valid/images/` | Validation images |
| `data/food_dataset/valid/labels/` | Validation YOLO labels |
| `data/food_dataset/test/images/` | Test images |
| `data/food_dataset/test/labels/` | Test YOLO labels |

### 72 Canonical Food Classes

`aloo_gobi`, `aloo_masala`, `appam`, `beetroot_poriyal`, `besan_cheela`, `bhakarwadi`, `bhakri`, `bhatura`, `bhindi_masala`, `biryani`, `carrot_poriyal`, `chai`, `chicken`, `chicken_65`, `chicken_biryani`, `chole`, `coconut_chutney`, `dal`, `dhokla`, `dosa`, `dum_aloo`, `eggs`, `fish_curry`, `ghevar`, `green_chutney`, `gulab_jamun`, `idli`, `jalebi`, `kaara_chutney`, `kali`, `kebab`, `khandvi`, `kheer`, `koozh`, `kulfi`, `lassi`, `lemon_rice`, `medu_vada`, `modak`, `mushroom_biryani`, `mutton_biryani`, `mutton_curry`, `nandu_masala`, `nei_satham`, `omelette`, `onion_pakoda`, `paal_kolukattai`, `palak_paneer`, `paneer_biryani`, `paratha`, `parupu_vadai`, `pidi_kolukattai`, `poha`, `poorna_kolukattai`, `prawn_thokku`, `puri`, `raita`, `rajma_curry`, `ras_malai`, `rice`, `roti`, `saag`, `salad`, `sambar`, `sambar_satham`, `samosa`, `shahi_paneer`, `thepla`, `upma`, `veg_briyani`, `veg_pulao`, `ven_pongal`.

### Per-Class Dataset Counts

Counts are image-level class counts. Multi-food images can contribute to more than one class total.

| Class | Train images before -> after | Valid images | Test images |
|---|---:|---:|---:|
| aloo_gobi | 556 -> 568 | 119 | 119 |
| aloo_masala | 520 -> 528 | 111 | 112 |
| appam | 210 -> 421 | 45 | 45 |
| beetroot_poriyal | 210 -> 421 | 45 | 45 |
| besan_cheela | 207 -> 414 | 44 | 45 |
| bhakarwadi | 256 -> 500 | 55 | 55 |
| bhakri | 79 -> 168 | 17 | 17 |
| bhatura | 680 -> 680 | 145 | 146 |
| bhindi_masala | 1046 -> 1056 | 224 | 224 |
| biryani | 700 -> 703 | 150 | 150 |
| carrot_poriyal | 210 -> 421 | 45 | 45 |
| chai | 340 -> 511 | 73 | 73 |
| chicken | 925 -> 925 | 198 | 198 |
| chicken_65 | 210 -> 421 | 45 | 45 |
| chicken_biryani | 210 -> 420 | 45 | 45 |
| chole | 1277 -> 1362 | 273 | 274 |
| coconut_chutney | 1007 -> 1207 | 216 | 216 |
| dal | 970 -> 985 | 208 | 208 |
| dhokla | 703 -> 704 | 151 | 151 |
| dosa | 1125 -> 1227 | 241 | 241 |
| dum_aloo | 358 -> 500 | 77 | 77 |
| eggs | 519 -> 561 | 111 | 111 |
| fish_curry | 362 -> 500 | 77 | 78 |
| ghevar | 235 -> 470 | 50 | 51 |
| green_chutney | 661 -> 748 | 141 | 142 |
| gulab_jamun | 272 -> 501 | 58 | 59 |
| idli | 821 -> 889 | 176 | 176 |
| jalebi | 872 -> 872 | 187 | 187 |
| kaara_chutney | 218 -> 457 | 46 | 47 |
| kali | 210 -> 423 | 45 | 45 |
| kebab | 161 -> 322 | 34 | 35 |
| khandvi | 325 -> 500 | 70 | 70 |
| kheer | 294 -> 500 | 63 | 63 |
| koozh | 210 -> 421 | 45 | 45 |
| kulfi | 332 -> 500 | 71 | 71 |
| lassi | 322 -> 500 | 69 | 69 |
| lemon_rice | 210 -> 420 | 45 | 45 |
| medu_vada | 386 -> 522 | 83 | 83 |
| modak | 120 -> 240 | 26 | 26 |
| mushroom_biryani | 210 -> 420 | 45 | 45 |
| mutton_biryani | 210 -> 421 | 45 | 45 |
| mutton_curry | 350 -> 500 | 75 | 75 |
| nandu_masala | 210 -> 420 | 45 | 45 |
| nei_satham | 210 -> 420 | 45 | 45 |
| omelette | 212 -> 440 | 45 | 46 |
| onion_pakoda | 333 -> 500 | 71 | 72 |
| paal_kolukattai | 210 -> 420 | 45 | 45 |
| palak_paneer | 1000 -> 1000 | 214 | 214 |
| paneer_biryani | 210 -> 420 | 45 | 45 |
| paratha | 127 -> 282 | 27 | 28 |
| parupu_vadai | 210 -> 425 | 45 | 45 |
| pidi_kolukattai | 210 -> 422 | 45 | 45 |
| poha | 1049 -> 1058 | 224 | 225 |
| poorna_kolukattai | 210 -> 421 | 45 | 45 |
| prawn_thokku | 210 -> 420 | 45 | 45 |
| puri | 380 -> 535 | 81 | 82 |
| raita | 239 -> 554 | 51 | 52 |
| rajma_curry | 1008 -> 1050 | 216 | 216 |
| ras_malai | 322 -> 500 | 69 | 69 |
| rice | 1776 -> 1856 | 380 | 381 |
| roti | 803 -> 821 | 172 | 172 |
| saag | 525 -> 525 | 112 | 113 |
| salad | 157 -> 360 | 34 | 34 |
| sambar | 475 -> 617 | 102 | 102 |
| sambar_satham | 210 -> 420 | 45 | 45 |
| samosa | 358 -> 500 | 77 | 77 |
| shahi_paneer | 878 -> 878 | 188 | 189 |
| thepla | 174 -> 377 | 37 | 38 |
| upma | 145 -> 290 | 31 | 31 |
| veg_briyani | 210 -> 420 | 45 | 45 |
| veg_pulao | 170 -> 364 | 36 | 37 |
| ven_pongal | 210 -> 433 | 45 | 45 |

## Model Layer

### Model Assets

| File | Purpose |
|---|---|
| `models/yolo11s_indian.pt` | Primary deployed YOLO11s model weights used by `VisionService` |
| `models/yolov8n_indian.pt` | Additional YOLO model weight file retained in the project |
| `models/class_names.json` | Class-name metadata for the deployed model package |
| `notebooks/train_yolo.ipynb` | Training notebook for YOLO experimentation |

### Runtime Model Scope

The runtime backend loads `models/yolo11s_indian.pt` by default through the `YOLO_MODEL_PATH` environment variable. The metadata file `models/class_names.json` currently lists 31 class labels for the deployed model package. The 72-class dataset in `data/food_dataset/` is the implemented expanded dataset asset and is available as the training corpus for broader class coverage.

### VisionService Implementation

Main file: `backend/services/vision_service.py`

Implemented behavior:

- Loads the YOLO model from the configured model path.
- Verifies the model file exists before startup completes.
- Performs a warm-up prediction on a dummy 640x640 image.
- Accepts raw uploaded image bytes from the API.
- Converts images to RGB using PIL.
- Uses Ultralytics YOLO letterboxing internally with `imgsz=640`.
- Runs prediction with confidence threshold `0.25` and IoU threshold `0.45`.
- Applies per-class confidence overrides for selected weaker classes:
  - `GreenChutney`: 0.50
  - `Dosa`: 0.45
  - `FishCurry`: 0.50
  - `Samosa`: 0.45
- Sorts detections by confidence.
- Returns all valid detections with food label, confidence, and `xyxy` bounding box.
- Returns source image width and height for frontend overlay scaling.
- Logs a short MD5 image fingerprint for debugging.

## Nutrition Layer

### Nutrition Database

| Asset | Purpose |
|---|---|
| `data/INDB.xlsx` | Source Indian Nutrient Database spreadsheet |
| `data/nutrition.db` | SQLite database used by the backend |
| `backend/scripts/merge_db.py` | Script used for nutrition database creation/merge work |

The nutrition database contains an `indb_foods` table with the core columns used by the application:

| Column | Meaning |
|---|---|
| `name` | Food display name from the database |
| `normalized_name` | Search-friendly normalized name |
| `calories` | Calories per 100g |
| `protein_g` | Protein in grams per 100g |
| `carbs_g` | Carbohydrates in grams per 100g |
| `fat_g` | Fat in grams per 100g |

### NutritionService Implementation

Main file: `backend/services/nutrition_service.py`

Implemented lookup sequence:

1. Connect to `data/nutrition.db` with `aiosqlite`.
2. Cache all food names and normalized names at startup.
3. Load precomputed YOLO-to-database mappings if the optional `yolo_mappings` table exists.
4. Resolve direct YOLO class mappings first.
5. Normalize the incoming food label.
6. Try exact normalized-name matching.
7. Try partial substring matching.
8. Generate alias-based variations through `backend/utils/food_normalizer.py`.
9. Apply fuzzy matching through `SequenceMatcher` as the final lookup method.
10. Return calories, protein, carbohydrates, and fat per 100g.

### Food Alias Support

Alias file: `backend/config/food_aliases.json`

Implemented aliases improve matching across English, Hindi, and regional naming styles. Examples:

| Base term | Supported aliases |
|---|---|
| `aloo` | `potato`, `alu` |
| `gobi` | `cauliflower`, `gobhi` |
| `paneer` | `cottagecheese`, `panir` |
| `dal` | `lentil`, `daal`, `dahl` |
| `chole` | `chana`, `chickpea`, `chanamasala` |
| `dosa` | `dhosai`, `dosai` |
| `idli` | `idly`, `iddli` |
| `biryani` | `biriyani`, `beriani` |
| `rice` | `chawal`, `bhaat`, `annam` |
| `roti` | `chapati`, `phulka` |

## Backend API

Backend framework: FastAPI  
Main file: `backend/main.py`

### Backend Features

- FastAPI app configured with title, description, and version.
- CORS enabled for local frontend origins:
  - `http://localhost:3000`
  - `http://127.0.0.1:3000`
- Rate limiting implemented through `slowapi`.
- Upload validation implemented for content type, empty files, and max size.
- Max upload size enforced at 10 MB.
- YOLO inference executed in a `ThreadPoolExecutor` to avoid blocking the event loop.
- Startup initializes nutrition service, vision service, model warm-up, and recommendation service.
- No-food results return HTTP 200 with an empty detection list and `food_not_found: true`.
- Service errors return structured FastAPI `HTTPException` responses.

### API Endpoints

| Endpoint | Method | Implemented purpose |
|---|---|---|
| `/` | GET | Root API description and endpoint list |
| `/api/health` | GET | Service health and model-loaded status |
| `/api/analyze-food` | POST | Accept image upload, run YOLO detection, attach nutrition data |
| `/api/test-nutrition/{food_name}` | GET | Debug single-food nutrition lookup |
| `/api/validate-nutrition` | GET | Validate nutrition coverage for the deployed model class list |
| `/api/user/calculate-macros` | POST | Calculate macro targets for goal, calories, and health condition |
| `/api/user/goals` | GET | Return supported dietary goals |
| `/api/user/health-conditions` | GET | Return supported health condition options |
| `/api/recommendations` | POST | Generate personalized dietary recommendations |

### Analyze Food Response Shape

```json
{
  "detections": [
    {
      "food_label": "Biryani",
      "display_name": "Biryani",
      "confidence": 0.91,
      "bounding_box": [120, 80, 520, 430],
      "macros": {
        "calories": 170.0,
        "protein_g": 5.2,
        "carbs_g": 25.0,
        "fat_g": 4.5
      },
      "macros_unit": "per_100g",
      "nutrition_source": "INDB"
    }
  ],
  "img_width": 640,
  "img_height": 480,
  "food_not_found": false
}
```

### No-Food Response Shape

```json
{
  "detections": [],
  "img_width": null,
  "img_height": null,
  "food_not_found": true,
  "message": "No food detected in image"
}
```

## Recommendation and Macro Engine

Main file: `backend/services/recommendation_service.py`

### Dietary Goals

| Goal | Carbs | Protein | Fat | Purpose |
|---|---:|---:|---:|---|
| Weight Loss | 40% | 35% | 25% | Higher protein and moderate carbs for satiety |
| Muscle Gain | 40% | 30% | 30% | Balanced macros with adequate protein |
| Maintenance | 50% | 25% | 25% | Balanced nutrition for maintaining weight |
| Endurance | 55% | 20% | 20% | Higher carbohydrates for sustained activity |

### Health Conditions

The backend implements macro and recommendation adjustments for eight specific health conditions plus the default `None` option.

| Condition | Implemented dietary emphasis |
|---|---|
| None | Standard goal-based macro split |
| Diabetic | Lower carbohydrate emphasis and higher protein support |
| Hypertension | Sodium-aware advice and slightly lower fat emphasis |
| Heart Disease | Lower saturated-fat style guidance |
| High Cholesterol | Lower fat, higher fiber, plant-protein guidance |
| Digestive Issues | Easily digestible food and smaller-meal guidance |
| Kidney Disease | Controlled protein and potassium-aware guidance |
| Anemia | Iron and vitamin C support |
| Thyroid Disorder | Iodine balance and selenium-aware guidance |

### Recommendation Provider Chain

The recommendation service uses the first available provider that returns useful output:

1. Groq with `llama-3.1-8b-instant`
2. OpenAI with `gpt-3.5-turbo`
3. Local Ollama with `llama2`
4. Built-in rule-based fallback recommendations

The response parser extracts up to three practical bullet-point recommendations and removes preamble text.

## Frontend Application

Frontend framework: Next.js 14 App Router  
Language: TypeScript  
Styling: Tailwind CSS  
Icons: Lucide React

### Frontend Files

| File | Implemented purpose |
|---|---|
| `frontend/app/page.tsx` | Main app screen, state management, API calls, macro tracking, goal and health selectors |
| `frontend/app/layout.tsx` | Root layout and metadata |
| `frontend/app/globals.css` | Tailwind imports and global styling |
| `frontend/components/ImageUpload.tsx` | Drag-and-drop upload, file preview, loading state, raw file forwarding |
| `frontend/components/ResultsPanel.tsx` | Detection summary, bounding boxes, nutrition cards, serving controls, recommendations |
| `frontend/components/NutritionLabel.tsx` | Calories, protein, carbs, and fat display cards |
| `frontend/components/ImageOverlay.tsx` | Canvas-based overlay component retained for detection visualization support |
| `frontend/styles/globals.css` | Additional shared style definitions |

### User Flow

1. User selects daily dietary goal.
2. User sets daily calorie target.
3. User selects health condition.
4. Frontend calculates or fetches macro targets.
5. User uploads a food image by dragging/dropping or file picker.
6. Frontend sends raw image file through `FormData` to `/api/analyze-food`.
7. Backend returns detections, nutrition values, bounding boxes, and image dimensions.
8. Frontend renders detected foods and confidence scores.
9. Frontend overlays bounding boxes on the uploaded image.
10. Frontend displays nutrition values per 100g.
11. User adjusts serving multiplier per detected item in 0.25x steps.
12. Macro and calorie totals update immediately.
13. Frontend fetches personalized recommendations from `/api/recommendations`.
14. Dietary guidance is displayed with goal and health-condition context.

### Implemented UI Features

- Sticky calorie status bar.
- Daily calorie remaining counter.
- Color-coded calorie progress bar:
  - Green below 50%
  - Yellow below 80%
  - Orange below 100%
  - Red at or above 100%
- Goal selector with backend fetch and local fallback.
- Health condition selector with backend fetch and local fallback.
- Collapsible macro details panel.
- Health-condition adaptation notice.
- Quick calorie presets: 1500, 1800, 2000, 2200, and 2500 kcal.
- Drag-and-drop upload component.
- FileReader image preview.
- AbortController timeout for image analysis requests.
- No-food detected state.
- Structured error messages for timeout, backend connectivity, and server errors.
- Detection confidence badges.
- Bounding box overlay for all detected foods.
- Nutrition cards for calories, protein, carbs, and fat.
- Serving-size multiplier controls per detected item.
- Remaining macro display for carbs, protein, and fat.
- AI dietary guidance panel.
- Reset button that clears analysis state while preserving goal configuration.

## Runtime Configuration

Environment file: `.env`

| Variable | Purpose | Default or usage |
|---|---|---|
| `YOLO_MODEL_PATH` | YOLO weights path | Defaults to `models/yolo11s_indian.pt` |
| `RATE_LIMIT_PER_MINUTE` | API rate limit | Defaults to `30` |
| `GROQ_API_KEY` | Groq recommendation provider | Optional |
| `OPENAI_API_KEY` | OpenAI recommendation provider | Optional |
| `OLLAMA_HOST` | Local Ollama endpoint | Defaults to `http://localhost:11434` |

## Local Run Instructions

### Backend

```bash
cd backend
python main.py
```

Backend URL: `http://localhost:8000`

Useful backend checks:

```bash
curl http://localhost:8000/api/health
curl http://localhost:8000/api/user/goals
curl http://localhost:8000/api/user/health-conditions
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend URL: `http://localhost:3000`

### Dataset Build

```bash
python scripts/build_master_dataset.py
```

Generated output: `data/food_dataset/`

## Dependencies

### Backend Dependencies

Defined in `requirements.txt`:

| Package | Role |
|---|---|
| `fastapi` | API framework |
| `uvicorn[standard]` | ASGI server |
| `slowapi` | Rate limiting |
| `python-multipart` | File upload handling |
| `torch` | ML runtime |
| `ultralytics` | YOLO model loading and inference |
| `opencv-python-headless` | Image-processing support |
| `pillow` | Image decoding and RGB conversion |
| `numpy`, `pandas`, `openpyxl` | Data processing |
| `sqlalchemy`, `aiosqlite` | Database access |
| `python-dotenv` | Environment variable loading |
| `httpx`, `requests` | HTTP clients |
| `groq`, `openai` | LLM recommendation providers |
| `roboflow` | Dataset/model workflow support |

### Frontend Dependencies

Defined in `frontend/package.json`:

| Package | Role |
|---|---|
| `next` | React framework |
| `react`, `react-dom` | UI rendering |
| `typescript` | Type safety |
| `tailwindcss`, `postcss`, `autoprefixer` | Styling pipeline |
| `lucide-react` | Icon components |
| `eslint`, `eslint-config-next` | Linting |

## Validation and Test Assets

The repository includes Python validation scripts under `tests/`.

| File | Validation focus |
|---|---|
| `tests/test_phase0.py` | Data foundation, INDB file, SQLite database, expected schema |
| `tests/test_phase1.py` | Backend service structure, model assets, API endpoint presence, rate limiting |
| `tests/test_phase2.py` | Frontend structure, overlay component, bounding box support |
| `tests/test_integration.py` | End-to-end service initialization, nutrition lookup, API/frontend integration points |
| `tests/test_api_live.py` | Live API checks against `http://localhost:8000` |
| `tests/check_api_mappings.py` | API/nutrition mapping validation support |
| `tests/debug_nutrition_lookup.py` | Nutrition lookup debugging |
| `tests/list_food_mappings.py` | Food mapping inspection |
| `tests/simple_check.py` | Lightweight repository checks |
| `tests/test_new_matching.py` | New food-name matching validation |

## Demo and Presentation Assets

| Asset location | Contents |
|---|---|
| `screenshots/` | UI screenshots and `Project Demo.mp4` |
| `presentations/` | Final and mid-term project PPT/PDF files |

These assets support demonstration of the implemented application workflow, UI states, and project explanation.

## Completed Implementation Summary

- [x] Indian-food YOLO dataset sources collected in `data/`.
- [x] Merged 72-class canonical dataset generated in `data/food_dataset/`.
- [x] Dataset build artifacts written: `data.yaml`, `build_log.txt`, and per-class CSV.
- [x] YOLO model assets included in `models/`.
- [x] FastAPI backend implemented.
- [x] YOLO inference service implemented.
- [x] Nutrition lookup service implemented with SQLite.
- [x] Food-name normalization and alias matching implemented.
- [x] Health check, analysis, nutrition validation, macro, goal, health-condition, and recommendation endpoints implemented.
- [x] LLM provider fallback chain implemented.
- [x] Rule-based dietary recommendation fallback implemented.
- [x] Next.js frontend implemented.
- [x] Drag-and-drop image upload implemented.
- [x] Detection result display implemented.
- [x] Bounding box visualization implemented.
- [x] Nutrition label cards implemented.
- [x] Daily calorie and macro tracking implemented.
- [x] Serving-size adjustment implemented.
- [x] Goal selection implemented.
- [x] Health-condition adaptation implemented.
- [x] Personalized recommendation display implemented.
- [x] Demo screenshots, video, and presentation files included.

## Final Project Description

The completed system demonstrates a full AI-assisted nutrition workflow for Indian food. It combines computer vision, food-name normalization, nutrition database lookup, personalized macro calculation, and LLM-backed dietary guidance in a single usable web application. The backend exposes a structured API for image analysis and recommendations, while the frontend provides an interactive workflow for users to upload food images, inspect detections, adjust servings, track daily macro impact, and receive nutrition-aware suggestions.
