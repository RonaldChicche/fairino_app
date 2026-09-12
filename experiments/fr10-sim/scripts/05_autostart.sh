#!/usr/bin/env bash
# 05_autostart.sh — en cada arranque de la instancia:
#   - fr10-sim.service: MoveIt2 + RViz con hardware simulado (demo de FAIRINO, sin Gazebo) en DISPLAY=:1
#   - fr10-layout.service: deja las ventanas dentro de la pantalla (RViz sola, o Gazebo | RViz)
#   - fr10-autoshutdown.service: apagado de seguridad a los FR10_AUTOSHUTDOWN_MIN minutos
#     (InstanceInitiatedShutdownBehavior=stop: la instancia queda stopped)
# Configuración: ~/fr10.env, generado con `fr10 env` (lo hace `fr10 setup`).
# Para usar Gazebo: ~/04_sim.sh gazebo | headless. Idempotente. Requiere 03_novnc.sh ya aplicado.
set -euxo pipefail

[ -r ~/fr10.env ] || { echo "falta ~/fr10.env: ejecuta 'fr10 env' desde el Mac" >&2; exit 1; }
set -a
. ~/fr10.env
set +a
: "${FR10_AUTOSHUTDOWN_MIN:?falta en ~/fr10.env}"

sudo DEBIAN_FRONTEND=noninteractive NEEDRESTART_MODE=l apt-get install -y -qq xdotool

sudo tee /etc/systemd/system/fr10-sim.service > /dev/null <<'EOF'
[Unit]
Description=Simulacion FR10: MoveIt2 + RViz con hardware simulado (mock) en DISPLAY=:1
Wants=network-online.target
After=fr10-fluxbox.service network-online.target
Requires=fr10-xvfb.service

[Service]
User=ubuntu
Environment=DISPLAY=:1
ExecStartPre=/bin/sleep 5
ExecStart=/bin/bash -c 'source /opt/ros/humble/setup.bash && source /home/ubuntu/fr10_ws/install/setup.bash && exec ros2 launch fairino10_v6_moveit2_config demo.launch.py'
StandardOutput=append:/home/ubuntu/launch.log
StandardError=append:/home/ubuntu/launch.log
KillSignal=SIGINT
TimeoutStopSec=30
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Gazebo y RViz abren con la barra de título fuera de la pantalla y no se pueden arrastrar.
# El tamaño se calcula con la resolución real de Xvfb (FR10_SCREEN), no con valores fijos.
sudo tee /usr/local/bin/fr10-layout > /dev/null <<'EOF'
#!/usr/bin/env bash
export DISPLAY=:1
TOP=24     # alto de la barra de título de fluxbox
BOTTOM=31  # barra de tareas de fluxbox más margen
RV=""
for _ in $(seq 1 240); do
  RV=$(xdotool search --name 'RViz$' 2> /dev/null | head -1)
  [ -n "$RV" ] && break
  sleep 1
done
[ -n "$RV" ] || exit 0
# Margen para que las apps terminen de fijar su propia geometría
sleep 5
read -r W H < <(xdpyinfo | awk '/dimensions:/ { split($2, d, "x"); print d[1], d[2] }')
HEIGHT=$((H - TOP - BOTTOM))
HALF=$((W / 2))
GZ=$(xdotool search --name '^Gazebo$' 2> /dev/null | head -1)
if [ -n "$GZ" ]; then
  xdotool windowsize "$GZ" $((HALF - 5)) "$HEIGHT" windowmove "$GZ" 0 "$TOP"
  xdotool windowsize "$RV" "$HALF" "$HEIGHT" windowmove "$RV" "$HALF" "$TOP"
else
  xdotool windowsize "$RV" "$W" "$HEIGHT" windowmove "$RV" 0 "$TOP"
fi
exit 0
EOF
sudo chmod +x /usr/local/bin/fr10-layout

sudo tee /etc/systemd/system/fr10-layout.service > /dev/null <<'EOF'
[Unit]
Description=Coloca las ventanas de RViz (y Gazebo) dentro del escritorio noVNC
After=fr10-sim.service
PartOf=fr10-sim.service

[Service]
Type=oneshot
RemainAfterExit=yes
User=ubuntu
ExecStart=/usr/local/bin/fr10-layout
TimeoutStartSec=300

[Install]
WantedBy=fr10-sim.service
EOF

sudo tee /etc/systemd/system/fr10-autoshutdown.service > /dev/null <<EOF
[Unit]
Description=Apagado de seguridad ${FR10_AUTOSHUTDOWN_MIN} min despues de cada arranque (la instancia queda stopped)
After=multi-user.target

[Service]
Type=oneshot
ExecStart=/sbin/shutdown -h +${FR10_AUTOSHUTDOWN_MIN}

[Install]
WantedBy=multi-user.target
EOF

# Detener cualquier simulación en marcha (servicio o lanzada a mano) antes de reiniciar el servicio
[ -x ~/04_sim.sh ] && ~/04_sim.sh stop || true

sudo systemctl daemon-reload
sudo systemctl enable fr10-sim fr10-layout fr10-autoshutdown
sudo systemctl restart fr10-sim
sudo systemctl start fr10-autoshutdown
systemctl is-enabled fr10-sim fr10-layout fr10-autoshutdown
systemctl is-active fr10-sim
