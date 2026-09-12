# robot-app

Sistema tipo *glambot* para eventos: un brazo FAIRINO FR10 ejecuta una ruta mientras una GoPro HERO10 graba, un nodo edge local renderiza el video con la plantilla del cliente y una web en Vercel lo entrega por QR. Si eres un agente, lee primero [CLAUDE.md](CLAUDE.md).

> **Estado: en diseño.** Solo está cerrado lo que Notion marca como "Decidido". Siguen abiertos la máquina de estados de la toma, el concepto de sesión, el catálogo de rutas, el formato de plantilla y la propia estructura de este repositorio (C2). Todavía no hay código de producción.

**Fuente de verdad:** [Robot App en Notion](https://app.notion.com/p/Robot-App-3d7ac27a4ba480f19cd9cde2427ea213). Las decisiones viven allí y este repo no las copia: por eso no existe `decisions.md`.

**Vista de lo acordado:** [`docs/architecture.excalidraw`](docs/architecture.excalidraw). Se abre en [excalidraw.com](https://excalidraw.com) (menú › Abrir) o con la extensión de Excalidraw para VS Code.

Este es el único README del repo, a propósito. Cuando una carpeta gane contenido, actualiza la tabla de abajo en lugar de crear otro README.

## Estructura

| Carpeta | Responsable de | No le corresponde |
|---|---|---|
| `apps/edge/` | Servicio Python junto al robot: mini PC x86 (D12), laptop mientras tanto (D4). Todo el camino crítico del evento | Nada que necesite internet para completar una toma |
| `apps/edge/src/edge/robot/` | Cliente del SDK FAIRINO: conexión, lectura de estado e invocación de primitivas Lua con parámetros (D2) | Generar trayectorias o validar límites (lo hace el controlador), decidir cuándo se mueve, seguridad física (D10) |
| `apps/edge/src/edge/camera/` | Cliente Open GoPro por USB: configuración de captura, grabar, confirmar que graba, listar y descargar | Decidir cuándo grabar, procesar video, alimentación de la cámara |
| `apps/edge/src/edge/session/` | Máquina de estados de una toma: una a la vez, con candado e idempotencia (D16). Coordina cámara, robot y render, incluidos los fallos a mitad de camino | Hablar directamente con el SDK o la cámara, HTTP, subidas |
| `apps/edge/src/edge/render/` | ffmpeg: del crudo al único archivo final según la plantilla (D17, D19, D20) | Definir la plantilla, descargar el crudo, subir el resultado |
| `apps/edge/src/edge/server/` | HTTP local en el wifi propio del edge (D15): interfaz del operador en HTML plano, QR, página local de respaldo (D21), PWA. Funciona sin internet | Lógica de la toma, página del invitado en la nube |
| `apps/edge/src/edge/uploader/` | Cola de subida con reintentos y persistencia entre reinicios (C3), por el router 4G/5G separado (D24) | Condicionar el camino crítico, subir el crudo (D17), guardar datos de contacto |
| `apps/edge/tests/` | Pruebas automatizadas de `apps/edge` | Pruebas de la web, exploración con el robot o la cámara reales (va en `experiments/`) |
| `apps/web/app/` | Monolito Next.js en Vercel (D13), `glam.datzoncompany.com`: página del invitado, galería del cliente, panel de plantillas, API de sesiones. Polling, sin realtime (D14) | Camino crítico del evento, interfaz del operador |
| `packages/contracts/` | Esquemas compartidos por edge y web: sesión, catálogo de rutas, plantilla y estados, definidos una sola vez. Pendientes en Notion: C1, C4, C5 | Lógica de negocio, acceso a datos, código de una sola app |
| `packages/design-tokens/` | Colores, tipografía y espaciado para la interfaz del operador y la web | Componentes, estilos de una pantalla, marca del cliente (va en la plantilla) |
| `infra/` | Aprovisionamiento y despliegue del edge: contenedor, arranque, punto de acceso wifi propio (D15, E1) | Código de aplicación, configuración de Vercel de `apps/web` |
| `docs/` | Diagramas: Mermaid (`.mmd`) para lo decidido, Excalidraw para bocetos (D11) | Decisiones (viven en Notion) |
| `experiments/` | Exploración anterior al monorepo, conservada sin cambios | Código de producción; nada de `apps/` ni `packages/` importa desde aquí |

Las carpetas vacías llevan `.gitkeep` solo para que git las conserve.

## Diagramas (`docs/`)

| Archivo | Estado | Contenido | Referencia en Notion |
|---|---|---|---|
| `architecture.excalidraw` | Creado | Vista general de lo acordado: zonas, dispositivos, capas, flujo de una toma, decisiones vigentes y superadas, pendientes, y notas N1–N19 sobre huecos y contradicciones | Secciones 1 a 6, D1–D25 |
| `session-state-machine.mmd` | Planificado | Secuencia y estados de una toma, incluidos los fallos a mitad de camino | A1 |
| `event-network.mmd` | Planificado | Red del evento: wifi del edge, tablet del operador, celular del invitado, router 4G/5G | D15, D24, E1 |
| `upload-and-delivery.mmd` | Planificado | Cola de subida y cambio entre modo nube y modo local del QR | C3, D21, G3 |

Los nombres de los archivos planificados son propuestas. Cuando la arquitectura se estabilice, lo acordado del `.excalidraw` pasa a Mermaid (D11).

## Contenido de `experiments/`

- `fr10-sim/`: simulación del FR10 en EC2 (ROS 2 Humble, MoveIt2 y Gazebo Sim) y el comando `fr10` para levantarla desde el Mac y abrir la WebApp de FAIRINO SimMachine (`fr10 webapp`). Detalle en `fr10-sim/SETUP.md` y `fr10-sim/NOTAS.md`. 2026-09-10 a 2026-09-11.
- `glambot-routes/`: rutas de glambot como programas Lua del controlador FAIRINO, con la cámara siempre mirando al objetivo. Incluye el generador del `.lua`, el planificador de semilla de cinemática inversa y las pruebas en FAIRINO SimMachine (Docker v3.9.3, robot FR5). Hallazgos y cómo reproducir, en `glambot-routes/NOTAS.md`. 2026-09-11.
- `env/` (en `.gitignore` salvo `.env.example`): variables de entorno de los experimentos. Los valores reales van en `env/.env`; la documentación usa placeholders.

Demos del SDK, en la raíz de `experiments/`. Se conservó su estructura relativa original: `scripts/` escribe en `../fairino` y las demos importan `fairino` desde su misma carpeta.

- `demo.py`: demo de control del FR10 con el SDK oficial de FAIRINO por XML-RPC. `--leer` imprime la postura; sin argumentos hace MoveJ A → B → A. Creado 2026-09-05, último cambio 2026-09-06.
- `gopro_demo.py`: demo de la GoPro HERO10 por USB con el SDK Open GoPro. `--leer` muestra modelo, firmware y batería; sin argumentos toma una foto y la descarga a `capturas/`. Creado 2026-09-06.
- `README_demos.md`: el README que estaba en la raíz, renombrado sin tocar su contenido. Explica cómo correr ambas demos y por qué el SDK de FAIRINO se vendoriza. 2026-09-05, último cambio 2026-09-06.
- `pyproject.toml`: proyecto uv `fr10-demo` de las demos (Python >=3.11,<3.14, dependencia `open-gopro`). 2026-09-05, último cambio 2026-09-06.
- `uv.lock`: lockfile de uv de `pyproject.toml`. 2026-09-05, último cambio 2026-09-06.
- `.python-version`: fija Python 3.13 para uv. 2026-09-06.
- `scripts/get_sdk.sh`: clona el SDK de FAIRINO y copia `Robot.py` y `README.txt` en `fairino/` (macOS/Linux). 2026-09-05, último cambio 2026-09-06.
- `scripts/get_sdk.ps1`: equivalente para PowerShell en Windows. 2026-09-05, último cambio 2026-09-06.
- `fairino/` (no versionado, en `.gitignore`): SDK de FAIRINO copiado por `get_sdk`. Descargado 2026-09-06.
- `__pycache__/` (no versionado, en `.gitignore`): bytecode generado al ejecutar las demos. 2026-09-06.
