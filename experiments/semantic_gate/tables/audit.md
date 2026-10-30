# SG study audit (t1)

valid = clean exit, trajectory, FINAL fallbacks = late = 0, n_in_core = 0, poses >= OpenVINS-v2 - 1. identical = byte-identical trajectory vs the reference (ctl_*: backend_v2 frozen run of the base method; sg m_b != m_s: the m_b = m_s twin). band tests = band-labelled chi2 tests (MSCKF + SLAM) over the runs.

| variant | runs | valid | identical / compared | band-labelled chi2 tests |
|---|--:|--:|--:|--:|
| ctl_openvins | 24 | 24 | 24 / 24 | 0 |
| ctl_savior_none | 24 | 24 | 24 / 24 | 0 |
| ctl_sens_fix1 | 24 | 24 | 24 / 24 | 0 |
| ctl_sf1_ms64 | 24 | 24 | 24 / 24 | 0 |
| ov_nis | 80 | 80 | - | 0 |
| sf1_chibest | 80 | 80 | - | 0 |
| sf1_nis | 80 | 80 | - | 0 |
| sg_s025_b025_kb0 | 80 | 80 | - | 0 |
| sg_s025_b025_kb1 | 80 | 80 | - | 0 |
| sg_s025_b050_kb0 | 20 | 20 | 20 / 20 | 0 |
| sg_s025_b050_kb1 | 20 | 20 | 20 / 20 | 0 |
| sg_s050_b025_kb0 | 20 | 20 | 20 / 20 | 0 |
| sg_s050_b025_kb1 | 20 | 20 | 20 / 20 | 0 |
| sg_s050_b050_kb0 | 80 | 80 | - | 0 |
| sg_s050_b050_kb1 | 80 | 80 | - | 0 |
