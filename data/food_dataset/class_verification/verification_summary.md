# Food Class Visual Verification

Classes checked: 72
Classes with image samples: 72
Classes without image samples: 0

## Manual Review Notes

Visual inspection of the generated contact sheets found that the class names are broadly aligned with the actual food images across all 72 classes. The dataset has normal sample-level noise, but no class-name list ordering problem was found.

Issues to review:

| File | Finding | Suggested action |
|---|---|---|
| `data/food_dataset/train/images/train27229-jalebi.jpg` | Labeled as `jalebi`, but the image does not visually look like jalebi. | Remove from `jalebi` or relabel from the source annotation if the correct class exists. |
| `data/food_dataset/train/labels/train18550-kaara_chutney.txt` | The `kaara_chutney` box is placed on the vada, while the visible chutney in the cup is not the boxed object. | Correct the bounding box/class assignment or remove that annotation. |
| `data/food_dataset/train/labels/train32747-nandu_masala.txt` | Full image is crab/`nandu_masala`, but the sampled box is extremely thin and produces a blank crop. | Correct the bounding box dimensions. |

Cleared after full-image check:

| File | Review result |
|---|---|
| `data/food_dataset/train/images/train9492-besan_cheela.jpg` | Valid rolled cheela sample. |
| `data/food_dataset/train/images/train34415-pidi_kolukattai.jpg` | Acceptable pidi/kozhukattai-style sample variant. |

## Contact Sheets

- `data/food_dataset/class_verification/class_verification_page_01.jpg`
- `data/food_dataset/class_verification/class_verification_page_02.jpg`
- `data/food_dataset/class_verification/class_verification_page_03.jpg`
- `data/food_dataset/class_verification/class_verification_page_04.jpg`
- `data/food_dataset/class_verification/class_verification_page_05.jpg`
- `data/food_dataset/class_verification/class_verification_page_06.jpg`
- `data/food_dataset/class_verification/class_verification_page_07.jpg`
- `data/food_dataset/class_verification/class_verification_page_08.jpg`

## Sample Counts

| Class ID | Class name | Available images | Displayed samples |
|---:|---|---:|---:|
| 0 | `aloo_gobi` | 798 | 4 |
| 1 | `aloo_masala` | 745 | 4 |
| 2 | `appam` | 511 | 4 |
| 3 | `beetroot_poriyal` | 511 | 4 |
| 4 | `besan_cheela` | 503 | 4 |
| 5 | `bhakarwadi` | 610 | 4 |
| 6 | `bhakri` | 195 | 4 |
| 7 | `bhatura` | 959 | 4 |
| 8 | `bhindi_masala` | 1501 | 4 |
| 9 | `biryani` | 997 | 4 |
| 10 | `carrot_poriyal` | 508 | 4 |
| 11 | `chai` | 643 | 4 |
| 12 | `chicken` | 1252 | 4 |
| 13 | `chicken_65` | 511 | 4 |
| 14 | `chicken_biryani` | 508 | 4 |
| 15 | `chole` | 1107 | 4 |
| 16 | `coconut_chutney` | 1327 | 4 |
| 17 | `dal` | 1371 | 4 |
| 18 | `dhokla` | 1006 | 4 |
| 19 | `dosa` | 1126 | 4 |
| 20 | `dum_aloo` | 654 | 4 |
| 21 | `eggs` | 742 | 4 |
| 22 | `fish_curry` | 655 | 4 |
| 23 | `ghevar` | 571 | 4 |
| 24 | `green_chutney` | 723 | 4 |
| 25 | `gulab_jamun` | 618 | 4 |
| 26 | `idli` | 953 | 4 |
| 27 | `jalebi` | 1246 | 4 |
| 28 | `kaara_chutney` | 131 | 4 |
| 29 | `kali` | 507 | 4 |
| 30 | `kebab` | 391 | 4 |
| 31 | `khandvi` | 640 | 4 |
| 32 | `kheer` | 625 | 4 |
| 33 | `koozh` | 511 | 4 |
| 34 | `kulfi` | 642 | 4 |
| 35 | `lassi` | 632 | 4 |
| 36 | `lemon_rice` | 510 | 4 |
| 37 | `medu_vada` | 509 | 4 |
| 38 | `modak` | 292 | 4 |
| 39 | `mushroom_biryani` | 510 | 4 |
| 40 | `mutton_biryani` | 464 | 4 |
| 41 | `mutton_curry` | 634 | 4 |
| 42 | `nandu_masala` | 510 | 4 |
| 43 | `nei_satham` | 510 | 4 |
| 44 | `omelette` | 514 | 4 |
| 45 | `onion_pakoda` | 576 | 4 |
| 46 | `paal_kolukattai` | 510 | 4 |
| 47 | `palak_paneer` | 1427 | 4 |
| 48 | `paneer_biryani` | 510 | 4 |
| 49 | `paratha` | 324 | 4 |
| 50 | `parupu_vadai` | 488 | 4 |
| 51 | `pidi_kolukattai` | 508 | 4 |
| 52 | `poha` | 1498 | 4 |
| 53 | `poorna_kolukattai` | 508 | 4 |
| 54 | `prawn_thokku` | 510 | 4 |
| 55 | `puri` | 573 | 4 |
| 56 | `raita` | 498 | 4 |
| 57 | `rajma_curry` | 1423 | 4 |
| 58 | `ras_malai` | 627 | 4 |
| 59 | `rice` | 1251 | 4 |
| 60 | `roti` | 832 | 4 |
| 61 | `saag` | 750 | 4 |
| 62 | `salad` | 59 | 4 |
| 63 | `sambar` | 68 | 4 |
| 64 | `sambar_satham` | 510 | 4 |
| 65 | `samosa` | 652 | 4 |
| 66 | `shahi_paneer` | 1250 | 4 |
| 67 | `thepla` | 362 | 4 |
| 68 | `upma` | 344 | 4 |
| 69 | `veg_briyani` | 510 | 4 |
| 70 | `veg_pulao` | 358 | 4 |
| 71 | `ven_pongal` | 384 | 4 |
