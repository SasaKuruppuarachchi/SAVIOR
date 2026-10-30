import os
from glob import glob

from setuptools import setup

package_name = 'savior_bringup'


def tree(src, dst_root):
    """data_files entries for every file below src (keeps the sub-directory layout)."""
    out = {}
    for path in glob(os.path.join(src, '**', '*'), recursive=True):
        if os.path.isfile(path):
            rel = os.path.relpath(os.path.dirname(path), src)
            out.setdefault(os.path.normpath(os.path.join(dst_root, rel)), []).append(path)
    return sorted(out.items())


setup(
    name=package_name,
    version='0.1.0',
    packages=[],  # launch/config-only package; tools are installed as plain scripts
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', glob('launch/*.launch.py')),
        *tree('config', 'share/' + package_name + '/config'),
        ('share/' + package_name + '/tools', glob('tools/*.py') + glob('tools/*.sh')),
        # executables for `ros2 run` / launch Node(): lib/<pkg>/<name>
        ('lib/' + package_name, ['tools/pose_recorder.py', 'tools/stats_recorder.py', 'tools/perception_offline.py']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Sasa Kuruppuarachchi',
    maintainer_email='sasa.kuruppuarachchi@gmail.com',
    description='SAVIOR launch files, dataset configs and dataset preparation tools',
    license='GPL-3.0-or-later',
)
