# Opciones de captura y de render

Qué ajustes tiene la GoPro HERO10 y qué filtros de ffmpeg usa el render, con el estado de cada uno. Se actualiza al probar algo. Las mediciones están en `resultados/calidad_20261027.json`; `calidad.py` repite la prueba.

**Estados:** Probado (hay resultado) · Parcial (resultado no concluyente o solo parte de las opciones) · No probado · Sin confirmar (id deducido del catálogo de la cámara, sin comprobar qué hace).

## Cómo repetir la prueba

```bash
# desde edge/, con la cámara conectada, quieta y la escena quieta
uv run python tools/camera-probe/calidad.py capture --serial 058 --out data/pruebas-captura/x \
    --modes 2_7K_4_3:120 5_3K:60 --sharpness Low --wb 5000K
uv run --with numpy python tools/camera-probe/calidad.py measure data/pruebas-captura/x --roi 560,1280,160,140
```

`capture` está sin probar con hardware tal como quedó escrito: parte de scripts que sí corrieron, pero la cámara estaba apagada al integrarlos. Prueba primero con un solo modo.

## Qué se midió y con qué cautelas

- Escena de una sala de noche, con focos domésticos. Una sola toma por modo, con la cámara fija.
- El ruido se mide sobre una zona estática del cuadro, y la zona cambia de un encuadre a otro (4:3 frente a 16:9).
- La nitidez medida solo compara clips con el mismo encuadre. Para comparar modos distintos, usa SNR.
- ISO 1600 en todos los clips, con obturador 1/121 a 120 fps y 1/61 a 60 fps: la cámara está en su tope de ISO.

## Cámara: captura

| Opción | Valores | Estado | Resultado |
|---|---|---|---|
| Resolución | 5.3K, 5K 4:3, 4K, 4K 4:3, 2.7K, 2.7K 4:3, 1080 | Parcial | Calidad medida en 5.3K, 4K, 4K 4:3 y 2.7K 4:3. 5K 4:3, 2.7K 16:9 y 1080 solo en la matriz inicial de latencia y tamaño |
| FPS | 24, 25, 30, 50, 60, 100, 120, 200, 240 | Parcial | Calidad medida en 60 y 120 |
| Lente | Max SuperView, SuperView, Wide, Linear, Linear + nivelación, Narrow | Parcial | Wide en todas las pruebas; el resto sin comparar |

Para un video vertical 9:16 a 1080 px de ancho, el recorte necesita al menos 1080 px: 2.7K 16:9 (855 px) y 1080p quedarían por debajo.

## Cámara: imagen

| Opción | Valores | Estado | Resultado |
|---|---|---|---|
| Nitidez (id 117) | Alta, Media, Baja | Probado | Baja baja el ruido y Alta lo sube mucho (4K a 120 fps: SNR 30,8 / 28,3 / 19,0) |
| Perfil de color (id 116) | Natural, Flat, Vibrant | Parcial | Natural en las pruebas. Flat colgó la cámara y no hay resultado |
| Compensación EV (id 118) | −2 a +2, pasos de 0,5 | Parcial | −1, 0 y +1 casi no cambiaron nada. La cámara venía en −0,5 sin saberlo, así que esas tomas no son fiables |
| Balance de blancos (id 115) | Auto, Native, 2300 K a 6500 K | Parcial | Auto marcó entre 4100 K y 4900 K. A 5500 K salió naranja |
| ISO mínimo (id 102) | 100 a 6400 | Parcial | Probé 400 y 1600 creyendo que era el máximo. Sin efecto visible |
| ISO máximo (id 13) | 100 a 6400 | Sin confirmar | Hoy en 1600, que coincide con el ISO fijo de todos los clips |
| Obturador (id 145) | Auto, 1/24 a 1/3840 | Sin confirmar | Sin probar |
| Compresión (id 106) | HEVC, H.264 + HEVC | Parcial | HEVC en todos los clips |
| Tasa de bits (id 160) | Alta, Estándar | Sin confirmar | Hoy en Estándar. Por la API del SDK no se pudo cambiar |

## Cámara: estabilización y funcionamiento

| Opción | Valores | Estado | Resultado |
|---|---|---|---|
| HyperSmooth | Apagado, Estándar, Alta, Boost | Parcial | Apagado en todas las pruebas, que es lo que va en el robot |
| Modo de rendimiento (id 173) | Máximo, Batería, Trípode/Estacionario | Parcial | Máximo, el de siempre |
| Antiparpadeo (id 134) | 60 Hz, 50 Hz | Parcial | 60 Hz, por defecto |
| Apagado automático (id 59) | 5, 15, 30 min, Nunca | No probado | Conviene "Nunca" durante el evento |

## ffmpeg: reducción de ruido

| Filtro | Estado | Resultado |
|---|---|---|
| `hqdn3d` | Probado | Con 3:3:10:10 y con 2:2:6:6 limpia el grano sin perder mucho detalle. Es el del render |
| `atadenoise`, `nlmeans`, `bm3d`, `fftdnoiz`, `tmix` | No probado | `nlmeans` y `bm3d` limpian más y son mucho más lentos |

## ffmpeg: nitidez, color y exposición

| Filtro | Estado | Resultado |
|---|---|---|
| `unsharp` | Parcial | En el render con 0,6; su efecto no está aislado |
| `eq` | Parcial | En el render; su efecto no está aislado |
| `cas`, `curves`, `colorbalance`, `lut3d`, `normalize`, `deflicker` | No probado | `normalize` es candidato a compensación automática; `deflicker` si la luz parpadea |

## ffmpeg: velocidad, encuadre y codificación

| Filtro u opción | Estado | Resultado |
|---|---|---|
| `setpts` y `fps` | Probado | Dan el 2× y el 4× real |
| `minterpolate` (modo `mci`) | Probado | Se ve bien en 5.3K a 60 fps y tarda unos 396 s para 4 s de captura. Otros modos y parámetros, sin probar |
| `crop` y `scale` lanczos | Probado | Recorte 9:16 a 1080×1920 nativo |
| `libx264` crf 18, preset `medium` | Probado | Salida `yuv420p`, rango estándar |
| `framerate`, `lenscorrection`, `zoompan`, `vidstab`, `-tune grain`, `libx265`, aceleración por hardware | No probado | La aceleración solo mejora la codificación, no la interpolación |

## Pendiente de la plantilla y la automatización

| Opción | Estado | Nota |
|---|---|---|
| `overlay`, `drawtext`, `xfade`, `concat` | No probado | Esperan el formato de plantilla (C5) |
| `amix`, `afade`, `loudnorm` | No probado | Esperan la música base (D20) |
| Telemetría de la cámara (ISO, obturador, balance) | Probado | `calidad.py` ya la lee; base para recomendar ajustes si la escena es oscura |

## Candidatos para la siguiente ronda

- ISO máximo (id 13) en 3200 y 6400, y la tasa de bits Alta (id 160).
- `atadenoise` frente a `hqdn3d`, y el efecto aislado de `unsharp` y `eq`.
- Los mismos modos con una luz mucho más fuerte, para ver cuánto sube el SNR.
- Medir el tiempo de render en el equipo del evento.
