# selective-masking summary (GT-centric, offline, pooled over the group): moving recall = masked share of moving potential-class instance-frames; static kept = unmasked share of static potential-class instance-frames (parked forklifts, pallets, boxes, standing people, trolleys); instance precision = moving masked / all masked; carried load on moving forklift masked / on parked forklift kept


## all

| variant | moving recall | static kept | instance precision | static forklift kept | static box kept | static pallet kept | static person kept | load on moving forklift masked | load on parked forklift kept |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| yolo_naive | 0.970 | 0.020 | 0.061 | 0.134 | 0.016 | 0.012 | 0.054 | 0.922 | 0.022 |
| yolo_p2 | 0.871 | 0.817 | 0.239 | 0.699 | 0.837 | 0.855 | 0.060 | 0.690 | 0.483 |
| yolo_p4 | 0.750 | 0.835 | 0.232 | 0.740 | 0.854 | 0.876 | 0.087 | 0.691 | 0.494 |
| yolo_p4_nointer | 0.582 | 0.973 | 0.586 | 0.959 | 0.998 | 0.999 | 0.091 | 0.270 | 0.979 |
| yolo_p4_noext | 0.749 | 0.836 | 0.232 | 0.749 | 0.855 | 0.876 | 0.087 | 0.690 | 0.501 |
| yolo_p6 | 0.885 | 0.902 | 0.373 | 0.743 | 0.928 | 0.932 | 0.084 | 0.733 | 0.665 |
| yolo_coco_person_p4 | 0.343 | 0.980 | 0.532 | 0.998 | 1.000 | 1.000 | 0.252 | 0.001 | 1.000 |
| oracle_moving_warp | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| oracle_class_naive_warp | 1.000 | 0.000 | 0.062 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 |

## L1+L2+L3

| variant | moving recall | static kept | instance precision | static forklift kept | static box kept | static pallet kept | static person kept | load on moving forklift masked | load on parked forklift kept |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| yolo_naive | 0.970 | 0.021 | 0.081 | 0.131 | 0.018 | 0.013 | 0.054 | 0.922 | 0.024 |
| yolo_p2 | 0.871 | 0.755 | 0.240 | 0.643 | 0.780 | 0.802 | 0.060 | 0.690 | 0.433 |
| yolo_p4 | 0.750 | 0.780 | 0.233 | 0.691 | 0.803 | 0.831 | 0.087 | 0.691 | 0.446 |
| yolo_p4_nointer | 0.582 | 0.964 | 0.587 | 0.952 | 0.997 | 0.998 | 0.091 | 0.270 | 0.977 |
| yolo_p4_noext | 0.749 | 0.781 | 0.233 | 0.703 | 0.804 | 0.831 | 0.087 | 0.690 | 0.453 |
| yolo_p6 | 0.885 | 0.869 | 0.374 | 0.696 | 0.903 | 0.908 | 0.084 | 0.733 | 0.633 |
| yolo_coco_person_p4 | 0.343 | 0.973 | 0.532 | 0.998 | 1.000 | 1.000 | 0.252 | 0.001 | 1.000 |
| oracle_moving_warp | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| oracle_class_naive_warp | 1.000 | 0.000 | 0.082 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 |

## L2+L3

| variant | moving recall | static kept | instance precision | static forklift kept | static box kept | static pallet kept | static person kept | load on moving forklift masked | load on parked forklift kept |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| yolo_naive | 0.968 | 0.024 | 0.109 | 0.129 | 0.019 | 0.013 | 0.062 | 0.922 | 0.027 |
| yolo_p2 | 0.859 | 0.718 | 0.273 | 0.586 | 0.747 | 0.760 | 0.069 | 0.690 | 0.402 |
| yolo_p4 | 0.727 | 0.751 | 0.265 | 0.645 | 0.778 | 0.800 | 0.096 | 0.691 | 0.416 |
| yolo_p4_nointer | 0.543 | 0.959 | 0.623 | 0.941 | 0.995 | 0.997 | 0.102 | 0.270 | 0.975 |
| yolo_p4_noext | 0.725 | 0.753 | 0.266 | 0.659 | 0.780 | 0.800 | 0.097 | 0.690 | 0.424 |
| yolo_p6 | 0.875 | 0.844 | 0.409 | 0.634 | 0.884 | 0.882 | 0.092 | 0.733 | 0.608 |
| yolo_coco_person_p4 | 0.281 | 0.973 | 0.562 | 0.998 | 1.000 | 1.000 | 0.300 | 0.001 | 1.000 |
| oracle_moving_warp | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| oracle_class_naive_warp | 1.000 | 0.000 | 0.110 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 |

## L0

| variant | moving recall | static kept | instance precision | static forklift kept | static box kept | static pallet kept | static person kept | load on moving forklift masked | load on parked forklift kept |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| yolo_naive | nan | 0.014 | 0.000 | 0.145 | 0.013 | 0.010 | - | nan | 0.000 |
| yolo_p2 | nan | 0.997 | 0.000 | 0.996 | 0.997 | 0.996 | - | nan | 0.997 |
| yolo_p4 | nan | 0.997 | 0.000 | 0.996 | 0.997 | 0.996 | - | nan | 0.997 |
| yolo_p4_nointer | nan | 1.000 | 0.000 | 0.999 | 1.000 | 1.000 | - | nan | 1.000 |
| yolo_p4_noext | nan | 0.997 | 0.000 | 0.996 | 0.997 | 0.997 | - | nan | 0.997 |
| yolo_p6 | nan | 0.998 | 0.000 | 0.996 | 0.999 | 0.997 | - | nan | 1.000 |
| yolo_coco_person_p4 | nan | 1.000 | 0.000 | 1.000 | 1.000 | 1.000 | - | nan | 1.000 |
| oracle_moving_warp | nan | 1.000 | nan | 1.000 | 1.000 | 1.000 | - | nan | 1.000 |
| oracle_class_naive_warp | nan | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | - | nan | 0.000 |
