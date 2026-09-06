# Demos FR10 (FAIRINO) + GoPro en Python

Dos demos minimas e independientes:

| Script | Que hace |
| ------ | -------- |
| `demo.py` | Mueve un brazo FAIRINO FR10 por RPC (sin ROS ni MoveIt) |
| `gopro_demo.py` | Conecta a una GoPro HERO10 por USB, toma una foto y la descarga |

Gestionado con [uv](https://docs.astral.sh/uv/), que tambien se encarga de
la version de Python (no hace falta conda ni pyenv).

**Python 3.13**, no 3.14: el SDK de GoPro declara `>=3.11,<3.14`. El SDK del
FR10 es Python puro y funciona en todo ese rango, asi que el limite lo pone
la camara. `uv` descarga y aisla esa version solo, con `uv sync`.

## Puesta en marcha

**macOS / Linux (bash):**

```bash
uv sync
./scripts/get_sdk.sh
```

**Windows (PowerShell):**

```powershell
uv sync
.\scripts\get_sdk.ps1
```

Si PowerShell bloquea el script por la politica de ejecucion, corre en su
lugar:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\get_sdk.ps1
```

`uv sync` instala el SDK de la GoPro y fija Python 3.13. El script del
segundo paso trae el SDK del FR10, que **no** es instalable con uv (ver mas
abajo) y no esta versionado; los dos scripts hacen lo mismo, elige el de tu
plataforma.

Si solo te interesa la demo de la GoPro, con `uv sync` basta.

## Demo del FR10: configurar antes de correr

Abre `demo.py` y edita dos cosas:

1. `ROBOT_IP` — la IP del controlador (de fabrica: `192.168.58.2`).
2. `POSTURA_A` y `POSTURA_B` — vienen en `None` a proposito. Son 6 angulos
   en grados `[J1..J6]`. Consiguelos moviendo el robot con el pendant y
   leyendo los valores, o corriendo:

   ```bash
   uv run demo.py --leer
   ```

   que se conecta, imprime la postura actual y no mueve nada.

## Demo del FR10: correr

```bash
uv run demo.py
```

Hace: conectar -> modo automatico + habilitar -> `MoveJ` a A -> a B -> de
vuelta a A -> cerrar. Imprime cada paso en consola.

No hace falta activar el venv a mano: `uv run` lo hace solo.

## Demo de la GoPro

```bash
uv run gopro_demo.py --leer   # solo conecta e informa, NO dispara
uv run gopro_demo.py          # conecta, toma una foto y la descarga
```

Conecta por **cable USB**. La camara se descubre sola por mDNS, no hace
falta que le digas el serial ni la IP.

Requisitos en la camara:

- Encendida (no basta con que este enchufada).
- Cable USB-C **de datos**, no solo de carga.
- `Preferencias > Conexiones > Conexion USB` en **GoPro Connect** (si esta
  en MTP/almacenamiento, la API no responde).

Las fotos se guardan en `capturas/` con un prefijo de fecha y hora
(`20260906-143022_GOPR0001.JPG`). Esa carpeta esta en `.gitignore` y la crea
el script solo.

A diferencia del SDK del FR10, este si esta en PyPI y lo instala `uv sync`.
El codigo es **async**, porque asi es la API del SDK oficial.

## Por que el SDK del FR10 no se instala con uv

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
`demo.py`. Eso hacen los scripts de `scripts/`, que clonan el repo, detectan
tu sistema y copian lo que corresponde:

| Plataforma      | Script                  |
| --------------- | ----------------------- |
| macOS / Linux   | `scripts/get_sdk.sh`    |
| Windows         | `scripts/get_sdk.ps1`   |

Por eso `fairino/` esta en `.gitignore`: es codigo de terceros que se repone
con el script, no se versiona.

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
