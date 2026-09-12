#!/usr/bin/env bash
# 04_sim.sh — elige cómo corre la simulación FR10 en la instancia.
#   ~/04_sim.sh mock       MoveIt2 + RViz con hardware simulado (demo de FAIRINO, sin Gazebo). Modo de fr10-sim.service
#   ~/04_sim.sh gazebo     Gazebo Sim con GUI (ogre2) + ros2_control + MoveIt2 + RViz
#   ~/04_sim.sh headless   Gazebo Sim sin GUI + ros2_control + MoveIt2 + RViz
#   ~/04_sim.sh stop
# Log: ~/launch.log
set -uo pipefail

# Los patrones con [x] evitan que pkill/pgrep coincidan con la línea de comando de este mismo script
PATTERNS='[i]gn gazebo|[m]ove_group|[r]viz2|[r]obot_state_publisher|[p]arameter_bridge|[r]os2_control_node|[r]os2 launch fairino10'

stop() {
  sudo systemctl stop fr10-sim 2> /dev/null || true
  pkill -INT -f '[r]os2 launch fairino10' || true
  for _ in $(seq 1 15); do
    pgrep -f "$PATTERNS" > /dev/null || return 0
    sleep 1
  done
  pkill -KILL -f "$PATTERNS" || true
}

launch_gazebo() {
  export DISPLAY=:1
  setsid nohup bash -c 'source /opt/ros/humble/setup.bash && source ~/fr10_ws/install/setup.bash && exec ros2 launch fairino10_v6_gazebo fr10_gz_moveit.launch.py "$@"' \
    _ "$@" > ~/launch.log 2>&1 < /dev/null &
  setsid nohup /usr/local/bin/fr10-layout > /dev/null 2>&1 < /dev/null &
}

case "${1:-}" in
  mock)
    stop
    sudo systemctl start fr10-sim
    ;;
  gazebo)
    stop
    # Sin GPU (Mesa llvmpipe): con ogre (1.x) el visor 3D parpadea en gris; ogre2 se ve estable (ver NOTAS.md)
    launch_gazebo "gz_args:=-r -v 3 --render-engine ogre2 empty.sdf" rviz:=true
    ;;
  headless)
    stop
    launch_gazebo rviz:=true
    ;;
  stop)
    stop
    ;;
  *)
    echo "uso: $0 mock|gazebo|headless|stop" >&2
    exit 2
    ;;
esac
