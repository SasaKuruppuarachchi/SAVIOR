# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 The SAVIOR authors
from glob import glob

from setuptools import find_packages, setup

package_name = "savior_perception"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml", "README.md"]),
        ("share/" + package_name + "/config", glob("config/*.yaml")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Sasa Kuruppuarachchi",
    maintainer_email="sasa.kuruppuarachchi@gmail.com",
    description="SAVIOR semantic front-end producing layered dynamic-object masks for OpenVINS",
    license="GPL-3.0-or-later",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "savior_node = savior_perception.node:main",
        ],
    },
)
