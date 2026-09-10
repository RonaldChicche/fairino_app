# session

Máquina de estados de una toma: una sola a la vez, con candado e idempotencia por ID de toma (D16). Coordina en orden cámara, robot y render, incluido qué pasa si algo falla a mitad de camino.

No le corresponde: hablar directamente con el SDK o con la cámara, servir HTTP ni subir archivos. Su diagrama se versiona en `docs/` (A1 en Notion).
