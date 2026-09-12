#!/usr/bin/env bash
# 01_install.sh — ROS 2 Humble desktop + colcon + MoveIt2 + Gazebo Fortress + ros_gz + noVNC
# Ubuntu 22.04 (Jammy) amd64. Ejecutar como usuario 'ubuntu' (usa sudo).
set -euxo pipefail
export DEBIAN_FRONTEND=noninteractive NEEDRESTART_MODE=a

sudo -E apt-get update
sudo -E apt-get install -y locales software-properties-common curl gnupg lsb-release git
sudo locale-gen en_US en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
sudo add-apt-repository -y universe

# Repositorio oficial de ROS 2 (paquete ros2-apt-source)
VER=$(curl -fsSL https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest | grep -F '"tag_name"' | awk -F'"' '{print $4}')
curl -fsSL -o /tmp/ros2-apt-source.deb \
  "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${VER}/ros2-apt-source_${VER}.$(. /etc/os-release && echo "$VERSION_CODENAME")_all.deb"
sudo -E dpkg -i /tmp/ros2-apt-source.deb
sudo -E apt-get update
sudo -E apt-get -y upgrade

# ROS 2 Humble + herramientas + MoveIt2 + ros2_control + Gazebo Fortress (ros_gz) + escritorio headless
sudo -E apt-get install -y \
  ros-humble-desktop ros-dev-tools python3-colcon-common-extensions python3-rosdep \
  ros-humble-moveit ros-humble-ros2-control ros-humble-ros2-controllers \
  ros-humble-ros-gz ros-humble-xacro ros-humble-joint-state-publisher-gui \
  xvfb x11vnc novnc websockify fluxbox xterm mesa-utils

# Plugin gz_ros2_control para Fortress (el nombre del paquete cambió entre versiones de Humble)
sudo -E apt-get install -y ros-humble-gz-ros2-control || sudo -E apt-get install -y ros-humble-ign-ros2-control

sudo rosdep init || true
rosdep update

grep -q '/opt/ros/humble/setup.bash' ~/.bashrc || echo 'source /opt/ros/humble/setup.bash' >> ~/.bashrc
echo "INSTALL_DONE"
