import os
from glob import glob

from setuptools import find_packages, setup

package_name = 'savior_eval'
rpg = os.path.join(package_name, 'third_party', 'rpg_trajectory_evaluation')

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    package_data={'savior_eval.third_party.rpg_trajectory_evaluation':
                  ['LICENSE', 'PORTING.md']},
    data_files=[
        ('share/ament_index/resource_index/packages',
         ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/config', glob('config/*.yaml')),
        ('share/' + package_name + '/third_party/rpg_trajectory_evaluation',
         [os.path.join(rpg, 'LICENSE'), os.path.join(rpg, 'PORTING.md')]),
        # PATH-visible wrappers (console_scripts live in lib/<pkg> for ros2 run)
        ('bin', ['scripts/savior-eval', 'scripts/savior-run']),
    ],
    install_requires=['setuptools'],
    zip_safe=False,
    maintainer='Sasa Kuruppuarachchi',
    maintainer_email='sasa.kuruppuarachchi@gmail.com',
    description='SAVIOR trajectory evaluation (rpg_trajectory_evaluation '
                'py3 port), comparison tables and experiment runner',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'savior-eval = savior_eval.cli:main',
            'savior-run = savior_eval.runner:main',
            'rpg-analyze-trajectory-single = savior_eval.third_party.'
            'rpg_trajectory_evaluation.analyze_trajectory_single:main',
            'rpg-analyze-trajectories = savior_eval.third_party.'
            'rpg_trajectory_evaluation.analyze_trajectories:main',
        ],
    },
)
