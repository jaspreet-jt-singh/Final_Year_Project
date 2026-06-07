# Project Status - AI-Based Food Recognition with Nutrition-Aware Recommendations

Document date: 2026-06-08  
Project type: Final year full-stack AI application  
Implementation status: Local full-stack prototype implemented

## Executive Summary

This project implements an AI-based Indian food recognition and nutrition recommendation system. A user uploads a food image, the system detects visible food items with a YOLO object detector, maps detected food labels to nutrition records, calculates calories and macronutrients, and generates personalized dietary guidance based on the user's goal and health condition.

The implemented system combines:

- A curated 72-class Indian-food YOLO dataset.
- A YOLO11s food detector.
- A FastAPI backend for image analysis, nutrition lookup, macro calculation, and recommendations.
- A SQLite nutrition database built from Indian food-composition data and supplemental audited rows.
- A Next.js frontend for upload, detection overlays, serving adjustment, daily macro tracking, and guidance.

## Implemented Scope

| Area | Implemented output |
|---|---|
| Dataset engineering | Five YOLO-format Indian food datasets merged into a canonical 72-class dataset |
| Dataset normalization | Raw class variants normalized into stable snake_case food labels |
| Dataset splitting | Train/validation/test split generated with a 70/15/15 target ratio |
| Train augmentation | Train-only augmentation applied for underrepresented classes |
| Food detection | YOLO11s detector trained for the expanded Indian-food dataset |
| Nutrition database | SQLite nutrition database with 1,010 food records, macro values, and source metadata |
| Nutrition mapping | Detector labels mapped to database entries through normalization, aliases, and audited mappings |
| Backend API | FastAPI routes for health checks, food analysis, nutrition validation, macro goals, health profiles, and recommendations |
| Recommendation engine | Goal-aware and health-condition-aware dietary guidance implemented with Groq |
| Frontend app | Next.js interface with upload, results, boxes, macros, serving controls, and personalized guidance |

## System Architecture

```text
User food image
  -> Next.js frontend upload
  -> FastAPI /api/analyze-food
  -> YOLO11s VisionService detection
  -> NutritionService SQLite lookup
  -> Detection boxes, confidence scores, and nutrition values
  -> Frontend result view with serving adjustment and macro totals
  -> /api/recommendations
  -> Personalized dietary suggestions
```

The application is separated into four layers:

| Layer | Responsibility |
|---|---|
| Data layer | YOLO food dataset, INDB spreadsheet, SQLite nutrition records, detector-to-database mappings |
| AI layer | YOLO model loading, image preprocessing, object detection, bounding-box extraction |
| Backend layer | API orchestration, validation, nutrition lookup, macro calculation, recommendation prompts |
| Frontend layer | Upload workflow, detection visualization, nutrition display, goal setup, serving adjustment |

### End-to-End Data Contract

The image-analysis workflow returns structured data that the frontend can render without additional parsing.

| Field | Meaning |
|---|---|
| `detections` | List of detected food items after confidence filtering |
| `food_label` | Raw detector class name |
| `display_name` | Nutrition database food name or formatted detector label |
| `confidence` | YOLO confidence score for the detection |
| `bounding_box` | Pixel coordinates in `[x1, y1, x2, y2]` format |
| `macros` | Calories, protein, carbohydrates, and fat for the mapped food |
| `macros_unit` | Current unit is `per_100g` |
| `nutrition_source` | Source metadata for the nutrition record |
| `img_width`, `img_height` | Original uploaded image dimensions used for overlay scaling |
| `food_not_found` | Explicit no-food state for images without valid detections |

## Dataset

Generated dataset path: `data/food_dataset/`

Five YOLO-format Indian food datasets were merged and normalized into one canonical dataset.

| Property | Value |
|---|---:|
| Canonical food classes | 72 |
| Train images | 36,852 |
| Validation images | 5,922 |
| Test images | 5,919 |
| Total exported image-label pairs | 48,693 |
| Split target ratio | 70/15/15 |
| Validation augmentation | None |
| Test augmentation | None |

### Source Datasets

| # | Source dataset | Listed classes | Train images | Valid images | Test images | Total images |
|---|---|---:|---:|---:|---:|---:|
| 1 | `Indian food detection.v1i.yolov11` | 17 | 7,547 | 1,053 | 453 | 9,053 |
| 2 | `indian food.v6i.yolov11` | 29 | 8,088 | 213 | 105 | 8,406 |
| 3 | `Indian_food.v2-indianfood-7.yolov11` | 7 | 1,698 | 159 | 92 | 1,949 |
| 4 | `indianfoodnet_yolo` | 30 | 11,387 | 1,073 | 576 | 13,036 |
| 5 | `south indian food detection.v19i.yolov11` | 31 | 6,478 | 1,294 | 581 | 8,353 |
| Total | Combined source pool | 114 raw class entries with overlap | 35,198 | 3,792 | 1,807 | 40,797 |

The raw label count is higher than the final class count because multiple datasets used different spellings or regional names for the same food. Examples include `AlooGobi`, `aloo gobhi`, and `aloo_gobi`; `Idli` and `idly`; `WhiteRice`, `rice`, and `satham`.

### Dataset Build Pipeline

The dataset builder creates a canonical YOLO dataset through these project steps:

1. Read source `data.yaml` files and source split folders.
2. Parse YOLO label files in normalized `class x y w h` format.
3. Convert raw source labels into canonical snake_case class names.
4. Preserve multi-food image labels when an image contains more than one class.
5. Create train, validation, and test splits using multilabel-aware splitting when possible.
6. Fall back to deterministic random splitting for rare-label edge cases.
7. Copy image files and rewritten YOLO label files into the canonical split folders.
8. Apply augmentation only to training images for underrepresented classes.
9. Write `data.yaml`, `build_log.txt`, and `split_class_counts_before_after.csv`.

### Generated Dataset Files

| File or folder | Purpose |
|---|---|
| `data/food_dataset/data.yaml` | YOLO dataset configuration with 72 class names |
| `data/food_dataset/build_log.txt` | Build summary, split ratio, augmentation targets, and class counts |
| `data/food_dataset/split_class_counts_before_after.csv` | Machine-readable before/after class counts |
| `data/food_dataset/train/images` | Training images |
| `data/food_dataset/train/labels` | Training labels |
| `data/food_dataset/valid/images` | Validation images |
| `data/food_dataset/valid/labels` | Validation labels |
| `data/food_dataset/test/images` | Held-out test images |
| `data/food_dataset/test/labels` | Held-out test labels |

### Canonical Label Examples

| Raw variants | Canonical class |
|---|---|
| `AlooGobi`, `aloo gobhi`, `aloo_gobi` | `aloo_gobi` |
| `CoconutChutney`, `thengai chutney`, `coconut chutney` | `coconut_chutney` |
| `Idli`, `idly` | `idli` |
| `WhiteRice`, `rice`, `satham` | `rice` |
| `lemon satham` | `lemon_rice` |
| `medu vadai`, `medu vada` | `medu_vada` |

### Canonical Food Classes

`aloo_gobi`, `aloo_masala`, `appam`, `beetroot_poriyal`, `besan_cheela`, `bhakarwadi`, `bhakri`, `bhatura`, `bhindi_masala`, `biryani`, `carrot_poriyal`, `chai`, `chicken`, `chicken_65`, `chicken_biryani`, `chole`, `coconut_chutney`, `dal`, `dhokla`, `dosa`, `dum_aloo`, `eggs`, `fish_curry`, `ghevar`, `green_chutney`, `gulab_jamun`, `idli`, `jalebi`, `kaara_chutney`, `kali`, `kebab`, `khandvi`, `kheer`, `koozh`, `kulfi`, `lassi`, `lemon_rice`, `medu_vada`, `modak`, `mushroom_biryani`, `mutton_biryani`, `mutton_curry`, `nandu_masala`, `nei_satham`, `omelette`, `onion_pakoda`, `paal_kolukattai`, `palak_paneer`, `paneer_biryani`, `paratha`, `parupu_vadai`, `pidi_kolukattai`, `poha`, `poorna_kolukattai`, `prawn_thokku`, `puri`, `raita`, `rajma_curry`, `ras_malai`, `rice`, `roti`, `saag`, `salad`, `sambar`, `sambar_satham`, `samosa`, `shahi_paneer`, `thepla`, `upma`, `veg_briyani`, `veg_pulao`, `ven_pongal`.

### Dataset Verification

Visual verification confirmed that all 72 classes have real image samples. Three annotation-level issues were identified for future cleanup:

| Finding |
|---|
| One `jalebi` sample did not visually match jalebi |
| One `kaara_chutney` bounding box was placed on vada instead of chutney |
| One `nandu_masala` bounding box was extremely thin and produced a poor crop |

## Model

The project uses YOLO11s for food object detection.

| Item | Value |
|---|---|
| Current local model path | `models/yolo11s_indian_food_best.pt` |
| Backend code default | `models/yolo11s_indian.pt` |
| Final training notebook | `notebooks/final_version_training.ipynb` |
| Image size | 640 |
| Final run name | `yolo11s_indian_food` |
| Training continuation | Resumed from epoch 56 and continued to epoch 100 |
| Best logged validation mAP@50 | 0.83379 at epoch 78 |

### Training Configuration

| Setting | Value |
|---|---|
| Detector family | YOLO object detection |
| Model variant | YOLO11s |
| Image size | 640 |
| Batch size | 16 in the final training run |
| AMP | Enabled |
| Epoch target | 100 |
| Final resumed stage | Epoch 56 through epoch 100 |
| Run name | `yolo11s_indian_food` |
| Primary metrics | Precision, recall, mAP@50, mAP@50:95 |

### Final Detector Metrics

| Split | Images | Instances | Precision | Recall | mAP@50 | mAP@50:95 |
|---|---:|---:|---:|---:|---:|---:|
| Validation | 5,922 | 8,812 | 0.847 | 0.807 | 0.830 | 0.692 |
| Held-out test | 5,919 | 8,875 | 0.842 | 0.801 | 0.820 | 0.680 |

The small gap between validation and held-out test performance indicates that the detector generalizes beyond the validation split, although visually similar dishes and lower-data classes still need deeper per-class error analysis.

### Inference Configuration

| Setting | Value |
|---|---|
| Input format | Uploaded image bytes |
| Image decoding | PIL RGB conversion |
| Manual resize | None; YOLO handles letterboxing internally |
| Inference image size | 640 |
| Base confidence threshold | 0.25 |
| IoU threshold | 0.45 |
| Warm-up input | Dummy 640x640 RGB image |
| Output ordering | Valid detections sorted by confidence descending |

The configured per-class confidence override table is:

| Class | Minimum confidence |
|---|---:|
| `GreenChutney` | 0.50 |
| `Dosa` | 0.45 |
| `FishCurry` | 0.50 |
| `Samosa` | 0.45 |

These overrides apply when the loaded detector's class names match the configured labels.

## Backend

Backend framework: FastAPI  
Main runtime service areas: vision, nutrition, goals, health profiles, and recommendations

### Implemented API Behavior

| Capability | Implementation |
|---|---|
| Health check | Confirms service availability |
| Food analysis | Accepts image uploads and returns detections, bounding boxes, confidence scores, and nutrition values |
| Nutrition lookup | Resolves food labels to database rows and macro values |
| Nutrition validation | Checks legacy deployed detector-class nutrition coverage through `/api/validate-nutrition` |
| Goal metadata | Provides supported dietary goals |
| Health profile metadata | Provides supported health-condition options |
| Macro calculation | Calculates daily macro targets from calories, goal, and health profile |
| Recommendations | Generates three practical dietary suggestions from detected foods and user context |

### API Endpoints

| Method | Path | Project behavior |
|---|---|---|
| `GET` | `/api/health` | Returns service status and model-loaded state |
| `GET` | `/api/test-nutrition/{food_name}` | Looks up one food label against the nutrition service |
| `GET` | `/api/validate-nutrition` | Validates nutrition lookup for the legacy deployed detector class list |
| `POST` | `/api/analyze-food` | Accepts one uploaded image and returns detections, boxes, image dimensions, and nutrition values |
| `POST` | `/api/user/calculate-macros` | Calculates macro targets from goal, calories, and health condition |
| `GET` | `/api/user/goals` | Returns supported dietary goals and base macro splits |
| `GET` | `/api/user/health-conditions` | Returns supported health profiles and descriptions |
| `POST` | `/api/recommendations` | Returns dietary suggestions for detected foods and user context |
| `GET` | `/` | Returns basic API metadata and endpoint names |

### Upload and Error Handling

| Rule | Behavior |
|---|---|
| Accepted upload field | `file` in `FormData` |
| Content type | Must start with `image/` |
| Empty file | Returns HTTP 400 |
| Maximum file size | 10 MB |
| Rate limit | `RATE_LIMIT_PER_MINUTE`, default 30 requests per minute |
| Backend not initialized | Returns HTTP 503 |
| No valid food detection | Returns HTTP 200 with empty `detections` and `food_not_found: true` |
| Nutrition missing for a detection | Returns the detection with `macros: null` and `nutrition_not_found: true` |

### Vision Service

The vision service:

- Loads YOLO weights from `YOLO_MODEL_PATH`.
- Validates that the model file exists before startup completes.
- Accepts raw uploaded image bytes.
- Converts images to RGB.
- Runs YOLO inference at image size 640.
- Uses confidence and IoU thresholds for detection filtering.
- Returns class labels, confidence values, bounding boxes, and image dimensions.
- Returns no result when no valid detections remain; the API converts this into an empty detection list.

### Nutrition Service

The nutrition service:

- Loads 1,010 food records from SQLite.
- Normalizes detector labels and database names.
- Uses 103 audited YOLO-to-database mappings for regional or spelling variants.
- Avoids unsafe substitutions when a confident mapping is unavailable.
- Returns calories, protein, carbohydrates, and fat with source metadata.

### Nutrition Database Coverage

| Item | Value |
|---|---:|
| Nutrition records | 1,010 |
| INDB records | 1,005 |
| Supplemental source-backed records | 5 |
| YOLO mapping rows | 103 |
| Expanded dataset classes checked | 72 |
| Expanded dataset classes with mapping rows | 72 |
| Failed expanded-class macro mappings | 0 |

The five supplemental rows are used for foods absent from the available INDB data: `Bhakarwadi`, `Ghevar`, `Jalebi`, `Khandvi`, and `Nandu Kari (Crab masala)`.

The expanded 72-class macro verification artifact reports:

| Status | Count |
|---|---:|
| Verified mappings | 51 |
| Review mappings | 21 |
| Failed mappings | 0 |

### Nutrition Database Schema

| Table | Important fields | Purpose |
|---|---|---|
| `indb_foods` | `name`, `normalized_name`, `calories`, `protein_g`, `carbs_g`, `fat_g`, `source`, `source_url`, `source_notes` | Stores per-100g food-composition records |
| `yolo_mappings` | `yolo_class`, `matched_food_name`, `match_score` | Stores audited detector-label to database-food mappings |

### Nutrition Lookup Pipeline

1. Check whether the detected class has a precomputed `yolo_mappings` row.
2. Resolve mapped detector classes directly to the accepted database food name.
3. If no mapping is present, normalize the detector label.
4. Try exact normalized-name matching.
5. Try partial matching between normalized detector labels and normalized database names.
6. Try generated food-name variations for regional spellings and formatting differences.
7. Try fuzzy matching as the final fallback.
8. Return `None` when no acceptable nutrition match is found.

The API response keeps numeric nutrition values separate from recommendation text. Calories and macronutrients come from SQLite, not from the language model.

## Nutrition and Personalization

The project supports four dietary goals:

| Goal | Carbs | Protein | Fat | Intended macro emphasis |
|---|---:|---:|---:|---|
| Weight Loss | 40% | 35% | 25% | Higher protein for satiety and muscle preservation |
| Muscle Gain | 40% | 30% | 30% | Balanced macros with adequate protein for muscle synthesis |
| Maintenance | 50% | 25% | 25% | Balanced nutrition for maintaining current weight |
| Endurance | 55% | 20% | 20% | Higher carbohydrates for sustained energy |

Health profiles adjust macro percentages before gram targets are calculated:

| Health profile | Carbs modifier | Protein modifier | Fat modifier | Implemented adjustment focus |
|---|---:|---:|---:|---|
| None | 1.00 | 1.00 | 1.00 | Uses the selected goal's base macro split |
| Diabetic | 0.80 | 1.15 | 1.00 | Reduces carbohydrate share and increases protein share |
| Hypertension | 1.00 | 1.00 | 0.90 | Pairs recommendations with lower-sodium guidance |
| Heart Disease | 1.05 | 1.00 | 0.80 | Reduces fat emphasis |
| High Cholesterol | 1.05 | 1.10 | 0.75 | Reduces fat and emphasizes fiber/plant-protein guidance |
| Digestive Issues | 1.00 | 0.90 | 0.85 | Reduces heavy fat/protein load and favors easier digestion |
| Kidney Disease | 1.15 | 0.60 | 1.00 | Reduces protein share |
| Anemia | 1.00 | 1.10 | 0.90 | Adds iron-supportive recommendation guidance |
| Thyroid Disorder | 1.00 | 1.05 | 1.00 | Slightly increases protein emphasis and adds thyroid-aware guidance |

Macro percentages are normalized back to 100% after health modifiers are applied.

Macro grams are calculated from calorie targets using:

| Macro | Calories per gram |
|---|---:|
| Carbohydrates | 4 kcal/g |
| Protein | 4 kcal/g |
| Fat | 9 kcal/g |

Example calculation flow:

```text
adjusted_macro_percent = goal_macro_percent * health_modifier
final_macro_percent = adjusted_macro_percent / sum(all_adjusted_macro_percents)
carbs_g = target_calories * carbs_percent / 100 / 4
protein_g = target_calories * protein_percent / 100 / 4
fat_g = target_calories * fat_percent / 100 / 9
```

## Recommendation Engine

The recommendation service uses Groq as the primary provider for concise dietary suggestions, with OpenAI, local Ollama, and deterministic fallback recommendations available when the preferred provider is unavailable.

| Item | Value |
|---|---|
| Provider | Groq |
| Model | `llama-3.1-8b-instant` |
| Primary environment key | `GROQ_API_KEY` |
| Fallback providers | OpenAI, Ollama, deterministic rule-based fallback |
| Prompt inputs | Detected foods, calorie/macro values, selected goal, selected health profile |
| Response format | Three practical dietary suggestions |

The recommendation layer receives already-computed nutrition values from the backend. It does not invent calorie or macro numbers.

## Frontend

Frontend framework: Next.js 14  
Language: TypeScript  
Styling: Tailwind CSS  
Icons: Lucide React

### Implemented User Flow

1. Select a dietary goal.
2. Set a daily calorie target.
3. Select a health condition.
4. Upload a food image.
5. View detected foods and bounding boxes.
6. Review calories, protein, carbs, and fat.
7. Adjust serving multipliers per detected item.
8. Track remaining daily calories and macros.
9. Read personalized dietary recommendations.

### Implemented UI Features

- Drag-and-drop image upload.
- Image preview before and after analysis.
- Structured loading and error states.
- No-food detected state.
- Detection confidence badges.
- Bounding box overlay.
- Nutrition cards for calories, protein, carbs, and fat.
- Serving multiplier controls from 0.25x to 10x.
- Daily calorie progress bar.
- Remaining calorie and macro display.
- Goal selector and calorie presets.
- Health-condition selector.
- Personalized guidance panel.
- Reset flow that clears analysis while preserving goal configuration.

### Frontend Component Responsibilities

| Component | Responsibility |
|---|---|
| `frontend/app/page.tsx` | Main application state, goal setup, calorie target, backend calls, upload orchestration, macro tracking |
| `frontend/components/ImageUpload.tsx` | Drag/drop input, image file selection, FileReader preview, raw file forwarding |
| `frontend/components/ResultsPanel.tsx` | Detection summary, bounding box overlay, serving multipliers, nutrition totals, recommendation fetch |
| `frontend/components/NutritionLabel.tsx` | Calories, protein, carbohydrates, and fat display |
| `frontend/components/ImageOverlay.tsx` | Canvas-based single-box overlay component retained for detection visualization support |

### Frontend Runtime Behavior

| Behavior | Detail |
|---|---|
| Backend base URL | `http://localhost:8000` |
| Analysis timeout | 30 seconds through `AbortController` |
| Metadata fallback | Local goal and health-condition defaults are used if backend metadata requests fail |
| Serving step | 0.25x |
| Serving range | 0.25x to 10x per detected food |
| Progress colors | Green below 50%, yellow below 80%, orange below 100%, red at or above 100% |

## Validation

The project includes validation coverage for:

| Validation area | Purpose |
|---|---|
| Dataset build | Confirms generated dataset structure, split files, labels, and class counts |
| Dataset visual checks | Confirms that each class has real image samples |
| Nutrition database | Confirms required nutrition fields and database records |
| Expanded mapping logic | Confirms all 72 canonical dataset classes resolve to nutrition rows with complete macro fields |
| API nutrition validation | Checks the legacy deployed detector class list through `/api/validate-nutrition` |
| Backend services | Confirms service imports, API routes, model path handling, and nutrition lookup |
| Frontend integration | Confirms expected frontend components and API response fields |
| Live API checks | Validate running backend endpoints when the server is active |

### Validation Artifacts

| Script or artifact | Project validation role |
|---|---|
| `scripts/build_master_dataset.py` | Rebuilds the canonical 72-class YOLO dataset |
| `scripts/verify_food_classes_with_images.py` | Generates visual class verification sheets from actual dataset images |
| `scripts/verify_yolo_class_macros.py` | Verifies macro availability and mapping quality for all 72 canonical classes |
| `data/food_dataset/class_verification/verification_summary.md` | Summarizes class image availability and annotation issues |
| `data/nutrition_verification/yolo_class_macro_verification.md` | Summarizes 72-class macro mapping status |
| `tests/test_phase0.py` | Validates nutrition foundation and core data assets |
| `tests/test_phase1.py` | Validates backend services, API code, database tables, and model-path handling |
| `tests/test_phase2.py` | Validates frontend structure and detection visualization integration |
| `tests/test_integration.py` | Checks service integration points for image analysis, nutrition lookup, and frontend fields |
| `tests/test_api_live.py` | Checks live backend endpoints when the API server is running |
| `tests/test_new_matching.py` | Validates normalized nutrition matching for selected detector classes |

### Current Verified Results

| Check | Result |
|---|---|
| Canonical dataset classes | 72 |
| Classes with visual samples | 72 |
| Classes without visual samples | 0 |
| Expanded classes with macro mappings | 72 |
| Expanded-class mapping failures | 0 |
| Known annotation issues for future cleanup | 3 |

## Local Run

### Runtime Configuration

| Variable | Purpose | Current behavior |
|---|---|---|
| `YOLO_MODEL_PATH` | Selects YOLO model weights | Current local model path is `models/yolo11s_indian_food_best.pt`; code default is `models/yolo11s_indian.pt` |
| `RATE_LIMIT_PER_MINUTE` | API rate limit for food analysis | Defaults to 30 |
| `GROQ_API_KEY` | Primary recommendation-provider key | Enables Groq recommendations when present |

### Backend

```bash
cd backend
python main.py
```

Backend URL: `http://localhost:8000`

Useful checks:

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

### Verification Commands

```bash
python scripts/verify_food_classes_with_images.py
python scripts/verify_yolo_class_macros.py
```

## Current Limitations

- Exact portion size is not estimated from image geometry; users adjust serving multipliers manually.
- Five nutrition records rely on supplemental source-backed rows because the available INDB file does not cover every class.
- Some visually similar Indian dishes still require deeper per-class detector error analysis.
- Known annotation issues should be cleaned before the next training cycle.
- End-to-end latency should be measured in the full local application, not only model inference.

## Completion Summary

- [x] Merged 72-class Indian-food YOLO dataset created.
- [x] Dataset split into train, validation, and held-out test sets.
- [x] YOLO11s detector trained and evaluated.
- [x] SQLite nutrition database integrated.
- [x] Detector-to-nutrition mapping implemented.
- [x] All 72 expanded dataset classes mapped to nutrition records.
- [x] FastAPI backend implemented.
- [x] Next.js frontend implemented.
- [x] Detection overlays implemented.
- [x] Serving adjustment implemented.
- [x] Daily calorie and macro tracking implemented.
- [x] Health-condition-aware macro adjustment implemented.
- [x] Personalized recommendation generation implemented.
- [x] Validation scripts and verification artifacts created.

## Final Project Description

The completed system demonstrates a full AI-assisted nutrition workflow for Indian food. It connects computer vision, label normalization, nutrition lookup, personalized macro calculation, and AI-backed dietary guidance in one usable web application. The backend exposes structured APIs for image analysis and recommendations, while the frontend lets users upload food images, inspect detections, adjust servings, track macro impact, and receive nutrition-aware suggestions.
