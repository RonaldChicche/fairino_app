#!/usr/bin/env bash
# 03_novnc.sh — escritorio virtual headless (Xvfb :1 + fluxbox) servido por noVNC en FR10_NOVNC_PORT.
# Sin GPU: RViz (y Gazebo, si se usa) renderizan por software (Mesa llvmpipe).
# Configuración: ~/fr10.env, generado con `fr10 env` desde el .env del Mac.
# Volver a ejecutarlo aplica cambios de puertos o resolución: reinicia el escritorio y la simulación.
set -euxo pipefail

[ -r ~/fr10.env ] || { echo "falta ~/fr10.env: ejecuta 'fr10 env' desde el Mac" >&2; exit 1; }
set -a
. ~/fr10.env
set +a
: "${FR10_NOVNC_PORT:?falta en ~/fr10.env}" "${FR10_VNC_PORT:?falta en ~/fr10.env}" "${FR10_SCREEN:?falta en ~/fr10.env}"

mkdir -p ~/.vnc
if [ ! -f ~/.vnc/passwd ]; then
  # Sin tuberías: con pipefail, 'tr < /dev/urandom | head' termina con SIGPIPE (exit 141)
  PW=$(python3 -c "import secrets, string; print(''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8)))")
  x11vnc -storepasswd "$PW" ~/.vnc/passwd
  printf '%s\n' "$PW" > ~/.vnc/password.txt
  chmod 600 ~/.vnc/passwd ~/.vnc/password.txt
fi

# noVNC sirve la página en "/" si existe index.html
[ -e /usr/share/novnc/index.html ] || sudo ln -s /usr/share/novnc/vnc.html /usr/share/novnc/index.html

sudo tee /etc/systemd/system/fr10-xvfb.service > /dev/null <<EOF
[Unit]
Description=Xvfb :1 para el escritorio de simulacion FR10
[Service]
User=ubuntu
ExecStart=/usr/bin/Xvfb :1 -screen 0 ${FR10_SCREEN}x24 -nolisten tcp
Restart=always
[Install]
WantedBy=multi-user.target
EOF

sudo tee /etc/systemd/system/fr10-fluxbox.service > /dev/null <<'EOF'
[Unit]
Description=Gestor de ventanas fluxbox en :1
After=fr10-xvfb.service
Requires=fr10-xvfb.service
[Service]
User=ubuntu
Environment=DISPLAY=:1
ExecStartPre=/bin/sleep 2
ExecStart=/usr/bin/fluxbox
Restart=always
[Install]
WantedBy=multi-user.target
EOF

sudo tee /etc/systemd/system/fr10-x11vnc.service > /dev/null <<EOF
[Unit]
Description=x11vnc sobre :1 (solo localhost)
After=fr10-xvfb.service
Requires=fr10-xvfb.service
[Service]
User=ubuntu
ExecStartPre=/bin/sleep 3
ExecStart=/usr/bin/x11vnc -display :1 -rfbport ${FR10_VNC_PORT} -localhost -forever -shared -rfbauth /home/ubuntu/.vnc/passwd
Restart=always
[Install]
WantedBy=multi-user.target
EOF

sudo tee /etc/systemd/system/fr10-novnc.service > /dev/null <<EOF
[Unit]
Description=noVNC (websockify) en el puerto ${FR10_NOVNC_PORT}
After=fr10-x11vnc.service
[Service]
User=ubuntu
ExecStart=/usr/bin/websockify --web /usr/share/novnc ${FR10_NOVNC_PORT} localhost:${FR10_VNC_PORT}
Restart=always
[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable fr10-xvfb fr10-fluxbox fr10-x11vnc fr10-novnc
sudo systemctl restart fr10-xvfb fr10-fluxbox fr10-x11vnc fr10-novnc
# La simulación dibuja en :1; si ya está instalada, se reinicia con el escritorio nuevo
if systemctl is-enabled --quiet fr10-sim 2> /dev/null; then
  sudo systemctl restart fr10-sim
fi
sleep 5
systemctl is-active fr10-xvfb fr10-fluxbox fr10-x11vnc fr10-novnc
