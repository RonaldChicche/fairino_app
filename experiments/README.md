# experiments

Exploración anterior a la estructura del monorepo, conservada sin cambios de contenido. Es referencia, no base: nada de `apps/` ni `packages/` importa desde aquí. Se mantuvo la estructura relativa original (`scripts/` escribe en `../fairino`, las demos importan `fairino` desde su misma carpeta).

- `demo.py`: demo de control del FR10 con el SDK oficial de FAIRINO por XML-RPC. `--leer` imprime la postura; sin argumentos hace MoveJ A → B → A. Creado 2026-09-05, último cambio 2026-09-06.
- `gopro_demo.py`: demo de la GoPro HERO10 por USB con el SDK Open GoPro. `--leer` muestra modelo, firmware y batería; sin argumentos toma una foto y la descarga a `capturas/`. Creado 2026-09-06.
- `README_demos.md`: el `README.md` que estaba en la raíz, renombrado sin tocar su contenido para no chocar con este archivo. Explica cómo correr ambas demos y por qué el SDK de FAIRINO se vendoriza. 2026-09-05, último cambio 2026-09-06.
- `pyproject.toml`: proyecto uv `fr10-demo` de las demos (Python >=3.11,<3.14, dependencia `open-gopro`). 2026-09-05, último cambio 2026-09-06.
- `uv.lock`: lockfile de uv correspondiente a `pyproject.toml`. 2026-09-05, último cambio 2026-09-06.
- `.python-version`: fija Python 3.13 para uv. 2026-09-06.
- `scripts/get_sdk.sh`: clona el SDK de FAIRINO y copia `Robot.py` y `README.txt` en `fairino/` (macOS/Linux). 2026-09-05, último cambio 2026-09-06.
- `scripts/get_sdk.ps1`: equivalente de `get_sdk.sh` para PowerShell en Windows. 2026-09-05, último cambio 2026-09-06.
- `fairino/` (no versionado, en `.gitignore`): SDK de FAIRINO copiado por `get_sdk` (`Robot.py`, `README.txt` con el historial de versiones del SDK). Descargado 2026-09-06.
- `__pycache__/` (no versionado, en `.gitignore`): bytecode generado al ejecutar `demo.py` y `gopro_demo.py`. 2026-09-06.
