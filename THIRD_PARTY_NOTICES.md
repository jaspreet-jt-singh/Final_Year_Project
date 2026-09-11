# Asset provenance and unresolved permissions

Reviewed 2026-09-12. This is an evidence inventory, not a legal determination or license grant. No datasets, checkpoint files, database records or dietary rules were changed by the publication audit.

## Image sources

The local exports identify these source versions and declare CC BY 4.0 in their YAML/README metadata:

| Local export | Declared source |
| --- | --- |
| Indian food detection.v1i.yolov11 | [project-z0tql / indian-food-detection-kzw9g, v1](https://universe.roboflow.com/project-z0tql/indian-food-detection-kzw9g/dataset/1) |
| indian food.v6i.yolov11 | [microplastics-vypxl / indian-food-txofy, v6](https://universe.roboflow.com/microplastics-vypxl/indian-food-txofy/dataset/6) |
| Indian_food.v2-indianfood-7.yolov11 | [indianfood / indian_food-pwzlc, v2](https://universe.roboflow.com/indianfood/indian_food-pwzlc/dataset/2) |
| indianfoodnet_yolo | [indianfoodnet / indianfoodnet, v1](https://universe.roboflow.com/indianfoodnet/indianfoodnet/dataset/1) |
| south indian food detection.v19i.yolov11 | [bharani-1ucid / south-indian-food-detection, v19](https://universe.roboflow.com/bharani-1ucid/south-indian-food-detection/dataset/19) |

These URLs were recovered from local export metadata; they are not proof of rights to every original image. In particular, IndianFood-7 and IndianFoodNet README files also state that some crawled copyrighted material lacks express owner authorization and describe research/academic use. That qualification must not be erased by treating the export's license label as blanket clearance. Preserve contributor attribution and have the owners/supervisors resolve downstream dataset, figure and checkpoint redistribution before a public research-asset release. Do not add the source datasets to `vercel-live`.

Several exports already contain augmented variants: the first, second and IndianFood-7 exports document three variants per source. Training-only augmentation performed by this repository does not prove the validation/test export contains only unique originals.

## Nutrition

The database imports `data/INDB.xlsx` and includes five supplemental records. The local workbook is now verified **byte-identical** to `INDB.xlsx` in the [original authors' repository at commit fbdb62b](https://github.com/lindsayjaacks/Indian-Nutrient-Databank-INDB-/blob/fbdb62bec519c6e2468582a799fb47e194b42558/INDB.xlsx). Both files have SHA-256 `65f91911de09ebdb4b80c4a3dc3ff372a35420e05444239d8df8a42e8b5b9ecf` and 1,063,585 bytes. The workbook's internal modification date is November 18, 2024. Reproduce the comparison with `python scripts/verify_nutrition_provenance.py --online`; omit `--online` for the offline CI fingerprint check. [Machine-readable evidence](research/evidence/nutrition-provenance.json) pins the source artifact.

The authors' [2024 article](https://pmc.ncbi.nlm.nih.gov/articles/PMC11277795/) explicitly identifies that repository as its data/code source. Its [2025 correction](https://pmc.ncbi.nlm.nih.gov/articles/PMC12147835/) corrects attribution to the original IFCT publications. This resolves artifact identity, not every reuse permission: the article declares CC BY 4.0, but the inspected repository has no blanket LICENSE and directs readers to the original sources for IFCT inputs. Confirm applicable derived-database and redistribution terms with the owners/supervisors; do not infer them solely from a public download or from the article's license.

Supplemental sources are recorded in the database and `backend/scripts/merge_db.py`: FatSecret Evolve Bhakarwadi nutrition label; Clearcals recipe pages for Ghevar, Jalebi, Khandvi and Nandu Kari. A citation/source URL is not blanket permission to reproduce material. Product/recipe records also do not establish equivalence with every photographed preparation.

## Code and model

The application uses third-party packages under their respective licenses. Review the actual locked distributions, including Ultralytics and the pretrained checkpoint's origin, before granting a project-wide redistribution license. The source repository currently has no project-wide LICENSE file. Its authors/supervisors must choose a compatible license; this implementation does not assign one on their behalf.

## Required owner decisions

- Confirm the terms applicable to the now-identified INDB workbook and derived database.
- Confirm rights/attribution for the five image sources, including the crawled-image qualifications, and inherited model obligations.
- Confirm author/institution ownership, code license and which artifacts may be publicly archived.
- Do not publish a merged dataset, relicense third-party assets, or pay fees merely because the website demo works.
