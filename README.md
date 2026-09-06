# Demo FR10 (FAIRINO) en Python

Demo minima para mover un brazo FAIRINO FR10 con el SDK oficial via RPC.
Sin ROS, sin MoveIt, sin frameworks pesados: solo libreria estandar + el SDK.

Gestionado con [uv](https://docs.astral.sh/uv/).

## Puesta en marcha

```bash
uv sync              # crea .venv y resuelve el proyecto
./scripts/get_sdk.sh # descarga el SDK oficial en ./fairino
```

El segundo paso es obligatorio: `fairino/` no esta versionado (ver abajo).

## Configurar antes de correr

Abre `demo.py` y edita dos cosas:

1. `ROBOT_IP` — la IP del controlador (de fabrica: `192.168.58.2`).
2. `POSTURA_A` y `POSTURA_B` — vienen en `None` a proposito. Son 6 angulos
   en grados `[J1..J6]`. Consiguelos moviendo el robot con el pendant y
   leyendo los valores, o corriendo:

   ```bash
   uv run demo.py --leer
   ```

   que se conecta, imprime la postura actual y no mueve nada.

## Correr la demo

```bash
uv run demo.py
```

Hace: conectar -> modo automatico + habilitar -> `MoveJ` a A -> a B -> de
vuelta a A -> cerrar. Imprime cada paso en consola.

No hace falta activar el venv a mano: `uv run` lo hace solo.

## Por que el SDK no se instala con uv

El SDK de FAIRINO **no es instalable** con `uv add` ni `pip install`. Dos
razones, ambas comprobadas:

```
$ uv add fairino
  x No solution found: fairino was not found in the package registry

$ uv add git+https://github.com/FAIR-INNOVATION/fairino-python-sdk
  error: ... does not appear to be a Python project, as neither
  `pyproject.toml` nor `setup.py` are present in the directory
```

No esta publicado en PyPI, y el repo de GitHub no trae metadatos de
empaquetado en la raiz — solo carpetas `linux/` y `windows/` con el codigo
suelto. (Hay un `setup.py` dentro de `fairino/`, pero es un script de
compilacion Cython para generar el `.so`, no declara un paquete instalable.)

La via oficial es **vendorizarlo**: copiar la carpeta `fairino` al lado de
`demo.py`. Eso hace `./scripts/get_sdk.sh`, que clona el repo, detecta tu
sistema y copia lo que corresponde. Por eso `fairino/` esta en `.gitignore`:
es codigo de terceros que se repone con el script, no se versiona.

### Nota para macOS

El repo solo trae `linux/` y `windows/`, pero `fairino/Robot.py` es identico
en las dos (mismo md5) y es Python puro —usa `xmlrpc` y `socket`, no carga
ningun `.so` ni `.dll`—, asi que la version de `linux/` corre sin problema en
macOS. Las carpetas `libfairino/` del repo si son binarios por plataforma,
pero esta demo no las necesita. El script copia solo `Robot.py` y
`README.txt`, omitiendo `__pycache__/` y `build/` (~150 MB de binarios de
otras plataformas).

## Notas

- `TOOL = 0` y `USER = 0` significan "sin herramienta ni sistema de pieza
  calibrados". Correcto para una demo; en produccion se calibran.
- `VELOCIDAD = 20` (%) esta bajo a proposito. Subelo con cuidado.
- `MoveJ` es movimiento en espacio de articulaciones: el efector final NO
  sigue una linea recta. Ten el area despejada y el paro de emergencia a mano.
- El SDK imprime su propio log (parte en chino) antes de los mensajes de
  esta demo. Es normal, no es un error del script.
- El SDK reintenta en bucle ante errores de socket, asi que si el robot se
  desconecta a media ejecucion el script puede quedarse colgado en vez de
  fallar. Ctrl+C para salir.

## Documentacion

https://fair-documentation.readthedocs.io/en/latest/SDKManual/python_intro.html
