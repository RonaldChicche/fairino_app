# edge

Servicio Python que corre junto al robot. Orquesta cada toma sin depender de internet: pide la ruta al robot, graba con la GoPro, renderiza y sube los resultados después. Las reglas duras de la raíz (`../CLAUDE.md`) mandan sobre este archivo.

**Foco:** seguridad física, camino crítico local y resiliencia. Aquí un error mueve un brazo industrial.

## Independencia (D36)

- No importa nada de `web/`. Habla con la web solo por HTTPS y por el contrato de datos.
- Dependencias, entorno y secretos propios: `pyproject.toml`, `uv.lock` y `.env`.
- Este archivo debe poder leerse sin el de la raíz, por si algún día `edge/` se separa a su propio repositorio.

## Estructura (D35)

- Diseño con *src layout*: el código vive en `src/edge/`.
- `session/` es el núcleo: la máquina de estados, el candado y los puertos que necesita (robot, cámara, render, subida).
- `robot/` y `camera/` son adaptadores de esos puertos, cada uno con su versión falsa. `session/` no importa de ellos.
- `app.py` conecta los adaptadores con el núcleo. Es el único lugar que conoce a todos.
- Todo lo que dependa de internet pasa por `uploader/`. El camino de la toma nunca espera a la nube.

## Pruebas

Herramienta: `pytest`, con `uv run pytest`.

**Se prueba**
- Las reglas duras: una sola toma a la vez, un reintento que no mueve el brazo dos veces, el robot que espera la confirmación de la cámara y el correo del invitado fuera de los logs.
- Las transiciones de la máquina de estados, en una sola prueba parametrizada.
- La cola de subida: reintentos, idempotencia y tope de intentos.
- Funciones puras con cálculo: cinemática y armado del comando de ffmpeg.

**No se prueba**
- El SDK de FAIRINO ni Open GoPro.
- Los adaptadores reales: se miden a mano con `tools/camera-probe` y con el robot, con el responsable presente.
- HTML, configuración y código de pegamento.

**Reglas**
- Un cambio pequeño agrega como máximo una prueba, y solo si cambia un comportamiento de la lista. Un bug corregido deja una sola prueba, la que lo habría detectado.
- Se parametriza en vez de repetir. Los falsos viven junto a su adaptador.
- Las líneas de pruebas no superan las del código de producción.
- Las pruebas automáticas nunca hablan con el robot ni con la cámara reales.
- Antes de agregar pruebas, di cuántas y por qué.
