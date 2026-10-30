#!/usr/bin/env python3
"""equiv_tables.py <equiv dir> <out tables dir>: Markdown + JSON tables of the offline Python <-> C++ equivalence runs
(equiv_offline.py outputs <equiv dir>/<run set>/<seq>.json) and of the YOLO segmenter equivalence (equiv_yolo.py outputs
<equiv dir>/yolo_<engine>/<seq>.json). Host python (json only)."""
import glob
import json
import os
import sys

SETS = [  # (dir, label)
    ('main_cv411', 'SAVIOR main (sens_fix1), C++ linked with OpenCV 4.11.0 (= Python cv2 4.11.0.86)'),
    ('main_sys2', 'SAVIOR main (sens_fix1), C++ linked with the system OpenCV 4.5.4 (Ubuntu 22.04 / ROS Humble), final code'),
    ('main_cv48b', 'SAVIOR main (sens_fix1), C++ linked with OpenCV 4.8.0 without IPP (JetPack 6 OpenCV version, x86 stand-in), final code'),
    ('main_sys', 'SAVIOR main, C++ with system OpenCV 4.5.4 BEFORE vendoring the 4.11 polygon fill (cv::fillPoly 4.5.4; = closed-loop method cpp_main)'),
    ('main_cv48', 'SAVIOR main, C++ with OpenCV 4.8.0 BEFORE vendoring the 4.11 polygon fill'),
    ('p7nb_cv411', 'SAVIOR-adaptive (p7_nb: adaptive gate + contact link), C++ OpenCV 4.11.0'),
    ('edge_cv411', 'SAVIOR-edge perception (main config + YOLO26n 672 detections), C++ OpenCV 4.11.0'),
    ('edge_sys2', 'SAVIOR-edge perception (main config + YOLO26n 672 detections), C++ system OpenCV 4.5.4, final code'),
]


def f6(x):
    return f'{100 * x:.4f} %'


def main():
    E, OUT = sys.argv[1], sys.argv[2]
    os.makedirs(OUT, exist_ok=True)
    L = ['# Offline Python <-> C++ equivalence (t1 tuning set, identical inputs: raw frames + gyro + cached YOLO detections)\n',
         'Each implementation keeps its own state over the whole sequence (no re-synchronisation). "identical" = bit-identical '
         'output / exactly equal values. Decision frames = every instance status, bbox, parent, track id, motion state '
         '(track id, moving/static/unknown, log-odds, observation, selective label + observation, duplicate flag) and the '
         'interaction links identical. Left/right agreement = share of mask pixels with the same 0/192/255 value.\n']
    summary = {}
    for d, label in SETS:
        files = sorted(glob.glob(f'{E}/{d}/*.json'))
        if not files:
            continue
        L += [f'\n## {label}\n', '| seq | frames | left px agree | right px agree | left core IoU | right core IoU | left identical frames |'
              ' right identical frames | decision frames identical | depth (disparity) equal | link frames identical | '
              'motion-state equal | first divergence |', '|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|---|']
        tot = {}
        for f in files:
            j = json.load(open(f))
            a = j['acc']
            for k, v in a.items():
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    tot[k] = tot.get(k, 0) + v
            fd = ', '.join(f'{k}@{v}' for k, v in sorted(a['first_div'].items(), key=lambda kv: kv[1])) or '-'
            L.append(f"| {j['seq']} | {a['frames']} | {f6(a['L_eq_px'] / a['px_total'])} | {f6(a['R_eq_px'] / a['px_total'])} | "
                     f"{a['L_core_inter'] / max(1, a['L_core_union']):.6f} | {a['R_core_inter'] / max(1, a['R_core_union']):.6f} | "
                     f"{a['L_frames_identical']} | {a['R_frames_identical']} | {a['decision_frames_identical']} | "
                     f"{a['disp_equal']}/{a['inst_frames']} | {a['links_frames_identical']} | {a['motion_equal']}/{a['inst_frames']} | {fd} |")
        a = tot
        L.append(f"| **all** | {a['frames']} | {f6(a['L_eq_px'] / a['px_total'])} | {f6(a['R_eq_px'] / a['px_total'])} | "
                 f"{a['L_core_inter'] / max(1, a['L_core_union']):.6f} | {a['R_core_inter'] / max(1, a['R_core_union']):.6f} | "
                 f"{a['L_frames_identical']} | {a['R_frames_identical']} | {a['decision_frames_identical']} | "
                 f"{a['disp_equal']}/{a['inst_frames']} | {a['links_frames_identical']} | {a['motion_equal']}/{a['inst_frames']} | |")
        summary[d] = {k: a[k] for k in ('frames', 'px_total', 'L_eq_px', 'R_eq_px', 'L_frames_identical', 'R_frames_identical',
                                        'decision_frames_identical', 'inst_frames', 'disp_equal', 'motion_equal',
                                        'links_frames_identical', 'n_links_py', 'n_links_cpp')}
        j0 = json.load(open(files[0]))
        L.append(f"\nOpenCV: Python cv2 {j0['opencv_py']}, C++ {j0['opencv_cpp']}; OpenCV threads {j0['threads']} (both); "
                 f"rectification maps identical: {j0['rect_identical']}.")
    # YOLO
    for d in sorted(glob.glob(f'{E}/yolo_*')):
        files = sorted(glob.glob(f'{d}/*.json'))
        if not files:
            continue
        eng = os.path.basename(d)[5:]
        L += [f'\n## YOLO26-seg TensorRT C++ vs Ultralytics 8.4.177 ({eng}; conf 0.25, iou 0.7, retina masks, 5 classes)\n',
              '| seq | frames | frames identical | detections (Ultralytics / C++) | class equal | box equal | max |score diff| |'
              ' union-mask px agree | instance-mask px agree | min instance IoU |', '|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|']
        T = {}
        for f in files:
            j = json.load(open(f))
            a = j['acc']
            for k, v in a.items():
                if k == 'inst_iou_min':
                    T[k] = min(T.get(k, 1.0), v)
                elif k == 'score_absdiff_max':
                    T[k] = max(T.get(k, 0.0), v)
                else:
                    T[k] = T.get(k, 0) + v
            L.append(f"| {j['seq']} | {a['frames']} | {a['frames_identical']} | {a['dets_ref']} / {a['dets_cpp']} | {a['cls_equal']} | "
                     f"{a['bbox_equal']} | {a['score_absdiff_max']:.2e} | {f6(a['union_px_equal'] / a['union_px'])} | "
                     f"{f6(a['mask_px_equal'] / max(1, a['mask_px']))} | {a['inst_iou_min']:.4f} |")
        a = T
        L.append(f"| **all** | {a['frames']} | {a['frames_identical']} | {a['dets_ref']} / {a['dets_cpp']} | {a['cls_equal']} | "
                 f"{a['bbox_equal']} | {a['score_absdiff_max']:.2e} | {f6(a['union_px_equal'] / a['union_px'])} | "
                 f"{f6(a['mask_px_equal'] / max(1, a['mask_px']))} | {a['inst_iou_min']:.4f} |")
        summary['yolo_' + eng] = T
    open(f'{OUT}/equivalence.md', 'w').write('\n'.join(L) + '\n')
    json.dump(summary, open(f'{OUT}/equivalence.json', 'w'), indent=1)
    print('\n'.join(L))


if __name__ == '__main__':
    main()
