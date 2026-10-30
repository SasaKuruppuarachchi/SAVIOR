# SPDX-License-Identifier: GPL-3.0-or-later
"""SAVIOR: OpenVINS fork with dynamic masks + savior_perception savior_node + bag play + recorder.

Same arguments as baseline.launch.py, plus:
  perception_params   params file for savior_node (default: savior_perception/config/default.yaml followed by
                      savior_bringup/config/<dataset>/savior_perception.yaml)
  roles_file          class-role yaml (default: savior_bringup/config/roles/coco_indoor.yaml)
  backend             segmenter.backend override (yolo | oracle_colormap | none; '' = from params files)
  model               segmenter.model override
  mask_policy         dynamic_mask_policy for OpenVINS (wait | latest)
  mask_timeout_ms     dynamic_mask_timeout_ms (default 1500: offline deterministic 'wait' runs)
  pset                savior_node parameter overrides "gating.enable=false tracker.enable=false" (YAML values,
                      applied last), e.g. the ablations of docs/INTERFACE.md §3.3
  stats_file          /savior/stats JSON-lines file: "auto" (default) = <output dir>/savior_stats.jsonl, "" = off
  perception_impl     python (default: savior_perception savior_node) | cpp (savior_perception_cpp savior_node_cpp,
                      same node name / parameters / topics / mask contract)
  (baseline args incl. feature_stats:=auto and ov_set:="dynamic_mask_threshold=256" also apply)
For offline runs use a slower bag rate (e.g. rate:=0.5): savior_node's depth-10 input queue drops frames
if it cannot keep up.

OpenVINS gets use_dynamic_mask=true, dynamic_mask_topic0/1 = /savior/mask/left|right as ROS parameter
overrides of the yaml (the fork's YamlParser prefers ROS parameters), so the dataset estimator_config.yaml
is shared with the baseline. Requires the SAVIOR OpenVINS fork (src/savior/open_vins) to be the
`ov_msckf` on the path; stock OpenVINS ignores the mask keys.

  ros2 launch savior_bringup savior.launch.py config:=uhumans2 \
      bag:=.../data/uhumans2/ros2/office_s1_06h output:=.../results/savior/.../stamped_traj_estimate.txt \
      backend:=oracle_colormap rate:=0.5
"""
import importlib.util
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, LogInfo, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

_spec = importlib.util.spec_from_file_location('savior_baseline_launch',
                                               os.path.join(os.path.dirname(__file__), 'baseline.launch.py'))
baseline = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(baseline)

# per-dataset perception I/O (left/right raw images, optional oracle semantic image, oracle colour map)
PERCEPTION_IO = {
    'uhumans2': {'left_topic': '/tesse/left_cam/mono/image_raw', 'right_topic': '/tesse/right_cam/mono/image_raw',
                 'seg_topic': '/tesse/seg_cam/rgb/image_raw', 'colormap': 'oracle/uhumans2_colormap.yaml',
                 'imu_topic': '/tesse/imu/noisy/imu'},
    'openloris_t265': {'left_topic': '/t265/fisheye1/image_raw', 'right_topic': '/t265/fisheye2/image_raw',
                       'seg_topic': '', 'colormap': '', 'imu_topic': '/t265/imu'},
    # P5 VIODE: the oracle colour map is per environment -> pset segmenter.colormap_file=.../oracle/viode_<env>_colormap.yaml
    # (and seg_right_topic=/cam1/segmentation + topics:=... for the GT right mask)
    'viode': {'left_topic': '/cam0/image_raw', 'right_topic': '/cam1/image_raw', 'seg_topic': '/cam0/segmentation',
              'colormap': '', 'imu_topic': '/imu0'},
    # P6 SAVIOR-Warehouse: class-colour GT (roles_file:=.../roles/warehouse.yaml)
    'warehouse': {'left_topic': '/cam0/image_raw', 'right_topic': '/cam1/image_raw', 'seg_topic': '/cam0/segmentation',
                  'colormap': 'oracle/warehouse_colormap.yaml', 'imu_topic': '/imu0'},
    # dataset:=warehouse_moving + roles_file:=.../roles/warehouse_oracle_moving.yaml: only truly moving instances
    'warehouse_moving': {'left_topic': '/cam0/image_raw', 'right_topic': '/cam1/image_raw',
                         'seg_topic': '/cam0/segmentation_moving', 'colormap': 'oracle/warehouse_colormap_moving.yaml',
                         'imu_topic': '/imu0'},
}


def static_mask0(config_path):
    """P4: OpenVINS static mask of cam0 (`use_mask: true` + `mask0:` in the estimator yaml) -> absolute path or ''.
    savior_node only uses it (motion.static_mask_file) when motion.enable is true."""
    import re
    try:
        text = open(config_path).read()
    except OSError:
        return ''
    if not re.search(r'^use_mask:\s*true', text, re.M):
        return ''
    m = re.search(r'^mask0:\s*"?([^"#\s]+)"?', text, re.M)
    if not m:
        return ''
    path = os.path.join(os.path.dirname(config_path), m.group(1))
    return path if os.path.isfile(path) else ''

ARGS = baseline.ARGS + [
    DeclareLaunchArgument('perception_params', default_value=''),
    DeclareLaunchArgument('roles_file', default_value=''),
    DeclareLaunchArgument('backend', default_value=''),
    DeclareLaunchArgument('model', default_value=''),
    DeclareLaunchArgument('mask_policy', default_value='wait'),
    DeclareLaunchArgument('mask_timeout_ms', default_value='1500'),
    DeclareLaunchArgument('publish_debug', default_value='false'),
    DeclareLaunchArgument('pset', default_value='', description='savior_node overrides "key=value ..."'),
    DeclareLaunchArgument('perception_impl', default_value='python',
                          description='python (savior_perception) | cpp (savior_perception_cpp savior_node_cpp)'),
    DeclareLaunchArgument('stats_file', default_value='auto',
                          description='/savior/stats JSON lines ("auto" = <output dir>/savior_stats.jsonl, "" = off)'),
]


def build(context):
    lc = lambda n: LaunchConfiguration(n).perform(context)  # noqa: E731
    share = get_package_share_directory('savior_bringup')
    config_path, cfg_name = baseline.resolve_config(lc('config'))
    dataset = lc('dataset') or cfg_name
    io = PERCEPTION_IO.get(dataset, {})
    calib = os.path.join(os.path.dirname(config_path), 'kalibr_imucam_chain.yaml')

    pparams = []
    pp = lc('perception_params')
    if not pp:
        try:
            pp = os.path.join(get_package_share_directory('savior_perception'), 'config', 'default.yaml')
        except Exception:  # package not built yet
            pp = ''
    if pp:
        pparams.append(pp)
    ds_pp = os.path.join(os.path.dirname(config_path), 'savior_perception.yaml')
    if not lc('perception_params') and os.path.isfile(ds_pp):
        pparams.append(ds_pp)
    over = {'calib_file': calib, 'cam_left': 'cam0', 'cam_right': 'cam1',
            'roles_file': lc('roles_file') or os.path.join(share, 'config', 'roles', 'coco_indoor.yaml'),
            'mask_left_topic': '/savior/mask/left', 'mask_right_topic': '/savior/mask/right',
            'publish_debug': lc('publish_debug').lower() == 'true',
            'use_sim_time': lc('use_sim_time').lower() in ('1', 'true', 'yes')}
    for k in ('left_topic', 'right_topic', 'imu_topic'):
        if io.get(k):
            over[k] = io[k]
    sm = static_mask0(config_path)
    if sm:
        over['motion.static_mask_file'] = sm
    backend = lc('backend')
    if backend:
        over['segmenter.backend'] = backend
    if io.get('colormap'):
        over['segmenter.colormap_file'] = os.path.join(share, 'config', io['colormap'])
    if backend.startswith('oracle') and io.get('seg_topic'):
        over['seg_topic'] = io['seg_topic']
    if lc('model'):
        over['segmenter.model'] = lc('model')
    over.update(baseline.parse_kv(lc('pset')))
    pparams.append(over)
    impl = lc('perception_impl').strip().lower() or 'python'
    if impl not in ('python', 'cpp', 'cpp_composed'):
        raise RuntimeError(f'perception_impl "{impl}": python | cpp | cpp_composed')
    pkg, exe = ('savior_perception', 'savior_node') if impl == 'python' else ('savior_perception_cpp', 'savior_node_cpp')
    composed = None
    if impl == 'cpp_composed':
        # savior_node + ov_msckf as components of one container, intra-process (zero-copy masks)
        from launch_ros.descriptions import ComposableNode
        flat = {}
        for p in pparams:
            if isinstance(p, dict):
                flat.update(p)
            else:
                import yaml
                with open(p) as fh:
                    d = (yaml.safe_load(fh) or {}).get('savior_node', {}).get('ros__parameters', {})
                def _fl(x, pre=''):
                    for k, v in x.items():
                        if isinstance(v, dict):
                            _fl(v, f'{pre}{k}.')
                        else:
                            flat[f'{pre}{k}'] = v
                _fl(d)
        composed = [ComposableNode(package='savior_perception_cpp', plugin='savior_perception_cpp::SaviorNode',
                                   name='savior_node', parameters=[flat],
                                   extra_arguments=[{'use_intra_process_comms': True}])]
        perception = LogInfo(msg='[savior] savior_node composed with ov_msckf (savior_container, intra-process)')
    else:
        perception = Node(package=pkg, executable=exe, name='savior_node', output='screen', parameters=pparams)
    extra = [perception, LogInfo(msg=f'[savior] savior_node ({pkg}/{exe}) parameters: {pparams}')]
    stats_file = baseline.output_sibling(context, lc('stats_file'), 'savior_stats.jsonl')
    if stats_file:
        extra.append(Node(package='savior_bringup', executable='stats_recorder.py', name='stats_recorder',
                          output='screen', parameters=[{'topic': '/savior/stats', 'output': stats_file,
                                                        'use_sim_time': over['use_sim_time']}]))

    ov_params = {'use_dynamic_mask': True,
                 'dynamic_mask_topic0': '/savior/mask/left', 'dynamic_mask_topic1': '/savior/mask/right',
                 'dynamic_mask_policy': lc('mask_policy'),
                 'dynamic_mask_timeout_ms': int(lc('mask_timeout_ms'))}
    # the oracle backend needs the semantic image too -> add it to the played topics
    # (backend '' = taken from the dataset savior_perception.yaml: uhumans2 -> oracle_colormap)
    if not backend and os.path.isfile(ds_pp):
        import yaml
        with open(ds_pp) as fh:
            backend = (yaml.safe_load(fh) or {}).get('savior_node', {}).get('ros__parameters', {}) \
                .get('segmenter', {}).get('backend', '')
    if backend.startswith('oracle') and io.get('seg_topic') and not lc('topics'):
        topics = baseline.TOPIC_PRESETS.get(dataset, []) + [io['seg_topic']]
        context.launch_configurations['topics'] = ' '.join(topics)
    # the bag starts only once savior_node is up (segmenter loaded + warmed up, subscriptions created)
    return baseline.build(context, extra_ov_params=ov_params, extra_actions=extra,
                          ready=(('container' if composed else perception), 'savior_node up:'), compose_with=composed)


def generate_launch_description():
    return LaunchDescription(ARGS + [OpaqueFunction(function=build)])
