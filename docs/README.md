# docs

**Fuente de verdad de las decisiones:** [Robot App en Notion](https://app.notion.com/p/Robot-App-3d7ac27a4ba480f19cd9cde2427ea213). Consúltala antes de cualquier decisión de arquitectura.

Esta carpeta no duplica decisiones: no existe `decisions.md` a propósito. Aquí se versionan los diagramas de lo ya decidido en Mermaid (`.mmd`) y los bocetos en Excalidraw (`.excalidraw`), según D11.

## Índice de diagramas

Planificados; todavía no existe ninguno. Los nombres de archivo son propuestas.

| Archivo | Contenido | Referencia en Notion |
|---|---|---|
| `session-state-machine.mmd` | Secuencia y estados de una toma, incluido qué pasa si falla a mitad de camino | A1 |
| `architecture.mmd` | Zona del evento frente a nube: robot, cámara, edge, web, almacenamiento y datos | Sección 2 |
| `event-network.mmd` | Red del evento: wifi propio del edge, tablet del operador, celular del invitado, router 4G/5G separado | D15, D24, E1 |
| `upload-and-delivery.mmd` | Cola de subida y cambio entre modo nube y modo local del QR | C3, D21, G3 |
