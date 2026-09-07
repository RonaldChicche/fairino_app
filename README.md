# FAIRINO FR10: conexion y lectura segura

Proyecto Python para conectar por RPC con un FAIRINO FR10 y leer su estado.
Durante esta fase, `demo.py` no contiene llamadas de movimiento, habilitacion
de servos ni cambio de modo.

`uv` administra una instalacion aislada de Python 3.13; no hace falta instalar
Python del sistema, Conda ni activar el entorno virtual manualmente.

## Preparar Windows

```powershell
uv sync
powershell -ExecutionPolicy Bypass -File .\scripts\get_sdk.ps1
```

El SDK de FAIRINO no esta publicado como paquete instalable. El segundo comando
descarga solamente `windows/fairino/Robot.py` desde la revision oficial
`v2.2.4_robot_v3.9.4` y lo guarda en `fairino/`. Esa revision usa el puerto de
estado legado `20004` que expone este controlador; las revisiones nuevas exigen
CNDE en `20005`.

## Conectar y leer el robot

1. Verifica `ROBOT_IP` en `demo.py` (la IP de fabrica es `192.168.58.2`).
2. Conecta la PC a la red del controlador y comprueba `ping 192.168.58.2`.
3. Ejecuta:

```powershell
uv run demo.py --leer
```

El script lee:

- posiciones de las seis articulaciones;
- pose TCP;
- codigos de error;
- paro de emergencia y paradas de seguridad;
- estado de comunicacion del SDK.

Después cierra la conexion. Cualquier argumento distinto de `--leer` se rechaza.

## Barrera de seguridad

No se implementaran ni ejecutaran movimientos hasta recibir confirmacion
explicita. Incluso entonces, el operador humano sera quien ejecute cualquier
accion fisica; Codex no ejecutara comandos de movimiento.

## GoPro (independiente y no prioritaria)

La utilidad `gopro_demo.py` usa `open-gopro`, que en Windows descarga varias
dependencias WinRT. Para que eso no bloquee el entorno del robot, se ejecuta de
forma separada:

```powershell
uv run --with open-gopro gopro_demo.py --leer
```

No es necesario para conectar al FR10.

## Documentacion y compatibilidad

- Manual oficial FAIRINO SDK: https://fairino-doc-en.readthedocs.io/latest/SDKManual/index.html
- uv y Python administrado: https://docs.astral.sh/uv/guides/install-python/

La documentacion `latest` corresponde actualmente al controlador 3.9.9. Para
este equipo usamos el SDK oficial `v2.2.4_robot_v3.9.4`, porque el controlador
expone el estado por `20004` y no el protocolo CNDE nuevo en `20005`. Antes de
incorporar una API del manual actual se debe contrastar con `fairino/Robot.py`.
