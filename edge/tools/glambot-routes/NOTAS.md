# NOTAS — glambot-routes

Rutas de glambot como programas Lua del controlador FAIRINO, generadas en el PC y probadas en FAIRINO SimMachine. Fecha: 2026-09-11.

> **La instancia de SimMachine en EC2 se dio de baja y `experiments/` se borró.** Este archivo conserva lo medido allí (hallazgos del Lua, del SDK y de la grúa en el FR5), que sigue valiendo para el robot real, y quita los pasos para levantar esa infraestructura. Todo lo verificado «en SimMachine» hay que reconfirmarlo en el FR10.

**Entorno de prueba (dado de baja):**
- SimMachine Docker v3.9.3 (controlador `V3.9.15-LX`, WebApp `v3.9.3`) en una instancia EC2, contenedor `fairino-container` en `192.168.58.2`.
- Descargado de fairino.support (Fairino Europe), SHA-256 `355f4c7f015b920d2a9ebf9b5e4456bbe1d1762895774d11d8976ded74238927`. El enlace de la documentación oficial (Google Drive) está retirado.
- **El robot simulado es un FR5** (`FR5-V1-002(V6.0)`). Pasarlo a FR10 exige la contraseña de modo mantenimiento, que FAIRINO no publica (pendiente con FAIRINO).
- **La WebApp solo muestra el robot en vivo si se abre sin puerto en la URL.** El estado en tiempo real (articulaciones, estado del programa, habilitación) llega por un WebSocket que la página arma como `ws://<location.host>:9999`. Entrando por `localhost:18080` queda `ws://localhost:18080:9999`, una URL inválida: la vista 3D se congela en la postura cero y parece que el robot no se mueve aunque el controlador sí lo haga. Solución: abrir el túnel por el puerto 80 local y el del WebSocket. Verificado con Chrome headless el 2026-09-11: con el WebSocket conectado, la vista 3D siguió un `MoveJ` del SDK.
- **SDK Python `v2.2.3_robot3.9.3`**, del repo oficial. El SDK que descarga `get_sdk` en `edge/vendor/fairino` (V2.2.8, para 3.9.9) lee el estado por CNDE (puerto 20005), que la 3.9.3 no tiene, y marca la conexión como caída.

## Archivos

| Archivo | Qué hace |
|---|---|
| `routes.py` | Geometría "mirar a un punto" en la convención FAIRINO (R = Rz·Ry·Rx), grúa vertical relativa al objetivo, conversión cámara → brida, interpolación de poses y generador del `.lua` |
| `planner.py` | Elige la semilla de cinemática inversa recorriendo la ruta con puntos intermedios y la IK del propio controlador, maximizando el margen a los límites |
| `run_route.py` | Ejecuta un `.lua` de ruta en el controlador emulando el lado del PC (objetivo, ID de toma, confirmación de cámara) y registra estados y poses |
| `crane_fr5.lua` | Programa generado y **ejecutado con éxito** en SimMachine (FR5) |

## Cómo reproducir

Hace falta un controlador FAIRINO alcanzable (el robot real, o un SimMachine propio) y el SDK de `edge/vendor/fairino` (`get_sdk.sh`). Desde esta carpeta:

```bash
ROUTE="--target -900 0 350 --standoff 350 --dz-start -150 --dz-end 250 --steps 6 --camera-offset 100"
python3 planner.py --ip <ip del controlador> --sdk <ruta del SDK> $ROUTE --samples 10 --max-jump 15 --extra-seed 0 -90 90 -90 -90 0
python3 routes.py $ROUTE --lua crane_fr5.lua --seed-joints <semilla del planner> --speed 20 --acc 50 --blend 10 --camera-timeout 30
python3 run_route.py --ip <ip del controlador> --sdk <ruta del SDK> --lua crane_fr5.lua $ROUTE --take-id 1 --camera-delay 1.5 --start-joints 0 -90 90 -90 -90 0
```

El SDK v2.2.3 (`v2.2.3_robot3.9.3`, del repo oficial) es el que habla bien con un controlador 3.9.3; con el robot real, usa el que corresponda a su versión.

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

   Los argumentos son **posicionales y sin nombres**, y el manual FRLua (`MoveJ` pág. 50, `MoveL` pág. 52) es la
   única fuente. Queda copiado aquí porque el manual no está en el repo y un argumento corrido mueve el brazo mal:

   ```
   MoveJ(j1, j2, j3, j4, j5, j6, x, y, z, rx, ry, rz, tool, user, speed, acc, ovl,
         ep1, ep2, ep3, ep4, blendT, offset,
         offset_x, offset_y, offset_z, offset_rx, offset_ry, offset_rz)

   MoveL(j1, j2, j3, j4, j5, j6, x, y, z, rx, ry, rz, tool, user, speed, acc, ovl, blendR, blendRMode,
         ep1, ep2, ep3, ep4, search, offset,
         offset_x, offset_y, offset_z, offset_rx, offset_ry, offset_rz, oacc, velAccParamMode)
   ```

   Son **29 argumentos para `MoveJ` y 33 para `MoveL`**: hay que pasarlos todos. Las diferencias entre las dos
   firmas son la fuente de errores: `MoveL` mete `blendR` y `blendRMode` justo después de `ovl` (donde `MoveJ`
   ya pasa a `ep1`), añade `search` antes de `offset`, y cierra con `oacc` y `velAccParamMode`. El `blendT` de
   `MoveJ` va después de `ep4`, no donde el `blendR` de `MoveL`.
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

**Del código del SDK** (`edge/vendor/fairino/Robot.py`):

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

## Hallazgos en el FR10 real (software 3.8.6)

Medidos el 2026-10-31 con `tools/robot-lab/`. Donde difieren de lo anotado arriba, vale esto.

> **Confirmación física:** solo el cuadrado de 200 mm a 10 % (`z_square.lua`) lo vio el responsable moverse con claridad. Las demás pruebas de movimiento de esta sección, hechas con poca atención o con recorridos de 6 a 10 cm, se midieron por el estado que reporta el controlador. Ese estado coincidió con lo visto en el cuadrado.

**Conexión y SDK**
- Controlador `FR10-V1-001(V6.0)`, software `v3.8.6`, firmware `V3.8.36-QX`, IP `192.168.58.2`. El Mac entra por cable con `192.168.58.100/24` en el adaptador USB-LAN.
- El SDK que corresponde es `v2.1.6_robot3.8.6` (`get_sdk` lo fija). El de 3.9.x abre el puerto de estado 20005 y llama a `GetLuaListPrepare`; el 3.8.6 no tiene ninguno de los dos y todo devuelve `-4`.
- Tras una tanda de lecturas seguidas (SDK incompatible, XML-RPC directo y sondeo de puertos) el controlador dejó de aceptar conexiones en 20003, 20004 y 8080 y el LED del extremo ciclaba colores (en el manual: comunicación no establecida). Se recuperó al reiniciar la caja. Causa sin confirmar: abrir una sola conexión por vez.

**Programas**
- Los Lua viven en `/fruser/`. `ProgramLoad` necesita la ruta completa: con solo el nombre devuelve 144.
- `LuaUpload` ejecuta el script para validarlo y devuelve el error de Lua con su línea. Un archivo que falla la validación **queda guardado** en el robot igualmente. En esa pasada la cinemática devuelve `nil`: el programa debe terminar antes de cualquier movimiento.
- La subida falla a veces con `-1` (el SDK devuelve lo mismo si no conecta al 20010, si falla el envío o si no llega `SUCCESS` en 0,5 s). Un reintento a los 2 s basta.
- `LuaDownLoad` necesita la barra final en la carpeta de destino. Un archivo que aparece en la lista pudo no descargarse (`-1`).

**Modo, ejecución y estado**
- En modo manual `ProgramRun` devuelve 0 pero el programa no corre. `Mode(0)` pasa a automático y `Mode(1)` a manual; `robot_state_pkg.robot_mode` lo confirma.
- Hay 20 variables de sistema (`s_var_1` a `s_var_20`), solo números, y conservan el valor entre ejecuciones y tras reiniciar.
- Estado en vivo en `robot_state_pkg`: `program_state`, `robot_state`, `motion_done`, `mc_queue_len`, `tl_cur_pos`, `EmergencyStop`. Se da por terminado con programa y movimiento parados y la cola vacía durante 1 s.
- Con herramienta 0 y pieza 0 activas, `GetForwardKin` del Lua coincide con la pose real del robot a menos de 0,01 mm.
- Prueba +100 mm en Z y vuelta, a 5 % (`z_relative.lua`, dos `MoveL` bloqueantes): dura unos 13,7 s (≈15,6 mm/s). La pose (`tl_cur_pos`) **sí se actualiza en vivo** durante el movimiento. `program_state` y `robot_state` pasan a 2 al arrancar y a 1 a la vez al terminar; `motion_done` vale 0 todo el tramo y no oscila entre los dos `MoveL`. `mc_queue_len` vale 0 siempre y no sirve como señal.
- La señal de fin sale del flujo de estado (TCP al puerto 20004, que el SDK deja en `robot_state_pkg`), no de una variable que escriba el Lua. `GetProgramState` y `GetRobotMotionDone` del SDK solo leen ese paquete. `frame_cnt` cuenta los paquetes y sirve para detectar que el flujo se congeló.
- Cuadrado de 60 mm en cuatro `MoveL` con blending de 10 mm a 5 % (`z_square.lua`): 14,1 s de movimiento a 15,9 mm/s de media y ningún tramo por debajo de 3 mm/s, así que **el brazo no se detiene en las esquinas**. `motion_done` sí cambia 7 veces durante el recorrido: no sirve como señal de fin (el hallazgo 10b de arriba era esa señal, no una parada física). La velocidad se calculó con `tl_cur_pos` a unos 200 Hz.
- Un error de Lua (suma con un valor `nil`) **no deja ningún código** en `main_code`/`sub_code`: el programa vuelve a `program_state = 1` en menos de 0,1 s como si hubiera terminado bien. El éxito hay que confirmarlo: variable de cierre alcanzada, el brazo se movió y la pose final es la esperada.
- **Paro de emergencia físico a mitad de una subida (botón externo por la botonera):** el estado pasa a `EmergencyStop = 1`, `main_code/sub_code = (5, 1)`, `rbtEnableState = 0` (deshabilitado, frenos puestos, pares en 0) y el programa y el movimiento quedan parados; el brazo se queda donde estaba. **No se recupera por software**: tras soltar el botón sigue `EmergencyStop = 1` con error `(6, 2)` y luego `(6, 5)`; `ResetAllError()` devuelve -1, `RobotEnable(1)` devuelve 0 pero no habilita, `Mode(1)` devuelve 14, y el botón "Clear" del panel responde `500 Error: Please release the emergency stop button first`. El panel indica "apaga y reinicia la caja de control", que fue lo que hubo que hacer. El manual habla de otras vías según el tipo de parada y la habilitación (*Initial > Safety > Emergency stop*): sin comprobar en este robot.
- **Corte del cable de red con un programa en marcha** (subida de 15 cm a 5 %, cable fuera unos 15 s, sin ninguna parada por pérdida de comunicación configurada): el brazo **siguió y terminó la ruta** solo, y al volver el cable quedó quieto en el punto de partida, sin repetir nada. El robot **no se detiene por perder la comunicación** con este firmware (3.8.6) en su configuración actual. El SDK v2.1.6 no tiene `SetRobotStopOnComDisc`. Se infiere, sin registro porque se perdió la salida del script, que las llamadas del cliente quedaron esperando hasta que volvió el cable (reintentos sin tope del SDK) y luego siguieron.
- `SetRobotStopOnComDisc` aparece en el SDK desde la v2.2.4 (robot 3.9.4) y no existe en las de 3.8.x ni en 3.9.0–3.9.3. Se decidió no actualizar el controlador. El manual 3.9.8 (sección 3.5.7) describe en la caja de control una entrada de **paro de emergencia** y una de **paro de protección** (categoría 1, reinicio automático o manual), ambas redundantes de dos canales, pensadas para dispositivos externos; no documenta ningún comando de software ni salida del controlador que dispare un paro. El cableado está solo en las figuras 3.5-10 a 3.5-12.
- Tras el paro, el controlador rechaza lecturas de variables de sistema (código 14): una lectura de estado después de un paro puede fallar y no debe romper el veredicto.
- Una sola lectura del estado dio una pose corrupta (`z = 66,0` entre dos lecturas de 949,4): los paquetes de estado pueden traer datos erróneos sueltos. Una pose no debe fiarse de una sola muestra.
- `ProgramPause` / `ProgramResume` / `ProgramStop` a mitad de un `MoveL` (a los 4 s, subiendo): los tres devuelven 0. La pausa pone `program_state` y `robot_state` en 3 y el brazo se detiene en menos de 1 mm; al reanudar sigue el trayecto y termina en el punto de partida (17,7 s con 3 s de pausa). `ProgramStop` deja el programa y el movimiento en 1 en 0,2 s y el brazo queda donde estaba, sin volver al inicio.
