# P5 mask quality vs VIODE GT segmentation (pixel level, summed over all frames). YOLO26s-seg TRT, conf 0.25.

yolo union = all YOLO vehicle masks (car/truck/bus/motorcycle/bicycle) vs GT all vehicles / GT dynamic vehicles. Variant rows: final left core (255) vs GT dynamic (P/R/IoU), core+band vs GT dynamic (recall), core vs GT all vehicles (P), right core vs GT right dynamic (P/R), masked core share of the image.

| seq | GT dyn px | yolo P/R (all veh) | yolo P/R (dyn) |
|---|--:|---|---|
| parking_lot_none | 0.00 % | 0.873 / 0.751 | 0.000 / - |
| parking_lot_low | 0.52 % | 0.904 / 0.857 | 0.489 / 0.965 |
| parking_lot_mid | 8.90 % | 0.925 / 0.594 | 0.862 / 0.584 |
| parking_lot_high | 10.51 % | 0.929 / 0.721 | 0.882 / 0.717 |
| city_day_none | 0.00 % | 0.903 / 0.894 | 0.000 / - |
| city_day_low | 0.58 % | 0.903 / 0.697 | 0.017 / 0.055 |
| city_day_mid | 2.80 % | 0.928 / 0.775 | 0.530 / 0.711 |
| city_day_high | 8.44 % | 0.935 / 0.546 | 0.698 / 0.486 |
| city_night_none | 0.00 % | 0.924 / 0.851 | 0.000 / - |
| city_night_low | 0.98 % | 0.923 / 0.917 | 0.695 / 0.940 |
| city_night_mid | 1.58 % | 0.915 / 0.850 | 0.744 / 0.847 |
| city_night_high | 3.51 % | 0.892 / 0.684 | 0.788 / 0.665 |

| seq | variant | core P (dyn) | core R (dyn) | core IoU (dyn) | core+band R (dyn) | core P (all veh) | right P/R (dyn) | core share |
|---|---|--:|--:|--:|--:|--:|---|--:|
| parking_lot_none | yolo_naive | 0.000 | - | 0.000 | - | 0.863 | 0.000 / - | 0.49 % |
| parking_lot_none | yolo_full_p2 | 0.000 | - | 0.000 | - | 0.863 | 0.000 / - | 0.49 % |
| parking_lot_none | yolo_p4_dyn | 0.000 | - | 0.000 | - | 0.863 | 0.000 / - | 0.49 % |
| parking_lot_none | yolo_p4_pot | 0.000 | - | 0.000 | - | 0.000 | 0.000 / - | 0.01 % |
| parking_lot_none | oracle_dynamic_warp | - | - | - | - | - | - / - | 0.00 % |
| parking_lot_none | oracle_all_vehicles_warp | 0.000 | - | 0.000 | - | 1.000 | 0.000 / - | 0.56 % |
| parking_lot_low | yolo_naive | 0.485 | 0.965 | 0.477 | 0.965 | 0.898 | 0.486 / 0.960 | 1.04 % |
| parking_lot_low | yolo_full_p2 | 0.485 | 0.965 | 0.477 | 0.971 | 0.898 | 0.486 / 0.960 | 1.04 % |
| parking_lot_low | yolo_p4_dyn | 0.485 | 0.965 | 0.477 | 0.971 | 0.898 | 0.485 / 0.964 | 1.04 % |
| parking_lot_low | yolo_p4_pot | 0.921 | 0.956 | 0.883 | 0.962 | 0.921 | 0.921 / 0.954 | 0.54 % |
| parking_lot_low | oracle_dynamic_warp | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.969 / 0.993 | 0.52 % |
| parking_lot_low | oracle_all_vehicles_warp | 0.480 | 1.000 | 0.480 | 1.000 | 1.000 | 0.460 / 0.993 | 1.09 % |
| parking_lot_mid | yolo_naive | 0.861 | 0.585 | 0.534 | 0.585 | 0.924 | 0.861 / 0.576 | 6.04 % |
| parking_lot_mid | yolo_full_p2 | 0.861 | 0.585 | 0.534 | 0.603 | 0.924 | 0.861 / 0.576 | 6.04 % |
| parking_lot_mid | yolo_p4_dyn | 0.861 | 0.585 | 0.534 | 0.603 | 0.924 | 0.860 / 0.577 | 6.04 % |
| parking_lot_mid | yolo_p4_pot | 0.926 | 0.527 | 0.505 | 0.543 | 0.926 | 0.925 / 0.520 | 5.06 % |
| parking_lot_mid | oracle_dynamic_warp | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.967 / 0.984 | 8.90 % |
| parking_lot_mid | oracle_all_vehicles_warp | 0.948 | 1.000 | 0.948 | 1.000 | 1.000 | 0.915 / 0.984 | 9.39 % |
| parking_lot_high | yolo_naive | 0.881 | 0.717 | 0.653 | 0.717 | 0.928 | 0.880 / 0.708 | 8.55 % |
| parking_lot_high | yolo_full_p2 | 0.881 | 0.717 | 0.653 | 0.734 | 0.928 | 0.880 / 0.708 | 8.55 % |
| parking_lot_high | yolo_p4_dyn | 0.881 | 0.717 | 0.653 | 0.734 | 0.928 | 0.879 / 0.708 | 8.55 % |
| parking_lot_high | yolo_p4_pot | 0.931 | 0.659 | 0.628 | 0.674 | 0.931 | 0.930 / 0.651 | 7.44 % |
| parking_lot_high | oracle_dynamic_warp | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.966 / 0.985 | 10.51 % |
| parking_lot_high | oracle_all_vehicles_warp | 0.956 | 1.000 | 0.956 | 1.000 | 1.000 | 0.922 / 0.985 | 11.00 % |
| city_day_none | yolo_naive | 0.000 | - | 0.000 | - | 0.897 | 0.000 / - | 1.91 % |
| city_day_none | yolo_full_p2 | 0.000 | - | 0.000 | - | 0.897 | 0.000 / - | 1.91 % |
| city_day_none | yolo_p4_dyn | 0.000 | - | 0.000 | - | 0.897 | 0.000 / - | 1.91 % |
| city_day_none | yolo_p4_pot | 0.000 | - | 0.000 | - | 0.637 | 0.000 / - | 0.04 % |
| city_day_none | oracle_dynamic_warp | - | - | - | - | - | - / - | 0.00 % |
| city_day_none | oracle_all_vehicles_warp | 0.000 | - | 0.000 | - | 1.000 | 0.000 / - | 1.92 % |
| city_day_low | yolo_naive | 0.016 | 0.055 | 0.013 | 0.055 | 0.898 | 0.016 / 0.054 | 1.93 % |
| city_day_low | yolo_full_p2 | 0.016 | 0.055 | 0.013 | 0.061 | 0.898 | 0.016 / 0.054 | 1.93 % |
| city_day_low | yolo_p4_dyn | 0.016 | 0.055 | 0.013 | 0.061 | 0.898 | 0.016 / 0.055 | 1.93 % |
| city_day_low | yolo_p4_pot | 0.403 | 0.048 | 0.045 | 0.053 | 0.783 | 0.402 / 0.048 | 0.07 % |
| city_day_low | oracle_dynamic_warp | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.992 / 0.982 | 0.58 % |
| city_day_low | oracle_all_vehicles_warp | 0.232 | 1.000 | 0.232 | 1.000 | 1.000 | 0.225 / 0.982 | 2.49 % |
| city_day_mid | yolo_naive | 0.528 | 0.711 | 0.435 | 0.711 | 0.926 | 0.531 / 0.708 | 3.76 % |
| city_day_mid | yolo_full_p2 | 0.528 | 0.711 | 0.435 | 0.735 | 0.926 | 0.531 / 0.708 | 3.76 % |
| city_day_mid | yolo_p4_dyn | 0.528 | 0.711 | 0.435 | 0.735 | 0.926 | 0.528 / 0.710 | 3.76 % |
| city_day_mid | yolo_p4_pot | 0.885 | 0.646 | 0.596 | 0.672 | 0.939 | 0.884 / 0.644 | 2.04 % |
| city_day_mid | oracle_dynamic_warp | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.984 / 0.989 | 2.80 % |
| city_day_mid | oracle_all_vehicles_warp | 0.622 | 1.000 | 0.622 | 1.000 | 1.000 | 0.610 / 0.989 | 4.50 % |
| city_day_high | yolo_naive | 0.697 | 0.486 | 0.401 | 0.486 | 0.933 | 0.698 / 0.481 | 5.88 % |
| city_day_high | yolo_full_p2 | 0.697 | 0.486 | 0.401 | 0.501 | 0.933 | 0.698 / 0.481 | 5.88 % |
| city_day_high | yolo_p4_dyn | 0.697 | 0.486 | 0.401 | 0.501 | 0.933 | 0.695 / 0.483 | 5.88 % |
| city_day_high | yolo_p4_pot | 0.924 | 0.382 | 0.370 | 0.392 | 0.944 | 0.924 / 0.380 | 3.48 % |
| city_day_high | oracle_dynamic_warp | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.986 / 0.985 | 8.44 % |
| city_day_high | oracle_all_vehicles_warp | 0.839 | 1.000 | 0.839 | 1.000 | 1.000 | 0.827 / 0.986 | 10.05 % |
| city_night_none | yolo_naive | 0.000 | - | 0.000 | - | 0.899 | 0.000 / - | 0.34 % |
| city_night_none | yolo_full_p2 | 0.000 | - | 0.000 | - | 0.899 | 0.000 / - | 0.34 % |
| city_night_none | yolo_p4_dyn | 0.000 | - | 0.000 | - | 0.899 | 0.000 / - | 0.34 % |
| city_night_none | yolo_p4_pot | 0.000 | - | 0.000 | - | 0.464 | 0.000 / - | 0.02 % |
| city_night_none | oracle_dynamic_warp | - | - | - | - | - | - / - | 0.00 % |
| city_night_none | oracle_all_vehicles_warp | 0.000 | - | 0.000 | - | 1.000 | 0.000 / - | 0.36 % |
| city_night_low | yolo_naive | 0.691 | 0.940 | 0.662 | 0.940 | 0.918 | 0.691 / 0.937 | 1.34 % |
| city_night_low | yolo_full_p2 | 0.691 | 0.940 | 0.662 | 0.956 | 0.918 | 0.691 / 0.937 | 1.34 % |
| city_night_low | yolo_p4_dyn | 0.691 | 0.940 | 0.662 | 0.956 | 0.918 | 0.689 / 0.937 | 1.34 % |
| city_night_low | yolo_p4_pot | 0.913 | 0.903 | 0.832 | 0.919 | 0.915 | 0.912 / 0.900 | 0.97 % |
| city_night_low | oracle_dynamic_warp | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.978 / 0.986 | 0.98 % |
| city_night_low | oracle_all_vehicles_warp | 0.734 | 1.000 | 0.734 | 1.000 | 1.000 | 0.713 / 0.986 | 1.34 % |
| city_night_mid | yolo_naive | 0.741 | 0.847 | 0.653 | 0.847 | 0.911 | 0.740 / 0.844 | 1.81 % |
| city_night_mid | yolo_full_p2 | 0.741 | 0.847 | 0.653 | 0.866 | 0.911 | 0.740 / 0.844 | 1.81 % |
| city_night_mid | yolo_p4_dyn | 0.741 | 0.847 | 0.653 | 0.866 | 0.911 | 0.739 / 0.844 | 1.81 % |
| city_night_mid | yolo_p4_pot | 0.905 | 0.813 | 0.749 | 0.831 | 0.909 | 0.903 / 0.810 | 1.42 % |
| city_night_mid | oracle_dynamic_warp | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.977 / 0.988 | 1.58 % |
| city_night_mid | oracle_all_vehicles_warp | 0.816 | 1.000 | 0.815 | 1.000 | 1.000 | 0.793 / 0.988 | 1.94 % |
| city_night_high | yolo_naive | 0.786 | 0.665 | 0.564 | 0.665 | 0.890 | 0.786 / 0.662 | 2.97 % |
| city_night_high | yolo_full_p2 | 0.786 | 0.665 | 0.564 | 0.682 | 0.890 | 0.786 / 0.662 | 2.97 % |
| city_night_high | yolo_p4_dyn | 0.786 | 0.665 | 0.564 | 0.682 | 0.890 | 0.785 / 0.665 | 2.97 % |
| city_night_high | yolo_p4_pot | 0.899 | 0.604 | 0.566 | 0.616 | 0.902 | 0.898 / 0.603 | 2.35 % |
| city_night_high | oracle_dynamic_warp | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.976 / 0.987 | 3.50 % |
| city_night_high | oracle_all_vehicles_warp | 0.908 | 1.000 | 0.907 | 1.000 | 1.000 | 0.884 / 0.987 | 3.86 % |
