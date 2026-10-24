# Artifact: Arquitectura Glambot FR10

Copia versionada del canvas de diseño que se publica en claude.ai. Esta carpeta es la copia durable; el artifact es privado de la cuenta del responsable.

- **Enlace:** https://claude.ai/artifact/42nHLrb2JE7nskCDeWaQ3r (para que otros lo vean hay que compartirlo desde el menú Share del artifact)
- **Versión copiada aquí:** 24, del 2026-10-24
- **Páginas:** Arquitectura, Entrega de videos, Pantallas de la app, Datos y Patrones y resiliencia

## Contenido

- `project/canvas.json`: índice. Lista las páginas y la posición y el tamaño de cada tablero.
- `project/*.dc.html`: un tablero por archivo. Los de `Main`, `Datos_*` y `Patrones_*` salen de los scripts de `generators/`.
- `generators/`: `build_main.py`, `build_datos.py` y `build_patrones.py` generan los tableros (`board_lib.py` es su código común); `check_main.py` comprueba que nada se solape. `python3 build_main.py salida.dc.html` genera `Main`; `python3 build_datos.py ../project` regenera los `Datos_*` y `python3 build_patrones.py ../project` los `Patrones_*`; ambos actualizan `canvas.json`.

Los `.dc.html` solo se dibujan dentro del tipo Design de Claude. En GitHub se ven como código. Para verlos hay que subirlos a un artifact de ese tipo o abrir el enlace de arriba.

## Cómo actualizarlo

1. Cambia el tablero, regenerándolo con su script o editándolo.
2. Publica los archivos cambiados en el artifact, junto con `canvas.json` si cambió el diseño del lienzo.
3. Copia aquí los archivos publicados y sube el número de versión de este README.
4. Haz el commit citando el ID de la decisión de Notion que motivó el cambio.
