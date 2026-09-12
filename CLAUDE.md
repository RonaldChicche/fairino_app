# CLAUDE.md

Guía para cualquier agente que trabaje en este repositorio (`robot-app`, remoto `RonaldChicche/fairino_app`).

## 1. Qué es

Un sistema tipo *glambot* para eventos: el invitado pide su toma, un brazo robótico industrial FAIRINO FR10 ejecuta una ruta mientras una GoPro HERO10 graba, y el video sale renderizado con la plantilla del cliente y disponible por QR en menos de un minuto. Un nodo *edge* junto al robot orquesta la toma y renderiza sin depender de internet, y una web en Vercel entrega el video y la galería. Es un sistema comercial que opera en eventos reales con público presente: un error puede significar un brazo industrial moviéndose cuando no debe cerca de personas, o una fila de invitados detenida frente al cliente.

**Estado: en diseño.** Solo está cerrado lo que Notion marca como "Decidido". El resto, incluida esta estructura de carpetas (C2), puede cambiar. No rellenes huecos de diseño por tu cuenta: si una tarea depende de algo pendiente en Notion, pregunta.

## 2. Fuente de verdad

Las decisiones del proyecto viven en Notion, no en este repositorio:

**[Robot App — Engineer Stack / My Roadmap](https://app.notion.com/p/Robot-App-3d7ac27a4ba480f19cd9cde2427ea213)**

- Léela completa antes de tomar cualquier decisión de arquitectura: tecnología, capa donde vive algo, contratos entre edge y web, red, seguridad o datos.
- Cita las decisiones por su ID (`D16`, `C3`…) en código, commits y documentación. No copies su contenido al repo: por eso no existe `docs/decisions.md`.
- Si el repo contradice a Notion, gana Notion. No lo "arregles" en silencio: señala la contradicción.
- Lo que está en "Decisiones superadas" ya se descartó y se conserva el porqué. No lo reintroduzcas sin pasar por la sección 6.

## 3. Mapa del repositorio

| Carpeta | Qué vive aquí | Qué NO vive aquí |
|---|---|---|
| `apps/edge/` | Servicio Python en el mini PC junto al robot (laptop mientras tanto, D4 y D12). Todo el camino crítico del evento | Nada que necesite internet para completar una toma |
| `apps/edge/src/edge/robot/` | Cliente del SDK FAIRINO: invocar primitivas Lua con parámetros y leer el estado del robot | Trayectorias propias, validación de límites, seguridad física |
| `apps/edge/src/edge/camera/` | Cliente Open GoPro por USB: grabar, confirmar que graba, listar y descargar | Decidir cuándo grabar, procesar video |
| `apps/edge/src/edge/session/` | Máquina de estados de una toma, con candado e idempotencia | Llamadas directas al SDK o a la cámara, HTTP, subidas |
| `apps/edge/src/edge/render/` | Wrapper de ffmpeg por plantilla: un archivo final por toma | Definir el formato de plantilla, subir el resultado |
| `apps/edge/src/edge/server/` | HTTP local: interfaz del operador en HTML plano, QR, página local de respaldo, PWA | Lógica de la toma, la web de la nube |
| `apps/edge/src/edge/uploader/` | Cola de subida con reintentos, persistente entre reinicios | Bloquear o condicionar el camino crítico |
| `apps/edge/tests/` | Pruebas de `apps/edge` | Pruebas de la web, scripts de exploración |
| `apps/web/` | Monolito Next.js en Vercel (D13) en `glam.datzoncompany.com`: página del invitado, galería del cliente, panel de plantillas, API de sesiones | Camino crítico del evento, interfaz del operador, realtime (D14) |
| `packages/contracts/` | Esquemas compartidos: sesión, catálogo de rutas, plantilla y estados | Lógica de negocio, código propio de una sola app |
| `packages/design-tokens/` | Colores, tipografía y espaciado para la interfaz del operador y la web | Componentes, marca del cliente del evento |
| `infra/` | Aprovisionamiento y despliegue del edge | Código de aplicación |
| `docs/` | Diagramas Mermaid de lo decidido y bocetos Excalidraw (D11). `architecture.excalidraw` es la vista general de lo acordado | Decisiones (viven en Notion) |
| `experiments/` | Demos y pruebas de exploración anteriores, conservadas tal cual | Código de producción; nada de `apps/` ni `packages/` importa desde aquí |

Hoy el repositorio solo tiene estructura y documentación: todavía no hay código de producción. El detalle de cada carpeta está en `README.md`, el único README del repo, a propósito: cuando una carpeta gane contenido, actualiza esa tabla en lugar de crear un README nuevo. Mantén este mapa y esa tabla en sincronía.

## 4. Reglas duras

No son negociables. Si una tarea exige romper alguna, detente y plantéalo (sección 6).

1. **Una sola toma a la vez, y ningún reintento mueve el brazo dos veces.** Ningún cambio en `apps/edge` puede permitir dos tomas simultáneas, ni que un reintento de red (del operador, del navegador, de un cliente HTTP o de la cola) dispare un movimiento duplicado. Toda orden que termine en movimiento lleva el ID de la toma, pasa por un único candado y es idempotente: un ID ya aceptado no vuelve a mover el robot.
   *Motivo:* hay un brazo robótico industrial con personas cerca. Es seguridad física, no elegancia. (D16)

2. **El robot no se mueve hasta que la cámara confirma que está grabando.** La confirmación es el estado de grabación que reporta la GoPro, no un tiempo de espera supuesto. Si la confirmación no llega, la toma no arranca.
   *Motivo:* la cuenta regresiva existe para absorber el arranque de la cámara (D18). Si el brazo se mueve antes, se pierde una toma irrepetible con el invitado posando. (D18; A3 y A4 en Notion)

3. **El camino crítico funciona sin internet.** Operador pide ruta → robot ejecuta → cámara graba → se renderiza: nada de ese camino puede depender de un servicio en la nube, ni para completarse ni esperando una respuesta. La nube recibe los resultados después, a través de la cola de subida.
   *Motivo:* la zona del evento tiene que funcionar con el cable de red desconectado, y la red del salón no es confiable el día que importa. (Sección 2 de Notion; D14, D15, D17, D24)

4. **Los datos de contacto del invitado son entrada transitoria.** Se usan para enviar y se descartan. No se persisten en base de datos, logs, trazas de error ni analítica. El registro de un envío guarda solo `session_id`, canal, timestamp y estado.
   *Motivo:* son datos personales de invitados de terceros que el negocio no necesita conservar; lo que no se guarda no se puede filtrar. (Indicada por el responsable del proyecto; aún no registrada como decisión en Notion.)

5. **Los IDs públicos de video son aleatorios, nunca correlativos.** Nada que aparezca en una URL, un QR o una respuesta pública puede ser un contador ni derivarse de uno.
   *Motivo:* el QR apunta a una página pública (D21). Con IDs correlativos, cualquiera podría recorrer los videos de otros invitados cambiando un número. (Indicada por el responsable del proyecto; aún no registrada como decisión en Notion.)

6. **La interfaz del operador es HTML plano servido por el edge.** Ni app nativa ni un segundo proyecto Next.js.
   *Motivo:* la tablet del operador se conecta al wifi del propio edge y tiene que operar sin internet (D15, sección 2). La única app Next.js es el monolito de la nube (D13); otra cadena de build en el edge es complejidad sin beneficio. (Derivada de D13 y D15; la forma "HTML plano" la indicó el responsable del proyecto.)

7. **El software no es la seguridad.** No escribas código que asuma ser la protección de las personas, ni desactives o esquives la parada del controlador por pérdida de comunicación.
   *Motivo:* la seguridad la dan el paro de emergencia cableado y la parada automática del controlador; el watchdog del SDK no es seguridad certificada. (D10; E2 en Notion)

8. **El edge elige primitivas, no genera movimiento.** `apps/edge` solo selecciona una primitiva Lua ya cargada en el controlador y sus parámetros; no envía trayectorias ni poses propias.
   *Motivo:* el robot valida sus propios límites antes de moverse. (D2)

## 5. Convenciones

- Documentación y comentarios en español. Nombres de código (módulos, funciones, variables, tipos, endpoints) en inglés.
- Los esquemas se definen **una sola vez** en `packages/contracts`. `apps/edge` y `apps/web` los consumen; no los redefinen ni los copian.
- Lo ya decidido se diagrama en Mermaid dentro de `docs/`; los bocetos van en Excalidraw (D11).
- El código de `experiments/` es referencia, no base: se reescribe en `apps/`, no se importa.

## 6. Cómo proponer un cambio de arquitectura

1. Se discute y se registra primero en Notion: la decisión con un ID nuevo y su "Por qué". Si reemplaza a otra, la anterior pasa a "Decisiones superadas"; nada se borra.
2. Solo después se toca el repositorio, citando el ID de la decisión en el commit.
3. Un agente que detecte que su tarea requiere cambiar una decisión, o que Notion no la cubre, se detiene y lo plantea en lugar de decidirlo por su cuenta en el código.
