# SAVIOR-Warehouse dataset: build report and sanity runs

Date: 2026-10-15. Dataset agent J; report saved by the coordinator.
- Code: `src/savior/savior_datasets/warehouse/` (README documents regeneration).
- Data: `data/warehouse/`.

## Dataset
- **Content:** 2 trajectories × 4 dynamic levels = 8 stereo-inertial sequences of about 110 s each, plus a 2720-image segmentation training set (COCO + YOLO export).
- **Rig:** ZED 2i 4 mm-lens variant (672×376, fx 470, 72°×44° FOV, 0.12 m baseline, 20 Hz), on a drone with quadrotor-flatness attitude. It hovers still for 3 s, then takes off with a 0.3 m climb.
  - The 4 mm lens is the default because the 2.1 mm lens only reached 6.7 % coverage on L3. The 2.1 mm rig stays available as an option.
  - The climb gives the IMU enough excitation for OpenVINS static init. Static init fires 0.6 s after take-off in every run.
- **IMU:** analytic, from a C²-smooth spline. Clean, noisy (BMI085-class model) and bias-truth streams.
- **Ground truth:** IMU pose (TUM), kalibr calibration, instance segmentation with per-instance class and moving flag, depth, and per-frame moving coverage.
- **Scenes:** both use `full_warehouse.usd`.
  - Scene A (aisles): objects cross the camera path.
  - Scene B (hall): a populated south hall, with objects moving parallel to the camera.
- **Dynamic levels:**
  - L0: static, including parked driverless forklifts, pallets and boxes;
  - L1: walking people;
  - L2: people plus forklifts with drivers carrying boxes (person → forklift → box chain);
  - L3: high, including a forklift co-moving ahead of the camera.
- **Checks:**
  - Clean gyro vs differentiated GT: RMS 1.6e-5 rad/s. Clean accel: RMS 2.9e-5 m/s².
  - Dead reckoning from the clean IMU: ≤ 1.5 mm per 10 s.
  - Noise statistics match the config within 1 %.
  - Stereo and reprojection geometry are verified with the GT depth and poses.
- **Size and speed:** about 18 GB total; rendering runs at 4.5–5.6 stereo frames/s.

## Sequences and stock-OpenVINS sanity runs
ATE is posyaw RMSE in m, at bag start offsets 0 / 0.3 / 0.6 s.

| sequence | moving coverage mean (p90) | features on movers | OpenVINS ATE [m] | oracle moving masks ATE [m] |
|---|---|---|---|---|
| aisles_t1_L0 | 0 | 0 | 0.047 / 0.162 / 0.062 | |
| aisles_t1_L1 | 1.1 % (3.1) | 2.9 % | 0.101 / 0.100 / 0.103 | |
| aisles_t1_L2 | 4.0 % (7.5) | 8.1 % | 0.246 / 0.166 / 0.229 | |
| aisles_t1_L3 | 16.7 % (29.6) | 17.6 % | 0.220 / 0.148 / 0.148 | 0.116 / 0.114 / 0.115 |
| hall_t1_L0 | 0 | 0 | 0.137 / 0.142 / 0.101 | |
| hall_t1_L1 | 0.9 % (3.2) | 4.1 % | 0.091 / 0.175 / 0.144 | |
| hall_t1_L2 | 5.2 % (11.0) | 15.2 % | 0.230 / 0.153 / 0.133 | |
| hall_t1_L3 | 25.0 % (33.9) | 31.3 % (89 % of frames > 10 %) | 5.23 / 4.87 / 3393 (diverged) | 0.147 / 0.160 / 0.180 |

- **Hall L3 failure:** a forklift co-moving 3.7 m ahead, plus others driving alongside, makes the filter believe it is standing still. The estimated speed drops to about 0.05 m/s, against a true 1 m/s.
- **Oracle path:** works end to end, with 4352/4352 masks matched exactly and 0 fallbacks.
- **Caveat:** these are 3-run sanity checks, not the benchmark. That needs ≥ 10 offsets, the compat control, and YOLO + P4 variants.

## Open items
- No optical flow, rotor drag, motion blur or rolling shutter.
- Coverage is below target for aisles L2 (4.0 %), and L1 is at the low end (about 1 %).
- Trolley is the rarest class in the segmentation set (813 train instances).
- YOLO26-seg has not been fine-tuned yet (the export is ready).
- Forklift B has broken textures, and the forklift wheels don't turn (the body is a single mesh).
- Bringup presets `warehouse` / `warehouse_moving` were added, and a private overlay install was built (`install_warehouse/`). The main install must be rebuilt to include the presets.
