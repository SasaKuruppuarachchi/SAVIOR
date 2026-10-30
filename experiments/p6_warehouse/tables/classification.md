# GT-centric classification (offline, deterministic, every frame): share of GT instance-frames (>= 200 px in cam0) whose pixels are >= 50 % inside the final core (255) mask; counts summed over the sequences of the group. For moving instances higher is better (recall), for static ones lower is better (1 - rate = kept unmasked). carried_* = box / pallet in a forklift actor block (load); driver = person in a forklift block.


## all (8 sequences)

| variant | person mov | person st | forklift mov | forklift st | box mov | box st | pallet mov | pallet st | trolley mov | trolley st | carried_box mov | carried_box st | carried_pallet mov | carried_pallet st | driver mov | driver st |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| yolo_naive | 0.99 | 0.95 | 0.99 | 0.87 | 0.92 | 0.98 | 0.94 | 0.99 | - | 0.98 | 0.92 | 0.98 | 0.94 | 0.97 | 0.99 | 0.97 |
| yolo_p2 | 0.98 | 0.94 | 0.86 | 0.30 | 0.70 | 0.16 | 0.66 | 0.15 | - | 0.10 | 0.70 | 0.53 | 0.66 | 0.48 | 0.98 | 0.95 |
| yolo_p4 | 0.96 | 0.91 | 0.46 | 0.26 | 0.69 | 0.15 | 0.70 | 0.12 | - | 0.09 | 0.69 | 0.51 | 0.70 | 0.48 | 0.96 | 0.93 |
| yolo_p4_nointer | 0.96 | 0.91 | 0.26 | 0.04 | 0.28 | 0.00 | 0.22 | 0.00 | - | 0.00 | 0.28 | 0.02 | 0.22 | 0.02 | 0.96 | 0.93 |
| yolo_p4_noext | 0.96 | 0.91 | 0.46 | 0.25 | 0.69 | 0.14 | 0.70 | 0.12 | - | 0.09 | 0.69 | 0.50 | 0.70 | 0.48 | 0.96 | 0.93 |
| yolo_p6 | 0.97 | 0.92 | 0.88 | 0.26 | 0.74 | 0.07 | 0.72 | 0.07 | - | 0.08 | 0.74 | 0.32 | 0.72 | 0.42 | 0.97 | 0.93 |
| yolo_coco_person_p4 | 0.75 | 0.75 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | - | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.55 | 0.42 |
| oracle_moving_warp | 1.00 | 0.00 | 1.00 | 0.00 | 1.00 | 0.00 | 1.00 | 0.00 | - | 0.00 | 1.00 | 0.00 | 1.00 | 0.00 | 1.00 | 0.00 |
| oracle_class_naive_warp | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | - | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |

(n = instance-frames: person:moving 16027, person:static 13959, forklift:moving 9875, forklift:static 14397, box:moving 7340, box:static 395498, pallet:moving 1774, pallet:static 102226, trolley:moving 0, trolley:static 3521, carried_box:moving 7340, carried_box:static 6926, carried_pallet:moving 1774, carried_pallet:static 1319, driver:moving 7057, driver:static 2143)

## L1+L2+L3 (6 sequences)

| variant | person mov | person st | forklift mov | forklift st | box mov | box st | pallet mov | pallet st | trolley mov | trolley st | carried_box mov | carried_box st | carried_pallet mov | carried_pallet st | driver mov | driver st |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| yolo_naive | 0.99 | 0.95 | 0.99 | 0.87 | 0.92 | 0.98 | 0.94 | 0.99 | - | 0.98 | 0.92 | 0.98 | 0.94 | 0.97 | 0.99 | 0.97 |
| yolo_p2 | 0.98 | 0.94 | 0.86 | 0.36 | 0.70 | 0.22 | 0.66 | 0.20 | - | 0.14 | 0.70 | 0.58 | 0.66 | 0.50 | 0.98 | 0.95 |
| yolo_p4 | 0.96 | 0.91 | 0.46 | 0.31 | 0.69 | 0.20 | 0.70 | 0.17 | - | 0.12 | 0.69 | 0.56 | 0.70 | 0.50 | 0.96 | 0.93 |
| yolo_p4_nointer | 0.96 | 0.91 | 0.26 | 0.05 | 0.28 | 0.00 | 0.22 | 0.00 | - | 0.00 | 0.28 | 0.02 | 0.22 | 0.02 | 0.96 | 0.93 |
| yolo_p4_noext | 0.96 | 0.91 | 0.46 | 0.30 | 0.69 | 0.20 | 0.70 | 0.17 | - | 0.12 | 0.69 | 0.56 | 0.70 | 0.50 | 0.96 | 0.93 |
| yolo_p6 | 0.97 | 0.92 | 0.88 | 0.30 | 0.74 | 0.10 | 0.72 | 0.09 | - | 0.11 | 0.74 | 0.35 | 0.72 | 0.44 | 0.97 | 0.93 |
| yolo_coco_person_p4 | 0.75 | 0.75 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | - | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.55 | 0.42 |
| oracle_moving_warp | 1.00 | 0.00 | 1.00 | 0.00 | 1.00 | 0.00 | 1.00 | 0.00 | - | 0.00 | 1.00 | 0.00 | 1.00 | 0.00 | 1.00 | 0.00 |
| oracle_class_naive_warp | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | - | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |

(n = instance-frames: person:moving 16027, person:static 13959, forklift:moving 9875, forklift:static 12125, box:moving 7340, box:static 291041, pallet:moving 1774, pallet:static 74465, trolley:moving 0, trolley:static 2523, carried_box:moving 7340, carried_box:static 6272, carried_pallet:moving 1774, carried_pallet:static 1249, driver:moving 7057, driver:static 2143)

## L2+L3 (4 sequences)

| variant | person mov | person st | forklift mov | forklift st | box mov | box st | pallet mov | pallet st | trolley mov | trolley st | carried_box mov | carried_box st | carried_pallet mov | carried_pallet st | driver mov | driver st |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| yolo_naive | 0.98 | 0.94 | 0.99 | 0.87 | 0.92 | 0.98 | 0.94 | 0.99 | - | 0.98 | 0.92 | 0.97 | 0.94 | 0.97 | 0.99 | 0.97 |
| yolo_p2 | 0.98 | 0.93 | 0.86 | 0.41 | 0.70 | 0.25 | 0.66 | 0.24 | - | 0.17 | 0.70 | 0.61 | 0.66 | 0.53 | 0.98 | 0.95 |
| yolo_p4 | 0.96 | 0.90 | 0.46 | 0.36 | 0.69 | 0.22 | 0.70 | 0.20 | - | 0.14 | 0.69 | 0.59 | 0.70 | 0.53 | 0.96 | 0.93 |
| yolo_p4_nointer | 0.95 | 0.90 | 0.26 | 0.06 | 0.28 | 0.00 | 0.22 | 0.00 | - | 0.00 | 0.28 | 0.03 | 0.22 | 0.02 | 0.96 | 0.93 |
| yolo_p4_noext | 0.96 | 0.90 | 0.46 | 0.34 | 0.69 | 0.22 | 0.70 | 0.20 | - | 0.14 | 0.69 | 0.58 | 0.70 | 0.53 | 0.96 | 0.93 |
| yolo_p6 | 0.97 | 0.91 | 0.88 | 0.37 | 0.74 | 0.12 | 0.72 | 0.12 | - | 0.13 | 0.74 | 0.38 | 0.72 | 0.47 | 0.97 | 0.93 |
| yolo_coco_person_p4 | 0.69 | 0.70 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | - | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.55 | 0.42 |
| oracle_moving_warp | 1.00 | 0.00 | 1.00 | 0.00 | 1.00 | 0.00 | 1.00 | 0.00 | - | 0.00 | 1.00 | 0.00 | 1.00 | 0.00 | 1.00 | 0.00 |
| oracle_class_naive_warp | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | - | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |

(n = instance-frames: person:moving 12949, person:static 9904, forklift:moving 9875, forklift:static 9885, box:moving 7340, box:static 189869, pallet:moving 1774, pallet:static 47717, trolley:moving 0, trolley:static 1602, carried_box:moving 7340, carried_box:static 5622, carried_pallet:moving 1774, carried_pallet:static 1179, driver:moving 7057, driver:static 2143)

## L0 (2 sequences)

| variant | person mov | person st | forklift mov | forklift st | box mov | box st | pallet mov | pallet st | trolley mov | trolley st | carried_box mov | carried_box st | carried_pallet mov | carried_pallet st | driver mov | driver st |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| yolo_naive | - | - | - | 0.85 | - | 0.99 | - | 0.99 | - | 0.98 | - | 1.00 | - | 1.00 | - | - |
| yolo_p2 | - | - | - | 0.00 | - | 0.00 | - | 0.00 | - | 0.00 | - | 0.00 | - | 0.00 | - | - |
| yolo_p4 | - | - | - | 0.00 | - | 0.00 | - | 0.00 | - | 0.00 | - | 0.00 | - | 0.00 | - | - |
| yolo_p4_nointer | - | - | - | 0.00 | - | 0.00 | - | 0.00 | - | 0.00 | - | 0.00 | - | 0.00 | - | - |
| yolo_p4_noext | - | - | - | 0.00 | - | 0.00 | - | 0.00 | - | 0.00 | - | 0.00 | - | 0.00 | - | - |
| yolo_p6 | - | - | - | 0.00 | - | 0.00 | - | 0.00 | - | 0.00 | - | 0.00 | - | 0.00 | - | - |
| yolo_coco_person_p4 | - | - | - | 0.00 | - | 0.00 | - | 0.00 | - | 0.00 | - | 0.00 | - | 0.00 | - | - |
| oracle_moving_warp | - | - | - | 0.00 | - | 0.00 | - | 0.00 | - | 0.00 | - | 0.00 | - | 0.00 | - | - |
| oracle_class_naive_warp | - | - | - | 1.00 | - | 1.00 | - | 1.00 | - | 1.00 | - | 1.00 | - | 1.00 | - | - |

(n = instance-frames: person:moving 0, person:static 0, forklift:moving 0, forklift:static 2272, box:moving 0, box:static 104457, pallet:moving 0, pallet:static 27761, trolley:moving 0, trolley:static 998, carried_box:moving 0, carried_box:static 654, carried_pallet:moving 0, carried_pallet:static 70, driver:moving 0, driver:static 0)
