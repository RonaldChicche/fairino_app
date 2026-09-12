# NOTAS — glambot-routes

Rutas de glambot como programas Lua del controlador FAIRINO, generadas en el PC y probadas en FAIRINO SimMachine. Fecha: 2026-09-11.

**Entorno de prueba:**
- SimMachine Docker v3.9.3 (controlador `V3.9.15-LX`, WebApp `v3.9.3`) en la instancia `fr10-sim`, contenedor `fairino-container` en `192.168.58.2`.
- Descargado de fairino.support (Fairino Europe), SHA-256 `355f4c7f015b920d2a9ebf9b5e4456bbe1d1762895774d11d8976ded74238927`. El enlace de la documentación oficial (Google Drive) está retirado.
- **El robot simulado es un FR5** (`FR5-V1-002(V6.0)`). Pasarlo a FR10 exige la contraseña de modo mantenimiento, que FAIRINO no publica (pendiente con FAIRINO).
- **La WebApp solo muestra el robot en vivo si se abre sin puerto en la URL.** El estado en tiempo real (articulaciones, estado del programa, habilitación) llega por un WebSocket que la página arma como `ws://<location.host>:9999`. Entrando por `localhost:18080` queda `ws://localhost:18080:9999`, una URL inválida: la vista 3D se congela en la postura cero y parece que el robot no se mueve aunque el controlador sí lo haga. Solución: `fr10 webapp up`, que abre el túnel por el puerto 80 local y el del WebSocket (detalle en `experiments/fr10-sim/SETUP.md`). Verificado con Chrome headless el 2026-09-11: con el WebSocket conectado, la vista 3D siguió un `MoveJ` del SDK.
- **SDK Python `v2.2.3_robot3.9.3`**, del repo oficial. El SDK vendorizado en `experiments/fairino` (V2.2.8, para 3.9.9) lee el estado por CNDE (puerto 20005), que la 3.9.3 no tiene, y marca la conexión como caída.

## Archivos

| Archivo | Qué hace |
|---|---|
| `routes.py` | Geometría "mirar a un punto" en la convención FAIRINO (R = Rz·Ry·Rx), grúa vertical relativa al objetivo, conversión cámara → brida, interpolación de poses y generador del `.lua` |
| `planner.py` | Elige la semilla de cinemática inversa recorriendo la ruta con puntos intermedios y la IK del propio controlador, maximizando el margen a los límites |
| `run_route.py` | Ejecuta un `.lua` de ruta en el controlador emulando el lado del PC (objetivo, ID de toma, confirmación de cámara) y registra estados y poses |
| `simmachine_probe.py`, `lua_probes/` | Pruebas mínimas de capacidades del Lua del controlador |
| `crane_fr5.lua` | Programa generado y **ejecutado con éxito** en SimMachine (FR5) |

## Cómo reproducir

**Preparar la instancia (una vez).** SimMachine se instala siguiendo `experiments/fr10-sim/SETUP.md` ("Desde cero", pasos 6 y 7). Luego, desde la raíz del repo:

```bash
# SDK Python v2.2.3_robot3.9.3 del repo oficial de FAIRINO: basta con Robot.py
fr10 ssh 'bash -s' <<'EOF'
set -e
TAG=v2.2.3_robot3.9.3
D=~/fairino_sdk_v2.2.3/fairino
mkdir -p "$D" && touch "$D/__init__.py"
P=$(curl -fsS "https://api.github.com/repos/FAIR-INNOVATION/fairino-python-sdk/git/trees/$TAG?recursive=1" \
  | python3 -c "import sys,json; c=[x['path'] for x in json.load(sys.stdin)['tree'] if x['path'].endswith('Robot.py')]; print(next((p for p in c if 'linux' in p.lower()), c[0]))")
curl -fsSL -o "$D/Robot.py" "https://raw.githubusercontent.com/FAIR-INNOVATION/fairino-python-sdk/$TAG/$P"
EOF

# Copiar esta carpeta a ~/glambot-routes en la instancia; repetir tras cada cambio
set -a; . experiments/env/.env; set +a
IP=$(aws ec2 describe-instances --region "$FR10_REGION" \
     --filters "Name=tag:Name,Values=$FR10_NAME" Name=instance-state-name,Values=running \
     --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)
scp -q -r -i "$FR10_PEM" -o HostKeyAlias="$FR10_NAME" -o UserKnownHostsFile=~/.config/fr10/known_hosts \
  experiments/glambot-routes "ubuntu@$IP:"
```

**En cada sesión:**
1. `fr10 up`
2. `fr10 ssh 'sudo docker start fairino-container'`
3. Para ver el robot: `fr10 webapp up`

Después, en la instancia (`fr10 ssh`, luego `cd ~/glambot-routes`):

```bash
ROUTE="--target -900 0 350 --standoff 350 --dz-start -150 --dz-end 250 --steps 6 --camera-offset 100"
python3 planner.py --ip 192.168.58.2 --sdk ~/fairino_sdk_v2.2.3 $ROUTE --samples 10 --max-jump 15 --extra-seed 0 -90 90 -90 -90 0
python3 routes.py $ROUTE --lua crane_fr5.lua --seed-joints <semilla del planner> --speed 20 --acc 50 --blend 10 --camera-timeout 30
python3 run_route.py --ip 192.168.58.2 --sdk ~/fairino_sdk_v2.2.3 --lua crane_fr5.lua $ROUTE --take-id 1 --camera-delay 1.5 --start-joints 0 -90 90 -90 -90 0
```

## Protocolo del `.lua` (variables de sistema)

- **PC → robot:** `s_var_1..3` = objetivo x, y, z (mm, base) · `s_var_4` = ID de toma · `s_var_5` = cámara grabando (el PC escribe el ID de toma).
- **Robot → PC:** `s_var_6` = estado (0 iniciado, 1 esperando cámara, 2 moviendo, 3 terminado, −1 punto inalcanzable, −2 la cámara no confirmó a tiempo) · `s_var_7` = ID aceptado.
- **Orden del programa:** comprueba que todos los puntos tienen solución antes de mover nada → espera la confirmación de la cámara → `MoveJ` al primer punto → `MoveL` por el resto.

## Hallazgos verificados en SimMachine

**Programas y subida**
1. **Ruta de los programas:** `/usr/local/etc/controller/lua/` (controlador tipo LA). Con `/fruser/`, `ProgramLoad` devuelve 144 = "LUA file does not exist" (tabla oficial de errores).
2. **`LuaUpload` valida el script ejecutándolo:**
   - en esa pasada la cinemática devuelve `nil`: el programa debe detectarlo y terminar sin moverse;
   - exige el nombre literal `s_var_N` en `SetSysVarValue`: pasarlo dentro de una variable de Lua da *"failed to query the database"*;
   - rechaza comas dentro de los argumentos de `SetSysVarValue` (*"Error number of parameters"*): hay que calcular antes en una variable local;
   - esa ejecución de validación **no escribe** variables de sistema.
3. **Subidas intermitentes:** el primer intento suele fallar. El log del controlador muestra *"bind error: Address already in use"* en el puerto de transferencia; reintentar tras 2 s funciona.

**Lua del controlador**
4. **Variables de sistema:** `GetSysVarValue`/`SetSysVarValue(s_var_N)` en Lua equivalen a `GetSysVarValue/SetSysVarValue(N)` del SDK. Son float y se leen en vivo mientras el programa corre: la espera activa de una señal del PC funciona.
5. **Librería `math`:** disponible. La lectura de `_VERSION` no fue concluyente.
6. **Cinemática:**
   - `GetInverseKin(type, x, y, z, rx, ry, rz, config)` devuelve 6 valores;
   - `GetInverseKinRef(type, {pose}, {ref})` devuelve una tabla;
   - `GetInverseKinHasSolution` devuelve un **número** (1/0), no un booleano.
7. **Movimiento:** `MoveJ` y `MoveL` con la firma textual del manual FRLua funcionan. Una prueba bajó exactamente 50 mm.
8. **La espera de la cámara sí bloquea el movimiento:** `motion_done` pasó a 0 recién después de que el PC confirmara la cámara.
9. **Las instrucciones que no son de movimiento se ejecutan por adelantado.** El `SetSysVarValue(s_var_6, 3)` del final llegó 19,5–27,9 s **antes** de que el brazo terminara. Consecuencia: el "terminé" para detener la cámara debe salir de `motion_done` / `program_state` del estado en tiempo real, no de una variable escrita al final del Lua. No verificado si existe en Lua una espera de fin de movimiento.

10b. **`motion_done` vuelve a 1 unos 0,3 s entre cada tramo `MoveL`**, aunque se pidió un blending de 10 mm. Ejecución lanzada desde el SDK el 2026-09-11: tras 5 s de espera de la cámara, el `MoveJ` de acercamiento duró 12,8 s y luego hubo 4 pausas de ~0,3 s separadas por tramos de ~1,5 s. No está verificado si el brazo se detiene físicamente o si solo cambia la señal. Si se detiene, el video tendría tirones: hay que revisar el blending (`blendRMode`, radio) antes de dar la ruta por buena.

**Estado en tiempo real y SDK v2.2.3**
10. **La pose no se actualiza durante la ejecución de la grúa.** Ni el paquete de estado (`flange_cur_pos`) ni `GetActualTCPPose()` cambiaron hasta el final, aunque en la prueba corta de 50 mm sí. No se puede medir la trayectoria intermedia sondeando, y el SDK no tiene funciones para grabar la trayectoria de un programa (TPD es para enseñanza por arrastre).
11. **Detalles del SDK v2.2.3:**
    - el atributo de conexión se llama `is_conect`;
    - `robot_state_pkg` se **reemplaza** con cada paquete, así que no hay que guardar la referencia;
    - `GetProgramState()` y `GetRobotMotionDone()` no consultan al controlador: leen el paquete, y `GetProgramState` devuelve `robot_state`.
12. **Límites blandos del FR5:** j1 ±175°, j2 −265…85°, j3 ±160°, j4 −265…85°, j5 ±175°, j6 ±175°.
13. **Marcos:** la orientación que calcula el controlador coincide con la del URDF de FAIRINO (base y brida). Así queda verificada la convención R = Rz·Ry·Rx de `routes.py`.

## Resultado de la grúa en el FR5

**Ruta probada:** objetivo (−900, 0, 350) mm. La cámara queda a 350 mm y sube de −150 a +250 mm respecto al objetivo, en 6 puntos, con un offset de cámara provisional de 100 mm.

**Primera ejecución:** usó como semilla la postura inicial (0, −90, 90, −90, −90, 0), que equivale a la `config 2`. Falló con **1/19 "LIN/ARC joint command limit exceeded"** a mitad del primer `MoveL`, con j4 = 84,99° contra su límite de 85°.

**`planner.py` sobre 51 muestras:**

| Semilla | Resultado |
|---|---|
| `config 0` | **Válida**: margen mínimo 11,2° (j2), salto máximo 3,6° |
| `config 7` | **Válida**: margen 10,3° |
| `config 2` / postura inicial | Sin solución en la muestra 5, que es donde falló el robot |
| Resto | Sin solución |

**Ejecución con `config 0`:** desde la postura inicial hasta el último punto, (−468,6; 0; 658,1; −125,5°), en 27,9 s, sin errores y con la pose final exacta.

## Fidelidad

- **En los puntos:** la orientación calculada apunta al objetivo con un error de 10⁻⁶° y el horizonte nivelado.
- **Entre puntos:** modelo de `MoveL` con posición lineal y orientación por slerp, sin blending. **No es una medición del controlador** (ver hallazgo 10).

  | Puntos | Error máximo del eje óptico | Error medio |
  |---|---|---|
  | 6 | 0,24° (unos 2 mm en el objetivo a 450 mm) | 0,11° |
  | 12 | 0,05° | — |
  | 24 | 0,011° | — |

- **Sin medir:** el efecto del blending (10 mm) y la trayectoria real del controlador. Hay que hacerlo en el robot real o con una función de registro si FAIRINO la ofrece.

## Pendientes y decisiones para registrar en Notion (CLAUDE.md §6)

- **Protocolo por variables de sistema** (IDs y estados) y señal de fin por `motion_done`/`program_state` → A1 y A2.
- **Rutas relativas al objetivo** con orientación precalculada y planificación de la semilla de IK → C4.
- **Acercamiento al primer punto:** hoy el Lua no mueve nada, tampoco el `MoveJ` de acercamiento, hasta que la cámara confirma (regla dura 2). Eso alarga la toma. Decidir si el acercamiento previo se permite.
- **FR10 en SimMachine:** pedir a FAIRINO la contraseña de modo mantenimiento (tipo 3, V01, `001(V6.0)`).
- **Offset real de la cámara** (B3): hoy son 100 mm sobre el eje Z de la brida, provisional.
- **Subir el número de puntos** (12–24) y medir el efecto del blending en el robot real.

## SDK Python: fallos a verificar en el robot real

Del rastreador oficial (`github.com/FAIR-INNOVATION/fairino-python-sdk/issues`, consultado el 2026-09-12) y de leer el SDK vendorizado. **Nada de esto está verificado**: SimMachine no sirve para probarlo, hace falta el FR10 real.

**Del código del SDK** (`experiments/fairino/Robot.py`):

- [ ] Cada función empieza con `while self.reconnect_flag: sleep(0.1)` y envuelve la llamada en un bucle que reintenta ante `socket.error` **sin tope ni tiempo límite**: puede no volver nunca. Medir qué ocurre al desconectar el cable a mitad de un `MoveL`.
- [ ] Los parámetros de reconexión son atributos de clase (`RPC._reconnect_enable`), compartidos entre instancias.
- [ ] `SetReConnectParam(enable, maxRetries, period)`: decidir si conviene reconexión silenciosa a mitad de toma o fallar claro.

**Reportado por otros usuarios y sin respuesta del fabricante:**

- [ ] `GetLuaList()` rompe las reconexiones posteriores de RPC/CNDE (2026-05-21). Nos afecta: se sube un Lua en cada toma.
- [ ] Fallos de checksum que corrompen datos del paquete de estado (2025-09-23).
- [ ] Una llamada XML-RPC puede apagar el robot (2025-09-20).
- [ ] `GetActualTCPPose()` devuelve error en algunas versiones (2025-07-18). Es la que usa `run_route.py`.
- [ ] El parámetro `block` de `MoveGripper` no tiene efecto: la semántica de bloqueo no se respeta.
- [ ] La estrategia de sobrevelocidad en movimiento lineal parece no implementada.
- [ ] No hay forma oficial de comprobar compatibilidad SDK ↔ versión de controlador. Ya nos mordió con V2.2.8 contra la 3.9.3.
- [ ] Sin soporte en macOS, arm64 ni Raspberry Pi: refuerza D12 (mini PC x86).
- Señal de fondo: casi todas las incidencias siguen abiertas y sin respuesta. Asumir cero soporte del fabricante.

**Parada por pérdida de comunicación (E2).** `SetRobotStopOnComDisc(portID, enable, confirmTime)`, con `portID` 0→8080, 1→8083, 2→20002, 3→20004 y `confirmTime` en ms [0–5000]. El puerto de comandos (20003) no es configurable; el vigilado es el 20004, el flujo de estado.

- [ ] Con el vigilante activo: cuánto tarda en detener y con qué tipo de parada (0, 1a, 1b o 2).
- [ ] Sin vigilante: confirmar que un programa Lua en marcha termina la ruta con el cable desconectado.
- [ ] Elegir `confirmTime`: tensión entre absorber un hipo de red, para que la toma termine, y responder rápido. Va a Notion como decisión.
