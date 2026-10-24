import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import board_lib as B
from board_lib import text, box, label, esc, INK, MUTED, BLUE, TEAL

B.PROJ = sys.argv[1]
PROJ = B.PROJ


def heading(y, t):
    return '<div style="position: absolute; left: 64px; top: %dpx; font-size: 18px; line-height: 24px; font-weight: 700">%s</div>' % (y, esc(t))


def card_row(y, cards, width=1312, gap=16):
    n = len(cards)
    cw = (width - gap * (n - 1)) // n
    hs = [text(0, 0, cw - 28, c, 14, 20)[1] for c in cards]
    ch = max(hs) + 28
    out = ''
    for i, c in enumerate(cards):
        x = 64 + i * (cw + gap)
        t, _ = text(14, 14, cw - 28, c, 14, 20)
        out += box(x, y, cw, ch, t)
    return out, ch


def table(y, cols, rows, headers):
    out = ''
    for (cx, cw), lab in zip(cols, headers):
        out += label(64 + cx, y, lab)
    y += 28
    for row in rows:
        raws = [('**%s**' % row[0])] + list(row[1:])
        hs = [text(0, 0, w, r, 14, 20)[1] for (_, w), r in zip(cols, raws)]
        rh = max(hs) + 24
        inner = ''
        for (cx, w), raw in zip(cols, raws):
            t, _ = text(cx, 12, w, raw, 14, 20)
            inner += t
        out += box(64, y, 1312, rh, inner)
        y += rh + 8
    return out, y


# ---------- Estilo y patrones ----------
body = heading(168, 'Estilo de arquitectura')
cards = [
    '**Tres capas (D1)**\nEl controlador mueve el brazo, el edge orquesta cada toma y la nube sirve el video. Cada capa trabaja en su propia escala de tiempo.',
    '**Edge offline-first (D17, C3)**\nTodo el camino de la toma es local. Los resultados salen por una cola cuando hay internet: guardar y reenviar.',
    '**Un solo proyecto en la nube (D27)**\nLa web y la API van juntas en Astro. Sin microservicios ni broker de mensajes. Consultas periódicas, sin tiempo real (D14).',
    '**Orquestación, no eventos**\n`session/` le dice a la cámara y al robot qué hacer, paso a paso. Nada reacciona a eventos sueltos.',
]
s, h = card_row(204, cards)
body += s
y = 204 + h + 40

body += heading(y, 'Patrones de diseño del edge y la web')
cols = [(16, 210), (242, 150), (408, 660), (1084, 212)]
rows = [
    ('Máquina de estados', '`session/`', 'Una toma tiene pasos fijos y fallos a mitad de camino que hay que manejar.', 'Decidido (A1 pendiente)'),
    ('Candado e idempotencia por ID', '`session/`', 'Un reintento no puede mover el brazo dos veces (regla 1).', 'Decidido (D16)'),
    ('Cola persistente con reintentos', '`uploader/`', 'Sobrevive a reinicios y a la falta de internet.', 'Decidido (C3)'),
    ('Comando', 'primitivas Lua', 'Una orden es el nombre de una primitiva más sus parámetros, con el ID de la toma (D2).', 'Decidido (D2)'),
    ('Adaptador', '`robot/` y `camera/`', '`session/` no habla con el SDK. Se puede probar con falsos, sin robot ni cámara.', 'Propuesto'),
    ('Transaction script', '`web/`', 'Endpoints delgados que llaman funciones simples. Sin capas extra para una API tan chica.', 'Propuesto'),
]
s, y = table(y + 32, cols, rows, ['Patrón', 'Dónde', 'Por qué', 'Estado'])
body += s
y += 32

body += heading(y, 'Patrones de aplicación y de datos')
app = ('**Aplicación**\n'
       'Interfaz del operador y Studio: páginas HTML planas servidas por el edge, con JavaScript solo donde hace falta (regla 6).\n'
       'Admin web: renderizado en el servidor con Astro y componentes interactivos puntuales.\n'
       'Página del invitado: casi estática y cacheable.\n'
       'Sincronización en un sentido por vez: el edge baja el catálogo antes del evento y sube los resultados después.\n'
       'Subida idempotente: el `id` lo genera el edge y la web hace upsert.')
dat = ('**Datos**\n'
       'Relacional: Postgres en Supabase (D28), con la clave generada del lado del edge.\n'
       'Archivo aparte, referencia en la base: el video vive en R2 y la base guarda solo `video_bucket_key` (claim check).\n'
       'Versiones inmutables de las rutas: editar crea otra fila, y cada toma apunta a la suya.\n'
       'Ciclo de vida: retención configurable y anonimización con limpieza diaria (D30, D31).\n'
       'Consistencia eventual: una toma es del edge hasta que sube, y de la nube después.\n'
       'Local en el edge: una carpeta por toma y la cola persistente. El almacenamiento de la cola no está decidido; propongo SQLite.')
s, ch = card_row(y + 36, [app, dat], gap=24)
body += s
y = y + 36 + ch + 24
nope = ('**Lo que no usamos, a propósito**\nMicroservicios, event sourcing, CQRS, DDD, un broker de mensajes, una capa de repositorios sobre Supabase y una capa de caché. No hacen falta para este tamaño y cada una añadiría piezas que mantener.')
t, h = text(16, 14, 1312 - 32, nope, 14, 20)
body += box(64, y, 1312, h + 28, t, bg='#e6f3f4', border='1px solid #9bd0d4')
H1 = y + h + 28 + 56
B.save('Patrones_Estilo.dc.html', 'Estilo de arquitectura y patrones', 1440, H1, body,
       'Qué estilo y qué patrones usamos hoy y por qué. Lo decidido cita su ID de Notion; lo propuesto aún no está registrado.')

# ---------- Resiliencia ----------
cols = [(16, 190), (222, 400), (638, 290), (944, 352)]
rows = [
    ('Robot (SDK)', 'Se aborta la toma, se detiene la cámara y queda `failed`. Nunca se reintenta el movimiento solo (reglas 1 y 7).', 'Tiempo límite en cada lectura de estado. Pasado el tiempo, cuenta como fallo.', 'El ID de la toma y el candado lo rechazan (D16).'),
    ('GoPro (USB)', 'Si no confirma que graba a tiempo, la toma no arranca (regla 2).', 'Espera acotada. No se supone un tiempo fijo.', 'Se lee el estado antes de repetir la orden de grabar.'),
    ('Descarga y render', 'Se conserva el original, se reintenta una vez y si no queda `failed`.', 'Tiempo límite.', 'Repetir el render sobrescribe el mismo archivo.'),
    ('Internet, R2 y la web', 'La cola reintenta con espera creciente y aleatoria, con un tope de intentos. Persiste entre reinicios (C3).', 'Tiempo límite. El camino de la toma nunca espera a la nube (regla 3).', 'El edge genera el `id` y la web hace upsert. El archivo se sube con el mismo nombre (`share_code`) y se sobrescribe.'),
    ('Supabase', 'La web responde 503 y el edge reintenta. La página dice "preparando tu video".', 'Igual que arriba.', 'Upsert por `id`.'),
    ('Servicio de correo (Resend)', 'Si el error es temporal, reintenta con espera. Si rebota, queda `bounced` y el operador corrige.', 'Si pide esperar por un límite diario, el envío pasa al día siguiente.', 'Cada envío es una fila en `email_deliveries`. El reenvío es una orden explícita con su propio ID, no un reintento ciego.'),
    ('Limpieza diaria', 'Si no corre un día, el siguiente la alcanza, porque se calcula por fecha.', 'Igual que arriba.', 'Correrla dos veces no hace nada extra.'),
]
body = heading(168, 'Qué pasa con cada dependencia externa')
s, y = table(200, cols, rows, ['Dependencia', 'Si falla', 'Si se demora', 'Si se repite'])
body += s
y += 24
cards = [
    '**¿Circuit breaker?**\nSí, uno pequeño y solo en `uploader/`. El router 4G va y viene: tras unos fallos seguidos la cola se pausa y prueba con una sola petición cada cierto tiempo. Son unas 20 líneas, sin librería.\nEn robot y cámara no se usa: se falla hacia el estado seguro. En correo y web no hace falta con un solo llamador y poco volumen.',
    '**A cuidar en un sistema de dos nodos**\nUna subida vieja no pisa un estado nuevo: el estado solo avanza.\nEl correo se envía solo cuando la subida terminó (`video_upload_status = done`).\nTras N intentos, un elemento imposible de subir pasa a `failed`.\nLa tablet muestra subidas pendientes y fallidas.\nSe propone guardar `received_at` con la hora del servidor, por si el reloj del edge está mal.',
    '**Estado**\nDecidido: candado e idempotencia (D16), cola persistente (C3) y camino local sin nube (regla 3).\nPropuesto: el breaker en `uploader/`, la espera creciente con aleatoriedad, el tope de intentos y la visibilidad en la tablet.\nSin verificar: si el servicio de correo ofrece clave de idempotencia. Si no, el estado en `email_deliveries` evita el doble envío.',
]
s, ch = card_row(y, cards, gap=16)
body += s
H2 = y + ch + 56
B.save('Patrones_Resiliencia.dc.html', 'Resiliencia: qué pasa cuando algo externo falla', 1440, H2, body,
       'Qué hace el sistema cuando algo externo falla, se demora o se repite. La regla de fondo: al menos una entrega más receptor idempotente equivale a una sola vez en efecto.')

# ---------- canvas.json ----------
cj = json.load(open('%s/canvas.json' % PROJ, encoding='utf-8'))
cj['pages'] = [p for p in cj['pages'] if p['id'] != 'page-patrones'] + [{'id': 'page-patrones', 'name': 'Patrones y resiliencia'}]
for name in [k for k in cj['boards'] if k.startswith('Patrones_')]:
    del cj['boards'][name]
cj['order'] = [n for n in cj['order'] if not n.startswith('Patrones_')]
for name, title, x, h in [('Patrones_Estilo.dc.html', 'Estilo y patrones', 0, H1), ('Patrones_Resiliencia.dc.html', 'Resiliencia', 1520, H2)]:
    cj['boards'][name] = {'x': x, 'y': 0, 'w': 1440, 'h': h, 'title': title, 'page': 'page-patrones'}
    cj['order'].append(name)
cj['notes']['titulo-patrones'] = {'kind': 'title1', 'maxW': 2960, 'page': 'page-patrones', 'text': 'Patrones y resiliencia', 'w': 240, 'x': 0, 'y': -280}
json.dump(cj, open('%s/canvas.json' % PROJ, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print(B.sizes)
