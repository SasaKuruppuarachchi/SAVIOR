"""Table + figure from results/p3a/diag/*.yaml (diag_analysis.py outputs)."""
import glob

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import yaml  # noqa: E402

P3 = '/home/sasa/workspace/savior_ws/results/p3a'
FATES = ['used', 'chi2', 'trifail', 'few', 'slam', 'slam_chi2', 'slam_trifail', 'slam_few', 'cap_dropped', 'no_update']
lines = ['# P3a feature fates (diagnostic OpenVINS build = install + logging only; trajectories equal to <= 4e-6 m)\n',
         'human track = >= 50 % of its observations on the oracle human mask (cam0 GT seg, cam1 stereo-warped); post-init tracks only.\n',
         '| run | kept obs on human cam0 / cam1 | frames with >= 1 human feature | human tracks / all | median (mean) length human vs other [frames] | '
         'human: used / chi2 / trifail / few / SLAM | MSCKF chi2 reject rate human vs other | share of MSCKF-used measurements on humans | share of SLAM-update meas. on humans |',
         '|---|--:|--:|--:|--:|---|--:|--:|--:|']
recs = {}
for f in sorted(glob.glob(f'{P3}/diag/*.yaml')):
    d = yaml.safe_load(open(f))
    p = d['post_init']
    h, o = p['human'], p['non_human']
    name = f.split('/')[-1][:-5]
    recs[name] = d
    ff = h['fate_frac']
    lines.append(f"| {name} | {100 * d['frac_kept_obs_on_human_cam0']:.2f} % / {100 * d['frac_kept_obs_on_human_cam1']:.2f} % | "
                 f"{100 * d['frames_with_feature_on_human_cam0']:.1f} % | {h['n_tracks']} / {p['all']['n_tracks']} | "
                 f"{h.get('len_frames_median', 0):.0f} ({h.get('len_frames_mean', 0):.1f}) vs {o['len_frames_median']:.0f} ({o['len_frames_mean']:.1f}) | "
                 + ' / '.join(f"{100 * ff.get(k, 0):.0f}" for k in ['used', 'chi2', 'trifail', 'few', 'slam']) + ' % | '
                 f"{100 * (h.get('msckf_chi2_reject_rate') or 0):.0f} % vs {100 * o['msckf_chi2_reject_rate']:.0f} % | "
                 f"{100 * p['frac_msckf_used_meas_human']:.2f} % | {100 * p['frac_slam_update_meas_human']:.3f} % |")
open(f'{P3}/tables/feature_fates.md', 'w').write('\n'.join(lines) + '\n')
print('\n'.join(lines))
# figure: fate distribution human vs other for the observe runs
sel = [k for k in ['06h_observe_run01', '06h_observe_run03', '12h_observe_run01', '12h_observe_run03'] if k in recs]
fig, ax = plt.subplots(figsize=(10, 4.2))
cols = {'used': '#1baf7a', 'chi2': '#e34948', 'trifail': '#eda100', 'few': '#c3c2b7', 'slam': '#2a78d6',
        'slam_chi2': '#6250d6', 'slam_trifail': '#e87ba4', 'slam_few': '#888888', 'cap_dropped': '#52514e', 'no_update': '#dddddd'}
labels, y = [], 0
seen = set()
for k in sel:
    for grp in ['human', 'non_human']:
        fr = recs[k]['post_init'][grp]['fate_frac']
        left = 0
        for fa in FATES:
            v = fr.get(fa, 0)
            if v > 0:
                ax.barh(y, v * 100, left=left, color=cols[fa], edgecolor='white', lw=1.5, height=0.7,
                        label=fa if fa not in seen else None)
                seen.add(fa)
                left += v * 100
        labels.append(f"{k.replace('_observe_', ' ')} {'human' if grp == 'human' else 'other'}"
                      f" (n={recs[k]['post_init'][grp]['n_tracks']})")
        y += 1
ax.set_yticks(range(len(labels)))
ax.set_yticklabels(labels, fontsize=9)
ax.invert_yaxis()
ax.set_xlabel('share of post-init tracks [%] by fate (MSCKF used / chi2-rejected / triangulation fail / < 2 meas / SLAM ...)')
ax.legend(frameon=False, fontsize=8, ncol=5, loc='lower center', bbox_to_anchor=(0.5, 1.0))
ax.spines[['top', 'right']].set_visible(False)
fig.tight_layout()
fig.savefig(f'{P3}/figures/feature_fates.png', dpi=130)
