# mask quality vs GT (offline): left core (255) vs GT moving pixels (precision / recall / IoU), core+band recall, right core vs GT right moving pixels (stereo warp for every variant offline), core / band / masked-static-potential share of the image

| seq | variant | L core P | L core R | L IoU | L core+band R | R core P | R core R | core % | band % | static-potential masked % |
|---|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| aisles_t1_L0 | yolo_naive | 0.0 | None | 0.0 | None | 0.0 | None | 18.16 | 0.00 | 17.54 |
| aisles_t1_L0 | yolo_p2 | 0.0 | None | 0.0 | None | 0.0 | None | 0.08 | 0.06 | 0.07 |
| aisles_t1_L0 | yolo_p4 | 0.0 | None | 0.0 | None | 0.0 | None | 0.07 | 0.05 | 0.07 |
| aisles_t1_L0 | yolo_p4_nointer | 0.0 | None | 0.0 | None | 0.0 | None | 0.01 | 0.01 | 0.00 |
| aisles_t1_L0 | yolo_p4_noext | 0.0 | None | 0.0 | None | 0.0 | None | 0.07 | 0.00 | 0.07 |
| aisles_t1_L0 | yolo_p6 | 0.0 | None | 0.0 | None | 0.0 | None | 0.04 | 0.04 | 0.03 |
| aisles_t1_L0 | yolo_coco_person_p4 | 0.0 | None | 0.0 | None | 0.0 | None | 0.00 | 0.00 | 0.00 |
| aisles_t1_L0 | oracle_moving_warp | None | None | None | None | None | None | 0.00 | 0.00 | 0.00 |
| aisles_t1_L0 | oracle_class_naive_warp | 0.0 | None | 0.0 | None | 0.0 | None | 19.12 | 0.00 | 19.12 |
| aisles_t1_L1 | yolo_naive | 0.0542 | 0.9596 | 0.0541 | 0.9596 | 0.0541 | 0.9241 | 19.88 | 0.00 | 18.07 |
| aisles_t1_L1 | yolo_p2 | 0.2177 | 0.9583 | 0.2156 | 0.9977 | 0.2157 | 0.9226 | 4.95 | 2.97 | 3.68 |
| aisles_t1_L1 | yolo_p4 | 0.2393 | 0.9582 | 0.2368 | 0.9976 | 0.2359 | 0.9225 | 4.50 | 2.90 | 3.24 |
| aisles_t1_L1 | yolo_p4_nointer | 0.5205 | 0.9546 | 0.5079 | 0.9972 | 0.5028 | 0.9144 | 2.06 | 1.94 | 0.87 |
| aisles_t1_L1 | yolo_p4_noext | 0.2389 | 0.9583 | 0.2364 | 0.9583 | 0.2356 | 0.9222 | 4.51 | 0.00 | 3.25 |
| aisles_t1_L1 | yolo_p6 | 0.3472 | 0.9582 | 0.342 | 0.9976 | 0.341 | 0.9224 | 3.10 | 2.45 | 1.88 |
| aisles_t1_L1 | yolo_coco_person_p4 | 0.504 | 0.9808 | 0.4991 | 0.9979 | 0.4945 | 0.9481 | 2.19 | 1.95 | 0.88 |
| aisles_t1_L1 | oracle_moving_warp | 1.0 | 1.0 | 1.0 | 1.0 | 0.9524 | 0.9372 | 1.12 | 0.00 | 0.00 |
| aisles_t1_L1 | oracle_class_naive_warp | 0.054 | 1.0 | 0.054 | 1.0 | 0.0527 | 0.9438 | 20.78 | 0.00 | 19.66 |
| aisles_t1_L2 | yolo_naive | 0.1655 | 0.963 | 0.1645 | 0.963 | 0.1676 | 0.9365 | 23.08 | 0.00 | 18.03 |
| aisles_t1_L2 | yolo_p2 | 0.4213 | 0.8669 | 0.3957 | 0.9011 | 0.4209 | 0.8433 | 8.16 | 4.28 | 4.08 |
| aisles_t1_L2 | yolo_p4 | 0.4636 | 0.9132 | 0.444 | 0.9478 | 0.4606 | 0.887 | 7.81 | 4.31 | 3.54 |
| aisles_t1_L2 | yolo_p4_nointer | 0.6765 | 0.7128 | 0.5316 | 0.7804 | 0.6558 | 0.687 | 4.18 | 2.98 | 0.93 |
| aisles_t1_L2 | yolo_p4_noext | 0.4633 | 0.915 | 0.4442 | 0.915 | 0.4604 | 0.8887 | 7.83 | 0.00 | 3.55 |
| aisles_t1_L2 | yolo_p6 | 0.5776 | 0.9134 | 0.5477 | 0.9486 | 0.5708 | 0.8872 | 6.27 | 3.79 | 2.03 |
| aisles_t1_L2 | yolo_coco_person_p4 | 0.5372 | 0.3039 | 0.2408 | 0.3671 | 0.5284 | 0.292 | 2.24 | 2.15 | 0.84 |
| aisles_t1_L2 | oracle_moving_warp | 1.0 | 0.9996 | 0.9996 | 0.9996 | 0.8759 | 0.9553 | 3.97 | 0.00 | 0.00 |
| aisles_t1_L2 | oracle_class_naive_warp | 0.1679 | 0.9996 | 0.1678 | 0.9996 | 0.1644 | 0.9574 | 23.63 | 0.00 | 19.66 |
| aisles_t1_L3 | yolo_naive | 0.4371 | 0.9679 | 0.4308 | 0.9679 | 0.4383 | 0.9507 | 36.96 | 0.00 | 17.68 |
| aisles_t1_L3 | yolo_p2 | 0.6276 | 0.9337 | 0.6008 | 0.9642 | 0.6181 | 0.9188 | 24.83 | 8.81 | 6.64 |
| aisles_t1_L3 | yolo_p4 | 0.5201 | 0.4048 | 0.2947 | 0.491 | 0.5186 | 0.3931 | 12.99 | 6.84 | 5.14 |
| aisles_t1_L3 | yolo_p4_nointer | 0.735 | 0.3529 | 0.313 | 0.4409 | 0.7215 | 0.3411 | 8.01 | 5.12 | 1.30 |
| aisles_t1_L3 | yolo_p4_noext | 0.52 | 0.4048 | 0.2947 | 0.4048 | 0.5184 | 0.3931 | 12.99 | 0.00 | 5.15 |
| aisles_t1_L3 | yolo_p6 | 0.6955 | 0.914 | 0.6527 | 0.947 | 0.6788 | 0.8977 | 21.93 | 8.31 | 4.17 |
| aisles_t1_L3 | yolo_coco_person_p4 | 0.6055 | 0.1078 | 0.1007 | 0.186 | 0.6064 | 0.105 | 2.97 | 3.57 | 0.96 |
| aisles_t1_L3 | oracle_moving_warp | 1.0 | 0.9998 | 0.9998 | 0.9998 | 0.839 | 0.9626 | 16.69 | 0.00 | 0.00 |
| aisles_t1_L3 | oracle_class_naive_warp | 0.4638 | 0.9998 | 0.4637 | 0.9998 | 0.4351 | 0.9641 | 35.98 | 0.00 | 19.30 |
| hall_t1_L0 | yolo_naive | 0.0 | None | 0.0 | None | 0.0 | None | 5.46 | 0.00 | 5.20 |
| hall_t1_L0 | yolo_p2 | 0.0 | None | 0.0 | None | 0.0 | None | 0.02 | 0.01 | 0.02 |
| hall_t1_L0 | yolo_p4 | 0.0 | None | 0.0 | None | 0.0 | None | 0.02 | 0.01 | 0.02 |
| hall_t1_L0 | yolo_p4_nointer | 0.0 | None | 0.0 | None | 0.0 | None | 0.00 | 0.00 | 0.00 |
| hall_t1_L0 | yolo_p4_noext | 0.0 | None | 0.0 | None | 0.0 | None | 0.02 | 0.00 | 0.01 |
| hall_t1_L0 | yolo_p6 | 0.0 | None | 0.0 | None | 0.0 | None | 0.03 | 0.02 | 0.03 |
| hall_t1_L0 | yolo_coco_person_p4 | 0.0 | None | 0.0 | None | 0.0 | None | 0.00 | 0.00 | 0.00 |
| hall_t1_L0 | oracle_moving_warp | None | None | None | None | None | None | 0.00 | 0.00 | 0.00 |
| hall_t1_L0 | oracle_class_naive_warp | 0.0 | None | 0.0 | None | 0.0 | None | 5.87 | 0.00 | 5.87 |
| hall_t1_L1 | yolo_naive | 0.1216 | 0.9742 | 0.1212 | 0.9742 | 0.1228 | 0.9639 | 7.19 | 0.00 | 5.96 |
| hall_t1_L1 | yolo_p2 | 0.3007 | 0.9731 | 0.2983 | 0.9989 | 0.3012 | 0.963 | 2.90 | 2.39 | 1.88 |
| hall_t1_L1 | yolo_p4 | 0.3354 | 0.9731 | 0.3323 | 0.9989 | 0.3357 | 0.963 | 2.60 | 2.23 | 1.59 |
| hall_t1_L1 | yolo_p4_nointer | 0.5053 | 0.9713 | 0.4979 | 0.9988 | 0.5003 | 0.9608 | 1.72 | 1.80 | 0.74 |
| hall_t1_L1 | yolo_p4_noext | 0.3353 | 0.9732 | 0.3322 | 0.9732 | 0.3355 | 0.9631 | 2.60 | 0.00 | 1.59 |
| hall_t1_L1 | yolo_p6 | 0.3828 | 0.973 | 0.3788 | 0.9989 | 0.3835 | 0.963 | 2.28 | 2.05 | 1.27 |
| hall_t1_L1 | yolo_coco_person_p4 | 0.4774 | 0.9901 | 0.4751 | 0.9987 | 0.4742 | 0.981 | 1.86 | 1.78 | 0.78 |
| hall_t1_L1 | oracle_moving_warp | 1.0 | 1.0 | 1.0 | 1.0 | 0.9683 | 0.9736 | 0.90 | 0.00 | 0.00 |
| hall_t1_L1 | oracle_class_naive_warp | 0.119 | 1.0 | 0.119 | 1.0 | 0.1174 | 0.9749 | 7.54 | 0.00 | 6.64 |
| hall_t1_L2 | yolo_naive | 0.3677 | 0.9673 | 0.3631 | 0.9673 | 0.3671 | 0.9557 | 13.73 | 0.00 | 7.37 |
| hall_t1_L2 | yolo_p2 | 0.4769 | 0.8105 | 0.429 | 0.8557 | 0.4754 | 0.8033 | 8.87 | 5.00 | 3.68 |
| hall_t1_L2 | yolo_p4 | 0.4984 | 0.8291 | 0.452 | 0.8782 | 0.4947 | 0.8187 | 8.68 | 4.99 | 3.37 |
| hall_t1_L2 | yolo_p4_nointer | 0.6793 | 0.5308 | 0.4244 | 0.6196 | 0.6648 | 0.521 | 4.08 | 3.40 | 0.87 |
| hall_t1_L2 | yolo_p4_noext | 0.4975 | 0.8232 | 0.4495 | 0.8232 | 0.4939 | 0.8127 | 8.64 | 0.00 | 3.36 |
| hall_t1_L2 | yolo_p6 | 0.5497 | 0.8267 | 0.4929 | 0.8769 | 0.5456 | 0.8163 | 7.85 | 4.80 | 2.57 |
| hall_t1_L2 | yolo_coco_person_p4 | 0.4953 | 0.21 | 0.173 | 0.2995 | 0.4946 | 0.2101 | 2.21 | 2.35 | 0.92 |
| hall_t1_L2 | oracle_moving_warp | 1.0 | 0.9996 | 0.9996 | 0.9996 | 0.8748 | 0.9741 | 5.22 | 0.00 | 0.00 |
| hall_t1_L2 | oracle_class_naive_warp | 0.3923 | 0.9996 | 0.3922 | 0.9996 | 0.3659 | 0.9746 | 13.30 | 0.00 | 8.08 |
| hall_t1_L3 | yolo_naive | 0.6322 | 0.9768 | 0.6229 | 0.9768 | 0.6286 | 0.9548 | 38.59 | 0.00 | 8.66 |
| hall_t1_L3 | yolo_p2 | 0.688 | 0.9296 | 0.6539 | 0.9528 | 0.683 | 0.9123 | 33.75 | 8.80 | 5.37 |
| hall_t1_L3 | yolo_p4 | 0.5466 | 0.3043 | 0.243 | 0.4174 | 0.5411 | 0.2951 | 13.91 | 8.01 | 4.69 |
| hall_t1_L3 | yolo_p4_nointer | 0.6678 | 0.2454 | 0.2187 | 0.3623 | 0.6533 | 0.2378 | 9.18 | 6.96 | 1.95 |
| hall_t1_L3 | yolo_p4_noext | 0.5574 | 0.3011 | 0.243 | 0.3011 | 0.5499 | 0.2913 | 13.49 | 0.00 | 4.41 |
| hall_t1_L3 | yolo_p6 | 0.7158 | 0.9319 | 0.6802 | 0.9593 | 0.7089 | 0.9116 | 32.52 | 8.94 | 4.19 |
| hall_t1_L3 | yolo_coco_person_p4 | 0.4995 | 0.0399 | 0.0383 | 0.0905 | 0.4979 | 0.0389 | 1.99 | 2.71 | 0.89 |
| hall_t1_L3 | oracle_moving_warp | 1.0 | 0.9999 | 0.9999 | 0.9999 | 0.8286 | 0.9627 | 24.98 | 0.00 | 0.00 |
| hall_t1_L3 | oracle_class_naive_warp | 0.7272 | 0.9999 | 0.7271 | 0.9999 | 0.6346 | 0.9645 | 34.35 | 0.00 | 9.37 |

# YOLO detection pixels vs GT class pixels (all / moving instances): fine-tuned (wh) vs COCO person

| seq | model | class | P all | R all | IoU all | R moving |
|---|---|---|--:|--:|--:|--:|
| aisles_t1_L0 | wh | person | 0.0 | None | 0.0 | None |
| aisles_t1_L0 | wh | forklift | 0.7841 | 0.9156 | 0.7312 | None |
| aisles_t1_L0 | wh | box | 0.9757 | 0.8996 | 0.8799 | None |
| aisles_t1_L0 | wh | pallet | 0.9304 | 0.9069 | 0.8493 | None |
| aisles_t1_L0 | wh | trolley | 0.7042 | 0.8883 | 0.6469 | None |
| aisles_t1_L0 | coco | person | 0.0 | None | 0.0 | None |
| aisles_t1_L1 | wh | person | 0.9324 | 0.9523 | 0.8908 | 0.9546 |
| aisles_t1_L1 | wh | forklift | 0.7845 | 0.9136 | 0.7303 | None |
| aisles_t1_L1 | wh | box | 0.9746 | 0.8984 | 0.8778 | None |
| aisles_t1_L1 | wh | pallet | 0.9313 | 0.9064 | 0.8496 | None |
| aisles_t1_L1 | wh | trolley | 0.7089 | 0.8977 | 0.6559 | None |
| aisles_t1_L1 | coco | person | 0.8924 | 0.9656 | 0.8649 | 0.9808 |
| aisles_t1_L2 | wh | person | 0.9286 | 0.9455 | 0.8813 | 0.9469 |
| aisles_t1_L2 | wh | forklift | 0.8135 | 0.9391 | 0.7727 | 0.9659 |
| aisles_t1_L2 | wh | box | 0.9742 | 0.8971 | 0.8762 | 0.836 |
| aisles_t1_L2 | wh | pallet | 0.9301 | 0.9044 | 0.8468 | 0.8717 |
| aisles_t1_L2 | wh | trolley | 0.6588 | 0.8856 | 0.6071 | None |
| aisles_t1_L2 | coco | person | 0.8805 | 0.9402 | 0.8339 | 0.9455 |
| aisles_t1_L3 | wh | person | 0.9274 | 0.9276 | 0.8648 | 0.9398 |
| aisles_t1_L3 | wh | forklift | 0.8454 | 0.9578 | 0.815 | 0.9659 |
| aisles_t1_L3 | wh | box | 0.9704 | 0.894 | 0.8703 | 0.7865 |
| aisles_t1_L3 | wh | pallet | 0.9273 | 0.898 | 0.839 | 0.8667 |
| aisles_t1_L3 | wh | trolley | 0.6502 | 0.9215 | 0.6161 | None |
| aisles_t1_L3 | coco | person | 0.8708 | 0.8923 | 0.788 | 0.9032 |
| hall_t1_L0 | wh | person | 0.0 | None | 0.0 | None |
| hall_t1_L0 | wh | forklift | 0.7668 | 0.8862 | 0.6981 | None |
| hall_t1_L0 | wh | box | 0.9759 | 0.8288 | 0.8122 | None |
| hall_t1_L0 | wh | pallet | 0.8972 | 0.8318 | 0.7594 | None |
| hall_t1_L0 | wh | trolley | 0.7069 | 0.7072 | 0.5469 | None |
| hall_t1_L0 | coco | person | 0.0 | None | 0.0 | None |
| hall_t1_L1 | wh | person | 0.9363 | 0.966 | 0.9065 | 0.9713 |
| hall_t1_L1 | wh | forklift | 0.7671 | 0.8803 | 0.6947 | None |
| hall_t1_L1 | wh | box | 0.9746 | 0.8277 | 0.8102 | None |
| hall_t1_L1 | wh | pallet | 0.8962 | 0.8281 | 0.7556 | None |
| hall_t1_L1 | wh | trolley | 0.7121 | 0.686 | 0.5371 | None |
| hall_t1_L1 | coco | person | 0.8892 | 0.9762 | 0.8703 | 0.9901 |
| hall_t1_L2 | wh | person | 0.9224 | 0.9486 | 0.8784 | 0.9506 |
| hall_t1_L2 | wh | forklift | 0.8105 | 0.949 | 0.7767 | 0.9638 |
| hall_t1_L2 | wh | box | 0.9739 | 0.8341 | 0.8159 | 0.8776 |
| hall_t1_L2 | wh | pallet | 0.8897 | 0.8449 | 0.7648 | 0.9033 |
| hall_t1_L2 | wh | trolley | 0.7149 | 0.6769 | 0.533 | None |
| hall_t1_L2 | coco | person | 0.8566 | 0.9213 | 0.7982 | 0.9356 |
| hall_t1_L3 | wh | person | 0.9213 | 0.9264 | 0.8585 | 0.9263 |
| hall_t1_L3 | wh | forklift | 0.814 | 0.9688 | 0.7932 | 0.9743 |
| hall_t1_L3 | wh | box | 0.9712 | 0.8426 | 0.8221 | 0.9001 |
| hall_t1_L3 | wh | pallet | 0.8903 | 0.8486 | 0.7682 | 0.8791 |
| hall_t1_L3 | wh | trolley | 0.7163 | 0.6559 | 0.5207 | None |
| hall_t1_L3 | coco | person | 0.8835 | 0.8692 | 0.7798 | 0.8767 |
