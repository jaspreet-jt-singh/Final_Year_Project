# Project Status - AI-Based Food Recognition with Nutrition-Aware Recommendations

Document date: 2026-06-06  
Project type: Final year full-stack AI application  
Implementation status: Local full-stack prototype implemented

## Executive Summary

This project implements an AI-based food recognition system focused on Indian food items. The application accepts a food image, detects visible food items with a YOLO object detection model, maps detected food labels to nutrition records from the Indian Nutrient Database, calculates calorie and macronutrient values, and generates personalized dietary guidance based on the user's daily goal and health condition.

The repository contains a working FastAPI backend, a Next.js frontend, a SQLite nutrition database, YOLO model weights, a merged 72-class YOLO dataset, an earlier larger 72-class master dataset export, dataset build scripts, validation scripts, screenshots, demo media, final report assets, and presentation assets.

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
| Recommendation engine | Goal-aware and health-condition-aware recommendation service implemented with Groq |
| Frontend application | Next.js 14 app implemented with upload, results, bounding boxes, macro tracking, serving adjustment, and dietary guidance |
| Training notebook | YOLO11s training notebook implemented in `notebooks/train_yolo.ipynb` |
| Report assets | Final report and presentation files included in `docx/` |
| Demo assets | Screenshots and demo video included in `screenshots/` |
| Repository hygiene | `.gitignore` and `.gitattributes` configured for generated data, model weights, line endings, and ignored runtime artifacts |

## Project Inventory

### Root-Level Structure

| Path | Contents |
|---|---|
| `backend/` | FastAPI app, service classes, nutrition database merge script, and utility modules |
| `frontend/` | Next.js application, React components, Tailwind configuration, TypeScript configuration, and package lock |
| `data/` | Raw YOLO datasets, generated merged datasets, INDB spreadsheet, SQLite nutrition database, and dataset zip archives |
| `models/` | YOLO model weights and deployed model class metadata |
| `notebooks/` | YOLO11s training notebook |
| `scripts/` | Dataset merge/build script for the 72-class YOLO dataset |
| `tests/` | Python validation scripts for data, API, nutrition matching, and frontend/backend integration points |
| `screenshots/` | Demo screenshots and `Project Demo.mp4` |
| `docx/` | Final report, presentation PDFs, and PPTX files |
| `requirements.txt` | Python dependency list |
| `PROJECT_STATUS.md` | Detailed implementation report |
| `.env` | Local runtime environment values; secrets are not documented verbatim |
| `.gitignore` | Ignores environment files, model binaries, generated datasets, screenshots, tests, logs, and frontend build outputs |
| `.gitattributes` | Enforces LF line endings for source, markdown, JSON, notebooks, and environment files |

### Tracked and Ignored Asset Policy

The project intentionally keeps several large or local artifacts outside normal git tracking:

| Ignored pattern | Reason |
|---|---|
| `.env`, `.env.local` | Local secrets and environment configuration |
| `models/*.pt`, `models/*.pth`, `models/*.onnx` | Large model binaries |
| `data/*.db` | Generated SQLite database |
| Raw dataset folders under `data/` | Large downloaded datasets |
| `data/*/train`, `data/*/valid`, `data/*/test` | Large generated split directories |
| `data/*.zip` | Dataset archive exports |
| `frontend/.next/`, `frontend/node_modules/` | Frontend build and dependency outputs |
| `tests/`, `screenshots/`, `presentations` | Local validation/demo artifacts |

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
  -> RecommendationService Groq dietary guidance
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
| 4 | `indianfoodnet_yolo` | 30 | 11,387 | 1,073 | 576 | 13,036 |
| 5 | `south indian food detection.v19i.yolov11` | 31 | 6,478 | 1,294 | 581 | 8,353 |
| Total | Combined sources | 114+ raw labels with overlap | 35,198 | 3,792 | 1,807 | 40,797 |

The raw class count is higher than the final class count because many food names appear in multiple spellings or formats. Examples include `AlooGobi`, `aloo gobhi`, and `aloo_gobi`; `Idli` and `idly`; `WhiteRice`, `rice`, and `satham`.

### Source Dataset Class Lists

These class lists are taken from the current source `data.yaml` files.

| Dataset | Class names |
|---|---|
| `Indian food detection.v1i.yolov11` | `Bhatura`, `BhindiMasala`, `Biryani`, `Chole`, `ShahiPaneer`, `chicken`, `dal`, `dhokla`, `gulab_jamun`, `idli`, `jalebi`, `modak`, `palak_paneer`, `poha`, `rice`, `roti`, `samosa` |
| `indian food.v6i.yolov11` | `aloo gobhi`, `aloo sabji`, `bhakarwadi`, `bhakri`, `bhindi`, `chole`, `coconut chutney`, `daal`, `dosa`, `eggs`, `idli`, `khandvi`, `medu vada`, `omelette`, `paratha`, `poha`, `puri`, `rajma`, `rice`, `roti phulka`, `saag`, `salad`, `sambhar`, `thepla`, `upma`, `varan`, `veg-pulao`, `yellow dhokla`, `yogurt` |
| `Indian_food.v2-indianfood-7.yolov11` | `besan_cheela`, `dosa`, `gulab_jamun`, `idli`, `palak_paneer`, `poha`, `samosa` |
| `indianfoodnet_yolo` | `AlooGobi`, `AlooMasala`, `Bhatura`, `BhindiMasala`, `Biryani`, `Chai`, `Chole`, `CoconutChutney`, `Dal`, `Dosa`, `DumAloo`, `FishCurry`, `Ghevar`, `GreenChutney`, `GulabJamun`, `Idli`, `Jalebi`, `Kebab`, `Kheer`, `Kulfi`, `Lassi`, `MuttonCurry`, `OnionPakoda`, `PalakPaneer`, `Poha`, `RajmaCurry`, `RasMalai`, `Samosa`, `ShahiPaneer`, `WhiteRice` |
| `south indian food detection.v19i.yolov11` | `appam`, `beetroot poriyal`, `boiled egg`, `carrot poriyal`, `chicken 65`, `chicken briyani`, `dosa`, `idly`, `kaara chutney`, `kali`, `koozh`, `lemon satham`, `medu vadai`, `mushroom briyani`, `mutton briyani`, `nandu masala`, `nei satham`, `paal kolukattai`, `paneer briyani`, `paneer masala`, `parupu vadai`, `pidi kolukattai`, `poorna kolukattai`, `prawn thokku`, `puthina chutney`, `sambar`, `sambar satham`, `satham`, `thengai chutney`, `veg briyani`, `ven pongal` |

### Source Dataset Metadata

| Dataset | Metadata files present | License/source metadata |
|---|---|---|
| `Indian food detection.v1i.yolov11` | `data.yaml`, `README.dataset.txt`, `README.roboflow.txt` | Roboflow metadata, CC BY 4.0 |
| `indian food.v6i.yolov11` | `data.yaml`, `README.dataset.txt`, `README.roboflow.txt` | Roboflow metadata, CC BY 4.0 |
| `Indian_food.v2-indianfood-7.yolov11` | `data.yaml`, `README.dataset.txt`, `README.roboflow.txt` | Roboflow metadata, CC BY 4.0 |
| `indianfoodnet_yolo` | `data.yaml`, `README.dataset.txt`, `README.roboflow.txt` | Roboflow metadata, CC BY 4.0 |
| `south indian food detection.v19i.yolov11` | `data.yaml`, `README.dataset.txt`, `README.roboflow.txt` | Roboflow metadata, CC BY 4.0 |

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

### Generated and Archived Data Assets

| Asset | Description |
|---|---|
| `data/food_dataset/` | Current balanced 72-class YOLO dataset generated by `scripts/build_master_dataset.py` |
| `data/food_dataset.zip` | Archive of the current generated food dataset |
| `data/master_dataset/` | Earlier larger 72-class generated dataset export with aggressive annotation-target augmentation |
| `data/master_dataset.zip` | Archive of the larger master dataset export |
| `data/INDB.xlsx` | Source nutrition spreadsheet used to build the SQLite nutrition database |
| `data/nutrition.db` | Runtime SQLite nutrition database used by `NutritionService` |
| Source dataset folders under `data/` | Original downloaded YOLO datasets used by the merge process |

### Secondary Master Dataset Export

The repository also contains `data/master_dataset/`, a heavier generated export that uses the same 72 canonical class names but applies much larger train augmentation than `data/food_dataset/`.

| Property | Value |
|---|---:|
| Canonical classes | 72 |
| Train images | 135,685 |
| Train labels | 135,685 |
| Validation images | 5,922 |
| Validation labels | 5,922 |
| Test images | 5,919 |
| Test labels | 5,919 |
| Total exported image-label pairs | 147,526 |
| Train augmentation target | 2,426 annotations per class |
| Validation augmentation | None |
| Test augmentation | None |

This larger export is documented as a retained dataset artifact. The current status report uses `data/food_dataset/` as the balanced merged dataset because it has more conservative train augmentation.

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

### Visual Class Verification

Visual verification artifacts were generated from actual dataset images with `scripts/verify_food_classes_with_images.py`.

| Artifact | Purpose |
|---|---|
| `data/food_dataset/class_verification/class_verification_page_01.jpg` to `class_verification_page_08.jpg` | Contact sheets showing four real image crops per class |
| `data/food_dataset/class_verification/verification_samples.csv` | Exact image and label paths used for each displayed sample |
| `data/food_dataset/class_verification/verification_summary.md` | Visual review notes and per-class sample counts |

Verification result: all 72 classes have real image samples, and the class-name list is visually aligned with the dataset. Three sample-level annotation issues were found for later cleanup:

| File | Finding |
|---|---|
| `data/food_dataset/train/images/train27229-jalebi.jpg` | Labeled as `jalebi`, but the image does not visually look like jalebi |
| `data/food_dataset/train/labels/train18550-kaara_chutney.txt` | `kaara_chutney` box is placed on the vada instead of the visible chutney |
| `data/food_dataset/train/labels/train32747-nandu_masala.txt` | Full image is crab, but the bounding box is extremely thin and produces a blank crop |

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
| `models/yolov8n_indian.pt` | Additional YOLOv8n model weight file retained in the project |
| `models/class_names.json` | Class-name metadata for the deployed model package; currently 31 labels |
| `notebooks/train_yolo.ipynb` | Training notebook for YOLO experimentation |

### Runtime Model Scope

The runtime backend loads `models/yolo11s_indian.pt` by default through the `YOLO_MODEL_PATH` environment variable. The metadata file `models/class_names.json` currently lists 31 class labels for the deployed model package. The 72-class dataset in `data/food_dataset/` is the implemented expanded dataset asset and is available as the training corpus for broader class coverage.

### Deployed Model Class Metadata

`models/class_names.json` currently contains these 31 labels:

`AlooGobi`, `AlooMasala`, `Bhatura`, `BhindiMasala`, `Biryani`, `Chai`, `Chole`, `CoconutChutney`, `Dal`, `Dosa`, `DumAloo`, `FishCurry`, `Ghevar`, `GreenChutney`, `GulabJamun`, `Idli`, `Jalebi`, `Kebab`, `Kheer`, `Kulfi`, `Lassi`, `MuttonCurry`, `OnionPakoda`, `PalakPaneer`, `Poha`, `RajmaCurry`, `RasMalai`, `Samosa`, `ShahiPaneer`, `VadaPav`, `WhiteRice`.

### YOLO Training Notebook

Notebook: `notebooks/train_yolo.ipynb`

Implemented training workflow:

1. Detects runtime environment for Kaggle, Colab, or local execution.
2. Locates the attached YOLO dataset `data.yaml`.
3. Uses YOLO11s as the training model.
4. Configures hardware-aware batch/workers:
   - Local RTX 3050 4GB target: batch 4, AMP enabled, workers 2.
   - Kaggle P100/T4 style target: batch 16, workers 4.
5. Trains an Ultralytics detection model with:
   - `epochs=100`
   - `imgsz=640`
   - `patience=20`
   - `amp=True`
   - `project=models/runs`
   - `name=yolo11s_indian`
6. Saves the best model as `models/yolo11s_indian.pt`.
7. Saves class names to `models/class_names.json`.
8. Includes training-curve plotting logic for `models/training_curves_yolo11s.png`.

Notebook output indicates the YOLO11s run trained for 91 epochs, stopped early after no improvement for 20 epochs, and selected epoch 71 as the best model checkpoint.

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

The current nutrition database contains 1,010 food records in `indb_foods` and 103 precomputed mappings in `yolo_mappings`. The food table is built from `data/INDB.xlsx` and five verified supplemental nutrition rows for dataset classes that are not present in INDB. The mapping table covers the expanded 72-class `data/food_dataset/` class list first, then appends legacy deployed-model class labels from `models/class_names.json` for backward compatibility.

| Table | Current purpose | Current count |
|---|---|---:|
| `indb_foods` | Nutrition records imported from INDB plus verified supplemental rows | 1,010 rows |
| `yolo_mappings` | Precomputed YOLO class to database food-name mappings | 103 rows |
| `sqlite_sequence` | SQLite internal autoincrement metadata | Internal |

The `indb_foods` table contains the core columns used by the application:

| Column | Meaning |
|---|---|
| `id` | SQLite autoincrement primary key |
| `name` | Food display name from the database |
| `normalized_name` | Search-friendly normalized name |
| `calories` | Calories per 100g |
| `protein_g` | Protein in grams per 100g |
| `carbs_g` | Carbohydrates in grams per 100g |
| `fat_g` | Fat in grams per 100g |
| `source` | Source label for the nutrition row, such as INDB or a verified supplemental source |
| `source_url` | Source URL for supplemental rows; blank for INDB imports |
| `source_notes` | Short provenance note for the row |

The `yolo_mappings` table contains:

| Column | Meaning |
|---|---|
| `yolo_class` | YOLO class name from the expanded dataset or legacy model metadata |
| `matched_food_name` | Matched database food record name |
| `match_score` | Mapping confidence score; `1.00` means a direct semantic match, lower values are nearest available INDB substitutes |

### Nutrition Database Build Script

Main file: `backend/scripts/merge_db.py`

Implemented behavior:

1. Reads `data/INDB.xlsx` from the `Nutrient Data` sheet.
2. Requires `food_name`, `energy_kcal`, `protein_g`, `carb_g`, and `fat_g`.
3. Renames columns into the runtime schema:
   - `food_name` -> `name`
   - `energy_kcal` -> `calories`
   - `carb_g` -> `carbs_g`
4. Adds `normalized_name` with `normalize_food_name()`.
5. Removes duplicate rows by normalized food name.
6. Converts nutrition fields to numeric values.
7. Drops rows missing calories, protein, carbs, or fat.
8. Adds source metadata for INDB imports.
9. Adds verified supplemental nutrition rows for `bhakarwadi`, `ghevar`, `jalebi`, `khandvi`, and `nandu_masala`.
10. Rebuilds `data/nutrition.db`.
11. Creates `indb_foods` with a `normalized_name` index and source metadata columns.
12. Loads expanded YOLO class names from `data/food_dataset/data.yaml`.
13. Appends legacy deployed YOLO class names from `models/class_names.json` when present.
14. Applies explicit class-to-database mappings before fuzzy matching to avoid semantically wrong matches.
15. Uses fuzzy matching only when the score is at least `0.78`.
16. Creates `yolo_mappings` with the selected database food name and mapping score.
17. Prints mapping coverage, unmapped classes, nutrition statistics, and YOLO-relevant food examples during execution.

### Precomputed YOLO-to-Database Mappings

The current `data/food_dataset/` class coverage is 72 mapped classes out of 72. The five classes that were missing from INDB now map to verified supplemental database rows. Values below are per 100g; recipe and brand variation still apply.

| Dataset class | Supplemental database row | Calories | Protein (g) | Carbs (g) | Fat (g) | Source |
|---|---|---:|---:|---:|---:|---|
| `bhakarwadi` | `Bhakarwadi` | 510.0 | 10.76 | 57.03 | 26.55 | FatSecret Evolve Bhakarwadi nutrition label, `https://www.fatsecret.co.in/calories-nutrition/evolve/bhakarwadi/100g` |
| `ghevar` | `Ghevar` | 351.2 | 3.5 | 39.6 | 19.9 | Clearcals Ghevar recipe nutrition, `https://clearcals.com/recipes/ghevar/` |
| `jalebi` | `Jalebi` | 316.8 | 3.4 | 44.6 | 13.8 | Clearcals Jalebi recipe nutrition, `https://clearcals.com/recipes/jalebi/` |
| `khandvi` | `Khandvi` | 232.7 | 9.3 | 21.7 | 12.1 | Clearcals Khandvi recipe nutrition, `https://clearcals.com/recipes/khandvi/` |
| `nandu_masala` | `Nandu Kari (Crab masala)` | 128.1 | 7.0 | 7.0 | 8.0 | Clearcals Nandu Kari recipe nutrition, `https://clearcals.com/recipes/nandu-kari/` |

| Dataset class | Matched database food name | Score |
|---|---|---:|
| `aloo_gobi` | `Potato cauliflower (Aloo gobhi)` | 1.00 |
| `aloo_masala` | `Potato curry (Aloo ki sabzi)` | 0.90 |
| `appam` | `Appam` | 1.00 |
| `beetroot_poriyal` | `Vegetables stir fry` | 0.75 |
| `besan_cheela` | `Gram flour chilla/cheela (Besan chilla/cheela)` | 1.00 |
| `bhakarwadi` | `Bhakarwadi` | 1.00 |
| `bhakri` | `Chapati/Roti` | 0.80 |
| `bhatura` | `Bhatura` | 1.00 |
| `bhindi_masala` | `Okra/Lady's fingers fry (Bhindi sabzi/sabji/subji)` | 0.95 |
| `biryani` | `Vegetable biryani/biriyani` | 0.85 |
| `carrot_poriyal` | `Carrot and cabbage with coconut (Nariyal ke saath pattagobhi aur gajar)` | 0.85 |
| `chai` | `Hot tea (Garam Chai)` | 1.00 |
| `chicken` | `Chicken curry` | 0.85 |
| `chicken_65` | `Chilli chicken` | 0.80 |
| `chicken_biryani` | `Chicken pulao` | 0.80 |
| `chole` | `Chickpeas curry (Safed channa curry)` | 1.00 |
| `coconut_chutney` | `Coconut chutney (Nariyal ki chutney)` | 1.00 |
| `dal` | `Mixed dal` | 0.90 |
| `dhokla` | `Dhokla` | 1.00 |
| `dosa` | `Plain dosa` | 0.95 |
| `dum_aloo` | `Dum aloo` | 1.00 |
| `eggs` | `Boiled egg (Ubla anda)` | 0.95 |
| `fish_curry` | `Fish curry (Machli curry)` | 1.00 |
| `ghevar` | `Ghevar` | 1.00 |
| `green_chutney` | `Green chutney` | 1.00 |
| `gulab_jamun` | `Gulab Jamun with khoya` | 1.00 |
| `idli` | `Idli` | 1.00 |
| `jalebi` | `Jalebi` | 1.00 |
| `kaara_chutney` | `Tomato chutney (Tamatar ki chutney)` | 0.85 |
| `kali` | `Maize porridge` | 0.70 |
| `kebab` | `Boti kebab` | 0.90 |
| `khandvi` | `Khandvi` | 1.00 |
| `kheer` | `Rice kheer (Chawal ki kheer)` | 1.00 |
| `koozh` | `Maize porridge` | 0.70 |
| `kulfi` | `Kulfi` | 1.00 |
| `lassi` | `Sweet Lassi (Meethi lassi)` | 0.95 |
| `lemon_rice` | `Lemon rice (Pulihora, Elumichai sadam, Chitranna)` | 1.00 |
| `medu_vada` | `Plain urad dal vada (Uzunne vada/Minapa garelu/Ulundu vadai/Medu vada)` | 1.00 |
| `modak` | `Semolina ladoo with coconut (Suji/Rava aur nariyal ke ladoo )` | 0.70 |
| `mushroom_biryani` | `Mushroom pulao` | 0.80 |
| `mutton_biryani` | `Mutton biryani/biriyani` | 1.00 |
| `mutton_curry` | `Mutton korma` | 0.85 |
| `nandu_masala` | `Nandu Kari (Crab masala)` | 1.00 |
| `nei_satham` | `Plain pulao` | 0.80 |
| `omelette` | `Plain omelette/omlet` | 1.00 |
| `onion_pakoda` | `Onion pakora/pakoda (Pyaaz ke pakode)` | 1.00 |
| `paal_kolukattai` | `Rice kheer (Chawal ki kheer)` | 0.75 |
| `palak_paneer` | `Spinach paneer (Palak paneer)` | 1.00 |
| `paneer_biryani` | `Paneer pulao` | 0.80 |
| `paratha` | `Plain parantha/paratha` | 0.95 |
| `parupu_vadai` | `Fermented bengal gram vada (Khameerikrit/Ufna hua channa dal ka vada)` | 0.90 |
| `pidi_kolukattai` | `Rice puttu (Ari puttu)` | 0.75 |
| `poha` | `Poha` | 1.00 |
| `poorna_kolukattai` | `Semolina ladoo with coconut (Suji/Rava aur nariyal ke ladoo )` | 0.70 |
| `prawn_thokku` | `Prawn curry (with coconut) (Jhinga curry)` | 0.85 |
| `puri` | `Poori` | 1.00 |
| `raita` | `Cucumber raita (Kheere ka raita)` | 0.90 |
| `rajma_curry` | `Kidney bean curry (Rajmah curry)` | 1.00 |
| `ras_malai` | `Rasmalai` | 1.00 |
| `rice` | `Boiled rice (Uble chawal)` | 1.00 |
| `roti` | `Chapati/Roti` | 1.00 |
| `saag` | `Sarson ka saag` | 1.00 |
| `salad` | `Tossed salad` | 0.90 |
| `sambar` | `Sambar` | 1.00 |
| `sambar_satham` | `Vegetable khichdi/khichri` | 0.80 |
| `samosa` | `Potato samosa (Aloo ka samosa)` | 1.00 |
| `shahi_paneer` | `Shahi paneer` | 1.00 |
| `thepla` | `Methi thepla` | 0.95 |
| `upma` | `Semolina upma (Suji/Rava upma)` | 0.95 |
| `veg_briyani` | `Vegetable biryani/biriyani` | 1.00 |
| `veg_pulao` | `Mixed vegetable pulao` | 1.00 |
| `ven_pongal` | `Plain khitchdi (Plain khichri/khichdi)` | 0.75 |

### YOLO Class Macro Verification

Macro verification artifacts were generated with `scripts/verify_yolo_class_macros.py`.

| Artifact | Purpose |
|---|---|
| `data/nutrition_verification/yolo_class_macro_verification.md` | Human-readable class-by-class macro verification table |
| `data/nutrition_verification/yolo_class_macro_verification.csv` | Machine-readable class-by-class macro verification table |

Verification result:

| Metric | Result |
|---|---:|
| YOLO dataset classes checked | 72 |
| Classes with a database mapping | 72 |
| Classes with calories, protein, carbs, and fat present | 72 |
| Failed macro rows | 0 |
| Direct or high-confidence verified mappings | 51 |
| Substitute mappings requiring review | 21 |

The 21 review mappings have complete macro data, but the mapped database row is a substitute or lower-confidence semantic approximation rather than an exact dish entry. The verification report also includes calculated macro calories and calorie-minus-macro-calorie deltas to surface consistency issues. These review rows should be treated as acceptable prototype estimates, not final clinical-grade values.

Review-list classes: `beetroot_poriyal`, `bhakri`, `biryani`, `carrot_poriyal`, `chicken`, `chicken_65`, `chicken_biryani`, `kaara_chutney`, `kali`, `koozh`, `modak`, `mushroom_biryani`, `mutton_curry`, `nei_satham`, `paal_kolukattai`, `paneer_biryani`, `pidi_kolukattai`, `poorna_kolukattai`, `prawn_thokku`, `sambar_satham`, and `ven_pongal`.

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
10. Return calories, protein, carbohydrates, fat, and nutrition source metadata per 100g.

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

### Backend Startup Sequence

At application startup, `backend/main.py` initializes services in this order:

1. Loads environment variables through `python-dotenv`.
2. Creates `NutritionService`.
3. Connects to `data/nutrition.db`.
4. Caches INDB food names and normalized names.
5. Loads `yolo_mappings` if available.
6. Creates `VisionService`.
7. Loads the configured YOLO model.
8. Warms up the YOLO model with a dummy 640x640 RGB image.
9. Creates `RecommendationService`.
10. Starts serving API requests.

### Backend Request Validation

| Request area | Implemented validation |
|---|---|
| Image content type | Upload must have an image MIME type |
| Empty upload | Empty files are rejected |
| File size | Uploads over 10 MB are rejected |
| Service readiness | `/api/analyze-food` returns 503 if vision or nutrition services are unavailable |
| Macro calories | Target calories must be positive and not above 5,000 |
| Recommendation body | JSON body must contain detected foods and a user goal |
| Rate limit | `/api/analyze-food` uses `RATE_LIMIT_PER_MINUTE`, defaulting to 30 requests per minute |

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

`/api/validate-nutrition` is implemented as a deployed-model validation utility. It checks a hardcoded 30-class deployed validation list and returns total classes, successful matches, success rate, and per-class lookup results.

### Macro Calculation Request Shape

```json
{
  "goal": "Weight Loss",
  "target_calories": 2000,
  "health_condition": "Diabetic"
}
```

### Macro Calculation Response Shape

```json
{
  "goal": "Weight Loss",
  "goal_key": "weight_loss",
  "target_calories": 2000,
  "carbs_g": 165,
  "protein_g": 205,
  "fat_g": 58,
  "carbs_percent": 33,
  "protein_percent": 41,
  "fat_percent": 26,
  "description": "Higher protein, moderate carbs, lower fat for satiety and muscle preservation | Adapted for Diabetic: Focus on low glycemic index foods, manage blood sugar spikes",
  "health_condition": "Diabetic",
  "health_condition_key": "diabetic"
}
```

### Recommendation Request Shape

```json
{
  "detected_foods": [
    {
      "food_label": "Biryani",
      "display_name": "Biryani",
      "confidence": 0.91,
      "macros": {
        "calories": 170,
        "protein_g": 5.2,
        "carbs_g": 25,
        "fat_g": 4.5
      }
    }
  ],
  "user_goal": "Weight Loss",
  "health_condition": "Diabetic"
}
```

### Recommendation Response Shape

```json
{
  "recommendations": [
    "Pair this meal with a fiber-rich salad to slow glucose absorption.",
    "Choose unsweetened curd or roasted chana as a protein-rich snack later.",
    "Keep the next meal lower in refined carbohydrates and include vegetables."
  ],
  "source": "groq",
  "health_condition": "diabetic"
}
```

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
      "nutrition_source": "INDB",
      "nutrition_source_url": null
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

The recommendation and macro engine implements personalized nutrition logic in two parts:

1. A deterministic macro calculator that adjusts carbohydrate, protein, and fat targets according to the selected dietary goal and health profile.
2. A Groq-powered recommendation flow that builds a prompt from detected foods, calories, the user's goal, and the user's health profile.

### Base Dietary Goals

These are the base macro splits before health-profile adjustment.

| Goal | Carbs | Protein | Fat | Purpose |
|---|---:|---:|---:|---|
| Weight Loss | 40% | 35% | 25% | Higher protein and moderate carbohydrates for satiety, calorie control, and muscle preservation |
| Muscle Gain | 40% | 30% | 30% | Balanced carbohydrates, protein, and fat to support training, recovery, and muscle synthesis |
| Maintenance | 50% | 25% | 25% | Balanced everyday intake for maintaining body weight and stable energy |
| Endurance | 55% | 20% | 20% | Higher carbohydrate intake for sustained activity, glycogen support, and longer exercise sessions |

### Macro Calculation Formula

The backend calculates macro targets with this logic:

```text
adjusted_carbs = base_carbs_percent * health_profile_carbs_modifier
adjusted_protein = base_protein_percent * health_profile_protein_modifier
adjusted_fat = base_fat_percent * health_profile_fat_modifier

total_adjusted = adjusted_carbs + adjusted_protein + adjusted_fat

final_carbs_percent = round(adjusted_carbs / total_adjusted * 100)
final_protein_percent = round(adjusted_protein / total_adjusted * 100)
final_fat_percent = 100 - final_carbs_percent - final_protein_percent

carbs_g = round((target_calories * final_carbs_percent / 100) / 4)
protein_g = round((target_calories * final_protein_percent / 100) / 4)
fat_g = round((target_calories * final_fat_percent / 100) / 9)
```

The calculator uses standard calorie conversion values:

| Macro | Calories per gram |
|---|---:|
| Carbohydrates | 4 kcal/g |
| Protein | 4 kcal/g |
| Fat | 9 kcal/g |

### Health Profile Macro Modifiers

Each health profile modifies the base goal split before the percentages are normalized back to 100%.

| Health profile | Carbs modifier | Protein modifier | Fat modifier | Nutrition reason implemented |
|---|---:|---:|---:|---|
| None | 1.00 | 1.00 | 1.00 | Keeps the selected goal's original macro split |
| Diabetic | 0.80 | 1.15 | 1.00 | Reduces carbohydrate share and increases protein share to support blood sugar stability and satiety |
| Hypertension | 1.00 | 1.00 | 0.90 | Slightly reduces fat emphasis and pairs recommendations with low-sodium guidance |
| Heart Disease | 1.05 | 1.00 | 0.80 | Reduces fat share while keeping protein stable and slightly increasing carbohydrate share |
| High Cholesterol | 1.05 | 1.10 | 0.75 | Reduces fat more strongly and increases protein emphasis, with guidance toward fiber and plant proteins |
| Digestive Issues | 1.00 | 0.90 | 0.85 | Reduces protein and fat load slightly to support easier digestion |
| Kidney Disease | 1.15 | 0.60 | 1.00 | Strongly reduces protein share and shifts energy toward carbohydrates and fat |
| Anemia | 1.00 | 1.10 | 0.90 | Increases protein share and slightly lowers fat share, with iron-supportive guidance |
| Thyroid Disorder | 1.00 | 1.05 | 1.00 | Slightly increases protein share while keeping carbohydrates and fat close to the base goal |

### Health Profile Dietary Requirements

| Health profile | Macro requirement | Recommendation focus |
|---|---|---|
| None | Uses the selected goal's base macro split | General balanced eating advice based on detected foods |
| Diabetic | Lower carbohydrate percentage, higher protein percentage | Low-glycemic foods, fiber, protein pairing, avoiding blood sugar spikes |
| Hypertension | Similar carbs/protein, slightly lower fat | Low-sodium choices, avoiding packaged snacks and added salt |
| Heart Disease | Lower fat percentage with stable protein | Heart-friendly cooking methods, lower saturated fat, omega-3 rich foods |
| High Cholesterol | Lowest fat emphasis among common profiles, higher protein | High-fiber foods, plant proteins, reduced saturated/trans fat intake |
| Digestive Issues | Lower fat and slightly lower protein | Easily digestible foods, less oily/spicy food, smaller frequent meals |
| Kidney Disease | Controlled protein requirement | Reduced protein load, potassium-aware choices, careful portioning |
| Anemia | Higher protein support and iron-aware guidance | Iron-rich foods, vitamin C pairing, avoiding tea/coffee near meals |
| Thyroid Disorder | Slightly higher protein requirement | Selenium-rich foods, iodine balance, cooked cruciferous vegetables |

### Weight Loss Macro Targets by Health Profile

Example gram targets use a 2,000 kcal daily target.

| Health profile | Carbs % | Protein % | Fat % | Carbs g/day | Protein g/day | Fat g/day |
|---|---:|---:|---:|---:|---:|---:|
| None | 40 | 35 | 25 | 200 | 175 | 56 |
| Diabetic | 33 | 41 | 26 | 165 | 205 | 58 |
| Hypertension | 41 | 36 | 23 | 205 | 180 | 51 |
| Heart Disease | 43 | 36 | 21 | 215 | 180 | 47 |
| High Cholesterol | 42 | 39 | 19 | 210 | 195 | 42 |
| Digestive Issues | 43 | 34 | 23 | 215 | 170 | 51 |
| Kidney Disease | 50 | 23 | 27 | 250 | 115 | 60 |
| Anemia | 40 | 38 | 22 | 200 | 190 | 49 |
| Thyroid Disorder | 39 | 36 | 25 | 195 | 180 | 56 |

### Muscle Gain Macro Targets by Health Profile

Example gram targets use a 2,000 kcal daily target.

| Health profile | Carbs % | Protein % | Fat % | Carbs g/day | Protein g/day | Fat g/day |
|---|---:|---:|---:|---:|---:|---:|
| None | 40 | 30 | 30 | 200 | 150 | 67 |
| Diabetic | 33 | 36 | 31 | 165 | 180 | 69 |
| Hypertension | 41 | 31 | 28 | 205 | 155 | 62 |
| Heart Disease | 44 | 31 | 25 | 220 | 155 | 56 |
| High Cholesterol | 43 | 34 | 23 | 215 | 170 | 51 |
| Digestive Issues | 43 | 29 | 28 | 215 | 145 | 62 |
| Kidney Disease | 49 | 19 | 32 | 245 | 95 | 71 |
| Anemia | 40 | 33 | 27 | 200 | 165 | 60 |
| Thyroid Disorder | 39 | 31 | 30 | 195 | 155 | 67 |

### Maintenance Macro Targets by Health Profile

Example gram targets use a 2,000 kcal daily target.

| Health profile | Carbs % | Protein % | Fat % | Carbs g/day | Protein g/day | Fat g/day |
|---|---:|---:|---:|---:|---:|---:|
| None | 50 | 25 | 25 | 250 | 125 | 56 |
| Diabetic | 43 | 31 | 26 | 215 | 155 | 58 |
| Hypertension | 51 | 26 | 23 | 255 | 130 | 51 |
| Heart Disease | 54 | 26 | 20 | 270 | 130 | 44 |
| High Cholesterol | 53 | 28 | 19 | 265 | 140 | 42 |
| Digestive Issues | 53 | 24 | 23 | 265 | 120 | 51 |
| Kidney Disease | 59 | 15 | 26 | 295 | 75 | 58 |
| Anemia | 50 | 28 | 22 | 250 | 140 | 49 |
| Thyroid Disorder | 49 | 26 | 25 | 245 | 130 | 56 |

### Endurance Macro Targets by Health Profile

Example gram targets use a 2,000 kcal daily target.

| Health profile | Carbs % | Protein % | Fat % | Carbs g/day | Protein g/day | Fat g/day |
|---|---:|---:|---:|---:|---:|---:|
| None | 55 | 20 | 20 | 275 | 100 | 44 |
| Diabetic | 51 | 26 | 23 | 255 | 130 | 51 |
| Hypertension | 59 | 22 | 19 | 295 | 110 | 42 |
| Heart Disease | 62 | 21 | 17 | 310 | 105 | 38 |
| High Cholesterol | 61 | 23 | 16 | 305 | 115 | 36 |
| Digestive Issues | 61 | 20 | 19 | 305 | 100 | 42 |
| Kidney Disease | 66 | 13 | 21 | 330 | 65 | 47 |
| Anemia | 58 | 23 | 19 | 290 | 115 | 42 |
| Thyroid Disorder | 57 | 22 | 21 | 285 | 110 | 47 |

### Groq Recommendation Integration

The implemented AI recommendation provider documented for the project is Groq.

| Item | Value |
|---|---|
| Provider | Groq |
| Model | `llama-3.1-8b-instant` |
| Environment key | `GROQ_API_KEY` |
| Prompt inputs | Detected foods, calories, selected goal, selected health profile, health-specific dietary guidance |
| Response format | Exactly three practical dietary suggestions |

The recommendation prompt asks Groq to produce realistic food advice compatible with the user's goal and health profile. The response parser extracts bullet-point recommendations and removes preamble text so the frontend can display concise guidance.

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
| `frontend/package.json` | Frontend scripts and dependencies |
| `frontend/package-lock.json` | Locked npm dependency versions |
| `frontend/next.config.js` | Next.js runtime configuration |
| `frontend/tailwind.config.js` | Tailwind content paths, primary color palette, and custom animations |
| `frontend/postcss.config.js` | Tailwind and Autoprefixer PostCSS plugins |
| `frontend/tsconfig.json` | TypeScript strict mode and `@/*` path alias |

### Frontend Configuration

| Config file | Implemented settings |
|---|---|
| `next.config.js` | `reactStrictMode: true`; image domain allows `localhost` |
| `tsconfig.json` | Strict TypeScript enabled, `moduleResolution: bundler`, `jsx: preserve`, `baseUrl: "."`, alias `@/* -> ./*` |
| `tailwind.config.js` | Scans `app/` and `components/`; defines orange `primary` color scale; adds `fade-in` and `slide-up` animations |
| `postcss.config.js` | Enables `tailwindcss` and `autoprefixer` |
| `app/globals.css` | Imports Tailwind layers and defines shared `.btn-primary` and `.card` component utilities |
| `styles/globals.css` | Mirrors shared global Tailwind utilities retained in the project |

### Frontend Package Scripts

| Script | Command | Purpose |
|---|---|---|
| `dev` | `next dev` | Start local development server |
| `build` | `next build` | Build production frontend |
| `start` | `next start` | Serve production build |
| `lint` | `next lint` | Run Next.js linting |

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

### Frontend State and Data Handling

`frontend/app/page.tsx` manages:

| State area | Implemented state |
|---|---|
| Image analysis | `analysis`, `isAnalyzing`, `error`, `imageUrl`, `noFood` |
| Goal setup | `selectedGoal`, `targetCalories`, `macroGoal`, `goalOptions` |
| Health setup | `selectedHealthCondition`, `healthConditionOptions`, `showConditionDetails` |
| Macro tracking | `consumedCalories`, `consumedProtein`, `consumedCarbs`, `consumedFat` |
| UI toggles | `showMacroDetails` |

The frontend uses backend metadata endpoints for goals and health conditions when available. If the metadata endpoints are unavailable, local defaults in `page.tsx` keep the UI usable.

### Component Implementation Details

| Component | Implemented details |
|---|---|
| `ImageUpload` | Tracks drag state, preview URL, and selected `File`; sends the original raw `File` to the parent instead of a canvas blob |
| `ResultsPanel` | Initializes serving multipliers per detection, recalculates totals whenever multipliers change, fetches recommendations after analysis, and displays source/ confidence metadata |
| `NutritionLabel` | Displays four compact metric cards with Lucide icons for calories, protein, carbs, and fat |
| `ImageOverlay` | Loads image dimensions, computes canvas scaling, and draws a bounding box and confidence label on a canvas overlay |

Serving controls in `ResultsPanel` support 0.25x increments, minimum 0.25x, and maximum 10x per detected food item.

### Implemented UI Features

- Sticky calorie status bar.
- Daily calorie remaining counter.
- Color-coded calorie progress bar:
  - Green below 50%
  - Yellow below 80%
  - Orange below 100%
  - Red at or above 100%
- Goal selector with backend fetch and local default values.
- Health condition selector with backend fetch and local default values.
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
| `transformers` | ML/NLP dependency retained in backend requirements |
| `opencv-python-headless` | Image-processing support |
| `pillow` | Image decoding and RGB conversion |
| `numpy`, `pandas`, `openpyxl` | Data processing |
| `sqlalchemy`, `aiosqlite` | Database access |
| `python-dotenv` | Environment variable loading |
| `httpx` | HTTP client dependency |
| `groq` | Groq recommendation provider |
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
| `tests/test_phase0.py` | Checks `data/INDB.xlsx`, `data/nutrition.db`, `indb_foods` schema, absence of old `food_label_map.json`, and `models/` presence |
| `tests/test_phase1.py` | Checks FastAPI service imports, nutrition/vision service files, database structure, model file presence, health endpoint code, analyze endpoint, and rate limiting |
| `tests/test_phase2.py` | Checks frontend `app/` and `components/` structure, `ImageOverlay`, bounding box support, and absence of redundant `frontend/src` |
| `tests/test_integration.py` | Initializes `VisionService` and `NutritionService`, creates synthetic images, checks nutrition lookup, and verifies API/frontend integration points |
| `tests/test_api_live.py` | Live checks against `http://localhost:8000` for health, nutrition validation, and single-food nutrition lookup |
| `tests/check_api_mappings.py` | Loads deployed YOLO classes and prints the actual nutrition display names returned by `NutritionService` |
| `tests/debug_nutrition_lookup.py` | Debugs nutrition lookup results for selected deployed classes |
| `tests/list_food_mappings.py` | Lists YOLO labels, generated search variations, and INDB spreadsheet matches |
| `tests/simple_check.py` | Direct SQLite check for selected foods such as Onion Pakoda, Kheer, Jalebi, Chole, Dal, Bhatura, and Samosa |
| `tests/test_new_matching.py` | Validates normalized matching for selected deployed classes |

The live API test scripts require the backend server to already be running at `http://localhost:8000`.

## Demo, Report, and Presentation Assets

| Asset location | Contents |
|---|---|
| `screenshots/` | 89 screenshot/demo media files, including `Project Demo.mp4`; total media size is about 86.4 MB |
| `docx/final_year_project_report.docx` | Final project report document |
| `docx/AI-Based-Food-Recognition-with-Nutrition-Aware-Recommendations.pdf` | Project presentation PDF |
| `docx/AI-Based-Food-Recognition-with-Nutrition-Aware-Recommendations.pptx` | Project presentation PPTX |
| `docx/Mid-Term_Food_Recognition_Project-Presentation.pdf` | Mid-term project presentation PDF |
| `docx/mid-term-food_recognition_project-presentation.pptx` | Mid-term project presentation PPTX |
| `docx/food_recognition_final.pptx` | Final food-recognition presentation PPTX |
| `docx/test.pdf` | Additional PDF artifact retained in the project |

These assets support demonstration of the implemented application workflow, UI states, final report, and project explanation.

## Completed Implementation Summary

- [x] Indian-food YOLO dataset sources collected in `data/`.
- [x] Merged 72-class canonical dataset generated in `data/food_dataset/`.
- [x] Larger 72-class `data/master_dataset/` export retained as a secondary dataset artifact.
- [x] Dataset archive files retained in `data/`.
- [x] Dataset build artifacts written: `data.yaml`, `build_log.txt`, and per-class CSV.
- [x] YOLO model assets included in `models/`.
- [x] YOLO11s training notebook included in `notebooks/train_yolo.ipynb`.
- [x] INDB spreadsheet imported into SQLite nutrition database.
- [x] Nutrition database rebuild script implemented in `backend/scripts/merge_db.py`.
- [x] Precomputed YOLO-to-database mapping table present in `data/nutrition.db`.
- [x] FastAPI backend implemented.
- [x] YOLO inference service implemented.
- [x] Nutrition lookup service implemented with SQLite.
- [x] Food-name normalization and alias matching implemented.
- [x] Health check, analysis, nutrition validation, macro, goal, health-condition, and recommendation endpoints implemented.
- [x] Groq recommendation integration implemented.
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
- [x] Frontend TypeScript, Tailwind, PostCSS, and Next.js configuration files included.
- [x] Validation scripts included under `tests/`.
- [x] Final report and presentation assets included under `docx/`.
- [x] Demo screenshots and video included under `screenshots/`.

## Final Project Description

The completed system demonstrates a full AI-assisted nutrition workflow for Indian food. It combines computer vision, food-name normalization, nutrition database lookup, personalized macro calculation, and Groq-backed dietary guidance in a single usable web application. The backend exposes a structured API for image analysis and recommendations, while the frontend provides an interactive workflow for users to upload food images, inspect detections, adjust servings, track daily macro impact, and receive nutrition-aware suggestions.
