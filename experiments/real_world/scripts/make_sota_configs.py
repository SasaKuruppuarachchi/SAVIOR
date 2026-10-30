#!/usr/bin/env python3
"""make_sota_configs.py : src/savior/sota/config/monado/{vins_fusion,dynavins} from the frozen VIODE SOTA configs + the Monado
Valve Index calibration.json (KANNALA_BRANDT intrinsics, body_T_cam = Basalt T_i_c, g_norm 9.558 = measured
static accelerometer norm, freq = half the 54 Hz camera rate as VIODE 10 for 20 Hz, image size). Nothing else changes.
FREEZE_AMENDMENT A2 (results/real_world/FREEZE_AMENDMENT.txt): the IMU noise is no longer the Basalt densities verbatim but
the SAVIOR-Warehouse SOTA derivation (src/savior/sota/config/warehouse/*: upstream VINS-Fusion EuRoC value x dataset density /
EuRoC kalibr density, keeping the upstream hand inflation; VINS treats acc_n/gyr_n as inflated discrete stds, so the raw
densities made the IMU 50-60x over-confident: DynaVINS diverged to 144 m ATE and VINS-Fusion gave 0.46 m on the static MIO07)."""
import json, re
import numpy as np
WS = '/home/sasa/workspace/savior_ws'
SC = f'{WS}/src/savior/sota/config'
C = json.load(open(f'{WS}/data/monado/raw/calibration.json'))['value0']


def T(d):
    w, x, y, z = d['qw'], d['qx'], d['qy'], d['qz']
    n = (w * w + x * x + y * y + z * z) ** .5
    w, x, y, z = w / n, x / n, y / n, z / n
    R = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)], [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                  [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
    M = np.eye(4); M[:3, :3] = R; M[:3, 3] = [d['px'], d['py'], d['pz']]
    return M


for k in range(2):
    ii = C['intrinsics'][k]['intrinsics']
    s = (f"%YAML:1.0\n---\n# Monado MSD Valve Index cam{k}: dataset calibration.json (Basalt kb4 = camodocal KANNALA_BRANDT, k1..k4 -> k2..k5)\n"
         f"model_type: KANNALA_BRANDT\ncamera_name: camera\nimage_width: 960\nimage_height: 960\nprojection_parameters:\n"
         f"   k2: {ii['k1']!r}\n   k3: {ii['k2']!r}\n   k4: {ii['k3']!r}\n   k5: {ii['k4']!r}\n"
         f"   mu: {ii['fx']!r}\n   mv: {ii['fy']!r}\n   u0: {ii['cx']!r}\n   v0: {ii['cy']!r}\n")
    for d in ('vins_fusion', 'dynavins'):
        open(f'{SC}/monado/{d}/cam{k}_kb.yaml', 'w').write(s)


def mat(M):
    return 'data: [' + ',\n          '.join(', '.join(f'{v:.12f}' for v in M[r]) for r in range(4)) + ']'


# A2: the warehouse rule (upstream VINS-Fusion EuRoC values scaled by dataset density / EuRoC kalibr density)
NZ = dict(acc_n=0.1 * C['accel_noise_std'][0] / 2.0e-3, gyr_n=0.01 * C['gyro_noise_std'][0] / 1.6968e-4,
          acc_w=0.001 * C['accel_bias_std'][0] / 3.0e-3, gyr_w=1.0e-4 * C['gyro_bias_std'][0] / 1.9393e-5)


for d, src in (('vins_fusion', 'viode/vins_fusion/calibration.yaml'), ('dynavins', 'viode/dynavins/calibration_stereo.yaml')):
    s = open(f'{SC}/{src}').read()
    s = s.replace('cam0_pinhole.yaml', 'cam0_kb.yaml').replace('cam1_pinhole.yaml', 'cam1_kb.yaml')
    s = re.sub(r'image_width: \d+', 'image_width: 960', s)
    s = re.sub(r'image_height: \d+', 'image_height: 960', s)
    for k in range(2):
        s, n = re.subn(r'(body_T_cam%d: !!opencv-matrix\s+rows: 4\s+cols: 4\s+dt: d\s+)data: \[[^\]]*\]' % k,
                       lambda m: m.group(1) + mat(T(C['T_imu_cam'][k])), s)
        assert n == 1
    for key, val in (('freq', '27                # half the 54 Hz camera rate (VIODE 10 for 20 Hz)'),
                     ('acc_n', f"{NZ['acc_n']:.4g}         # A2: 0.1 x {C['accel_noise_std'][0]!r} / 2.0e-3 (EuRoC VINS x Monado/EuRoC density)"),
                     ('gyr_n', f"{NZ['gyr_n']:.4g}      # A2: 0.01 x {C['gyro_noise_std'][0]!r} / 1.6968e-4"),
                     ('acc_w', f"{NZ['acc_w']:.4g}    # A2: 0.001 x {C['accel_bias_std'][0]!r} / 3.0e-3"),
                     ('gyr_w', f"{NZ['gyr_w']:.4g}    # A2: 1.0e-4 x {C['gyro_bias_std'][0]!r} / 1.9393e-5"),
                     ('g_norm', '9.558     # measured static accelerometer norm of the released data (= OpenVINS gravity_mag)')):
        s, n = re.subn(r'^%s:.*' % key, f'{key}: {val}', s, flags=re.M)
        assert n == 1, key
    hdr = ("%YAML:1.0\n# SAVIOR real-world study (results/real_world): Monado MSD Valve Index. = the frozen VIODE config\n"
           f"# src/savior/sota/config/{src} with ONLY the dataset calibration (KANNALA_BRANDT, body_T_cam, IMU noise by the\n"
           "# warehouse density-ratio rule = FREEZE_AMENDMENT A2, g_norm), image size and freq changed (scripts/make_sota_configs.py).\n")
    s = s.replace('%YAML:1.0\n', hdr, 1)
    open(f'{SC}/monado/{d}/' + src.split('/')[-1], 'w').write(s)
print('ok')
