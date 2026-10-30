# CLAUDE.md

Guía para cualquier agente que trabaje en este repositorio (`robot-app`, remoto `RonaldChicche/fairino_app`).

## 1. Qué es

Un sistema tipo *glambot* para eventos: el invitado pide su toma, un brazo robótico industrial FAIRINO FR10 ejecuta una ruta mientras una GoPro HERO10 graba, y el video sale renderizado con la plantilla del evento; el invitado lo recibe por correo y, si hay tiempo, por QR. Un nodo *edge* junto al robot orquesta la toma y renderiza sin depender de internet, y una web en Vercel entrega el video. Es un sistema comercial que opera en eventos reales con público presente: un error puede significar un brazo industrial moviéndose cuando no debe cerca de personas, o una fila de invitados detenida frente al cliente.

**Estado: en diseño.** Solo está cerrado lo que Notion marca como "Decidido". El resto puede cambiar. No rellenes huecos de diseño por tu cuenta: si una tarea depende de algo pendiente en Notion, pregunta.

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
| `edge/` | Servicio Python en el mini PC junto al robot (laptop mientras tanto, D4 y D12). Todo el camino crítico del evento | Nada que necesite internet para completar una toma |
| `edge/src/edge/robot/` | Cliente del SDK FAIRINO: invocar primitivas Lua con parámetros y leer el estado del robot | Trayectorias propias, validación de límites, seguridad física |
| `edge/src/edge/camera/` | Cliente Open GoPro por USB: grabar, confirmar que graba, listar y descargar | Decidir cuándo grabar, procesar video |
| `edge/src/edge/session/` | Máquina de estados de una toma, con candado e idempotencia | Llamadas directas al SDK o a la cámara, HTTP, subidas |
| `edge/src/edge/render/` | Wrapper de ffmpeg por plantilla: un archivo final por toma | Definir el formato de plantilla, subir el resultado |
| `edge/src/edge/server/` | HTTP local: interfaz del operador y Studio de rutas en HTML plano, QR, página local de respaldo, PWA | Lógica de la toma, la web de la nube |
| `edge/src/edge/uploader/` | Cola de subida con reintentos, persistente entre reinicios | Bloquear o condicionar el camino crítico |
| `edge/tests/` | Pruebas de `edge` | Pruebas de la web, scripts de exploración |
| `edge/tools/` | Herramientas offline: planificación de rutas (cinemática, planificador, generador del Lua, simulador, modelo del FR10), `camera-probe` y `get_sdk`, que descarga el SDK de FAIRINO | Código que corra en el camino crítico de una toma |
| `edge/vendor/`, `edge/data/` | `vendor/fairino/` es el SDK descargado; `data/` guarda la cola y las tomas locales. Git ignora ambas | Código propio |
| `web/` | Astro en Vercel (D27) en `glam.datzoncompany.com`: página del invitado, panel de administración, API de sesiones, envío de correos y limpieza diaria, sobre Supabase (D28) | Camino crítico del evento, interfaz del operador, realtime (D14) |
| `docs/` | Diagramas Mermaid de lo decidido y los artifacts versionados (D29). `architecture.excalidraw` está superado por el artifact | Decisiones (viven en Notion) |

Hoy el código de producción es el núcleo de `edge/src/edge/session/` con sus falsos, el adaptador de la cámara en `camera/` y el render en `render/`; `web/` es solo el esqueleto de Astro, y `edge/tools/` guarda las herramientas de planificación. El detalle de cada carpeta está en `README.md`, el único README del repo, a propósito: cuando una carpeta gane contenido, actualiza esa tabla en lugar de crear un README nuevo. Mantén este mapa y esa tabla en sincronía.

## 4. Reglas duras

No son negociables. Si una tarea exige romper alguna, detente y plantéalo (sección 6).

1. **Una sola toma a la vez, y ningún reintento mueve el brazo dos veces.** Ningún cambio en `edge/` puede permitir dos tomas simultáneas, ni que un reintento de red (del operador, del navegador, de un cliente HTTP o de la cola) dispare un movimiento duplicado. Toda orden que termine en movimiento lleva el ID de la toma, pasa por un único candado y es idempotente: un ID ya aceptado no vuelve a mover el robot.
   *Motivo:* hay un brazo robótico industrial con personas cerca. Es seguridad física, no elegancia. (D16)

2. **El robot no se mueve hasta que la cámara confirma que está grabando.** La confirmación es el estado de grabación que reporta la GoPro, no un tiempo de espera supuesto. Si la confirmación no llega, la toma no arranca.
   *Motivo:* la cuenta regresiva existe para absorber el arranque de la cámara (D18). Si el brazo se mueve antes, se pierde una toma irrepetible con el invitado posando. (D18; A3 y A4 en Notion)

3. **El camino crítico funciona sin internet.** Operador pide ruta → robot ejecuta → cámara graba → se renderiza: nada de ese camino puede depender de un servicio en la nube, ni para completarse ni esperando una respuesta. La nube recibe los resultados después, a través de la cola de subida.
   *Motivo:* la zona del evento tiene que funcionar con el cable de red desconectado, y la red del salón no es confiable el día que importa. (Sección 2 de Notion; D14, D15, D17, D24)

4. **Del invitado solo se guarda el correo, por evento, y se anonimiza después.** No se pide nombre ni teléfono. El correo sirve únicamente para enviarle el enlace de su video. Nunca aparece en logs, trazas de error ni analítica. El registro de un envío guarda solo `session_id`, canal, timestamp y estado. Pasado el plazo configurable del evento, el correo se borra y queda un ID aleatorio de invitado; las tomas y la ubicación del video en el bucket se conservan.
   *Motivo:* el render tarda, así que el enlace llega por correo; lo que no se necesita no se conserva ni se expone. (D30 y D31 en Notion.)

5. **Los IDs públicos de video son aleatorios, nunca correlativos.** Nada que aparezca en una URL, un QR o una respuesta pública puede ser un contador ni derivarse de uno.
   *Motivo:* el QR apunta a una página pública (D21). Con IDs correlativos, cualquiera podría recorrer los videos de otros invitados cambiando un número. (Indicada por el responsable del proyecto; aún no registrada como decisión en Notion.)

6. **La interfaz del operador es HTML plano servido por el edge.** Ni app nativa ni un segundo proyecto con framework.
   *Motivo:* la tablet del operador se conecta al wifi del propio edge y tiene que operar sin internet (D15, sección 2). La única app con framework es la web en Astro (D27); otra cadena de build en el edge es complejidad sin beneficio. (Derivada de D15 y D27; la forma "HTML plano" la indicó el responsable del proyecto.)

7. **El software no es la seguridad.** No escribas código que asuma ser la protección de las personas, ni desactives o esquives la parada del controlador por pérdida de comunicación.
   *Motivo:* la seguridad la dan el paro de emergencia cableado y la parada automática del controlador; el watchdog del SDK no es seguridad certificada. (D10; E2 en Notion)

8. **El edge elige primitivas, no genera movimiento.** `edge/` solo selecciona una primitiva Lua ya cargada en el controlador y sus parámetros; no envía trayectorias ni poses propias. Única excepción (D38): en modo Studio, con el operador presente, el edge puede mandar movimientos sueltos; nunca durante una toma ni desde el camino crítico, y el control del Studio y el candado de la toma se excluyen.
   *Motivo:* el robot valida sus propios límites antes de moverse. (D2)

## 5. Convenciones

- Documentación y comentarios en español. Nombres de código (módulos, funciones, variables, tipos, endpoints) en inglés.
- **Los programas Lua que se cargan en el controlador no llevan ningún comentario.** Ni los escritos a mano ni los que genera un script. Si encuentras alguno, quítalo.
  *Motivo:* se leen dentro de la interfaz del robot, donde estorban y confunden. (Indicada por el responsable del proyecto.)
- **Comentarios al mínimo en el resto del código.** Se comenta el *porqué* que no se deduce leyendo: una trampa del hardware, un dato medido, una decisión rara con su motivo. Lo que narra lo que la línea ya dice, sobra. Si hace falta contexto largo, va al README de la carpeta.
- **`edge/` y `web/` son proyectos independientes (D36).** No se importan entre sí y cada uno tiene su `CLAUDE.md` con su foco y su política de pruebas; léelo al trabajar ahí.
- **Pocas pruebas, solo de comportamientos que importan.** Un cambio pequeño agrega como máximo una; las líneas de prueba no superan las del código. Ninguna prueba automática toca el robot, la cámara, el correo real ni la base de producción (D36).
- Los esquemas se definen **una sola vez**; `edge/` y `web/` los consumen, no los redefinen ni los copian. Su ubicación (`shared/` o `supabase/`) está por decidir.
- Lo ya decidido se diagrama en Mermaid dentro de `docs/`; los artifacts de diseño se versionan en `docs/artifacts/` (D29).

## 6. Cómo proponer un cambio de arquitectura

1. Se discute y se registra primero en Notion: la decisión con un ID nuevo y su "Por qué". Si reemplaza a otra, la anterior pasa a "Decisiones superadas"; nada se borra.
2. Solo después se toca el repositorio, citando el ID de la decisión en el commit.
3. Un agente que detecte que su tarea requiere cambiar una decisión, o que Notion no la cubre, se detiene y lo plantea en lugar de decidirlo por su cuenta en el código.
