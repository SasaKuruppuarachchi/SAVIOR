# P7 stage D no-harm check (COCO YOLO26s-seg, person dynamic; main with coco_indoor roles, prior_static_classes chair,suitcase,backpack,handbag,cart); 10 offsets 0.0-1.8 s, rate 0.5

## Median ATE [m] (n runs; [k] = failures, ATE > ~2 % of path)

| seq | openvins | savior_none | yolo_naive | p7_nb |
|---|--:|--:|--:|--:|
| uhumans2_office_s1_06h | 0.3000 (n=10) | 0.3000 (n=10) | 0.2751 (n=10) | 0.2950 (n=10) |
| openloris_cafe1-1 | 0.1730 (n=10) | 0.1730 (n=10) | 0.1690 (n=10) | 0.1763 (n=10) |

### Paired ATE vs openvins (geometric-mean ratio - 1; Holm over seq x method)

| seq | method | n | change [95 % CI] | p | Holm p | wins/losses/identical |
|---|---|--:|---|--:|--:|---|
| uhumans2_office_s1_06h | savior_none | 10 | -0.5 % [-1.5, +0.0] | 0.695 | 1.000 | 5/5/0 |
| uhumans2_office_s1_06h | yolo_naive | 10 | +2.9 % [-18.6, +30.3] | 0.770 | 1.000 | 5/5/0 |
| uhumans2_office_s1_06h | p7_nb | 10 | +12.2 % [-23.4, +58.7] | 0.625 | 1.000 | 5/5/0 |
| openloris_cafe1-1 | savior_none | 10 | +0.0 % [-0.0, +0.0] | 0.375 | 1.000 | 1/3/6 |
| openloris_cafe1-1 | yolo_naive | 10 | -3.0 % [-9.7, +2.5] | 0.625 | 1.000 | 5/5/0 |
| openloris_cafe1-1 | p7_nb | 10 | +0.7 % [-7.0, +9.4] | 0.922 | 1.000 | 5/5/0 |

### Paired ATE vs yolo_naive (geometric-mean ratio - 1; Holm over seq x method)

| seq | method | n | change [95 % CI] | p | Holm p | wins/losses/identical |
|---|---|--:|---|--:|--:|---|
| uhumans2_office_s1_06h | openvins | 10 | -2.8 % [-23.2, +22.8] | 0.770 | 1.000 | 5/5/0 |
| uhumans2_office_s1_06h | savior_none | 10 | -3.3 % [-23.5, +22.3] | 0.695 | 1.000 | 6/4/0 |
| uhumans2_office_s1_06h | p7_nb | 10 | +9.0 % [-18.0, +42.1] | 0.625 | 1.000 | 5/5/0 |
| openloris_cafe1-1 | openvins | 10 | +3.1 % [-2.5, +10.7] | 0.625 | 1.000 | 5/5/0 |
| openloris_cafe1-1 | savior_none | 10 | +3.1 % [-2.5, +10.7] | 0.625 | 1.000 | 5/5/0 |
| openloris_cafe1-1 | p7_nb | 10 | +3.8 % [-4.5, +13.2] | 0.557 | 1.000 | 5/5/0 |

## Median RPE [m] (n runs; [k] = failures, ATE > ~2 % of path)

| seq | openvins | savior_none | yolo_naive | p7_nb |
|---|--:|--:|--:|--:|
| uhumans2_office_s1_06h | 0.1346 (n=10) | 0.1346 (n=10) | 0.1545 (n=10) | 0.1359 (n=10) |
| openloris_cafe1-1 | 0.1730 (n=10) | 0.1730 (n=10) | 0.1729 (n=10) | 0.1759 (n=10) |

### Paired RPE vs openvins (geometric-mean ratio - 1; Holm over seq x method)

| seq | method | n | change [95 % CI] | p | Holm p | wins/losses/identical |
|---|---|--:|---|--:|--:|---|
| uhumans2_office_s1_06h | savior_none | 10 | -0.1 % [-0.2, +0.0] | 0.846 | 1.000 | 5/5/0 |
| uhumans2_office_s1_06h | yolo_naive | 10 | +13.6 % [+2.9, +26.0] | 0.193 | 0.967 | 4/6/0 |
| uhumans2_office_s1_06h | p7_nb | 10 | +3.2 % [-3.6, +10.5] | 0.557 | 1.000 | 5/5/0 |
| openloris_cafe1-1 | savior_none | 10 | +0.0 % [-0.0, +0.0] | 0.875 | 1.000 | 2/2/6 |
| openloris_cafe1-1 | yolo_naive | 10 | -0.3 % [-3.2, +2.0] | 0.492 | 1.000 | 3/7/0 |
| openloris_cafe1-1 | p7_nb | 10 | +1.4 % [-0.1, +2.9] | 0.131 | 0.785 | 3/7/0 |

### Paired RPE vs yolo_naive (geometric-mean ratio - 1; Holm over seq x method)

| seq | method | n | change [95 % CI] | p | Holm p | wins/losses/identical |
|---|---|--:|---|--:|--:|---|
| uhumans2_office_s1_06h | openvins | 10 | -12.0 % [-20.6, -2.8] | 0.193 | 0.961 | 6/4/0 |
| uhumans2_office_s1_06h | savior_none | 10 | -12.0 % [-20.6, -2.8] | 0.160 | 0.961 | 6/4/0 |
| uhumans2_office_s1_06h | p7_nb | 10 | -9.1 % [-18.6, +1.7] | 0.160 | 0.961 | 7/3/0 |
| openloris_cafe1-1 | openvins | 10 | +0.3 % [-1.9, +3.3] | 0.492 | 1.000 | 7/3/0 |
| openloris_cafe1-1 | savior_none | 10 | +0.3 % [-1.9, +3.3] | 0.492 | 1.000 | 7/3/0 |
| openloris_cafe1-1 | p7_nb | 10 | +1.7 % [-0.5, +4.5] | 0.557 | 1.000 | 5/5/0 |

