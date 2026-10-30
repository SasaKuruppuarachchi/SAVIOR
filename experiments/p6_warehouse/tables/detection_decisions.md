# detection-centric decisions (each detected instance -> GT instance with the largest overlap >= 30 % of its area; moving precision = masked moving / masked (moving + static); incl_fp = also counting masked detections without GT); pooled over all sequences by summing per-sequence counts is not possible from the ratios, so per sequence


## aisles_t1_L0

| variant | class | n det | n moving | moving precision | precision incl FP det | moving recall | static kept |
|---|---|--:|--:|--:|--:|--:|--:|
| yolo_naive | person | 79 | 0 | None | 0.0 | None | None |
| yolo_naive | forklift | 1033 | 0 | 0.0 | 0.0 | None | 0.0 |
| yolo_naive | box | 159217 | 0 | 0.0 | 0.0 | None | 0.0 |
| yolo_naive | pallet | 41727 | 0 | 0.0 | 0.0 | None | 0.0 |
| yolo_naive | trolley | 298 | 0 | 0.0 | 0.0 | None | 0.0 |
| yolo_naive | all | 202109 | 0 | 0.0 | 0.0 | None | 0.0 |
| yolo_naive | load on static forklift | 1021 | - | masked 1.000 | - | - | {'root': 1021} |
| yolo_p2 | person | 79 | 0 | None | 0.0 | None | None |
| yolo_p2 | forklift | 1033 | 0 | 0.0 | 0.0 | None | 0.9869 |
| yolo_p2 | box | 159217 | 0 | 0.0 | 0.0 | None | 0.9965 |
| yolo_p2 | pallet | 41727 | 0 | 0.0 | 0.0 | None | 0.9953 |
| yolo_p2 | trolley | 298 | 0 | None | None | None | 1.0 |
| yolo_p2 | all | 202109 | 0 | 0.0 | 0.0 | None | 0.9962 |
| yolo_p2 | load on static forklift | 1021 | - | masked 0.005 | - | - | {'promoted': 5, 'unpromoted': 1016} |
| yolo_p4 | person | 79 | 0 | None | 0.0 | None | None |
| yolo_p4 | forklift | 1033 | 0 | 0.0 | 0.0 | None | 0.9869 |
| yolo_p4 | box | 159217 | 0 | 0.0 | 0.0 | None | 0.9967 |
| yolo_p4 | pallet | 41727 | 0 | 0.0 | 0.0 | None | 0.9957 |
| yolo_p4 | trolley | 298 | 0 | None | None | None | 1.0 |
| yolo_p4 | all | 202109 | 0 | 0.0 | 0.0 | None | 0.9964 |
| yolo_p4 | load on static forklift | 1021 | - | masked 0.005 | - | - | {'promoted': 5, 'unpromoted': 1016} |
| yolo_p4_nointer | person | 79 | 0 | None | 0.0 | None | None |
| yolo_p4_nointer | forklift | 1033 | 0 | 0.0 | 0.0 | None | 0.993 |
| yolo_p4_nointer | box | 159217 | 0 | 0.0 | 0.0 | None | 0.9999 |
| yolo_p4_nointer | pallet | 41727 | 0 | 0.0 | 0.0 | None | 1.0 |
| yolo_p4_nointer | trolley | 298 | 0 | None | None | None | 1.0 |
| yolo_p4_nointer | all | 202109 | 0 | 0.0 | 0.0 | None | 0.9999 |
| yolo_p4_nointer | load on static forklift | 1021 | - | masked 0.000 | - | - | {'unpromoted': 1021} |
| yolo_p4_noext | person | 79 | 0 | None | 0.0 | None | None |
| yolo_p4_noext | forklift | 1033 | 0 | 0.0 | 0.0 | None | 0.9869 |
| yolo_p4_noext | box | 159217 | 0 | 0.0 | 0.0 | None | 0.9967 |
| yolo_p4_noext | pallet | 41727 | 0 | 0.0 | 0.0 | None | 0.9957 |
| yolo_p4_noext | trolley | 298 | 0 | None | None | None | 1.0 |
| yolo_p4_noext | all | 202109 | 0 | 0.0 | 0.0 | None | 0.9964 |
| yolo_p4_noext | load on static forklift | 1021 | - | masked 0.005 | - | - | {'promoted': 5, 'unpromoted': 1016} |
| yolo_p6 | person | 79 | 0 | None | 0.0 | None | None |
| yolo_p6 | forklift | 1033 | 0 | 0.0 | 0.0 | None | 0.9869 |
| yolo_p6 | box | 159217 | 0 | 0.0 | 0.0 | None | 0.999 |
| yolo_p6 | pallet | 41727 | 0 | 0.0 | 0.0 | None | 0.9983 |
| yolo_p6 | trolley | 298 | 0 | None | None | None | 1.0 |
| yolo_p6 | all | 202109 | 0 | 0.0 | 0.0 | None | 0.9988 |
| yolo_p6 | load on static forklift | 1021 | - | masked 0.003 | - | - | {'promoted': 3, 'unpromoted': 1018} |
| yolo_coco_person_p4 | person | 5 | 0 | None | 0.0 | None | None |
| yolo_coco_person_p4 | forklift | 1 | 0 | 0.0 | 0.0 | None | 0.0 |
| yolo_coco_person_p4 | box | 1 | 0 | 0.0 | 0.0 | None | 0.0 |
| yolo_coco_person_p4 | pallet | 1 | 0 | None | 0.0 | None | None |
| yolo_coco_person_p4 | all | 7 | 0 | 0.0 | 0.0 | None | 0.0 |

## aisles_t1_L1

| variant | class | n det | n moving | moving precision | precision incl FP det | moving recall | static kept |
|---|---|--:|--:|--:|--:|--:|--:|
| yolo_naive | person | 3944 | 1724 | 0.4554 | 0.4371 | 1.0 | 0.0 |
| yolo_naive | forklift | 1038 | 0 | 0.0 | 0.0 | None | 0.0 |
| yolo_naive | box | 152893 | 0 | 0.0 | 0.0 | None | 0.0 |
| yolo_naive | pallet | 40534 | 0 | 0.0 | 0.0 | None | 0.0 |
| yolo_naive | trolley | 298 | 0 | 0.0 | 0.0 | None | 0.0 |
| yolo_naive | all | 198398 | 1724 | 0.0088 | 0.0087 | 1.0 | 0.0 |
| yolo_naive | load on static forklift | 953 | - | masked 1.000 | - | - | {'root': 953} |
| yolo_p2 | person | 3944 | 1724 | 0.457 | 0.4424 | 0.9872 | 0.0194 |
| yolo_p2 | forklift | 1038 | 0 | 0.0 | 0.0 | None | 0.9088 |
| yolo_p2 | box | 152893 | 0 | 0.0 | 0.0 | None | 0.8765 |
| yolo_p2 | pallet | 40534 | 0 | 0.0 | 0.0 | None | 0.8912 |
| yolo_p2 | trolley | 298 | 0 | 0.0 | 0.0 | None | 0.8047 |
| yolo_p2 | all | 198398 | 1724 | 0.0633 | 0.0627 | 0.9872 | 0.8705 |
| yolo_p2 | load on static forklift | 953 | - | masked 0.039 | - | - | {'promoted': 37, 'unpromoted': 916} |
| yolo_p4 | person | 3944 | 1724 | 0.4619 | 0.447 | 0.9872 | 0.0383 |
| yolo_p4 | forklift | 1038 | 0 | 0.0 | 0.0 | None | 0.9088 |
| yolo_p4 | box | 152893 | 0 | 0.0 | 0.0 | None | 0.8808 |
| yolo_p4 | pallet | 40534 | 0 | 0.0 | 0.0 | None | 0.8954 |
| yolo_p4 | trolley | 298 | 0 | 0.0 | 0.0 | None | 0.8047 |
| yolo_p4 | all | 198398 | 1724 | 0.0654 | 0.0648 | 0.9872 | 0.8749 |
| yolo_p4 | load on static forklift | 953 | - | masked 0.039 | - | - | {'promoted': 37, 'unpromoted': 916} |
| yolo_p4_nointer | person | 3944 | 1724 | 0.4538 | 0.4406 | 0.949 | 0.0451 |
| yolo_p4_nointer | forklift | 1038 | 0 | 0.0 | 0.0 | None | 0.9919 |
| yolo_p4_nointer | box | 152893 | 0 | 0.0 | 0.0 | None | 0.9999 |
| yolo_p4_nointer | pallet | 40534 | 0 | 0.0 | 0.0 | None | 1.0 |
| yolo_p4_nointer | trolley | 298 | 0 | None | None | None | 1.0 |
| yolo_p4_nointer | all | 198398 | 1724 | 0.4503 | 0.4373 | 0.949 | 0.9897 |
| yolo_p4_nointer | load on static forklift | 953 | - | masked 0.000 | - | - | {'unpromoted': 953} |
| yolo_p4_noext | person | 3944 | 1724 | 0.4619 | 0.447 | 0.9872 | 0.0383 |
| yolo_p4_noext | forklift | 1038 | 0 | 0.0 | 0.0 | None | 0.9048 |
| yolo_p4_noext | box | 152893 | 0 | 0.0 | 0.0 | None | 0.8813 |
| yolo_p4_noext | pallet | 40534 | 0 | 0.0 | 0.0 | None | 0.8936 |
| yolo_p4_noext | trolley | 298 | 0 | 0.0 | 0.0 | None | 0.8047 |
| yolo_p4_noext | all | 198398 | 1724 | 0.0654 | 0.0648 | 0.9872 | 0.8749 |
| yolo_p4_noext | load on static forklift | 953 | - | masked 0.039 | - | - | {'promoted': 37, 'unpromoted': 916} |
| yolo_p6 | person | 3944 | 1724 | 0.4622 | 0.4474 | 0.9872 | 0.0398 |
| yolo_p6 | forklift | 1038 | 0 | 0.0 | 0.0 | None | 0.9433 |
| yolo_p6 | box | 152893 | 0 | 0.0 | 0.0 | None | 0.952 |
| yolo_p6 | pallet | 40534 | 0 | 0.0 | 0.0 | None | 0.9513 |
| yolo_p6 | trolley | 298 | 0 | 0.0 | 0.0 | None | 0.835 |
| yolo_p6 | all | 198398 | 1724 | 0.131 | 0.1292 | 0.9872 | 0.9419 |
| yolo_p6 | load on static forklift | 953 | - | masked 0.038 | - | - | {'promoted': 36, 'unpromoted': 917} |
| yolo_coco_person_p4 | person | 3319 | 1577 | 0.4817 | 0.4808 | 1.0 | 0.0225 |
| yolo_coco_person_p4 | forklift | 7 | 0 | 0.0 | 0.0 | None | 0.0 |
| yolo_coco_person_p4 | box | 4 | 0 | 0.0 | 0.0 | None | 0.0 |
| yolo_coco_person_p4 | pallet | 4 | 0 | None | 0.0 | None | None |
| yolo_coco_person_p4 | all | 3329 | 1577 | 0.4802 | 0.4793 | 1.0 | 0.0223 |

## aisles_t1_L2

| variant | class | n det | n moving | moving precision | precision incl FP det | moving recall | static kept |
|---|---|--:|--:|--:|--:|--:|--:|
| yolo_naive | person | 5051 | 2773 | 0.5663 | 0.549 | 1.0 | 0.0 |
| yolo_naive | forklift | 2801 | 1196 | 0.4402 | 0.427 | 1.0 | 0.0 |
| yolo_naive | box | 151688 | 1270 | 0.0085 | 0.0084 | 1.0 | 0.0 |
| yolo_naive | pallet | 39681 | 427 | 0.0109 | 0.0108 | 1.0 | 0.0 |
| yolo_naive | trolley | 238 | 0 | 0.0 | 0.0 | None | 0.0 |
| yolo_naive | all | 199116 | 5666 | 0.0288 | 0.0285 | 1.0 | 0.0 |
| yolo_naive | load on moving forklift | 1708 | - | masked 1.000 | - | - | {'root': 1708} |
| yolo_naive | load on static forklift | 1102 | - | masked 1.000 | - | - | {'root': 1102} |
| yolo_p2 | person | 5051 | 2773 | 0.5679 | 0.5538 | 0.991 | 0.0155 |
| yolo_p2 | forklift | 2801 | 1196 | 0.7918 | 0.7826 | 0.7918 | 0.8363 |
| yolo_p2 | box | 151688 | 1270 | 0.0419 | 0.0416 | 0.7362 | 0.8562 |
| yolo_p2 | pallet | 39681 | 427 | 0.0569 | 0.0561 | 0.6581 | 0.8799 |
| yolo_p2 | trolley | 238 | 0 | 0.0 | 0.0 | None | 0.8109 |
| yolo_p2 | all | 199116 | 5666 | 0.1474 | 0.1462 | 0.8667 | 0.8515 |
| yolo_p2 | load on moving forklift | 1708 | - | masked 0.717 | - | - | {'promoted': 1224, 'unpromoted': 484} |
| yolo_p2 | load on static forklift | 1102 | - | masked 0.083 | - | - | {'promoted': 91, 'unpromoted': 1011} |
| yolo_p4 | person | 5051 | 2773 | 0.5726 | 0.5583 | 0.991 | 0.0344 |
| yolo_p4 | forklift | 2801 | 1196 | 0.8024 | 0.7936 | 0.8554 | 0.8343 |
| yolo_p4 | box | 151688 | 1270 | 0.0457 | 0.0453 | 0.7803 | 0.8607 |
| yolo_p4 | pallet | 39681 | 427 | 0.0664 | 0.0655 | 0.7611 | 0.8822 |
| yolo_p4 | trolley | 238 | 0 | 0.0 | 0.0 | None | 0.8109 |
| yolo_p4 | all | 199116 | 5666 | 0.1556 | 0.1543 | 0.8978 | 0.8556 |
| yolo_p4 | load on moving forklift | 1708 | - | masked 0.775 | - | - | {'promoted': 920, 'root': 404, 'unpromoted': 384} |
| yolo_p4 | load on static forklift | 1102 | - | masked 0.117 | - | - | {'promoted': 129, 'unpromoted': 973} |
| yolo_p4_nointer | person | 5051 | 2773 | 0.5687 | 0.5555 | 0.9697 | 0.04 |
| yolo_p4_nointer | forklift | 2801 | 1196 | 0.9364 | 0.931 | 0.4064 | 0.9783 |
| yolo_p4_nointer | box | 151688 | 1270 | 0.8972 | 0.8136 | 0.2543 | 0.9998 |
| yolo_p4_nointer | pallet | 39681 | 427 | 1.0 | 0.6694 | 0.1897 | 1.0 |
| yolo_p4_nointer | trolley | 238 | 0 | None | None | None | 1.0 |
| yolo_p4_nointer | all | 199116 | 5666 | 0.6292 | 0.6167 | 0.6317 | 0.989 |
| yolo_p4_nointer | load on moving forklift | 1708 | - | masked 0.237 | - | - | {'root': 404, 'unpromoted': 1304} |
| yolo_p4_nointer | load on static forklift | 1102 | - | masked 0.000 | - | - | {'unpromoted': 1102} |
| yolo_p4_noext | person | 5051 | 2773 | 0.5726 | 0.5584 | 0.991 | 0.0344 |
| yolo_p4_noext | forklift | 2801 | 1196 | 0.8025 | 0.7938 | 0.8595 | 0.8337 |
| yolo_p4_noext | box | 151688 | 1270 | 0.0456 | 0.0453 | 0.7811 | 0.8603 |
| yolo_p4_noext | pallet | 39681 | 427 | 0.0667 | 0.0658 | 0.7658 | 0.882 |
| yolo_p4_noext | trolley | 238 | 0 | 0.0 | 0.0 | None | 0.8109 |
| yolo_p4_noext | all | 199116 | 5666 | 0.1555 | 0.1542 | 0.8992 | 0.8553 |
| yolo_p4_noext | load on moving forklift | 1708 | - | masked 0.777 | - | - | {'promoted': 923, 'root': 404, 'unpromoted': 381} |
| yolo_p4_noext | load on static forklift | 1102 | - | masked 0.115 | - | - | {'promoted': 127, 'unpromoted': 975} |
| yolo_p6 | person | 5051 | 2773 | 0.573 | 0.5587 | 0.991 | 0.0358 |
| yolo_p6 | forklift | 2801 | 1196 | 0.8627 | 0.854 | 0.8562 | 0.8928 |
| yolo_p6 | box | 151688 | 1270 | 0.0979 | 0.0968 | 0.7386 | 0.9418 |
| yolo_p6 | pallet | 39681 | 427 | 0.1302 | 0.1275 | 0.74 | 0.9456 |
| yolo_p6 | trolley | 238 | 0 | 0.0 | 0.0 | None | 0.8109 |
| yolo_p6 | all | 199116 | 5666 | 0.2787 | 0.2757 | 0.887 | 0.932 |
| yolo_p6 | load on moving forklift | 1708 | - | masked 0.739 | - | - | {'promoted': 848, 'root': 414, 'unpromoted': 446} |
| yolo_p6 | load on static forklift | 1102 | - | masked 0.103 | - | - | {'promoted': 113, 'unpromoted': 989} |
| yolo_coco_person_p4 | person | 3613 | 1934 | 0.5415 | 0.5401 | 0.9917 | 0.0275 |
| yolo_coco_person_p4 | forklift | 255 | 240 | 0.9449 | 0.9412 | 1.0 | 0.0 |
| yolo_coco_person_p4 | box | 1 | 0 | 0.0 | 0.0 | None | 0.0 |
| yolo_coco_person_p4 | pallet | 8 | 0 | None | 0.0 | None | None |
| yolo_coco_person_p4 | all | 3868 | 2174 | 0.5683 | 0.567 | 0.9926 | 0.0273 |

## aisles_t1_L3

| variant | class | n det | n moving | moving precision | precision incl FP det | moving recall | static kept |
|---|---|--:|--:|--:|--:|--:|--:|
| yolo_naive | person | 6242 | 3433 | 0.5669 | 0.55 | 1.0 | 0.0 |
| yolo_naive | forklift | 5033 | 2653 | 0.5632 | 0.5271 | 1.0 | 0.0 |
| yolo_naive | box | 139320 | 1604 | 0.0117 | 0.0115 | 1.0 | 0.0 |
| yolo_naive | pallet | 32809 | 378 | 0.0117 | 0.0115 | 1.0 | 0.0 |
| yolo_naive | trolley | 247 | 0 | 0.0 | 0.0 | None | 0.0 |
| yolo_naive | all | 182999 | 8068 | 0.0448 | 0.0441 | 1.0 | 0.0 |
| yolo_naive | load on moving forklift | 2004 | - | masked 1.000 | - | - | {'root': 2004} |
| yolo_naive | load on static forklift | 1252 | - | masked 1.000 | - | - | {'root': 1252} |
| yolo_p2 | person | 6242 | 3433 | 0.5695 | 0.5545 | 0.9942 | 0.0164 |
| yolo_p2 | forklift | 5033 | 2653 | 0.8064 | 0.7575 | 0.8666 | 0.7318 |
| yolo_p2 | box | 139320 | 1604 | 0.0386 | 0.0377 | 0.8678 | 0.7441 |
| yolo_p2 | pallet | 32809 | 378 | 0.0303 | 0.0296 | 0.7037 | 0.7336 |
| yolo_p2 | trolley | 247 | 0 | 0.0 | 0.0 | None | 0.7654 |
| yolo_p2 | all | 182999 | 8068 | 0.1373 | 0.1347 | 0.9135 | 0.731 |
| yolo_p2 | load on moving forklift | 2004 | - | masked 0.834 | - | - | {'promoted': 1671, 'unpromoted': 333} |
| yolo_p2 | load on static forklift | 1252 | - | masked 0.150 | - | - | {'promoted': 188, 'unpromoted': 1064} |
| yolo_p4 | person | 6242 | 3433 | 0.5688 | 0.5553 | 0.9732 | 0.0343 |
| yolo_p4 | forklift | 5033 | 2653 | 0.6529 | 0.6333 | 0.4056 | 0.7221 |
| yolo_p4 | box | 139320 | 1604 | 0.0436 | 0.0432 | 0.7388 | 0.8081 |
| yolo_p4 | pallet | 32809 | 378 | 0.0417 | 0.0412 | 0.7196 | 0.8042 |
| yolo_p4 | trolley | 247 | 0 | 0.0 | 0.0 | None | 0.8189 |
| yolo_p4 | all | 182999 | 8068 | 0.1424 | 0.141 | 0.7281 | 0.7946 |
| yolo_p4 | load on moving forklift | 2004 | - | masked 0.730 | - | - | {'promoted': 805, 'root': 658, 'unpromoted': 541} |
| yolo_p4 | load on static forklift | 1252 | - | masked 0.180 | - | - | {'promoted': 225, 'unpromoted': 1027} |
| yolo_p4_nointer | person | 6242 | 3433 | 0.566 | 0.5555 | 0.954 | 0.0427 |
| yolo_p4_nointer | forklift | 5033 | 2653 | 0.9269 | 0.9195 | 0.2152 | 0.9781 |
| yolo_p4_nointer | box | 139320 | 1604 | 0.6259 | 0.6071 | 0.341 | 0.9976 |
| yolo_p4_nointer | pallet | 32809 | 378 | 0.6727 | 0.5286 | 0.2937 | 0.9983 |
| yolo_p4_nointer | trolley | 247 | 0 | None | 0.0 | None | 1.0 |
| yolo_p4_nointer | all | 182999 | 8068 | 0.6053 | 0.5964 | 0.5583 | 0.9829 |
| yolo_p4_nointer | load on moving forklift | 2004 | - | masked 0.328 | - | - | {'root': 658, 'unpromoted': 1346} |
| yolo_p4_nointer | load on static forklift | 1252 | - | masked 0.000 | - | - | {'unpromoted': 1252} |
| yolo_p4_noext | person | 6242 | 3433 | 0.5688 | 0.5553 | 0.9732 | 0.0343 |
| yolo_p4_noext | forklift | 5033 | 2653 | 0.6508 | 0.6317 | 0.406 | 0.7191 |
| yolo_p4_noext | box | 139320 | 1604 | 0.0438 | 0.0433 | 0.7406 | 0.8082 |
| yolo_p4_noext | pallet | 32809 | 378 | 0.042 | 0.0415 | 0.7249 | 0.8043 |
| yolo_p4_noext | trolley | 247 | 0 | 0.0 | 0.0 | None | 0.8189 |
| yolo_p4_noext | all | 182999 | 8068 | 0.1426 | 0.1412 | 0.7288 | 0.7946 |
| yolo_p4_noext | load on moving forklift | 2004 | - | masked 0.733 | - | - | {'promoted': 810, 'root': 658, 'unpromoted': 536} |
| yolo_p4_noext | load on static forklift | 1252 | - | masked 0.179 | - | - | {'promoted': 224, 'unpromoted': 1028} |
| yolo_p6 | person | 6242 | 3433 | 0.5685 | 0.5551 | 0.9729 | 0.0335 |
| yolo_p6 | forklift | 5033 | 2653 | 0.8276 | 0.7832 | 0.8251 | 0.7784 |
| yolo_p6 | box | 139320 | 1604 | 0.0771 | 0.0747 | 0.8335 | 0.8818 |
| yolo_p6 | pallet | 32809 | 378 | 0.0553 | 0.0538 | 0.7513 | 0.8479 |
| yolo_p6 | trolley | 247 | 0 | 0.0 | 0.0 | None | 0.7654 |
| yolo_p6 | all | 182999 | 8068 | 0.2302 | 0.2253 | 0.8862 | 0.8612 |
| yolo_p6 | load on moving forklift | 2004 | - | masked 0.813 | - | - | {'promoted': 947, 'root': 683, 'unpromoted': 374} |
| yolo_p6 | load on static forklift | 1252 | - | masked 0.129 | - | - | {'promoted': 162, 'unpromoted': 1090} |
| yolo_coco_person_p4 | person | 4792 | 3029 | 0.6292 | 0.6276 | 0.9709 | 0.0103 |
| yolo_coco_person_p4 | forklift | 146 | 59 | 0.4155 | 0.4041 | 1.0 | 0.0 |
| yolo_coco_person_p4 | box | 7 | 0 | 0.0 | 0.0 | None | 0.0 |
| yolo_coco_person_p4 | pallet | 2 | 0 | None | 0.0 | None | None |
| yolo_coco_person_p4 | all | 4938 | 3088 | 0.6224 | 0.6209 | 0.9715 | 0.0098 |

## hall_t1_L0

| variant | class | n det | n moving | moving precision | precision incl FP det | moving recall | static kept |
|---|---|--:|--:|--:|--:|--:|--:|
| yolo_naive | person | 7 | 0 | None | 0.0 | None | None |
| yolo_naive | forklift | 1570 | 0 | 0.0 | 0.0 | None | 0.0 |
| yolo_naive | box | 77777 | 0 | 0.0 | 0.0 | None | 0.0 |
| yolo_naive | pallet | 14595 | 0 | 0.0 | 0.0 | None | 0.0 |
| yolo_naive | trolley | 1165 | 0 | 0.0 | 0.0 | None | 0.0 |
| yolo_naive | all | 95041 | 0 | 0.0 | 0.0 | None | 0.0 |
| yolo_naive | load on static forklift | 653 | - | masked 1.000 | - | - | {'root': 653} |
| yolo_p2 | person | 7 | 0 | None | 0.0 | None | None |
| yolo_p2 | forklift | 1570 | 0 | 0.0 | 0.0 | None | 0.9974 |
| yolo_p2 | box | 77777 | 0 | 0.0 | 0.0 | None | 0.9972 |
| yolo_p2 | pallet | 14595 | 0 | 0.0 | 0.0 | None | 0.9976 |
| yolo_p2 | trolley | 1165 | 0 | 0.0 | 0.0 | None | 0.9991 |
| yolo_p2 | all | 95041 | 0 | 0.0 | 0.0 | None | 0.9973 |
| yolo_p2 | load on static forklift | 653 | - | masked 0.000 | - | - | {'unpromoted': 653} |
| yolo_p4 | person | 7 | 0 | None | 0.0 | None | None |
| yolo_p4 | forklift | 1570 | 0 | 0.0 | 0.0 | None | 0.9974 |
| yolo_p4 | box | 77777 | 0 | 0.0 | 0.0 | None | 0.9972 |
| yolo_p4 | pallet | 14595 | 0 | 0.0 | 0.0 | None | 0.9976 |
| yolo_p4 | trolley | 1165 | 0 | 0.0 | 0.0 | None | 0.9991 |
| yolo_p4 | all | 95041 | 0 | 0.0 | 0.0 | None | 0.9973 |
| yolo_p4 | load on static forklift | 653 | - | masked 0.000 | - | - | {'unpromoted': 653} |
| yolo_p4_nointer | person | 7 | 0 | None | 0.0 | None | None |
| yolo_p4_nointer | forklift | 1570 | 0 | 0.0 | 0.0 | None | 0.9994 |
| yolo_p4_nointer | box | 77777 | 0 | 0.0 | 0.0 | None | 1.0 |
| yolo_p4_nointer | pallet | 14595 | 0 | None | None | None | 1.0 |
| yolo_p4_nointer | trolley | 1165 | 0 | None | 0.0 | None | 1.0 |
| yolo_p4_nointer | all | 95041 | 0 | 0.0 | 0.0 | None | 1.0 |
| yolo_p4_nointer | load on static forklift | 653 | - | masked 0.000 | - | - | {'unpromoted': 653} |
| yolo_p4_noext | person | 7 | 0 | None | 0.0 | None | None |
| yolo_p4_noext | forklift | 1570 | 0 | 0.0 | 0.0 | None | 0.9974 |
| yolo_p4_noext | box | 77777 | 0 | 0.0 | 0.0 | None | 0.9981 |
| yolo_p4_noext | pallet | 14595 | 0 | 0.0 | 0.0 | None | 0.998 |
| yolo_p4_noext | trolley | 1165 | 0 | 0.0 | 0.0 | None | 0.9991 |
| yolo_p4_noext | all | 95041 | 0 | 0.0 | 0.0 | None | 0.998 |
| yolo_p4_noext | load on static forklift | 653 | - | masked 0.000 | - | - | {'unpromoted': 653} |
| yolo_p6 | person | 7 | 0 | None | 0.0 | None | None |
| yolo_p6 | forklift | 1570 | 0 | 0.0 | 0.0 | None | 0.9974 |
| yolo_p6 | box | 77777 | 0 | 0.0 | 0.0 | None | 0.9989 |
| yolo_p6 | pallet | 14595 | 0 | 0.0 | 0.0 | None | 0.9963 |
| yolo_p6 | trolley | 1165 | 0 | 0.0 | 0.0 | None | 0.9991 |
| yolo_p6 | all | 95041 | 0 | 0.0 | 0.0 | None | 0.9985 |
| yolo_p6 | load on static forklift | 653 | - | masked 0.000 | - | - | {'unpromoted': 653} |
| yolo_coco_person_p4 | person | 1 | 0 | None | 0.0 | None | None |
| yolo_coco_person_p4 | forklift | 3 | 0 | 0.0 | 0.0 | None | 0.0 |
| yolo_coco_person_p4 | pallet | 1 | 0 | None | 0.0 | None | None |
| yolo_coco_person_p4 | all | 4 | 0 | 0.0 | 0.0 | None | 0.0 |

## hall_t1_L1

| variant | class | n det | n moving | moving precision | precision incl FP det | moving recall | static kept |
|---|---|--:|--:|--:|--:|--:|--:|
| yolo_naive | person | 4495 | 1618 | 0.3645 | 0.36 | 1.0 | 0.0 |
| yolo_naive | forklift | 1578 | 0 | 0.0 | 0.0 | None | 0.0 |
| yolo_naive | box | 73435 | 0 | 0.0 | 0.0 | None | 0.0 |
| yolo_naive | pallet | 14248 | 0 | 0.0 | 0.0 | None | 0.0 |
| yolo_naive | trolley | 1192 | 0 | 0.0 | 0.0 | None | 0.0 |
| yolo_naive | all | 94824 | 1618 | 0.0173 | 0.0171 | 1.0 | 0.0 |
| yolo_naive | load on static forklift | 667 | - | masked 1.000 | - | - | {'root': 667} |
| yolo_p2 | person | 4495 | 1618 | 0.3646 | 0.3626 | 0.9944 | 0.006 |
| yolo_p2 | forklift | 1578 | 0 | 0.0 | 0.0 | None | 0.8329 |
| yolo_p2 | box | 73435 | 0 | 0.0 | 0.0 | None | 0.8014 |
| yolo_p2 | pallet | 14248 | 0 | 0.0 | 0.0 | None | 0.8095 |
| yolo_p2 | trolley | 1192 | 0 | 0.0 | 0.0 | None | 0.9445 |
| yolo_p2 | all | 94824 | 1618 | 0.0739 | 0.073 | 0.9944 | 0.7805 |
| yolo_p2 | load on static forklift | 667 | - | masked 0.601 | - | - | {'promoted': 401, 'unpromoted': 266} |
| yolo_p4 | person | 4495 | 1618 | 0.3706 | 0.3687 | 0.9944 | 0.0312 |
| yolo_p4 | forklift | 1578 | 0 | 0.0 | 0.0 | None | 0.8413 |
| yolo_p4 | box | 73435 | 0 | 0.0 | 0.0 | None | 0.8146 |
| yolo_p4 | pallet | 14248 | 0 | 0.0 | 0.0 | None | 0.822 |
| yolo_p4 | trolley | 1192 | 0 | 0.0 | 0.0 | None | 0.9445 |
| yolo_p4 | all | 94824 | 1618 | 0.0783 | 0.0773 | 0.9944 | 0.7938 |
| yolo_p4 | load on static forklift | 667 | - | masked 0.601 | - | - | {'promoted': 401, 'unpromoted': 266} |
| yolo_p4_nointer | person | 4495 | 1618 | 0.3729 | 0.372 | 0.974 | 0.0606 |
| yolo_p4_nointer | forklift | 1578 | 0 | None | 0.0 | None | 1.0 |
| yolo_p4_nointer | box | 73435 | 0 | 0.0 | 0.0 | None | 0.9997 |
| yolo_p4_nointer | pallet | 14248 | 0 | None | 0.0 | None | 1.0 |
| yolo_p4_nointer | trolley | 1192 | 0 | None | 0.0 | None | 1.0 |
| yolo_p4_nointer | all | 94824 | 1618 | 0.3713 | 0.3703 | 0.974 | 0.9709 |
| yolo_p4_nointer | load on static forklift | 667 | - | masked 0.000 | - | - | {'unpromoted': 667} |
| yolo_p4_noext | person | 4495 | 1618 | 0.3706 | 0.3687 | 0.9951 | 0.0308 |
| yolo_p4_noext | forklift | 1578 | 0 | 0.0 | 0.0 | None | 0.8432 |
| yolo_p4_noext | box | 73435 | 0 | 0.0 | 0.0 | None | 0.8153 |
| yolo_p4_noext | pallet | 14248 | 0 | 0.0 | 0.0 | None | 0.8217 |
| yolo_p4_noext | trolley | 1192 | 0 | 0.0 | 0.0 | None | 0.9462 |
| yolo_p4_noext | all | 94824 | 1618 | 0.0786 | 0.0775 | 0.9951 | 0.7943 |
| yolo_p4_noext | load on static forklift | 667 | - | masked 0.601 | - | - | {'promoted': 401, 'unpromoted': 266} |
| yolo_p6 | person | 4495 | 1618 | 0.3706 | 0.369 | 0.9944 | 0.0312 |
| yolo_p6 | forklift | 1578 | 0 | 0.0 | 0.0 | None | 0.9717 |
| yolo_p6 | box | 73435 | 0 | 0.0 | 0.0 | None | 0.9249 |
| yolo_p6 | pallet | 14248 | 0 | 0.0 | 0.0 | None | 0.9199 |
| yolo_p6 | trolley | 1192 | 0 | 0.0 | 0.0 | None | 0.9748 |
| yolo_p6 | all | 94824 | 1618 | 0.1467 | 0.1441 | 0.9944 | 0.8981 |
| yolo_p6 | load on static forklift | 667 | - | masked 0.253 | - | - | {'promoted': 169, 'unpromoted': 498} |
| yolo_coco_person_p4 | person | 3640 | 1497 | 0.4199 | 0.4189 | 1.0 | 0.0309 |
| yolo_coco_person_p4 | forklift | 11 | 0 | 0.0 | 0.0 | None | 0.0 |
| yolo_coco_person_p4 | box | 25 | 0 | 0.0 | 0.0 | None | 0.0 |
| yolo_coco_person_p4 | pallet | 2 | 0 | None | 0.0 | None | None |
| yolo_coco_person_p4 | all | 3673 | 1497 | 0.4161 | 0.415 | 1.0 | 0.0305 |

## hall_t1_L2

| variant | class | n det | n moving | moving precision | precision incl FP det | moving recall | static kept |
|---|---|--:|--:|--:|--:|--:|--:|
| yolo_naive | person | 7161 | 3576 | 0.5042 | 0.4994 | 1.0 | 0.0 |
| yolo_naive | forklift | 5603 | 2245 | 0.4035 | 0.4007 | 1.0 | 0.0 |
| yolo_naive | box | 69670 | 2266 | 0.0331 | 0.0325 | 1.0 | 0.0 |
| yolo_naive | pallet | 14288 | 758 | 0.0536 | 0.0531 | 1.0 | 0.0 |
| yolo_naive | trolley | 1060 | 0 | 0.0 | 0.0 | None | 0.0 |
| yolo_naive | all | 97628 | 8845 | 0.0919 | 0.0906 | 1.0 | 0.0 |
| yolo_naive | load on moving forklift | 3028 | - | masked 1.000 | - | - | {'root': 3028} |
| yolo_naive | load on static forklift | 4418 | - | masked 1.000 | - | - | {'root': 4418} |
| yolo_p2 | person | 7161 | 3576 | 0.5042 | 0.5014 | 0.9969 | 0.0028 |
| yolo_p2 | forklift | 5603 | 2245 | 0.5317 | 0.5285 | 0.7176 | 0.5725 |
| yolo_p2 | box | 69670 | 2266 | 0.0855 | 0.0841 | 0.7251 | 0.7343 |
| yolo_p2 | pallet | 14288 | 758 | 0.1261 | 0.1254 | 0.6992 | 0.7257 |
| yolo_p2 | trolley | 1060 | 0 | 0.0 | 0.0 | None | 0.8868 |
| yolo_p2 | all | 97628 | 8845 | 0.2184 | 0.2162 | 0.8309 | 0.6992 |
| yolo_p2 | load on moving forklift | 3028 | - | masked 0.718 | - | - | {'promoted': 2175, 'unpromoted': 853} |
| yolo_p2 | load on static forklift | 4418 | - | masked 0.560 | - | - | {'promoted': 2473, 'unpromoted': 1945} |
| yolo_p4 | person | 7161 | 3576 | 0.511 | 0.5084 | 0.9969 | 0.0299 |
| yolo_p4 | forklift | 5603 | 2245 | 0.5445 | 0.5413 | 0.7626 | 0.5685 |
| yolo_p4 | box | 69670 | 2266 | 0.0888 | 0.0875 | 0.7467 | 0.7378 |
| yolo_p4 | pallet | 14288 | 758 | 0.129 | 0.1283 | 0.7111 | 0.7281 |
| yolo_p4 | trolley | 1060 | 0 | 0.0 | 0.0 | None | 0.8868 |
| yolo_p4 | all | 97628 | 8845 | 0.2244 | 0.2222 | 0.8488 | 0.7032 |
| yolo_p4 | load on moving forklift | 3028 | - | masked 0.737 | - | - | {'promoted': 1721, 'root': 511, 'unpromoted': 796} |
| yolo_p4 | load on static forklift | 4418 | - | masked 0.557 | - | - | {'promoted': 2460, 'root': 1, 'unpromoted': 1957} |
| yolo_p4_nointer | person | 7161 | 3576 | 0.5153 | 0.5134 | 0.9857 | 0.0569 |
| yolo_p4_nointer | forklift | 5603 | 2245 | 0.9193 | 0.9161 | 0.3452 | 0.9795 |
| yolo_p4_nointer | box | 69670 | 2266 | 0.9575 | 0.9396 | 0.199 | 0.9997 |
| yolo_p4_nointer | pallet | 14288 | 758 | 0.9836 | 0.9524 | 0.0792 | 0.9999 |
| yolo_p4_nointer | trolley | 1060 | 0 | None | 0.0 | None | 1.0 |
| yolo_p4_nointer | all | 97628 | 8845 | 0.5856 | 0.5838 | 0.5439 | 0.9611 |
| yolo_p4_nointer | load on moving forklift | 3028 | - | masked 0.169 | - | - | {'root': 511, 'unpromoted': 2517} |
| yolo_p4_nointer | load on static forklift | 4418 | - | masked 0.000 | - | - | {'root': 1, 'unpromoted': 4417} |
| yolo_p4_noext | person | 7161 | 3576 | 0.5109 | 0.5081 | 0.9966 | 0.0296 |
| yolo_p4_noext | forklift | 5603 | 2245 | 0.5431 | 0.5398 | 0.7523 | 0.5719 |
| yolo_p4_noext | box | 69670 | 2266 | 0.0889 | 0.0875 | 0.7454 | 0.7385 |
| yolo_p4_noext | pallet | 14288 | 758 | 0.1294 | 0.1286 | 0.7124 | 0.7286 |
| yolo_p4_noext | trolley | 1060 | 0 | 0.0 | 0.0 | None | 0.8898 |
| yolo_p4_noext | all | 97628 | 8845 | 0.2242 | 0.222 | 0.8459 | 0.7039 |
| yolo_p4_noext | load on moving forklift | 3028 | - | masked 0.736 | - | - | {'promoted': 1719, 'root': 511, 'unpromoted': 798} |
| yolo_p4_noext | load on static forklift | 4418 | - | masked 0.559 | - | - | {'promoted': 2469, 'root': 1, 'unpromoted': 1948} |
| yolo_p6 | person | 7161 | 3576 | 0.511 | 0.5085 | 0.9969 | 0.0299 |
| yolo_p6 | forklift | 5603 | 2245 | 0.5878 | 0.5842 | 0.7604 | 0.6393 |
| yolo_p6 | box | 69670 | 2266 | 0.1818 | 0.1778 | 0.7039 | 0.8915 |
| yolo_p6 | pallet | 14288 | 758 | 0.2521 | 0.2504 | 0.6834 | 0.8852 |
| yolo_p6 | trolley | 1060 | 0 | 0.0 | 0.0 | None | 0.9629 |
| yolo_p6 | all | 97628 | 8845 | 0.356 | 0.3522 | 0.8349 | 0.8472 |
| yolo_p6 | load on moving forklift | 3028 | - | masked 0.698 | - | - | {'promoted': 1550, 'root': 564, 'unpromoted': 914} |
| yolo_p6 | load on static forklift | 4418 | - | masked 0.318 | - | - | {'promoted': 1404, 'root': 1, 'unpromoted': 3013} |
| yolo_coco_person_p4 | person | 4882 | 2635 | 0.5423 | 0.5418 | 1.0 | 0.0085 |
| yolo_coco_person_p4 | forklift | 523 | 451 | 0.8623 | 0.8623 | 1.0 | 0.0 |
| yolo_coco_person_p4 | box | 2 | 0 | 0.0 | 0.0 | None | 0.0 |
| yolo_coco_person_p4 | pallet | 2 | 0 | None | 0.0 | None | None |
| yolo_coco_person_p4 | all | 5406 | 3086 | 0.5733 | 0.5729 | 1.0 | 0.0082 |

## hall_t1_L3

| variant | class | n det | n moving | moving precision | precision incl FP det | moving recall | static kept |
|---|---|--:|--:|--:|--:|--:|--:|
| yolo_naive | person | 7101 | 3750 | 0.5335 | 0.5281 | 1.0 | 0.0 |
| yolo_naive | forklift | 7535 | 3406 | 0.462 | 0.452 | 1.0 | 0.0 |
| yolo_naive | box | 59324 | 2619 | 0.0451 | 0.0441 | 1.0 | 0.0 |
| yolo_naive | pallet | 12009 | 753 | 0.0636 | 0.0627 | 1.0 | 0.0 |
| yolo_naive | trolley | 1015 | 0 | 0.0 | 0.0 | None | 0.0 |
| yolo_naive | all | 86718 | 10528 | 0.1234 | 0.1214 | 1.0 | 0.0 |
| yolo_naive | load on moving forklift | 3377 | - | masked 1.000 | - | - | {'root': 3377} |
| yolo_naive | load on static forklift | 3763 | - | masked 1.000 | - | - | {'root': 3763} |
| yolo_p2 | person | 7101 | 3750 | 0.5334 | 0.5289 | 0.9952 | 0.0043 |
| yolo_p2 | forklift | 7535 | 3406 | 0.5678 | 0.5539 | 0.8934 | 0.416 |
| yolo_p2 | box | 59324 | 2619 | 0.0852 | 0.0829 | 0.6644 | 0.6634 |
| yolo_p2 | pallet | 12009 | 753 | 0.12 | 0.1186 | 0.6693 | 0.6665 |
| yolo_p2 | trolley | 1015 | 0 | 0.0 | 0.0 | None | 0.785 |
| yolo_p2 | all | 86718 | 10528 | 0.2426 | 0.2385 | 0.8567 | 0.6235 |
| yolo_p2 | load on moving forklift | 3377 | - | masked 0.665 | - | - | {'promoted': 2245, 'root': 2, 'unpromoted': 1130} |
| yolo_p2 | load on static forklift | 3763 | - | masked 0.660 | - | - | {'promoted': 2483, 'root': 2, 'unpromoted': 1278} |
| yolo_p4 | person | 7101 | 3750 | 0.5353 | 0.5314 | 0.9843 | 0.0229 |
| yolo_p4 | forklift | 7535 | 3406 | 0.4234 | 0.4141 | 0.3814 | 0.554 |
| yolo_p4 | box | 59324 | 2619 | 0.1005 | 0.0986 | 0.7213 | 0.6954 |
| yolo_p4 | pallet | 12009 | 753 | 0.1278 | 0.1271 | 0.6521 | 0.6976 |
| yolo_p4 | trolley | 1015 | 0 | 0.0 | 0.0 | None | 0.8935 |
| yolo_p4 | all | 86718 | 10528 | 0.2254 | 0.2226 | 0.7 | 0.6614 |
| yolo_p4 | load on moving forklift | 3377 | - | masked 0.705 | - | - | {'promoted': 1507, 'root': 874, 'unpromoted': 996} |
| yolo_p4 | load on static forklift | 3763 | - | masked 0.577 | - | - | {'promoted': 2066, 'root': 107, 'unpromoted': 1590} |
| yolo_p4_nointer | person | 7101 | 3750 | 0.5403 | 0.5377 | 0.9741 | 0.0522 |
| yolo_p4_nointer | forklift | 7535 | 3406 | 0.7918 | 0.7823 | 0.2681 | 0.9395 |
| yolo_p4_nointer | box | 59324 | 2619 | 0.6664 | 0.6603 | 0.2753 | 0.9935 |
| yolo_p4_nointer | pallet | 12009 | 753 | 0.6923 | 0.6892 | 0.2032 | 0.9939 |
| yolo_p4_nointer | trolley | 1015 | 0 | None | None | None | 1.0 |
| yolo_p4_nointer | all | 86718 | 10528 | 0.5902 | 0.588 | 0.5167 | 0.9495 |
| yolo_p4_nointer | load on moving forklift | 3377 | - | masked 0.259 | - | - | {'root': 874, 'unpromoted': 2503} |
| yolo_p4_nointer | load on static forklift | 3763 | - | masked 0.028 | - | - | {'root': 107, 'unpromoted': 3656} |
| yolo_p4_noext | person | 7101 | 3750 | 0.5346 | 0.5308 | 0.9816 | 0.0226 |
| yolo_p4_noext | forklift | 7535 | 3406 | 0.4398 | 0.4301 | 0.3755 | 0.5893 |
| yolo_p4_noext | box | 59324 | 2619 | 0.1009 | 0.099 | 0.7121 | 0.7005 |
| yolo_p4_noext | pallet | 12009 | 753 | 0.1262 | 0.1257 | 0.6401 | 0.6991 |
| yolo_p4_noext | trolley | 1015 | 0 | 0.0 | 0.0 | None | 0.8996 |
| yolo_p4_noext | all | 86718 | 10528 | 0.227 | 0.2242 | 0.6941 | 0.6673 |
| yolo_p4_noext | load on moving forklift | 3377 | - | masked 0.695 | - | - | {'promoted': 1475, 'root': 873, 'unpromoted': 1029} |
| yolo_p4_noext | load on static forklift | 3763 | - | masked 0.569 | - | - | {'promoted': 2033, 'root': 107, 'unpromoted': 1623} |
| yolo_p6 | person | 7101 | 3750 | 0.5358 | 0.5314 | 0.9859 | 0.0232 |
| yolo_p6 | forklift | 7535 | 3406 | 0.6308 | 0.6148 | 0.9266 | 0.5343 |
| yolo_p6 | box | 59324 | 2619 | 0.1789 | 0.1729 | 0.7919 | 0.8285 |
| yolo_p6 | pallet | 12009 | 753 | 0.2223 | 0.2198 | 0.7703 | 0.817 |
| yolo_p6 | trolley | 1015 | 0 | 0.0 | 0.0 | None | 0.857 |
| yolo_p6 | all | 86718 | 10528 | 0.3623 | 0.356 | 0.903 | 0.7762 |
| yolo_p6 | load on moving forklift | 3377 | - | masked 0.786 | - | - | {'promoted': 1747, 'root': 908, 'unpromoted': 722} |
| yolo_p6 | load on static forklift | 3763 | - | masked 0.464 | - | - | {'promoted': 1638, 'root': 109, 'unpromoted': 2016} |
| yolo_coco_person_p4 | person | 4815 | 2959 | 0.4575 | 0.4568 | 0.5164 | 0.0211 |
| yolo_coco_person_p4 | forklift | 162 | 80 | 0.4968 | 0.4875 | 0.975 | 0.0 |
| yolo_coco_person_p4 | box | 4 | 0 | 0.0 | 0.0 | None | 0.0 |
| yolo_coco_person_p4 | all | 4976 | 3039 | 0.459 | 0.4583 | 0.5285 | 0.0202 |
| yolo_coco_person_p4 | load on static forklift | 1 | - | masked 1.000 | - | - | {'root': 1} |
