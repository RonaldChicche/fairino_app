# robot-app

Sistema tipo *glambot* para eventos: un brazo FAIRINO FR10 ejecuta una ruta mientras una GoPro HERO10 graba, un nodo edge local renderiza el video con la plantilla del evento y el invitado lo recibe por correo con un enlace a una web en Vercel. Si eres un agente, lee primero [CLAUDE.md](CLAUDE.md); cada proyecto tiene además el suyo: [edge/CLAUDE.md](edge/CLAUDE.md) y [web/CLAUDE.md](web/CLAUDE.md).

> **Estado: en diseño.** Solo está cerrado lo que Notion marca como "Decidido". Siguen abiertos la máquina de estados de la toma (A1), el catálogo de rutas (C4) y el formato de plantilla (C5). Todavía no hay código de producción.

**Fuente de verdad:** [Robot App en Notion](https://app.notion.com/p/Robot-App-3d7ac27a4ba480f19cd9cde2427ea213). Las decisiones viven allí y este repo no las copia: por eso no existe `decisions.md`.

**Vista de lo acordado:** [`docs/artifacts/arquitectura-glambot/`](docs/artifacts/arquitectura-glambot/README.md). Un canvas con la arquitectura, la entrega de videos, las pantallas de la app y el modelo de datos.

Este es el único README del repo, a propósito. Cuando una carpeta gane contenido, actualiza la tabla de abajo en lugar de crear otro README.

## Estructura

| Carpeta | Responsable de | No le corresponde |
|---|---|---|
| `edge/` | Servicio Python junto al robot: mini PC x86 (D12), laptop mientras tanto (D4). Todo el camino crítico del evento | Nada que necesite internet para completar una toma |
| `edge/src/edge/robot/` | Cliente del SDK FAIRINO: conexión, lectura de estado e invocación de primitivas Lua con parámetros (D2) | Generar trayectorias o validar límites (lo hace el controlador), decidir cuándo se mueve, seguridad física (D10) |
| `edge/src/edge/camera/` | Cliente Open GoPro por USB: configuración de captura, grabar, confirmar que graba, listar y descargar | Decidir cuándo grabar, procesar video, alimentación de la cámara |
| `edge/src/edge/session/` | Máquina de estados de una toma: una a la vez, con candado e idempotencia (D16). Coordina cámara, robot y render, incluidos los fallos a mitad de camino | Hablar directamente con el SDK o la cámara, HTTP, subidas |
| `edge/src/edge/render/` | ffmpeg: del crudo al único archivo final según la plantilla, con la música base (D17, D19, D20) | Definir la plantilla, descargar el crudo, subir el resultado |
| `edge/src/edge/server/` | HTTP local en el wifi propio del edge (D15): interfaz del operador y Studio de rutas en HTML plano (D32), QR, página local de respaldo (D21, D33), PWA. Funciona sin internet | Lógica de la toma, página del invitado en la nube |
| `edge/src/edge/uploader/` | Cola de subida con reintentos y persistencia entre reinicios (C3), por el router 4G/5G separado (D24) | Condicionar el camino crítico, subir el crudo (D17), registrar el correo del invitado en logs |
| `edge/tests/` | Pruebas automatizadas de `edge` | Pruebas de la web, exploración con el robot o la cámara reales |
| `edge/tools/` | Herramientas de planificación offline `glambot-routes/` (cinemática, planificador, generador del Lua, simulador de tomas y rutas de ejemplo) y `fr10-model/` (URDF y mallas del FR10), más `camera-probe/` (mide la GoPro) y `get_sdk.sh`/`.ps1` (descargan el SDK de FAIRINO en `edge/vendor/fairino/`) | Código que corra en el camino crítico de una toma (D2) |
| `edge/vendor/`, `edge/data/` | SDK de FAIRINO descargado y datos locales (cola, tomas). Git las ignora | Código propio |
| `web/` | Astro en Vercel (D27), `glam.datzoncompany.com`: página del invitado, panel de administración, API de sesiones, envío de correos y limpieza diaria, sobre Supabase (D28) | Camino crítico del evento, interfaz del operador |
| `docs/` | Diagramas Mermaid (`.mmd`) para lo decidido y artifacts de diseño versionados en `docs/artifacts/` (D29) | Decisiones (viven en Notion) |

Las carpetas vacías llevan `.gitkeep` solo para que git las conserve.

## Diagramas (`docs/`)

| Archivo | Estado | Contenido | Referencia en Notion |
|---|---|---|---|
| `artifacts/arquitectura-glambot/` | Creado | Canvas con cuatro páginas: arquitectura, entrega de videos, pantallas de la app y datos. Fuentes de los tableros y los scripts que los generan | D1–D34 |
| `architecture.excalidraw` | Superado | Vista anterior de la arquitectura. La reemplaza el artifact (D29); se borra | D1–D25 |
| `session-state-machine.mmd` | Creado | Secuencia y estados de una toma, incluidos los fallos a mitad de camino | A1, D37 |
| `event-network.mmd` | Planificado | Red del evento: wifi del edge, tablet del operador, celular del invitado, router 4G/5G | D15, D24, E1 |
| `upload-and-delivery.mmd` | Planificado | Cola de subida, envío del correo y cambio entre modo nube y modo local | C3, D21, G3 |
