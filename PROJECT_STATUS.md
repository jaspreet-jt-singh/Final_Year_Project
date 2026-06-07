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
| Nutrition database | SQLite nutrition database with food records, macro values, and source metadata |
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

| # | Source dataset | Listed classes | Total images |
|---|---|---:|---:|
| 1 | `Indian food detection.v1i.yolov11` | 17 | 9,053 |
| 2 | `indian food.v6i.yolov11` | 29 | 8,406 |
| 3 | `Indian_food.v2-indianfood-7.yolov11` | 7 | 1,949 |
| 4 | `indianfoodnet_yolo` | 30 | 13,036 |
| 5 | `south indian food detection.v19i.yolov11` | 31 | 8,353 |
| Total | Combined source pool | 114+ raw labels with overlap | 40,797 |

The raw label count is higher than the final class count because multiple datasets used different spellings or regional names for the same food. Examples include `AlooGobi`, `aloo gobhi`, and `aloo_gobi`; `Idli` and `idly`; `WhiteRice`, `rice`, and `satham`.

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

### Final Detector Metrics

| Split | Images | Instances | Precision | Recall | mAP@50 | mAP@50:95 |
|---|---:|---:|---:|---:|---:|---:|
| Validation | 5,922 | 8,812 | 0.847 | 0.807 | 0.830 | 0.692 |
| Held-out test | 5,919 | 8,875 | 0.842 | 0.801 | 0.820 | 0.680 |

The small gap between validation and held-out test performance indicates that the detector generalizes beyond the validation split, although visually similar dishes and lower-data classes still need deeper per-class error analysis.

## Backend

Backend framework: FastAPI  
Main runtime service areas: vision, nutrition, goals, health profiles, and recommendations

### Implemented API Behavior

| Capability | Implementation |
|---|---|
| Health check | Confirms service availability |
| Food analysis | Accepts image uploads and returns detections, bounding boxes, confidence scores, and nutrition values |
| Nutrition lookup | Resolves food labels to database rows and macro values |
| Nutrition validation | Checks detector-class coverage against nutrition mappings |
| Goal metadata | Provides supported dietary goals |
| Health profile metadata | Provides supported health-condition options |
| Macro calculation | Calculates daily macro targets from calories, goal, and health profile |
| Recommendations | Generates three practical dietary suggestions from detected foods and user context |

### Vision Service

The vision service:

- Loads YOLO weights from `YOLO_MODEL_PATH`.
- Validates that the model file exists before startup completes.
- Accepts raw uploaded image bytes.
- Converts images to RGB.
- Runs YOLO inference at image size 640.
- Uses confidence and IoU thresholds for detection filtering.
- Returns class labels, display names, confidence values, and bounding boxes.
- Handles no-food states with an empty detection list.

### Nutrition Service

The nutrition service:

- Loads food records from SQLite.
- Normalizes detector labels and database names.
- Uses aliases and audited mappings for regional or spelling variants.
- Avoids unsafe substitutions when a confident mapping is unavailable.
- Returns calories, protein, carbohydrates, and fat with source metadata.

## Nutrition and Personalization

The project supports four dietary goals:

| Goal | Intended macro emphasis |
|---|---|
| Weight Loss | Lower calories, higher protein emphasis |
| Muscle Gain | Higher protein with balanced carbohydrates and fats |
| Maintenance | Balanced macro distribution |
| Endurance | Higher carbohydrate emphasis |

Health profiles adjust macro percentages before gram targets are calculated:

| Health profile | Implemented adjustment focus |
|---|---|
| None | Uses the selected goal's base macro split |
| Diabetic | Reduces carbohydrate share and increases protein share |
| Hypertension | Pairs recommendations with lower-sodium guidance |
| Heart Disease | Reduces fat emphasis |
| High Cholesterol | Reduces fat and emphasizes fiber/plant-protein guidance |
| Digestive Issues | Reduces heavy fat/protein load and favors easier digestion |
| Kidney Disease | Reduces protein share |
| Anemia | Adds iron-supportive recommendation guidance |
| Thyroid Disorder | Slightly increases protein emphasis and adds thyroid-aware guidance |

Macro grams are calculated from calorie targets using:

| Macro | Calories per gram |
|---|---:|
| Carbohydrates | 4 kcal/g |
| Protein | 4 kcal/g |
| Fat | 9 kcal/g |

## Recommendation Engine

The recommendation service uses Groq to generate concise dietary suggestions.

| Item | Value |
|---|---|
| Provider | Groq |
| Model | `llama-3.1-8b-instant` |
| Environment key | `GROQ_API_KEY` |
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

## Validation

The project includes validation coverage for:

| Validation area | Purpose |
|---|---|
| Dataset build | Confirms generated dataset structure, split files, labels, and class counts |
| Dataset visual checks | Confirms that each class has real image samples |
| Nutrition database | Confirms required nutrition fields and database records |
| Mapping logic | Confirms detector labels resolve to intended nutrition rows |
| Backend services | Confirms service imports, API routes, model path handling, and nutrition lookup |
| Frontend integration | Confirms expected frontend components and API response fields |
| Live API checks | Validate running backend endpoints when the server is active |

## Local Run

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

## Current Limitations

- Exact portion size is not estimated from image geometry; users adjust serving multipliers manually.
- A small number of nutrition records rely on supplemental source-backed rows because the available INDB file does not cover every class.
- Some visually similar Indian dishes still require deeper per-class detector error analysis.
- Known annotation issues should be cleaned before the next training cycle.
- End-to-end latency should be measured in the full local application, not only model inference.

## Completion Summary

- [x] Merged 72-class Indian-food YOLO dataset created.
- [x] Dataset split into train, validation, and held-out test sets.
- [x] YOLO11s detector trained and evaluated.
- [x] SQLite nutrition database integrated.
- [x] Detector-to-nutrition mapping implemented.
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
