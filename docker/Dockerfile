# syntax=docker/dockerfile:1
# check=skip=InvalidBaseImagePlatform
#
# (check=skip: the arm64 base is legitimately a foreign-arch image when linting on amd64.)
#
# SAVIOR development image: ROS 2 Humble + OpenVINS build deps + PyTorch/Ultralytics/TensorRT.
#
# One Dockerfile, two targets, selected with the PLATFORM build arg:
#   amd64  desktop x86_64, CUDA 12.8 (needed for Blackwell / sm_120 GPUs)
#   arm64  NVIDIA Jetson Orin (JetPack 6 / L4T r36, CUDA 12.6, TensorRT 10.3 from the base image)
#
# PLATFORM defaults to the BuildKit target architecture, so a plain `docker build .` picks the
# right branch. ./build.sh passes it explicitly (and the host uid/gid), see README.md.
#
# Stages:  base-amd64 | base-arm64  ->  common (ROS 2 + OpenVINS deps)  ->  ml (Python/ML)  ->  dev
#
# Nothing workspace-specific (paths, weights, caches) is baked in: the colcon workspace is mounted
# at runtime and caches/weights live inside it (see run.sh / README.md).

ARG TARGETARCH
ARG PLATFORM=${TARGETARCH}

# Base images. Override with --build-arg if you need a different point release.
#   amd64: CUDA >= 12.8 is the first release with Blackwell (sm_120) support. cudnn-devel gives
#          nvcc + cuDNN headers for building custom CUDA code later.
#   arm64: l4t-jetpack r36.4.0 = JetPack 6.1 userspace (also used with JetPack 6.2 / r36.4.3) (CUDA 12.6, cuDNN 9, TensorRT 10.3 incl.
#          python3-libnvinfer). Its L4T version must match the BSP flashed on the Jetson (r36.x).
ARG BASE_IMAGE_AMD64=nvidia/cuda:12.8.1-cudnn-devel-ubuntu22.04
ARG BASE_IMAGE_ARM64=nvcr.io/nvidia/l4t-jetpack:r36.4.0

FROM ${BASE_IMAGE_AMD64} AS base-amd64
FROM ${BASE_IMAGE_ARM64} AS base-arm64

# =================================================================================================
# common: OS tooling, ROS 2 Humble, OpenVINS build dependencies
# =================================================================================================
FROM base-${PLATFORM} AS common
ARG PLATFORM

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    ROS_DISTRO=humble \
    # All driver capabilities: "graphics" is needed for rviz2 (OpenGL) next to compute/utility.
    NVIDIA_DRIVER_CAPABILITIES=all

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Version of the official ROS apt source package (provides the repo entry + signing key).
ARG ROS_APT_SOURCE_VERSION=1.3.0

# On Jetson the NVIDIA apt repo ships its own OpenCV 4.8 under the same package names as Ubuntu's.
# ROS Humble's cv_bridge is built against Ubuntu's OpenCV 4.5.4, so block NVIDIA's OpenCV and remove
# it if the base image already contains it.
RUN if [ "${PLATFORM}" = "arm64" ]; then \
        printf 'Package: *opencv*\nPin: origin "repo.download.nvidia.com"\nPin-Priority: -1\n' \
            > /etc/apt/preferences.d/savior-no-nvidia-opencv; \
        pkgs="$(dpkg-query -W -f='${Package} ${Status}\n' '*opencv*' 2>/dev/null | awk '/ installed$/{print $1}')"; \
        if [ -n "${pkgs}" ]; then apt-get purge -y ${pkgs}; fi; \
    fi

RUN apt-get update && apt-get install -y --no-install-recommends \
        bash-completion build-essential ca-certificates cmake curl gdb git gnupg less \
        locales lsb-release nano pkg-config python3-dev python3-pip software-properties-common \
        sudo wget \
    && add-apt-repository -y universe \
    && curl -fsSL -o /tmp/ros2-apt-source.deb \
        "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${ROS_APT_SOURCE_VERSION}/ros2-apt-source_${ROS_APT_SOURCE_VERSION}.$(. /etc/os-release && echo "${VERSION_CODENAME}")_all.deb" \
    && apt-get install -y /tmp/ros2-apt-source.deb \
    && rm -f /tmp/ros2-apt-source.deb \
    && rm -rf /var/lib/apt/lists/*

# ROS 2 Humble (ros-base + the packages SAVIOR/OpenVINS use) and OpenVINS build deps.
# OpenCV comes from Ubuntu (libopencv-dev 4.5.4) because cv_bridge links against it.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ros-humble-ros-base \
        ros-humble-cv-bridge \
        ros-humble-vision-opencv \
        ros-humble-image-transport \
        ros-humble-message-filters \
        ros-humble-rosbag2 \
        ros-humble-rosbag2-storage-mcap \
        ros-humble-tf2-ros \
        ros-humble-tf2-eigen \
        ros-humble-tf2-geometry-msgs \
        ros-humble-rviz2 \
        ros-humble-rmw-cyclonedds-cpp \
        python3-colcon-common-extensions \
        python3-rosdep \
        python3-pytest \
        libeigen3-dev \
        libceres-dev \
        libboost-all-dev \
        libopencv-dev \
    && rosdep init \
    && rm -rf /var/lib/apt/lists/*

# =================================================================================================
# ml: Python / ML stack on the system python3.10 (the interpreter ROS Humble uses)
# =================================================================================================
FROM common AS ml
ARG PLATFORM

# torch/torchvision: same version on both arches so behaviour matches between desktop and Jetson.
#   amd64: official cu128 wheels (contain sm_120 kernels for Blackwell).
#   arm64: NVIDIA Jetson wheels for JetPack 6 / CUDA 12.6 from the jetson-ai-lab index.
ARG TORCH_VERSION=2.9.1
ARG TORCHVISION_VERSION=0.24.1
ARG TORCH_INDEX_AMD64=https://download.pytorch.org/whl/cu128
ARG TORCH_INDEX_ARM64=https://pypi.jetson-ai-lab.io/jp6/cu126
# TensorRT python for amd64 only (arm64 uses python3-libnvinfer from JetPack). Kept on the 10.x
# major line like JetPack 6; >= 10.8 is required for Blackwell.
ARG TENSORRT_VERSION_AMD64=10.16.1.11
# cuDSS (sparse solver, a hard link-time dependency of the Jetson torch >= 2.8 wheels), Jetson
# (linux-aarch64, CUDA 12) redistributable from developer.download.nvidia.com/compute/cudss/redist.
ARG CUDSS_URL_ARM64=https://developer.download.nvidia.com/compute/cudss/redist/libcudss/linux-aarch64/libcudss-linux-aarch64-0.6.0.5_cuda12-archive.tar.xz
ARG CUDSS_SHA256_ARM64=e6f5d5122d735f9dbfd42c9eaba067a557a5613ee4a6001806935de11aff4b09

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # Never let ultralytics pip-install packages at runtime (would silently diverge from the image).
    YOLO_AUTOINSTALL=false

COPY requirements.txt /opt/savior/requirements.txt

RUN set -eux; \
    # Global pins applied to every pip call: numpy<2 (cv_bridge is built against numpy 1.x) and the
    # torch pair, so no later install can swap them out.
    printf 'numpy==1.26.4\ntorch==%s\ntorchvision==%s\n' "${TORCH_VERSION}" "${TORCHVISION_VERSION}" \
        > /opt/savior/constraints.txt; \
    export PIP_CONSTRAINT=/opt/savior/constraints.txt; \
    python3 -m pip install --upgrade "pip==26.2.1"; \
    if [ "${PLATFORM}" = "amd64" ]; then \
        python3 -m pip install --index-url "${TORCH_INDEX_AMD64}" \
            "torch==${TORCH_VERSION}" "torchvision==${TORCHVISION_VERSION}"; \
        python3 -m pip install "tensorrt-cu12==${TENSORRT_VERSION_AMD64}" "onnxruntime-gpu==1.23.2"; \
        # Drop the builder resources for *Windows-target* engines (~3 GB, never used on Linux).
        find /usr/local/lib/python3.10/dist-packages/tensorrt_libs -name 'libnvinfer_builder_resource_win_*' -delete; \
    else \
        # The Jetson torch wheel links libopenblas.so.0 and libcudss.so.0, which JetPack's base
        # image does not ship (all other CUDA libs it needs are in l4t-jetpack).
        apt-get update; \
        apt-get install -y --no-install-recommends libopenblas0; \
        rm -rf /var/lib/apt/lists/*; \
        curl -fsSL -o /tmp/cudss.tar.xz "${CUDSS_URL_ARM64}"; \
        echo "${CUDSS_SHA256_ARM64}  /tmp/cudss.tar.xz" | sha256sum -c -; \
        mkdir -p /opt/cudss; \
        tar -xJf /tmp/cudss.tar.xz -C /opt/cudss --strip-components=1 --wildcards '*/lib/libcudss.so*' '*/LICENSE*'; \
        rm -f /tmp/cudss.tar.xz; \
        echo /opt/cudss/lib > /etc/ld.so.conf.d/cudss.conf; \
        ldconfig; \
        python3 -m pip install --index-url "${TORCH_INDEX_ARM64}" \
            "torch==${TORCH_VERSION}" "torchvision==${TORCHVISION_VERSION}"; \
        python3 -m pip install "onnxruntime==1.23.2"; \
    fi; \
    python3 -m pip install -r /opt/savior/requirements.txt; \
    # ultralytics without deps: it hard-requires opencv-python (GUI build); we ship the headless
    # build instead (requirements.txt), its remaining deps are listed there explicitly.
    python3 -m pip install --no-deps "ultralytics==8.4.177"; \
    python3 -c "import numpy; assert numpy.__version__.startswith('1.'), numpy.__version__"; \
    # Import smoke test. On Jetson the GPU driver libraries are only mounted at `docker run` time,
    # so a failure there is reported but does not fail the build (run savior-check-env instead).
    if [ "${PLATFORM}" = "amd64" ]; then \
        python3 -c "import torch, torchvision, cv2, tensorrt, ultralytics"; \
    else \
        python3 -c "import torch, torchvision, cv2, tensorrt, ultralytics" \
            || echo "WARNING: python import smoke test failed at build time (expected without GPU libs?)"; \
    fi

# =================================================================================================
# dev: non-root user matching the host uid/gid, entrypoint
# =================================================================================================
FROM ml AS dev
ARG PLATFORM

ARG USERNAME=savior
ARG USER_UID=1000
ARG USER_GID=1000

# run.sh/exec.sh read these to warn when the image uid/gid does not match the calling user.
LABEL org.savior.platform="${PLATFORM}" org.savior.uid="${USER_UID}" org.savior.gid="${USER_GID}"

# Create (or adopt) the user/group with the requested ids. If the base image already has a user
# with that uid, it is renamed. Group memberships: video/render are needed for GPU access on Jetson,
# dialout/plugdev for serial/USB sensors.
RUN set -eux; \
    if ! getent group "${USER_GID}" >/dev/null; then groupadd --gid "${USER_GID}" "${USERNAME}"; fi; \
    existing="$(getent passwd "${USER_UID}" | cut -d: -f1 || true)"; \
    if [ -n "${existing}" ]; then \
        usermod --login "${USERNAME}" --home "/home/${USERNAME}" --move-home --gid "${USER_GID}" \
            --shell /bin/bash "${existing}"; \
    else \
        useradd --uid "${USER_UID}" --gid "${USER_GID}" --create-home --shell /bin/bash "${USERNAME}"; \
    fi; \
    for g in video render dialout plugdev; do \
        if getent group "${g}" >/dev/null; then usermod -aG "${g}" "${USERNAME}"; fi; \
    done; \
    echo "${USERNAME} ALL=(ALL) NOPASSWD:ALL" > "/etc/sudoers.d/${USERNAME}"; \
    chmod 0440 "/etc/sudoers.d/${USERNAME}"

COPY --chmod=0755 entrypoint.sh /usr/local/bin/savior-entrypoint
COPY --chmod=0755 check_env.py /usr/local/bin/savior-check-env

# Interactive shells (docker exec -it ... bash) get the same environment as the entrypoint.
RUN echo 'source /usr/local/bin/savior-entrypoint' >> /etc/bash.bashrc

USER ${USERNAME}
WORKDIR /home/${USERNAME}
RUN rosdep update --rosdistro "${ROS_DISTRO}"

ENTRYPOINT ["/usr/local/bin/savior-entrypoint"]
CMD ["bash"]
