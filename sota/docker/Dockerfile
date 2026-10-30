# savior-sota:noetic - SOTA stereo-inertial baselines for SAVIOR's controlled comparison (ROS 1 Noetic, Ubuntu 20.04)
#   VINS-Fusion (GPL-3.0), DynaVINS (GPL-3.0), ORB-SLAM3 (GPL-3.0) + sota_tools (pose recorder, ORB-SLAM3 bag driver)
# Build with ../build.sh (host network for the build only; experiments run with --network none).
FROM ros:noetic-perception-focal@sha256:32370c500818eaefb8491d7d85e9f415541b7f4bfec8afc59c4240653e7a77e4

ARG VINS_FUSION_COMMIT=be55a937a57436548ddfb1bd324bc1e9a9e828e0
ARG DYNAVINS_COMMIT=0b4f492aeeb1a3752507a9b9a50124e10bfcf091
ARG ORB_SLAM3_COMMIT=4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4
ARG PANGOLIN_COMMIT=dd801d244db3a8e27b7fe8020cd751404aa818fd
ARG JOBS=8

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
      git cmake build-essential python3-catkin-tools \
      libceres-dev libgoogle-glog-dev libgflags-dev libsuitesparse-dev libeigen3-dev \
      libglew-dev libgl1-mesa-dev libegl1-mesa-dev libwayland-dev libxkbcommon-dev wayland-protocols \
      libboost-serialization-dev libssl-dev \
      ros-noetic-cv-bridge ros-noetic-image-transport ros-noetic-tf ros-noetic-pcl-ros ros-noetic-rosbag \
    && rm -rf /var/lib/apt/lists/*

# fetch a pinned commit without history
RUN printf '#!/bin/sh\nset -e\nmkdir -p "$3" && cd "$3" && git init -q && git remote add origin "$1" && git fetch -q --depth 1 origin "$2" && git checkout -q FETCH_HEAD && rm -rf .git\n' > /usr/local/bin/fetch_commit && chmod +x /usr/local/bin/fetch_commit

# ---- Pangolin v0.6 (ORB-SLAM3 viewer dependency; viewer is disabled at run time)
RUN fetch_commit https://github.com/stevenlovegrove/Pangolin.git $PANGOLIN_COMMIT /tmp/Pangolin \
 && cd /tmp/Pangolin && mkdir build && cd build \
 && cmake .. -DCMAKE_BUILD_TYPE=Release -DBUILD_EXAMPLES=OFF -DBUILD_TESTS=OFF -DBUILD_PANGOLIN_PYTHON=OFF \
      -DBUILD_PANGOLIN_FFMPEG=OFF -DBUILD_PANGOLIN_LIBREALSENSE=OFF -DBUILD_PANGOLIN_OPENNI2=OFF \
 && make -j$JOBS install && cd / && rm -rf /tmp/Pangolin && ldconfig

# ---- sources (pinned) + patches
COPY patches /opt/sota/patches
RUN mkdir -p /opt/sota/catkin_ws/src \
 && fetch_commit https://github.com/HKUST-Aerial-Robotics/VINS-Fusion.git $VINS_FUSION_COMMIT /opt/sota/catkin_ws/src/VINS-Fusion \
 && fetch_commit https://github.com/url-kaist/dynaVINS.git $DYNAVINS_COMMIT /opt/sota/catkin_ws/src/dynaVINS \
 && fetch_commit https://github.com/UZ-SLAMLab/ORB_SLAM3.git $ORB_SLAM3_COMMIT /opt/sota/ORB_SLAM3 \
 && bash /opt/sota/patches/apply_patches.sh /opt/sota/catkin_ws/src/VINS-Fusion /opt/sota/catkin_ws/src/dynaVINS /opt/sota/ORB_SLAM3 \
 && printf 'VINS-Fusion %s\ndynaVINS %s\nORB_SLAM3 %s\nPangolin %s\n' $VINS_FUSION_COMMIT $DYNAVINS_COMMIT $ORB_SLAM3_COMMIT $PANGOLIN_COMMIT > /opt/sota/COMMITS.txt

# ---- ORB-SLAM3 (third-party libs + library only; upstream examples are not needed)
RUN cd /opt/sota/ORB_SLAM3 \
 && for d in DBoW2 g2o Sophus; do (cd Thirdparty/$d && mkdir -p build && cd build && cmake .. -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTS=OFF && make -j$JOBS); done \
 && (cd Vocabulary && tar -xf ORBvoc.txt.tar.gz && rm ORBvoc.txt.tar.gz) \
 && mkdir -p build && cd build && cmake .. -DCMAKE_BUILD_TYPE=Release && make -j$JOBS ORB_SLAM3 \
 && rm -rf /opt/sota/ORB_SLAM3/build /opt/sota/ORB_SLAM3/Thirdparty/*/build

# ---- catkin workspace: VINS-Fusion (camera_models, vins, loop_fusion), DynaVINS, sota_tools
COPY ros/sota_tools /opt/sota/catkin_ws/src/sota_tools
RUN cd /opt/sota/catkin_ws && . /opt/ros/noetic/setup.sh \
 && catkin config --extend /opt/ros/noetic --cmake-args -DCMAKE_BUILD_TYPE=Release -DORB_SLAM3_ROOT=/opt/sota/ORB_SLAM3 \
 && catkin build -j$JOBS --no-status \
 && rm -rf build logs

ENV LD_LIBRARY_PATH=/opt/sota/ORB_SLAM3/lib:/opt/sota/ORB_SLAM3/Thirdparty/DBoW2/lib:/opt/sota/ORB_SLAM3/Thirdparty/g2o/lib:/usr/local/lib
RUN printf '#!/bin/bash\nsource /opt/sota/catkin_ws/devel/setup.bash\nexec "$@"\n' > /opt/sota/entrypoint.sh && chmod +x /opt/sota/entrypoint.sh
ENTRYPOINT ["/opt/sota/entrypoint.sh"]
CMD ["bash"]
