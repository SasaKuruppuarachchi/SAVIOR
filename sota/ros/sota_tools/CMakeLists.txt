cmake_minimum_required(VERSION 3.0.2)
project(sota_tools)
set(CMAKE_BUILD_TYPE Release)
set(CMAKE_CXX_STANDARD 14)
find_package(catkin REQUIRED COMPONENTS roscpp rosbag sensor_msgs cv_bridge)
find_package(OpenCV 4.2 REQUIRED)
find_package(Eigen3 REQUIRED)
find_package(Pangolin REQUIRED)
set(ORB_SLAM3_ROOT "/opt/sota/ORB_SLAM3" CACHE PATH "ORB-SLAM3 source/build root")
catkin_package()
catkin_install_python(PROGRAMS scripts/pose_recorder.py DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION})
include_directories(${catkin_INCLUDE_DIRS} ${EIGEN3_INCLUDE_DIR} ${Pangolin_INCLUDE_DIRS}
  ${ORB_SLAM3_ROOT} ${ORB_SLAM3_ROOT}/include ${ORB_SLAM3_ROOT}/include/CameraModels ${ORB_SLAM3_ROOT}/Thirdparty/Sophus)
add_executable(orbslam3_bag_si src/orbslam3_bag_si.cc)
target_link_libraries(orbslam3_bag_si ${catkin_LIBRARIES} ${OpenCV_LIBS} ${Pangolin_LIBRARIES}
  ${ORB_SLAM3_ROOT}/lib/libORB_SLAM3.so ${ORB_SLAM3_ROOT}/Thirdparty/DBoW2/lib/libDBoW2.so
  ${ORB_SLAM3_ROOT}/Thirdparty/g2o/lib/libg2o.so -lboost_serialization -lcrypto)
