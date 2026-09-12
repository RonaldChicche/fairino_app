cmake_minimum_required(VERSION 3.8)
project(fairino10_v6_gazebo)

find_package(ament_cmake REQUIRED)

install(DIRECTORY launch urdf config
  DESTINATION share/${PROJECT_NAME}
)

install(PROGRAMS scripts/fr10_move_to_pose.py
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
