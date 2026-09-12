# SETUP — Simulación FAIRINO FR10 (ROS 2 Humble + Gazebo Sim Fortress + MoveIt2) en EC2

## Configuración

`fr10` no tiene valores fijos en el código: lee sus variables `FR10_*` de `experiments/env/.env`, o de `~/.config/fr10/.env` en una computadora sin el repo. Toda la carpeta `experiments/env/` está en `.gitignore` salvo la plantilla.

```bash
cp experiments/env/.env.example experiments/env/.env   # desde la raíz del repo; luego reemplaza los <PLACEHOLDERS>
```

Esta documentación muestra los IDs de AWS y las IPs como placeholders (`<AWS_ACCOUNT_ID>`, `<INSTANCE_ID>`, `<SG_ID>`, `<IP_CLIENTE>`…). Los valores reales están en `experiments/env/.env` o se consultan con `fr10 status`.

## Uso diario: un comando

```bash
fr10 up       # arranca todo y abre Gazebo + RViz en el navegador
fr10 down     # detiene la instancia (stop; el script no tiene ninguna ruta a terminate)
fr10 status   # estado, IP de la instancia, tu IP y reglas del security group
fr10 ssh      # terminal en la instancia (requiere el .pem)
fr10 env      # copia a la instancia (~/fr10.env) la configuración de sus scripts (requiere el .pem)
fr10 webapp   # túnel a la WebApp de FAIRINO SimMachine en http://localhost (requiere el .pem y sudo)
```

`fr10 up` hace, en orden:
1. Obtiene la IP pública **actual** de la máquina donde corre (`checkip.amazonaws.com`, con `api.ipify.org` de respaldo).
2. En el security group, revoca la regla que **esta misma máquina** tenía con su IP anterior y autoriza la nueva en los puertos 22 y `FR10_NOVNC_PORT`. Cada máquina se identifica con `~/.config/fr10/client-id`, que va en la descripción de sus reglas (`fr10:<client-id>`), así que actualizar la IP de un equipo no le quita el acceso a otro.
3. Arranca la instancia (si se estaba deteniendo, espera primero) y obtiene su IP pública nueva.
4. Espera a que noVNC responda en `FR10_NOVNC_PORT` y lee la contraseña VNC del parámetro de SSM Parameter Store `FR10_PASSWORD_PARAM` (SecureString). En Mac también la copia al portapapeles.
5. Abre `http://<IP>:<NOVNC_PORT>/vnc.html?autoconnect=true&resize=scale`. Por defecto arranca **MoveIt2 + RViz con hardware simulado** (demo de FAIRINO, sin Gazebo), listo en ~1 min, con RViz a pantalla completa.

**Modos de simulación** (requieren el `.pem`; el modo por defecto vuelve en cada arranque):

```bash
fr10 ssh '~/04_sim.sh mock'       # MoveIt2 + RViz con hardware simulado (por defecto)
fr10 ssh '~/04_sim.sh gazebo'     # Gazebo Sim con GUI (ogre2) + MoveIt2 + RViz, lado a lado
fr10 ssh '~/04_sim.sh headless'   # Gazebo Sim sin GUI + MoveIt2 + RViz
fr10 ssh '~/04_sim.sh stop'
```

La instancia se **detiene sola** a los `FR10_AUTOSHUTDOWN_MIN` minutos de cada arranque (`fr10-autoshutdown.service`).

**Variables de la instancia** (`FR10_NOVNC_PORT`, `FR10_VNC_PORT`, `FR10_SCREEN`, `FR10_AUTOSHUTDOWN_MIN`, `FR10_MAINTAINER_EMAIL`): se editan en el `.env` del Mac y se copian con `fr10 env`, que `fr10 setup` también ejecuta. Aplicar un cambio: puertos o resolución → `fr10 env && fr10 ssh '~/03_novnc.sh'` (reinicia escritorio y simulación, y si cambia `FR10_NOVNC_PORT` hay que ejecutar `fr10 up` para abrir el puerto nuevo); minutos de apagado → `fr10 setup`; email → `fr10 env && fr10 ssh '~/02_build_ws.sh'`. Para cancelar ese apagado: `fr10 ssh 'sudo shutdown -c'`.

Opciones de línea de comandos: `FR10_NO_BROWSER=1` (no abrir el navegador) y `FR10_ENV_FILE=<ruta>` (usar otro `.env`). El resto de la configuración va en el `.env`.

### WebApp de FAIRINO SimMachine (`fr10 webapp`)

SimMachine es el controlador FAIRINO en Docker dentro de la instancia. Los hallazgos y las pruebas están en `experiments/glambot-routes/NOTAS.md`. Su WebApp solo es accesible desde dentro de la instancia, así que `fr10 webapp` la trae a esta máquina por un túnel SSH (requiere el `.pem`).

```bash
fr10 webapp up       # abre el túnel y http://localhost en el navegador
fr10 webapp status   # indica si el túnel está abierto y si la WebApp responde
fr10 webapp down     # cierra el túnel
```

- **Por qué el puerto 80 y `sudo`:** la vista 3D y el estado del robot llegan por un canal en vivo (WebSocket) que la página arma como `ws://<host de la URL>:<FR10_WEBAPP_WS_PORT>`. Si la URL lleva puerto, por ejemplo `localhost:18080`, esa dirección es inválida: la página carga, pero el robot aparece congelado aunque se mueva. Por eso el túnel usa el puerto 80 local, que en macOS exige `sudo`, además de `FR10_WEBAPP_WS_PORT`.
- **Qué cambia en esta máquina:** nada persistente. Es un proceso `ssh` de root en segundo plano que dura hasta `fr10 webapp down`, un reinicio o un corte de red. No toca `/etc/hosts`, `~/.ssh/config` ni el navegador. Mientras está abierto, `http://localhost` lleva a la WebApp y los puertos 80 y `FR10_WEBAPP_WS_PORT` quedan ocupados.
- **Credenciales:** `FR10_WEBAPP_USER` y `FR10_WEBAPP_PASSWORD` en `experiments/env/.env`, que está en `.gitignore`. No se escriben en archivos versionados.
- **Tras arrancar la instancia:** el contenedor no arranca solo (política `restart=no`). Antes de `fr10 webapp up`, ejecuta `fr10 ssh 'sudo docker start fairino-container'`. Si la IP de la instancia cambió, el túnel anterior queda sin conexión: `fr10 webapp down` y luego `fr10 webapp up`.
- **Variables:** `FR10_SIM_IP`, `FR10_WEBAPP_PORT` y `FR10_WEBAPP_WS_PORT`.

### Usarlo desde otra computadora

Solo hace falta el AWS CLI con sesión iniciada, el archivo `fr10` y su `.env`. **No hace falta el `.pem`**, salvo para `fr10 ssh`, `fr10 setup`, `fr10 env` y `fr10 webapp`.

1. Instalar [AWS CLI v2](https://aws.amazon.com/cli/) e iniciar sesión en la cuenta `<AWS_ACCOUNT_ID>`: `aws login`, o `aws configure` con credenciales propias.
2. Copiar `experiments/fr10-sim/fr10` a la otra máquina (AirDrop, USB, repositorio privado…) y dejarlo en el `PATH`:
   ```bash
   mkdir -p ~/.local/bin && cp fr10 ~/.local/bin/ && chmod +x ~/.local/bin/fr10
   ```
3. Crear `~/.config/fr10/.env` a partir de `experiments/env/.env.example`, con los valores reales.
4. `fr10 up`. La primera vez crea el `client-id` de esa máquina y su propia regla.
5. Linux: funciona igual (abre el navegador con `xdg-open`). Windows: usar WSL (Ubuntu), con el AWS CLI instalado dentro de WSL.
6. Si esa máquina ya no se va a usar, desde cualquier otra: `fr10 prune` (revoca las reglas de todas las máquinas excepto la actual).

Si se usa otro usuario IAM, necesita estos permisos: `sts:GetCallerIdentity`, `ec2:DescribeInstances`, `ec2:StartInstances`, `ec2:StopInstances`, `ec2:DescribeSecurityGroupRules`, `ec2:AuthorizeSecurityGroupIngress`, `ec2:RevokeSecurityGroupIngress`, `ssm:GetParameter` y `kms:Decrypt` sobre la clave `aws/ssm`.

## Datos de la instancia

| Campo | Valor |
|---|---|
| Nombre (tag) | `fr10-sim` (así la encuentra `fr10`, sin IDs fijos) |
| Instance ID | `<INSTANCE_ID>` |
| Región / AZ | `us-east-1` / `us-east-1a` |
| Tipo | `c5.2xlarge` (8 vCPU, 16 GiB, x86_64, sin GPU) desde el 2026-09-11, para correr SimMachine junto a la simulación. Se lanzó como `c5.xlarge` (4 vCPU, 7.5 GiB); cambio de tipo en "Desde cero", paso 6 |
| AMI | `<AMI_ID>` — `ubuntu-jammy-22.04-amd64-server-20260904`, owner Canonical `099720109477` |
| Disco | 50 GB gp3 (`/dev/sda1`) |
| Key pair | `fr10-key` (`<KEY_PAIR_ID>`) → `~/.ssh/fr10-key.pem` (chmod 400) |
| Security group | `fr10-sg` (`<SG_ID>`), VPC por defecto `<VPC_ID>` |
| Puertos | 22 (SSH) y `<NOVNC_PORT>` (noVNC), solo desde las IPs que registra `fr10 up` (una regla `/32` por máquina) |
| IP pública | Dinámica: cambia en cada arranque. Consultar con `fr10 status` |
| Acceso visual | `http://<IP>:<NOVNC_PORT>` → noVNC; contraseña en el parámetro de SSM `FR10_PASSWORD_PARAM` (y en la instancia: `~/.vnc/password.txt`) |
| Configuración en la instancia | `~/fr10.env`, generado por `fr10 env`: no se edita a mano |
| Usuario SSH | `ubuntu` |
| Servicios en la instancia | `fr10-xvfb`, `fr10-fluxbox`, `fr10-x11vnc`, `fr10-novnc`, `fr10-sim` (MoveIt2 + RViz mock), `fr10-layout` (coloca las ventanas dentro de la pantalla), `fr10-autoshutdown` (systemd, habilitados) |
| Estado | Consultar con `fr10 status` |
| Capturas | `screenshots/fr10_mock.png` (modo por defecto: MoveIt2 + RViz mock), `screenshots/fr10_novnc_gui.png` y `screenshots/fr10_novnc_final.png` (Gazebo GUI + RViz con Ogre 1.x), `screenshots/fr10_boot.png` y `screenshots/fr10_gazebo_render.png` (frames grises y buenos del parpadeo de Ogre 1.x) |

## Desde cero

Todos los archivos están en `experiments/fr10-sim/` del repo; la configuración, en `experiments/env/`:

```
fr10-sim/
├── fr10                   # comando de uso diario (enlazado en ~/.local/bin/fr10)
├── SETUP.md, NOTAS.md
├── scripts/
│   ├── 01_install.sh      # ROS 2 Humble desktop, colcon, MoveIt2, ros2_control, Gazebo Fortress (ros_gz), gz_ros2_control, Xvfb/x11vnc/noVNC
│   ├── 02_build_ws.sh     # ~/fr10_ws: clona frcobot_ros2, ignora otros modelos, copia fairino10_v6_gazebo, colcon build
│   ├── 03_novnc.sh        # servicios systemd: Xvfb :1 (FR10_SCREEN) + fluxbox + x11vnc (localhost:FR10_VNC_PORT) + websockify/noVNC (FR10_NOVNC_PORT)
│   ├── 04_sim.sh          # mock | gazebo | headless | stop
│   └── 05_autostart.sh    # fr10-sim.service (mock al arrancar) + fr10-layout.service (ventanas) + fr10-autoshutdown.service (stop a las 5 h)
├── fairino10_v6_gazebo/   # paquete ROS 2 nuevo (Gazebo Sim + gz_ros2_control + MoveIt2 + script Python)
└── screenshots/
```

### 1. Verificar el CLI
```bash
aws sts get-caller-identity
```

### 2. Key pair y security group
```bash
umask 077
aws ec2 create-key-pair --region us-east-1 --key-name fr10-key --key-type rsa --key-format pem \
  --query KeyMaterial --output text > ~/.ssh/fr10-key.pem
chmod 400 ~/.ssh/fr10-key.pem

VPC=$(aws ec2 describe-vpcs --region us-east-1 --filters Name=isDefault,Values=true --query 'Vpcs[0].VpcId' --output text)
SG=$(aws ec2 create-security-group --region us-east-1 --group-name fr10-sg \
      --description "FR10 sim: SSH and noVNC" --vpc-id $VPC --query GroupId --output text)
# Sin reglas de entrada: las crea 'fr10 up' con la IP de cada máquina
```

### 3. Lanzar la instancia
```bash
AMI=$(aws ssm get-parameter --region us-east-1 \
  --name /aws/service/canonical/ubuntu/server/22.04/stable/current/amd64/hvm/ebs-gp2/ami-id \
  --query Parameter.Value --output text)
set -a; . experiments/env/.env; set +a                     # desde la raíz del repo
printf '#!/bin/bash\nshutdown -h +%s\n' "$FR10_AUTOSHUTDOWN_MIN" > userdata.sh   # solo el primer arranque; luego fr10-autoshutdown

aws ec2 run-instances --region us-east-1 --image-id $AMI --instance-type c5.xlarge \
  --key-name fr10-key --security-group-ids $SG \
  --block-device-mappings 'DeviceName=/dev/sda1,Ebs={VolumeSize=50,VolumeType=gp3,DeleteOnTermination=true}' \
  --instance-initiated-shutdown-behavior stop \
  --user-data file://userdata.sh \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=fr10-sim}]'

ln -sfn "$(pwd)/experiments/fr10-sim/fr10" ~/.local/bin/fr10   # desde la raíz del repo
FR10_NO_BROWSER=1 fr10 up          # autoriza tu IP y espera a la instancia (noVNC aún no existe: cortar con Ctrl+C tras "esperando noVNC")
IP=$(aws ec2 describe-instances --region us-east-1 --filters Name=tag:Name,Values=fr10-sim Name=instance-state-name,Values=running \
      --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)
```

### 4. Instalar, compilar, noVNC y autoarranque
Desde `experiments/fr10-sim/`:
```bash
K=~/.ssh/fr10-key.pem
scp -i $K -r scripts/01_install.sh scripts/02_build_ws.sh scripts/03_novnc.sh fairino10_v6_gazebo ubuntu@$IP:~/
ssh -i $K ubuntu@$IP 'chmod +x ~/0*.sh ~/fairino10_v6_gazebo/scripts/*.py'
ssh -i $K ubuntu@$IP '~/01_install.sh > ~/install.log 2>&1'   # ~10 min; termina con INSTALL_DONE
fr10 env                                                        # ~/fr10.env: lo leen 02, 03 y 05
ssh -i $K ubuntu@$IP '~/02_build_ws.sh'                         # colcon build: 5 paquetes
ssh -i $K ubuntu@$IP '~/03_novnc.sh && . ~/fr10.env && curl -I localhost:$FR10_NOVNC_PORT'  # HTTP/1.1 200 OK
fr10 setup                                                      # 04_sim.sh + 05_autostart.sh + contraseña VNC en SSM
```

### 5. Verificar
```bash
fr10 up
fr10 ssh 'grep "You can start planning now" ~/launch.log'
fr10 ssh 'source /opt/ros/humble/setup.bash && source ~/fr10_ws/install/setup.bash && ros2 run fairino10_v6_gazebo fr10_move_to_pose.py'
fr10 down
```

### 6. Cambiar el tipo de instancia (para SimMachine)
SimMachine y la simulación juntos necesitan más CPU y RAM que `c5.xlarge`. El tipo solo se puede cambiar con la instancia detenida:
```bash
set -a; . experiments/env/.env; set +a                     # desde la raíz del repo
fr10 down
IID=$(aws ec2 describe-instances --region "$FR10_REGION" \
      --filters "Name=tag:Name,Values=$FR10_NAME" Name=instance-state-name,Values=stopped \
      --query 'Reservations[0].Instances[0].InstanceId' --output text)
aws ec2 modify-instance-attribute --region "$FR10_REGION" --instance-id "$IID" --instance-type '{"Value": "c5.2xlarge"}'
fr10 up
```

### 7. FAIRINO SimMachine (controlador FAIRINO en Docker)
Se descargó de fairino.support (Fairino Europe), porque el enlace de Google Drive de la documentación oficial está retirado. Los hallazgos y las pruebas de rutas están en `experiments/glambot-routes/NOTAS.md`.
```bash
fr10 ssh 'bash -s' <<'EOF'
set -e
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq docker.io unzip
sudo systemctl enable --now docker
mkdir -p ~/simmachine && cd ~/simmachine
curl -fL --retry 3 -o SimMachine_Docker_v3.9.3.zip "https://fairino.support/download/SimMachine%20Docker_v3.9.3.zip"
echo "355f4c7f015b920d2a9ebf9b5e4456bbe1d1762895774d11d8976ded74238927  SimMachine_Docker_v3.9.3.zip" | sha256sum -c -
unzip -p SimMachine_Docker_v3.9.3.zip "FAIRINO SimMachine Docker/FAIRINOSimMachine/FAIRINOSimMachine.tar" | sudo docker load
sudo docker network create --driver bridge --subnet 192.168.58.0/24 --gateway 192.168.58.1 fairino-net
sudo docker run -d --name fairino-container --privileged -u root --net fairino-net --ip 192.168.58.2 fairino_simmachine:v3.9.3
EOF
```
- **Imagen:** `fairino_simmachine:v3.9.3`, basada en Ubuntu 18.04. Trae el controlador `V3.9.15-LX` y un robot FR5. Pasarlo a FR10 exige la contraseña de modo mantenimiento de FAIRINO (pendiente).
- **Puertos del contenedor**, accesibles solo desde dentro de la instancia:
  - 80: WebApp
  - 9999: canal en vivo de la WebApp
  - 20003: SDK por XML-RPC
  - 20004: estado en tiempo real
  - 20010: subida de archivos (`LuaUpload`)

  La WebApp se abre en esta máquina con `fr10 webapp up`. Los scripts del SDK corren en la instancia.
- **Credenciales de la WebApp:** `FR10_WEBAPP_USER` y `FR10_WEBAPP_PASSWORD` en `experiments/env/.env`.
- **El contenedor no arranca solo** (política `restart=no`). Tras cada `fr10 up`, ejecuta `fr10 ssh 'sudo docker start fairino-container'`.

## Verificaciones rápidas dentro de la instancia (`fr10 ssh`)

```bash
source /opt/ros/humble/setup.bash && source ~/fr10_ws/install/setup.bash
ros2 --help
ign gazebo --version                         # Gazebo Sim, version 6.18.0
systemctl status fr10-sim                    # simulación (log: ~/launch.log)
ros2 control list_controllers                # joint_state_broadcaster + fairino10_controller: active
ros2 param get /move_group robot_description | grep -o '<robot name="[^"]*"'
ign model --list                             # solo en modo gazebo/headless: ground_plane, fairino10_v6
. ~/fr10.env && curl -I localhost:$FR10_NOVNC_PORT
ros2 daemon stop                             # si 'ros2 node list' sale vacío con los nodos corriendo
~/04_sim.sh mock | gazebo | headless | stop  # cambiar de modo
```
