# NOTAS — Simulación FR10 en EC2

Fecha: 2026-09-10. Instancia `<INSTANCE_ID>` (`fr10-sim`). Repo del fabricante: `FAIR-INNOVATION/frcobot_ros2` commit `5bed0b0263c8f1e95f51aa45079f904d463c5c50` (2026-09-02).

## Decisiones

### Gazebo Sim Fortress (6.18.0), no Harmonic
- Fortress es la versión emparejada oficialmente con ROS 2 Humble: `ros-humble-ros-gz` y `ros-humble-gz-ros2-control` salen del repositorio de ROS con binarios para Jammy amd64 y funcionan con un solo `apt install`.
- Harmonic también tiene binarios para Jammy amd64, pero para Humble necesita el `ros_gz` del repositorio de OSRF (paquetes `ros-humble-ros-gzharmonic`), incompatibles con `ros-humble-ros-gz`, y `gz_ros2_control` compilado desde fuente. Es más frágil para el mismo resultado.
- **Advertencia:** el soporte de Fortress termina en septiembre de 2026. Los binarios siguen instalándose, pero no habrá parches. Si hace falta soporte a largo plazo, lo siguiente sería Harmonic con ROS 2 Jazzy sobre Ubuntu 24.04.

### Acceso visual: noVNC en lugar de gzweb
- `gzweb` es de Gazebo Classic y no funciona con Gazebo Sim. La alternativa web de Gazebo Sim necesita un servidor websocket y compilar el cliente, y solo muestra Gazebo.
- noVNC sirve el escritorio completo: la GUI de Gazebo **y** RViz con el panel MotionPlanning, en el navegador y sin cliente.
- Pila: `Xvfb :1` → `fluxbox` → `x11vnc` (solo `localhost:5901`, con contraseña) → `websockify`/noVNC en `:8080`. Son 4 servicios systemd (`fr10-*`) que arrancan solos.
- Sin GPU: el render es por software (Mesa llvmpipe). Al principio la GUI usaba `--render-engine ogre` (Ogre 1.x) con la suposición, no probada, de que Ogre 2 no funcionaría por software. **Era incorrecto:** con Ogre 1.x el visor 3D parpadea en gris, y con `ogre2` se ve estable (ver la sección del 2026-09-11). `04_sim.sh gazebo` usa `ogre2`. Con la GUI abierta, el factor de tiempo real ronda 0.35–0.45 (medido).

### Seguridad
- El security group abre los puertos 22 y `FR10_NOVNC_PORT` **solo a las IPs `/32` de las máquinas que ejecutan `fr10 up`**, nunca a `0.0.0.0/0`. noVNC va por HTTP sin TLS, y el escritorio incluye una terminal: abierto a internet equivaldría a dar acceso a la instancia a quien adivine una contraseña de 8 caracteres.
- La contraseña VNC es aleatoria (8 caracteres, el máximo de VNC). Está en `~/.vnc/password.txt` dentro de la instancia y en SSM Parameter Store (parámetro `FR10_PASSWORD_PARAM` del `.env`, SecureString con la clave `aws/ssm`), de donde la lee `fr10 up`. No está en este repositorio.

### Alcance del workspace (`~/fr10_ws`)
- Se compilan 5 paquetes: `fairino_description`, `fairino_msgs`, `fairino_hardware`, `fairino10_v6_moveit2_config` y el nuevo `fairino10_v6_gazebo`.
- Con `COLCON_IGNORE` quedan fuera las configuraciones MoveIt de los otros modelos (FR3, FR3MT, FR5, FR16, FR20, FR30) y los 10 drivers `fairino_hardware_v3_*`/`_master`, que dependen de la versión de firmware del robot real y no aplican a simulación.
- `fairino_hardware` compila solo con *warnings* (`-Wwrite-strings`, `-Wsign-compare`) en `fairino_version.cpp`. No es un error, así que no se tocó.
- No se modificó ningún archivo del fabricante: toda la adaptación está en el paquete nuevo `fairino10_v6_gazebo`. Así un `git pull` del repo original no pisa nada.

### Script de movimiento (`fr10_move_to_pose.py`)
- Usa la acción `/move_action` (`moveit_msgs/action/MoveGroup`) con restricciones de **posición y orientación** de `wrist3_link` en `base_link`, es decir, un objetivo cartesiano y no articular.
- No usa `moveit_py`, que no tiene binarios para Humble; solo `rclpy` y `moveit_msgs`.
- Sin argumentos, la pose objetivo se calcula con `/compute_fk` a partir de la postura `pos2` del SRDF de FAIRINO, así que siempre es alcanzable. Con `--xyz/--rpy` se da una pose arbitraria.
- No se fía del `SUCCESS` de MoveIt: después de ejecutar lee `/joint_states`, calcula la cinemática directa de la postura final y **falla (exit 1) si el error de posición supera 10 mm**. Así detectó el problema de gravedad descrito abajo.

## Qué se adaptó de Gazebo Classic y por qué

El repo de FAIRINO solo trae MoveIt con `mock_components/GenericSystem`. Lo único de Gazebo que contiene son dependencias comentadas en `package.xml` (`gazebo_ros_control`, `joint_trajectory_controller`). Todo esto es nuevo en `fairino10_v6_gazebo`:

| Gazebo Classic (lo esperado por el repo) | Gazebo Sim Fortress (lo implementado) | Motivo |
|---|---|---|
| `gazebo_ros_control` / `libgazebo_ros2_control.so` | plugin `libgz_ros2_control-system.so`, clase `gz_ros2_control::GazeboSimROS2ControlPlugin` | Gazebo Classic está descontinuado (enero 2025); en Gazebo Sim el puente con ros2_control es `gz_ros2_control` |
| `mock_components/GenericSystem` (demo MoveIt) | `gz_ros2_control/GazeboSimSystem` | Las articulaciones las mueve el motor de física, no un mock |
| `gazebo_ros` `spawn_entity.py` | `ros_gz_sim create -topic robot_description` | Spawner equivalente en ros_gz |
| `/clock` publicado por `gazebo_ros` | `ros_gz_bridge parameter_bridge /clock@rosgraph_msgs/msg/Clock[ignition.msgs.Clock` | Gazebo Sim no publica en ROS sin puente |
| `gazebo.launch.py` | `ros_gz_sim gz_sim.launch.py` (`ign gazebo -r -s empty.sdf` headless o con GUI) | Equivalente de Gazebo Sim |
| Mallas `package://fairino_description/...` | Se reescriben a `file://<share>/...` al generar el URDF en el launch | Gazebo Sim, RViz y MoveIt resuelven `file://` igual, sin depender de `IGN_GAZEBO_RESOURCE_PATH` |
| Base sin fijar | Link `world` + joint fijo `world_to_base_link` | Sin eso Gazebo deja el brazo suelto |
| Solo interfaz de estado `position` | `position` + `velocity` | El JTC necesita velocidad con hardware físico |
| `use_sim_time` sin definir | `use_sim_time: true` en `robot_state_publisher`, controladores, `move_group` y RViz | El tiempo lo marca Gazebo vía `/clock` |
| — | JTC: `stopped_velocity_tolerance: 0.0`, `goal_time: 0.0`, `allow_nonzero_velocity_at_trajectory_end` | Evitar abortos por la oscilación residual de la física |
| — | MoveIt: `allowed_start_tolerance: 0.05`, `execution_duration_monitoring: false` | Con RTF < 1 (GUI por software) la ejecución tarda más en reloj de pared |
| — | Compensación de gravedad en los links del brazo (`turnGravityOff`), argumento xacro `gravity_compensation` (por defecto `true`) | Ver el error 7 |

## Errores encontrados

1. **La instancia arm64 `gazebo-ros2` (`<INSTANCE_ID_ARM64_ANTERIOR>`, c7g.xlarge) ya estaba `terminated`** al empezar. El paso 2 no requirió acción.
2. **`timeout` no existe en macOS.** Un chequeo por SSH falló con `command not found: timeout`. Se sustituyó por `ssh -o ConnectTimeout`.
3. **SSH colgado al lanzar la instalación con `nohup … &`.** La sesión no se cerraba y la herramienta la pasó a segundo plano a los 120 s. La instalación siguió corriendo sin problema. Después se usó `ssh -n` + `setsid nohup … & disown`.
4. **`03_novnc.sh` salió con código 141 (SIGPIPE).** Con `set -o pipefail`, `tr -dc … < /dev/urandom | head -c 8` falla cuando `head` cierra la tubería. Se reemplazó por `python3 -c "import secrets…"`. Resuelto al 2º intento.
5. **`pkill -f` mató mi propia sesión SSH (código 255).** El patrón (`ign gazebo|move_group…`) aparecía en la línea de comando del `bash -c` remoto. `04_sim.sh` usa patrones con corchetes (`[i]gn gazebo`), que no coinciden consigo mismos.
6. **`position_proportional_gain` del YAML no se aplica.** El log muestra `The position_proportional_gain has been set to: 0.1`. Según el código de `gz_ros2_control` (rama humble, `gz_ros2_control_plugin.cpp`), el nodo `gz_ros2_control` se crea (línea 357) antes de cargar el `--params-file` en el contexto rcl (líneas 391–396), así que ese nodo nunca ve el YAML. Se quitó el bloque para no dejar configuración sin efecto. Además, el valor por defecto no es tan bajo como parece: `gz_system.cpp` multiplica el error por `update_rate` (100 Hz), así que la ganancia efectiva es 10 s⁻¹.
7. **El hombro (j2) se hunde con gravedad.** Con la pose `(-0.5, 0.4, 0.6)`, MoveIt dio `SUCCESS` pero el script midió **16.07 mm** de error y salió con exit 1. Diagnóstico con el brazo quieto:
   - `controller_state` → `error.positions = [-0.00094, 0.02352, ~0, ~0, ~0, ~0]`: 23.5 mrad solo en j2.
   - Unos 30 s después j2 seguía en 0.1752 rad. Con un comando de ~0.235 rad/s hacia la referencia, la articulación no se movía: estaba **saturada por esfuerzo**, no era un problema de ganancia.
   - Causa: el URDF de FAIRINO limita j1–j3 a `effort="150"` N·m, y el torque estático de gravedad con el brazo casi horizontal, calculado con las masas del propio URDF, es de unos 170 N·m (estimación a mano). El robot real sostiene el brazo con sus servos (probablemente el 150 del URDF es torque nominal y no pico, sin verificar).
   - Solución: desactivar la gravedad en los links del brazo en Gazebo, lo que emula la compensación de los servos, sin inventar límites de torque.
   - Resultado verificado (el SDF convertido tiene 7 links con `<gravity>` desactivada):
     - Pose `(-0.5, 0.4, 0.6)`, rpy `(π, 0, 0)`: **4.10 mm, exit 0** (antes 16.07 mm, exit 1).
     - Pose por defecto (FK de `pos2`): **4.62 mm, exit 0**.
     - `controller_state error.positions` con el brazo quieto: **~1e-10 rad** en las 6 articulaciones (antes 23.5 mrad en j2).
     - Con gravedad (`gravity_compensation:=false`), la primera prueba headless hacia `pos2` dio 4.13 mm. Esa postura carga menos el hombro, por eso no falló.
8. **`pkill` volvió a matar mi sesión SSH, aun usando corchetes.** `pkill -f "[i]gn gazebo -g"` no coincide consigo mismo, pero sí con **otra** parte del mismo comando remoto, que contenía el texto literal `ign gazebo -g` (la línea que lanzaba la GUI). El truco de los corchetes solo protege si el texto buscado no aparece en ningún otro lugar de la línea de comando. Para experimentos así: escribir los comandos en un archivo y ejecutarlo (`bash /tmp/x.sh`), o matar por PID. Además, al matar la GUI de Gazebo también terminó el servidor (lanzados juntos por `ign gazebo`), mientras `fr10-sim.service` seguía `active` con solo `move_group` y RViz vivos. Se corrigió con un reinicio de la instancia.

## Observaciones sin causa verificada

- **Error cartesiano residual de ~4 mm aunque el JTC sigue la trayectoria con error ~0.** El desvío está en el plan que devuelve MoveIt, no en el seguimiento. Probablemente viene de la tolerancia con que KDL/OMPL muestrean el objetivo (región de posición: esfera de 2 mm de radio; orientación: ±0.01 rad), pero no se investigó. Por eso el script usa una tolerancia de 10 mm.
- **Aviso al procesar el xacro:** `Using load_yaml() directly is deprecated. Use xacro.load_yaml() instead.` Solo es un aviso. No se cambió a `xacro.load_yaml()` para no tocar un archivo ya verificado sin volver a validarlo.
- **Visor 3D de Gazebo gris. Diagnóstico del 2026-09-10, corregido el 2026-09-11:** la causa real es el parpadeo de Ogre 1.x, no un primer render lento; las capturas sueltas caían en frames buenos o malos (ver la sección del 2026-09-11). Se conserva el razonamiento original, que resultó incorrecto: Salió gris en `screenshots/fr10_novnc_final.png` (~2 min tras lanzar) y en `screenshots/fr10_boot.png` (tomada 46 s después del arranque). En la misma sesión del arranque en frío, la captura de las 14:15:36 (`screenshots/fr10_gazebo_render.png`) ya mostraba la cuadrícula y el FR10 en la pose alcanzada. Mediciones: CPU `ign gazebo gui` 153 %, `rviz2` 136 %, `ign gazebo server` 69 % (≈360 % de 400 % en 4 vCPU), render por software (`llvmpipe`, OpenGL 4.5, Mesa 23.2.1), motor `ogre` 1.x cargado sin errores en `ogre.log`. Si se ve gris: esperar 1–2 min. Si molesta, un tipo de instancia con más vCPU (p. ej. c5.2xlarge) acortaría la espera; no se probó. Un experimento con la GUI relanzada sola (E2) seguía negro a los 45 s; el experimento con `ogre2` (E3) no llegó a ejecutarse (ver error 8).
- **RViz:** `Action server: /recognize_objects not available`. Es normal sin percepción configurada.
- **move_group:** `No 3D sensor plugin(s) defined for octomap updates`. Es normal sin sensores 3D.

## Comando `fr10`: IPs dinámicas y acceso desde varias máquinas

Problema: tanto la IP de la instancia (sin Elastic IP) como las de los clientes (ISP dinámico) cambian, y el security group solo admite IPs concretas.

Decisiones:
- **Una regla por máquina, identificada en la descripción** (`fr10:<client-id>`, con el ID guardado en `~/.config/fr10/client-id`). `fr10 up` revoca solo las reglas de esa máquina cuyo CIDR ya no coincide con su IP actual. Revocar "la anterior" sin identificar al dueño le quitaría el acceso a otra computadora. Si dos máquinas comparten IP (misma red), la segunda no crea una regla duplicada, porque AWS la rechazaría. `fr10 prune` limpia las reglas de máquinas que ya no se usan.
- **La instancia se busca por el tag `Name=fr10-sim`**, no por ID. El script es un único archivo que se copia tal cual a otra máquina.
- **Otra máquina no necesita el `.pem`:** la simulación arranca sola (`fr10-sim.service`) y la contraseña VNC se lee de SSM Parameter Store. El `.pem` solo hace falta para `fr10 ssh` y `fr10 setup`.
- **Sin rol IAM ni SSM Agent en la instancia:** SSM solo se usa como almacén de la contraseña, escrita desde el Mac con `fr10 setup`. Así no hay que crear roles ni perfiles de instancia.
- **Compatible con bash 3.2** (el de macOS) y con Linux; en Windows, vía WSL. Nada de arrays asociativos ni otras funciones de bash 4. Para generar el ID se usa `od -N3` en vez de `tr < /dev/urandom | head`, para no repetir el SIGPIPE del error 4.
- **Apagado de seguridad en cada arranque** con `fr10-autoshutdown.service` (`shutdown -h +300`). Sustituye al user-data, que solo corría en el primer arranque. `InstanceInitiatedShutdownBehavior=stop` garantiza que el apagado **detiene** la instancia y no la termina.
- **La simulación como servicio systemd** (`fr10-sim.service`, `Restart=on-failure`, `KillSignal=SIGINT`, log en `~/launch.log`). `04_sim.sh gui` pasa a usar el servicio para no lanzar dos simulaciones a la vez.
- Las reglas creadas a mano al principio (`ssh`/`novnc` para `<IP_CLIENTE>/32`) se eliminaron con `fr10 prune` y se reemplazaron por las gestionadas por `fr10`.

Pruebas realizadas (2026-09-10):
- Regla falsa con la descripción de este Mac y la IP de documentación `203.0.113.7/32` (no enrutable), como "IP anterior" → `fr10 up` la revocó en los puertos 22 y 8080 y autorizó `<IP_CLIENTE>/32`.
- `fr10 up` con la instancia detenida → la arrancó, obtuvo la IP nueva (`<IP_INSTANCIA_2>`; antes era `<IP_INSTANCIA_1>`) y noVNC respondió en ~29 s en total.
- `fr10 up` repetido con la instancia encendida → no duplicó reglas y leyó la contraseña de SSM.
- `fr10 setup` → `fr10-sim` y `fr10-autoshutdown` quedaron activados, y la contraseña quedó en SSM como SecureString.
- Arranque en frío (`fr10 down` + `fr10 up`, con `~/launch.log` vaciado antes) → IP nueva `<IP_INSTANCIA_3>`. Arranque del SO a las 14:12:38 UTC y `fr10-sim` activo a las 14:12:51, sin intervención. Resultados:
  - "You can start planning now" aparece 1 vez en el log.
  - Los dos controladores quedan `active`.
  - Apagado programado (`MODE=poweroff`).
  - `fr10_move_to_pose.py --xyz -0.5 0.4 0.6 --rpy 3.14159 0 0` → 4.13 mm, exit 0.
  - Captura: `screenshots/fr10_boot.png`.

## 2026-09-11: parpadeo de Gazebo, pausa, ventanas y cambio a modo mock

Síntomas reportados: el visor 3D de Gazebo parpadeaba en gris y las ventanas no se podían mover.

Hallazgos:
1. **El parpadeo lo causa Ogre 1.x, no la falta de CPU.** Método: 12 capturas del visor midiendo el contraste (gris liso frente a cuadrícula).
   - Con RViz activo, solo 4 de 12 frames tenían imagen.
   - Con RViz pausado (SIGSTOP), la GUI subió de 173 % a 265 % de CPU y el parpadeo siguió igual (3 de 12).
   - Probé otras GUIs contra el mismo servidor, mientras la original seguía parpadeando: Ogre 1.x con `QSG_RENDER_LOOP=basic` fue peor (casi todo en blanco); **`ogre2` salió estable en 12 de 12**.
   - Pendiente: confirmar `ogre2` con el brazo en movimiento, porque durante esa prueba la simulación estaba en pausa.
2. **La simulación estaba en pausa.** `/stats` mostraba `paused: true` con las iteraciones congeladas en 74061, y por eso no se publicaba `/joint_states`. Se reanudó con `ign service -s /world/empty/control --reqtype ignition.msgs.WorldControl --reptype ignition.msgs.Boolean --req "pause: false"`. No se pudo determinar quién la pausó: el factor de tiempo real ya estaba congelado en la primera medición, antes de las pruebas invasivas.
3. **Ventanas inalcanzables.** Gazebo abría en y = −126 y RViz medía 975 px de alto en una pantalla de 900, así que sus barras de título quedaban fuera de la pantalla. Ahora `fr10-layout.service` (con `xdotool`) las coloca en cada arranque.
4. **ROS 2 perdió el descubrimiento de los nodos de la simulación** entre las 02:41 y las 02:45 UTC. Los procesos seguían vivos, pero `ros2 node list --no-daemon` no los veía y `/controller_manager` no respondía. Un `talker` nuevo sí funcionaba, así que el DDS del host estaba sano.
   - Descartados: memoria, `/dev/shm`, entorno de ROS y red.
   - Hipótesis de que `needrestart` reinició servicios tras `apt install xdotool`: **descartada** por el journal (ningún servicio reiniciado, sin eventos de red después del arranque).
   - **Causa no identificada.** No se descarta que la provocaran mis pruebas sobre la sesión: SIGSTOP de RViz, matar GUIs de prueba, comandos cortados con `timeout`. Se resolvió reiniciando la simulación.
5. **`ros2 node list` vacío con `xmlrpc.client.Fault: !rclpy.ok()`** es el daemon de la CLI en mal estado, no un fallo de los nodos. Se resuelve con `ros2 daemon stop`.

Errores propios en esta sesión: un `set -u` en mi script remoto hizo fallar el `source` de ROS (`AMENT_TRACE_SETUP_FILES: unbound variable`); no es un fallo del proyecto. Además, las pruebas se hicieron sobre la sesión en vivo del usuario (ventanas extra, RViz congelado unos segundos, intentos de mover el brazo). Para la próxima: diagnosticar con capturas y lecturas, y probar cambios en una simulación aparte o con aviso previo.

**Decisión: el modo por defecto pasa a ser MoveIt2 + RViz con hardware simulado** (demo de FAIRINO con `mock_components`), elegido por el usuario para escribir y probar scripts de movimiento.
- Motivo: no necesita Gazebo, no parpadea, usa mucha menos CPU y la física de Gazebo hoy no aporta nada, porque la gravedad está compensada y no hay objetos.
- Gazebo sigue disponible con `~/04_sim.sh gazebo` (GUI con `ogre2`) o `~/04_sim.sh headless`.
- `fr10-sim.service` ahora lanza `fairino10_v6_moveit2_config demo.launch.py` y tiene `Wants=network-online.target`.

Verificación del modo mock tras `fr10 setup`:
- "You can start planning now" una vez y 0 procesos de Gazebo.
- `fairino10_controller` y `joint_state_broadcaster` activos.
- `fr10_move_to_pose.py`: 1.34 mm (pos2) y 1.71 mm (`-0.5 0.4 0.6`), exit 0.
- RViz a pantalla completa, 1600×845 en (0, 24). Captura: `screenshots/fr10_mock.png`.

Recordatorio para Robot App: ni MoveIt ni Gazebo emulan el controlador FAIRINO. En producción el edge invoca primitivas Lua por el SDK (D2); esta simulación sirve para probar rutas y alcance con el URDF, no el camino SDK → Lua.

## Limitaciones y pendientes

- **Modo Gazebo con `ogre2` sin verificar con movimiento** (ver la sección del 2026-09-11).
- **Si el apagado de 5 h interrumpe el trabajo:** cancelarlo con `fr10 ssh 'sudo shutdown -c'` (requiere el `.pem`). Sin `.pem`, basta con `fr10 down` + `fr10 up`, que reinicia el contador.
- **Credenciales de `aws login` temporales:** cuando expiran, `fr10` falla con un mensaje claro y basta con volver a ejecutar `aws login`.
- **Costos:** "nada de pago" se interpretó como nada de software o AMIs de pago del Marketplace ni GPU. c5.xlarge on-demand se cobra por hora mientras está `running`, y el volumen gp3 de 50 GB se sigue cobrando aunque la instancia esté `stopped`.
- **Con gravedad compensada, Gazebo no reproduce la dinámica real bajo carga.** Sirve para validar planificación y ejecución de trayectorias con MoveIt2, no para dimensionar torques.
- **Fortress al final de su soporte** (ver Decisiones).
- **RTF ~0.35 con la GUI abierta** (render por software en 4 vCPU). En modo `headless` la simulación va más fluida.
