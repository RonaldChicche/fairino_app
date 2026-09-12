#!/usr/bin/env bash
# 02_build_ws.sh — workspace ~/fr10_ws con frcobot_ros2 (solo FR10) + fairino10_v6_gazebo
# Requiere ~/fairino10_v6_gazebo copiado previamente a la instancia y ~/fr10.env (`fr10 env` desde el Mac).
set -eo pipefail
[ -r ~/fr10.env ] || { echo "falta ~/fr10.env: ejecuta 'fr10 env' desde el Mac" >&2; exit 1; }
set -a
. ~/fr10.env
set +a
source /opt/ros/humble/setup.bash
set -ux
: "${FR10_MAINTAINER_EMAIL:?falta en ~/fr10.env}"

mkdir -p ~/fr10_ws/src
cd ~/fr10_ws/src
[ -d frcobot_ros2 ] || git clone https://github.com/FAIR-INNOVATION/frcobot_ros2.git
git -C frcobot_ros2 log -1 --format='frcobot_ros2 commit %H (%cd)'

# Solo FR10: se ignoran las configs MoveIt de otros modelos y los drivers de hardware por versión de firmware
for d in frcobot_ros2/fairino{3,5,16,20,30,3mt}_v6_moveit2_config frcobot_ros2/fairino_hardware_*; do
  touch "$d/COLCON_IGNORE"
done

rm -rf fairino10_v6_gazebo
cp -r ~/fairino10_v6_gazebo .
# El package.xml versionado lleva un email genérico; el real viene de ~/fr10.env
sed -i "s|maintainer@example.com|${FR10_MAINTAINER_EMAIL}|" fairino10_v6_gazebo/package.xml

cd ~/fr10_ws
colcon list
colcon build --symlink-install --event-handlers console_direct+ 2>&1 | tee ~/colcon_build.log
grep -q '/fr10_ws/install/setup.bash' ~/.bashrc || echo 'source ~/fr10_ws/install/setup.bash' >> ~/.bashrc
