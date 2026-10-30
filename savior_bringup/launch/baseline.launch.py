# SPDX-License-Identifier: GPL-3.0-or-later
"""Stock-OpenVINS baseline: ov_msckf + ros2 bag play + TUM pose recorder.

  ros2 launch savior_bringup baseline.launch.py \
      config:=$(ros2 pkg prefix savior_bringup)/share/savior_bringup/config/uhumans2/estimator_config.yaml \
      bag:=$SAVIOR_WS/data/uhumans2/ros2/office_s1_00h \
      output:=$SAVIOR_WS/results/baseline/uhumans2_office_s1_00h/run_01/stamped_traj_estimate.txt \
      topics:="/tesse/left_cam/mono/image_raw /tesse/right_cam/mono/image_raw /tesse/imu/noisy/imu /tf_static"

Offline bag replay is deterministic by default (deterministic:=true, OpenVINS fork deterministic_processing): upstream
OpenVINS processes images / initializes in detached threads, so its result depends on CPU load (cafe1-1: ATE 0.165 vs
0.154 m for the same bag under load). Use deterministic:=false for the upstream behaviour.

Sequence: ov_msckf starts, the bag starts `start_delay` s later (real-time `rate`), and when
`ros2 bag play` exits the whole launch shuts down after `end_delay` s (lets OpenVINS drain its queue).
The recorder writes /ov_msckf/poseimu (IMU pose in the global frame, IMU clock) in TUM format.
Topic names come from the kalibr yaml files next to `config` (OpenVINS reads `rostopic` there).

`config` may also be a dataset name (uhumans2, openloris_t265) resolved inside this package.
`dataset` presets select the topics to play when `topics` is empty.
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (DeclareLaunchArgument, EmitEvent, ExecuteProcess, LogInfo, OpaqueFunction,
                            RegisterEventHandler, TimerAction)
from launch.event_handlers import OnProcessExit, OnProcessIO
from launch.events import Shutdown
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

# topics needed by OpenVINS per dataset (images, IMU, tf_static); other topics in the bag are not played
TOPIC_PRESETS = {
    'uhumans2': ['/tesse/left_cam/mono/image_raw', '/tesse/right_cam/mono/image_raw',
                 '/tesse/imu/noisy/imu', '/tf_static'],
    'openloris_t265': ['/t265/fisheye1/image_raw', '/t265/fisheye2/image_raw', '/t265/imu', '/tf_static'],
    'viode': ['/cam0/image_raw', '/cam1/image_raw', '/imu0'],   # P5 (oracle: + /cam0|1/segmentation, see savior.launch.py)
    # P6 SAVIOR-Warehouse (Isaac Sim): noisy IMU; /imu0_clean, /cam0/segmentation(_moving), /gt/pose are in the bag too
    'warehouse': ['/cam0/image_raw', '/cam1/image_raw', '/imu0', '/tf_static'],
    'warehouse_moving': ['/cam0/image_raw', '/cam1/image_raw', '/imu0', '/tf_static'],   # P6 oracle MOVING masks
}

ARGS = [
    DeclareLaunchArgument('config', default_value='uhumans2',
                          description='path to estimator_config.yaml, or a config dir name in savior_bringup/config'),
    DeclareLaunchArgument('bag', description='ROS 2 bag directory to play'),
    DeclareLaunchArgument('output', description='TUM output file for the estimated IMU trajectory'),
    DeclareLaunchArgument('dataset', default_value='', description='topic preset: uhumans2 | openloris_t265 '
                          '(default: derived from config)'),
    DeclareLaunchArgument('topics', default_value='', description='space separated topics to play (overrides preset)'),
    DeclareLaunchArgument('rate', default_value='1.0', description='bag play rate (1.0 = real time)'),
    DeclareLaunchArgument('start_offset', default_value='0.0', description='bag start offset [s]'),
    DeclareLaunchArgument('start_delay', default_value='3.0', description='wait before playing the bag [s] (savior: '
                          'after savior_node is up)'),
    DeclareLaunchArgument('ready_timeout', default_value='120.0',
                          description='savior: play the bag at the latest this long after launch start [s]'),
    DeclareLaunchArgument('end_delay', default_value='3.0', description='wait after the bag ended before shutdown [s]'),
    DeclareLaunchArgument('use_sim_time', default_value='false',
                          description='OpenVINS uses message stamps only; true requires a /clock in the bag'),
    DeclareLaunchArgument('verbosity', default_value='INFO', description='OpenVINS verbosity'),
    DeclareLaunchArgument('namespace', default_value='ov_msckf'),
    DeclareLaunchArgument('ov_package', default_value='ov_msckf', description='package providing run_subscribe_msckf'),
    DeclareLaunchArgument('pose_topic', default_value='', description='default: /<namespace>/poseimu'),
    DeclareLaunchArgument('record_timing', default_value='', description='if set: OpenVINS timing csv path'),
    DeclareLaunchArgument('deterministic', default_value='true',
                          description='OpenVINS (SAVIOR fork) deterministic_processing: synchronous subscriber, '
                          'initializer on IMU up to the image time, lossless QoS -> results independent of CPU load and '
                          'mask waiting (offline bag replay). false = upstream multi-threaded behaviour (online use)'),
    DeclareLaunchArgument('feature_stats', default_value='',
                          description='OpenVINS (SAVIOR fork) record_feature_stats csv: path, "auto" = '
                          '<output dir>/feature_stats.csv, "" = off'),
    DeclareLaunchArgument('ov_set', default_value='',
                          description='extra ov_msckf parameter overrides "key=value key2=value2" (values are YAML: '
                          'true, 256, 0.5, text)'),
    DeclareLaunchArgument('ov_sigterm_timeout', default_value='3', description='s after SIGINT before SIGTERM'),
    DeclareLaunchArgument('ov_sigkill_timeout', default_value='2', description='s after SIGTERM before SIGKILL'),
]


def resolve_config(cfg):
    if os.path.isfile(cfg):
        return os.path.abspath(cfg), os.path.basename(os.path.dirname(os.path.abspath(cfg)))
    share = get_package_share_directory('savior_bringup')
    path = os.path.join(share, 'config', cfg, 'estimator_config.yaml')
    if not os.path.isfile(path):
        raise RuntimeError(f'config "{cfg}" is neither a file nor a config dir in {share}/config')
    return path, cfg


def parse_kv(text):
    """'a=1 b.c=false d=txt' -> {'a': 1, 'b.c': False, 'd': 'txt'} (values parsed as YAML scalars)."""
    import yaml
    out = {}
    for item in text.split():
        k, sep, v = item.partition('=')
        if not sep or not k:
            raise RuntimeError(f'expected key=value, got "{item}"')
        out[k] = yaml.safe_load(v) if v != '' else ''
    return out


def output_sibling(context, value, default_name):
    """'' -> None, 'auto' -> <dir of output>/<default_name>, else the absolute path."""
    if not value or value.lower() in ('none', 'off', 'false'):
        return None
    if value == 'auto':
        out = os.path.abspath(LaunchConfiguration('output').perform(context))
        return os.path.join(os.path.dirname(out), default_name)
    return os.path.abspath(value)


def ov_extra_params(context):
    """Extra ROS parameters for ov_msckf (override yaml values). Hook for savior.launch.py."""
    p = {}
    timing = LaunchConfiguration('record_timing').perform(context)
    if timing:
        p.update({'record_timing_information': True, 'record_timing_filepath': timing})
    if LaunchConfiguration('deterministic').perform(context).lower() in ('1', 'true', 'yes'):
        p['deterministic_processing'] = True
    fs = output_sibling(context, LaunchConfiguration('feature_stats').perform(context), 'feature_stats.csv')
    if fs:
        p['record_feature_stats'] = fs
    return p


def start_after_ready(play, delay, ready_action, ready_text, max_wait):
    """Start `play` `delay` s after `ready_action` printed `ready_text` (stdout or stderr), at the latest after
    `max_wait` s. A fixed start delay raced the perception node start-up (TensorRT engine load + warmup took > 3 s
    with 10 parallel runs, so the first frames of the bag got no mask)."""
    state = {'started': False}

    def fire(_event=None, _context=None):
        if state['started']:
            return None
        state['started'] = True
        return [TimerAction(period=delay, actions=[play])]

    def on_io(event):
        if ready_text in event.text.decode(errors='replace'):
            return fire()
        return None

    return [RegisterEventHandler(OnProcessIO(target_action=ready_action, on_stdout=on_io, on_stderr=on_io)),
            TimerAction(period=max_wait, actions=[OpaqueFunction(function=lambda ctx: fire())])]


def build(context, extra_ov_params=None, extra_actions=None, ready=None, compose_with=None):
    """ready: optional (action, text): play the bag start_delay s after `action` printed `text` (savior.launch.py).
    compose_with: optional list of launch_ros ComposableNode descriptions: ov_msckf runs as a component
    (savior_ov_component) in ONE multi-threaded component container together with them, intra-process comms on
    (ready[0] == 'container' then targets that container)."""
    lc = lambda n: LaunchConfiguration(n).perform(context)  # noqa: E731
    config_path, cfg_name = resolve_config(lc('config'))
    dataset = lc('dataset') or cfg_name
    topics = lc('topics').split() or TOPIC_PRESETS.get(dataset, [])
    use_sim_time = lc('use_sim_time').lower() in ('1', 'true', 'yes')
    ns = lc('namespace')
    pose_topic = lc('pose_topic') or f'/{ns}/poseimu'
    output = os.path.abspath(lc('output'))
    os.makedirs(os.path.dirname(output), exist_ok=True)

    params = {'verbosity': lc('verbosity'), 'use_stereo': True, 'max_cameras': 2,
              'config_path': config_path, 'use_sim_time': use_sim_time}
    params.update(ov_extra_params(context))
    params.update(extra_ov_params or {})
    params.update(parse_kv(lc('ov_set')))  # explicit overrides win
    # NOTE: run_subscribe_msckf does not exit on SIGINT (hangs after visualize_final(), upstream too)
    # -> short SIGTERM/SIGKILL escalation so `ros2 launch` returns by itself. The pose recorder is a
    # separate process that flushes every line and closes its file on SIGINT.
    if compose_with is None:
        ov = Node(package=lc('ov_package'), executable='run_subscribe_msckf', namespace=ns, name='run_subscribe_msckf',
                  output='screen', parameters=[params], emulate_tty=True,
                  sigterm_timeout=lc('ov_sigterm_timeout'), sigkill_timeout=lc('ov_sigkill_timeout'))
    else:
        from launch_ros.actions import ComposableNodeContainer
        from launch_ros.descriptions import ComposableNode
        ov_comp = ComposableNode(package='savior_ov_component', plugin='savior_ov_component::OvMsckfComponent',
                                 name='run_subscribe_msckf', namespace=ns, parameters=[params],
                                 extra_arguments=[{'use_intra_process_comms': True}])
        ov = ComposableNodeContainer(name='savior_container', namespace='', package='rclcpp_components',
                                     executable='component_container_mt', output='screen', emulate_tty=True,
                                     composable_node_descriptions=[ov_comp] + list(compose_with),
                                     sigterm_timeout=lc('ov_sigterm_timeout'), sigkill_timeout=lc('ov_sigkill_timeout'))
        if ready and ready[0] == 'container':
            ready = (ov, ready[1])
    rec = Node(package='savior_bringup', executable='pose_recorder.py', name='pose_recorder', output='screen',
               parameters=[{'topic': pose_topic, 'output': output, 'use_sim_time': use_sim_time}])
    cmd = ['ros2', 'bag', 'play', lc('bag'), '--rate', lc('rate'), '--start-offset', lc('start_offset'),
           '--read-ahead-queue-size', '2000', '--disable-keyboard-controls']
    if topics:
        cmd += ['--topics'] + topics
    if use_sim_time:
        cmd += ['--clock', '200']
    play = ExecuteProcess(cmd=cmd, output='screen', name='bag_play')
    end_delay = float(lc('end_delay'))
    actions = [
        LogInfo(msg=f'[baseline] config={config_path} bag={lc("bag")} topics={topics} -> {output}'),
        LogInfo(msg=f'[baseline] ov_msckf parameters: {params}'),
        ov, rec, *(extra_actions or []),
        *(start_after_ready(play, float(lc('start_delay')), ready[0], ready[1], float(lc('ready_timeout')))
          if ready else [TimerAction(period=float(lc('start_delay')), actions=[play])]),
        RegisterEventHandler(OnProcessExit(target_action=play, on_exit=[
            LogInfo(msg='[baseline] bag finished, shutting down'),
            TimerAction(period=end_delay, actions=[EmitEvent(event=Shutdown(reason='bag finished'))])])),
    ]
    return actions


def generate_launch_description():
    return LaunchDescription(ARGS + [OpaqueFunction(function=build)])
