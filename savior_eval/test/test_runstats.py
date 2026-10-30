"""savior-eval runstats: parsing of the OpenVINS mask-sync log line, feature stats csv and /savior/stats lines."""

import json
import os

import yaml

from savior_eval import runstats
from savior_eval.cli import main

FINAL = ('[run_subscribe_msckf-1] \x1b[0m\x1b[36m[SAVIOR-MASK] FINAL: wait policy, 2 measurements (4 cam masks): '
         'exact=5 fallback_latest=1 fallback_empty=0 late_masks=0 | hold avg=18.6ms max=115.1ms | pending=0\n')


def _run(tmp_path, name='run_01', md5_line='1.0 0 0 0 0 0 0 1\n'):
    rd = tmp_path / 'm' / name
    rd.mkdir(parents=True)
    (rd / 'launch.log').write_text('[SAVIOR-MASK] FINAL: wait policy, 1 measurements (2 cam masks): exact=0 '
                                   'fallback_latest=0 fallback_empty=2 late_masks=0 | hold avg=1.0ms max=1.0ms\n' + FINAL)
    (rd / 'feature_stats.csv').write_text(
        'timestamp,cam_id,n_tracked,n_new,n_rejected_mask,relaxed,n_in_band,n_in_core\n'
        '1.0,0,10,5,2,1,3,0\n1.0,1,8,2,0,0,0,0\n2.0,0,20,0,1,0,1,0\n2.0,1,9,1,0,0,0,0\n')
    rows = [{'timings_ms': {'segment': 4.0, 'total': 10.0}, 'n_by_role': {'dynamic': 2, 'potential': 1},
             'n_promoted': 1, 'n_carried': 0, 'core_px': 100, 'ext_px': 50, 'image_size': [10, 20]},
            {'timings_ms': {'segment': 6.0, 'total': 20.0}, 'n_by_role': {'dynamic': 0, 'potential': 0},
             'n_promoted': 0, 'n_carried': 1, 'core_px': 0, 'ext_px': 0, 'image_size': [10, 20]}]
    (rd / 'savior_stats.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in rows))
    (rd / 'stamped_traj_estimate.txt').write_text('# header\n' + md5_line)
    bag = tmp_path / 'bag'
    bag.mkdir(exist_ok=True)
    meta = {'rosbag2_bagfile_information': {'topics_with_message_count': [
        {'message_count': 2, 'topic_metadata': {'name': '/l', 'type': 'sensor_msgs/msg/Image'}},
        {'message_count': 400, 'topic_metadata': {'name': '/imu', 'type': 'sensor_msgs/msg/Imu'}}]}}
    (bag / 'metadata.yaml').write_text(yaml.safe_dump(meta))
    (rd / 'run_info.yaml').write_text(yaml.safe_dump({'bag': str(bag)}))
    return str(rd)


def test_run_stats(tmp_path):
    r = runstats.run_stats(_run(tmp_path))
    ms = r['mask_sync']   # the LAST FINAL line wins
    assert (ms["measurements"], ms["cam_masks"], ms["exact"], ms["fallback_latest"]) == (2, 4, 5, 1)
    assert ms['hold_max_ms'] == 115.1
    c0 = r['feature_stats']['cam0']
    assert c0['frames'] == 2 and c0['kept_mean'] == 17.5 and c0['rejected_mask'] == 3 and c0['relaxed_frames'] == 1
    assert c0['in_band'] == 4 and r['core_invariant_ok']
    s = r['savior']
    assert s['frames'] == 2 and r['bag_images'] == 2 and r['images_received'] == 2 and r['masks_equal_images'] and not r['all_exact']
    assert s['timings_ms']['segment']['median'] == 5.0 and s['frames_with_dynamic'] == 0.5
    assert s['core_frac_mean'] == 0.25


def test_runstats_cli(tmp_path):
    _run(tmp_path, 'run_01')
    _run(tmp_path, 'run_02')
    out = tmp_path / 'rs.md'
    assert main(['runstats', '--runs', str(tmp_path / 'm'), '--out', str(out)]) == 0
    md = out.read_text()
    assert 'bit-identical across runs: **yes**' in md and '| segment |' in md
    assert os.path.isfile(tmp_path / 'm' / 'run_01' / 'runstats.yaml')


def test_bag_images_respects_start_offset(tmp_path):
    """P4: with a bag start offset OpenVINS receives fewer images than the bag holds; bag_images reports the replay."""
    rd = _run(tmp_path)
    meta_fn = os.path.join(tmp_path, 'bag', 'metadata.yaml')
    meta = yaml.safe_load(open(meta_fn))
    meta['rosbag2_bagfile_information']['topics_with_message_count'][0]['message_count'] = 50
    open(meta_fn, 'w').write(yaml.safe_dump(meta))
    r = runstats.run_stats(rd)
    assert r['bag_images_total'] == 50 and r['bag_images'] == 2 == r['images_received']
