import json, re, sys

PROJ = sys.argv[1]
SANS = "'IBM Plex Sans', system-ui, sans-serif"
MONO = "'IBM Plex Mono', ui-monospace, monospace"
INK, MUTED, BLUE, BORDER, TEAL, CLOUD = '#14202b', '#4a5866', '#3a4a85', '#9eaedd', '#0e7c86', '#4c62c7'
FONTS = '<link rel="preconnect" href="https://fonts.googleapis.com"><link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&amp;family=IBM+Plex+Sans:wght@400;600;700&amp;display=swap" rel="stylesheet">'


def esc(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def toks(text):
    out, pend = [], False
    for part in re.split(r'(\*\*.+?\*\*|`.+?`)', text):
        if not part:
            continue
        if part.startswith('**'):
            st, s = 'b', part[2:-2]
        elif part.startswith('`'):
            st, s = 'c', part[1:-1]
        else:
            st, s = '', part
        for t in re.findall(r'\S+|\s+', s):
            if t.isspace():
                pend = True
            else:
                out.append((t, st, pend))
                pend = False
    return out


def wlen(word, st, size):
    k = {'': 0.55, 'b': 0.59, 'c': 0.64}[st]
    return len(word) * size * k


def wrap(text, width, size):
    lines = []
    for para in text.split('\n'):
        cur, w = [], 0
        for word, st, sp in toks(para):
            ww = wlen(word, st, size)
            add = ww + (size * 0.3 if cur and sp else 0)
            if cur and w + add > width:
                lines.append(cur)
                cur, w, sp = [], 0, False
                add = ww
            assert ww <= width, 'palabra demasiado larga: ' + word
            cur.append((word, st, sp if cur else False))
            w += add
        lines.append(cur)
    return lines


def render_line(line, size):
    s = ''
    for word, st, sp in line:
        w = esc(word)
        if st == 'b':
            w = '<b>' + w + '</b>'
        elif st == 'c':
            w = '<code style="font-family: %s; font-size: %spx; background: #eef1f6; border-radius: 4px; padding: 0 3px">%s</code>' % (MONO, size - 1, w)
        s += (' ' if sp else '') + w
    return s


def text(x, y, w, t, size=14, lh=20, color=INK, extra=''):
    lines = wrap(t, w, size)
    inner = ''.join('<div style="white-space: nowrap">%s</div>' % render_line(l, size) for l in lines)
    h = len(lines) * lh
    return ('<div style="position: absolute; left: %dpx; top: %dpx; width: %dpx; font-size: %dpx; line-height: %dpx; color: %s; %s">%s</div>'
            % (x, y, w, size, lh, color, extra, inner)), h


def box(x, y, w, h, inner='', bg='#ffffff', border='1px solid ' + BORDER, radius=10, extra=''):
    return ('<div style="position: absolute; left: %dpx; top: %dpx; width: %dpx; height: %dpx; box-sizing: border-box; background: %s; border: %s; border-radius: %dpx; %s">%s</div>'
            % (x, y, w, h, bg, border, radius, extra, inner))


def line_svg(points, color=CLOUD, dash=False):
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    x0, y0, x1, y1 = min(xs) - 4, min(ys) - 4, max(xs) + 4, max(ys) + 4
    w, h = x1 - x0, y1 - y0
    d = 'M ' + ' L '.join('%d %d' % (px - x0, py - y0) for px, py in points)
    da = 'stroke-dasharray: 6 6; ' if dash else ''
    return ('<svg width="%d" height="%d" viewBox="0 0 %d %d" preserveAspectRatio="none" style="position: absolute; left: %dpx; top: %dpx; width: %dpx; height: %dpx; overflow: visible; fill: none; stroke: %s; stroke-width: 2; %sstroke-linecap: round; stroke-linejoin: round"><path d="%s"></path></svg>'
            % (w, h, w, h, x0, y0, w, h, color, da, d))


def tag(x, y, t, color=BLUE):
    return '<div style="position: absolute; left: %dpx; top: %dpx; font-size: 12px; line-height: 14px; font-weight: 700; color: %s">%s</div>' % (x, y, color, t)


def label(x, y, t):
    return '<div style="position: absolute; left: %dpx; top: %dpx; font-size: 12px; line-height: 16px; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; color: %s">%s</div>' % (x, y, BLUE, t)


def page(title, w, h, body, sub, subw=900):
    head = '<div style="position: absolute; left: 64px; top: 64px; font-size: 30px; line-height: 36px; font-weight: 700">%s</div>' % esc(title)
    s, sh = text(64, 108, subw, sub, 15, 22, MUTED)
    return ('<!doctype html>\n<html lang="es">\n<head>\n<meta charset="utf-8">\n<title>%s</title>\n<script src="./support.js"></script>\n</head>\n<body>\n<x-dc>\n<helmet>\n%s\n<style>\nbody{margin:0}\n</style>\n</helmet>\n'
            '<div style="position: relative; width: %dpx; height: %dpx; background: #f3f6f8; font-family: %s; color: %s">\n%s\n%s\n%s\n</div>\n</x-dc>\n'
            '<script type="text/x-dc" data-dc-script data-props=\'{"$preview":{"width":%d,"height":%d}}\'>\nclass Component extends DCLogic {\nrenderVals() {\nreturn {};\n}\n}\n</script>\n</body>\n</html>\n'
            % (esc(title), FONTS, w, h, SANS, INK, head, s, body, w, h))


sizes = {}


def save(name, title, w, h, body, sub, subw=900):
    open('%s/%s' % (PROJ, name), 'w', encoding='utf-8').write(page(title, w, h, body, sub, subw))
    sizes[name] = (w, h)


# ---------------- esquema ----------------
# (columna, tipo, clave, qué guarda, ejemplo)
S = {}
S['events'] = ('Una fecha concreta con una empresa. Agrupa todas las tomas de esa jornada.', [
    ('id', 'uuid', 'PK', 'Identificador interno del evento. Lo genera la base.', '9f1c2a7e…'),
    ('company_name', 'text', '', 'Nombre de la empresa o persona que contrata el evento.', 'Banco Andino'),
    ('event_date', 'date', '', 'Fecha del evento. Empresa más fecha identifican el evento: no puede haber dos iguales.', '2026-11-14'),
    ('status', 'text', '', 'Si el evento sigue abierto o ya se cerró. Valores: active, closed.', 'active'),
    ('video_retention_days', 'int', '', 'Días que el video sigue disponible, contados desde la toma. Vacío usa el valor global de app_settings. 0 significa que no se borra nunca.', '7'),
    ('email_retention_days', 'int', '', 'Días después de la fecha del evento en que se anonimizan los correos. Vacío usa el valor global.', '7'),
    ('created_at', 'timestamptz', '', 'Cuándo se creó la fila.', '2026-10-24 18:02'),
])
S['event_guests'] = ('Una persona que se tomó un video en un evento. Se identifica solo por su correo.', [
    ('id', 'uuid', 'PK', 'Identificador interno del invitado en ese evento. Sobrevive a la anonimización.', '5b7d0c41…'),
    ('event_id', 'uuid', 'FK', 'Evento al que pertenece. La misma persona en otro evento es otro invitado.', '9f1c2a7e…'),
    ('email', 'text', '', 'Correo al que se envía el enlace. No se repite dentro del evento. Queda vacío al anonimizar (D30).', 'ana@correo.com'),
    ('email_anonymized_at', 'timestamptz', '', 'Cuándo se borró el correo. Vacío mientras el correo siga guardado.', '2026-11-21 03:00'),
    ('created_at', 'timestamptz', '', 'Cuándo el operador registró el correo.', '2026-11-14 21:05'),
])
S['sessions'] = ('Una toma, de principio a fin. Es la entidad central: une evento, invitado, ruta, plantilla y video.', [
    ('id', 'uuid', 'PK', 'Identificador interno de la toma. Lo genera el edge, así un reintento de subida actualiza la fila en vez de duplicarla (regla 1).', 'c04e91ab…'),
    ('share_code', 'text', 'UQ', 'Código aleatorio que va en la URL y en el QR: /v/{share_code}. Nunca es un contador (regla 5).', 'k3f9x2m7qa'),
    ('event_id', 'uuid', 'FK', 'Evento al que pertenece la toma.', '9f1c2a7e…'),
    ('guest_id', 'uuid', 'FK', 'Invitado al que se envía el video.', '5b7d0c41…'),
    ('route_id', 'uuid', 'FK', 'Versión exacta de la ruta que se ejecutó. Editar una ruta crea otra fila, así las tomas viejas no cambian.', '71aa30d2…'),
    ('template_id', 'uuid', 'FK', 'Plantilla con la que se renderizó: formato, ralentización y música.', '2e60b8f5…'),
    ('edge_device_id', 'uuid', 'FK', 'Equipo edge que hizo la toma.', 'aa13c7e0…'),
    ('process_status', 'text', '', 'En qué paso va la toma. Propuesta: requested, recording, moving, processing, ready, failed. Los fija el diagrama A1.', 'ready'),
    ('failure_reason', 'text', '', 'Motivo del fallo cuando process_status es failed. Vacío si todo salió bien.', 'camera_not_recording'),
    ('taken_at', 'timestamptz', '', 'Momento en que se hizo la toma.', '2026-11-14 21:07'),
    ('video_upload_status', 'text', '', 'Si el video ya subió al bucket: pending, uploading, done o failed. Va aparte porque la toma puede estar lista y la subida pendiente por falta de internet.', 'done'),
    ('video_bucket_key', 'text', '', 'Ubicación del video en el bucket R2. Se conserva aunque el archivo se borre.', 'v/k3f9x2m7qa.mp4'),
    ('video_duration_ms', 'int', '', 'Duración del video final en milisegundos.', '15500'),
    ('video_width', 'int', '', 'Ancho del video final en píxeles.', '1215'),
    ('video_height', 'int', '', 'Alto del video final en píxeles.', '2160'),
    ('video_fps', 'numeric', '', 'Cuadros por segundo del video final.', '30'),
    ('video_size_bytes', 'bigint', '', 'Tamaño del archivo en bytes.', '19500000'),
    ('video_deleted_at', 'timestamptz', '', 'Cuándo la limpieza borró el archivo del bucket. Vacío mientras exista. Con valor, la página muestra que el video ya no está disponible.', '2026-11-21 03:00'),
])
S['routes'] = ('Un movimiento del brazo ya probado en el Studio. El edge solo elige cuál ejecutar (D2).', [
    ('id', 'uuid', 'PK', 'Identificador de esta versión de la ruta.', '71aa30d2…'),
    ('name', 'text', '', 'Nombre que ve el operador en la lista.', 'Arco lateral'),
    ('version', 'int', '', 'Número de versión. Cada edición aprobada crea una fila nueva y las anteriores no se tocan.', '3'),
    ('lua_program_name', 'text', '', 'Nombre con el que el programa quedó cargado en el controlador del robot. Es lo que el edge invoca.', 'arco_lateral_v3'),
    ('lua_source', 'text', '', 'Código Lua completo, sin comentarios. Sirve para recargar la ruta en un controlador nuevo o reiniciado.', 'movel(...)'),
    ('lua_sha256', 'text', '', 'Huella del código. Antes de un evento el edge comprueba que lo cargado en el robot coincide.', 'e3b0c442…'),
    ('waypoints', 'jsonb', '', 'Puntos y objetivo con los que se planificó la ruta, para poder reeditarla en el Studio.', '[{x, y, z}, …]'),
    ('default_params', 'jsonb', '', 'Parámetros por defecto, por ejemplo la velocidad. El edge puede ajustarlos al invocar la ruta (D2).', '{"speed": 20}'),
    ('sample_clip_bucket_key', 'text', '', 'Clip de muestra grabado al probar la ruta. Se muestra al operador en la lista.', 'samples/arco_v3.mp4'),
    ('is_approved', 'bool', '', 'true: el operador puede usarla en eventos. Las no aprobadas son borradores del Studio.', 'true'),
    ('created_at', 'timestamptz', '', 'Cuándo se guardó esta versión.', '2026-10-30 16:40'),
])
S['templates'] = ('Cómo se ve el video final. La diseña la empresa y el operador elige una antes de la toma.', [
    ('id', 'uuid', 'PK', 'Identificador de la plantilla.', '2e60b8f5…'),
    ('name', 'text', '', 'Nombre que ve el operador.', 'Stories en cámara lenta'),
    ('format', 'text', '', 'Formato del video: vertical_9_16 para stories o wide_16_9 para el formato largo.', 'vertical_9_16'),
    ('slowdown_factor', 'numeric', '', 'Cuántas veces más lento se reproduce. Con 4, una toma de 3 segundos dura 12.', '4'),
    ('music_track_id', 'uuid', 'FK', 'Pista de música que lleva esta plantilla.', '8d2f6a19…'),
    ('is_active', 'bool', '', 'false: la plantilla no aparece para el operador.', 'true'),
    ('created_at', 'timestamptz', '', 'Cuándo se creó la plantilla.', '2026-10-28 11:15'),
])
S['music_tracks'] = ('Pistas libres de derechos que usan las plantillas.', [
    ('id', 'uuid', 'PK', 'Identificador de la pista.', '8d2f6a19…'),
    ('title', 'text', '', 'Nombre de la pista.', 'Neon Drive'),
    ('audio_bucket_key', 'text', '', 'Ubicación del audio en el bucket R2.', 'music/neon-drive.mp3'),
    ('license_note', 'text', '', 'De dónde salió y bajo qué licencia se puede usar comercialmente.', 'Licencia libre, uso comercial'),
    ('is_active', 'bool', '', 'false: la pista no se ofrece en plantillas nuevas.', 'true'),
])
S['edge_devices'] = ('Un equipo de captura: la laptop o el mini PC junto al robot.', [
    ('id', 'uuid', 'PK', 'Identificador del equipo.', 'aa13c7e0…'),
    ('name', 'text', '', 'Nombre del equipo para reconocerlo.', 'laptop-pruebas'),
    ('api_token_hash', 'text', '', 'Huella del token con el que el edge se identifica ante la web. El token en sí no se guarda.', '5f4dcc3b…'),
    ('last_seen_at', 'timestamptz', '', 'Última vez que el edge habló con la web.', '2026-11-14 21:12'),
    ('is_active', 'bool', '', 'false: el token deja de funcionar.', 'true'),
])
S['email_deliveries'] = ('Cada intento de enviar el enlace de un video. Nunca guarda la dirección de correo.', [
    ('id', 'uuid', 'PK', 'Identificador del envío.', 'd1e7b2c3…'),
    ('session_id', 'uuid', 'FK', 'Toma cuyo enlace se envió.', 'c04e91ab…'),
    ('channel', 'text', '', 'Canal del envío. Por ahora siempre email; deja espacio para otros.', 'email'),
    ('status', 'text', '', 'queued, sent, bounced o failed. bounced significa que la dirección no existe: el operador la corrige y reenvía.', 'sent'),
    ('provider_message_id', 'text', '', 'Identificador que devuelve el servicio de correo, para rastrear el envío.', 'msg_8f2a…'),
    ('sent_at', 'timestamptz', '', 'Cuándo se envió. Cada reenvío es una fila nueva.', '2026-11-14 21:09'),
])
S['arm_telemetry'] = ('Resumen de lo que hizo el brazo durante una toma. Se construye después.', [
    ('session_id', 'uuid', 'PK FK', 'Toma a la que corresponde el resumen. Hay una por toma.', 'c04e91ab…'),
    ('motion_summary', 'jsonb', '', 'Resumen del movimiento: rangos de articulaciones, trayectoria de la herramienta y duración. El detalle crudo se queda en el edge.', '{"duration_ms": 3100}'),
    ('controller_errors', 'jsonb', '', 'Errores, paros y alertas que reportó el controlador durante la toma.', '[]'),
    ('recorded_at', 'timestamptz', '', 'Cuándo se guardó el resumen.', '2026-11-14 21:10'),
])
S['app_settings'] = ('Valores globales que se editan en el panel. No se relaciona con otras tablas.', [
    ('setting_key', 'text', 'PK', 'Nombre del valor. Hoy: default_video_retention_days y default_email_retention_days.', 'default_video_retention_days'),
    ('setting_value', 'text', '', 'El valor, escrito como texto.', '7'),
    ('description', 'text', '', 'Para qué sirve, para quien lo edita en el panel.', 'Días que un video sigue disponible'),
])

# ---------- 1. Modelo de datos (ERD) ----------
TW = 296


def table(x, y, name, core=True):
    cols = S[name][1]
    n = len(cols)
    h = 42 + 22 * n
    border = '1px solid ' + BORDER if core else '1px dashed ' + CLOUD
    s = ('<div style="height: 32px; line-height: 32px; padding: 0 12px; background: #dde4f7; display: flex; justify-content: space-between"><span style="font-family: %s; font-weight: 600; font-size: 14px">%s</span><span style="font-size: 11px; color: %s">%s</span></div>'
         % (MONO, name, BLUE, 'núcleo' if core else 'después'))
    for i, (c, t, k, _, _) in enumerate(cols):
        top = 36 + i * 22
        kc = TEAL if 'PK' in k else BLUE
        s += ('<div style="position: absolute; left: 0; top: %dpx; width: %dpx; height: 22px; line-height: 22px; font-family: %s; font-size: 12px">'
              '<span style="position: absolute; left: 12px">%s</span><span style="position: absolute; left: 184px; color: %s">%s</span>'
              '<span style="position: absolute; left: 244px; width: 40px; text-align: right; font-size: 11px; font-weight: 600; color: %s">%s</span></div>'
              % (top, TW, MONO, c, MUTED, t, kc, k))
    return box(x, y, TW, h, s, border=border, extra='overflow: hidden'), h


C1, C2, C3 = 64, 416, 768
pos = {
    'events': (C2, 200), 'event_guests': (C1, 200), 'sessions': (C2, 470),
    'edge_devices': (C1, 620), 'arm_telemetry': (C1, 860), 'app_settings': (C1, 1040),
    'routes': (C3, 470), 'templates': (C3, 790), 'music_tracks': (C3, 1030),
    'email_deliveries': (C2, 980),
}
body = ''
hts = {}
for k, (x, y) in pos.items():
    s, h = table(x, y, k, core=(k != 'arm_telemetry'))
    body += s
    hts[k] = h
R1, R2 = C1 + TW, C2 + TW
body += line_svg([(R1, 260), (C2, 260)]) + tag(C2 - 14, 242, '1') + tag(R1 + 4, 242, 'N')
body += line_svg([(564, 396), (564, 470)]) + tag(570, 400, '1') + tag(570, 452, 'N')
body += line_svg([(212, 352), (212, 540), (C2, 540)]) + tag(218, 356, '1') + tag(C2 - 14, 522, 'N')
body += line_svg([(R1, 700), (C2, 700)]) + tag(R1 + 4, 682, '1') + tag(C2 - 14, 682, 'N')
body += line_svg([(R2, 540), (C3, 540)]) + tag(R2 + 4, 522, 'N') + tag(C3 - 14, 522, '1')
body += line_svg([(R2, 860), (C3, 860)]) + tag(R2 + 4, 842, 'N') + tag(C3 - 14, 842, '1')
body += line_svg([(916, 986), (916, 1030)]) + tag(922, 990, 'N') + tag(922, 1012, '1')
body += line_svg([(564, 908), (564, 980)]) + tag(570, 912, '1') + tag(570, 962, 'N')
body += line_svg([(R1, 880), (C2, 880)]) + tag(R1 + 4, 862, '1') + tag(C2 - 14, 862, '1')

NX, NW = 1128, 248
notes = [
    '**Cómo leerlo**\n`PK` clave primaria: identifica la fila.\n`FK` clave foránea: apunta a otra tabla.\n`UQ` valor único: no se repite.\n`1` y `N` en cada línea: una fila de un lado se relaciona con muchas del otro.\nBorde punteado: se construye después.\nLos nombres van en inglés, como el código. Qué guarda cada columna está explicado en las páginas siguientes.',
    '**Reglas que ya trae el diseño**\n`sessions.id` lo genera el edge: un reintento actualiza la fila y no la duplica (regla 1).\n`share_code` es aleatorio, nunca un contador (regla 5).\nEl correo vive solo en `event_guests` y se borra al anonimizar (regla 4, D30).\nLa retención es configurable por evento (D31): el video se borra, el registro y su `video_bucket_key` se conservan.\nNo hay tabla de clientes: el evento es empresa más fecha.',
]
y = 200
for n in notes:
    t, h = text(NX + 14, y + 14, NW - 28, n, 13, 20)
    body += box(NX, y, NW, h + 28, t, bg='#e9edfa', border='1px solid #bac6eb')
    y += h + 28 + 24
H_MODELO = max(max(pos[k][1] + hts[k] for k in pos), y) + 64
save('Datos_Modelo.dc.html', 'Modelo de datos', 1440, H_MODELO, body,
     'Diez tablas en Supabase (Postgres), esquema public. Nueve son el núcleo; la de borde punteado se construye después. Notación: diagrama entidad-relación con PK, FK y cardinalidad 1 a N.')

# ---------- 2-5. Diccionario de columnas ----------
CC = [(16, 230), (262, 110), (388, 620), (1024, 272)]


def colboard(fname, title, sub, tables):
    body = ''
    y = 168
    for tname in tables:
        purpose, cols = S[tname]
        body += ('<div style="position: absolute; left: 64px; top: %dpx; font-family: %s; font-size: 18px; line-height: 24px; font-weight: 600">%s</div>' % (y, MONO, tname))
        t, h = text(64, y + 28, 1100, purpose, 14, 20, MUTED)
        body += t
        y += 28 + h + 16
        for (cx, cw), lab in zip(CC, ['Columna', 'Tipo', 'Qué guarda', 'Ejemplo']):
            body += label(64 + cx, y, lab)
        y += 24
        for c, tp, k, desc, ex in cols:
            cells = [
                (c + ('  ' + k if k else ''), 230),
                (tp, 110), (desc, 620), (ex, 272),
            ]
            _, hd = text(0, 0, 620, desc, 14, 20)
            rh = max(hd, 20) + 20
            inner = ''
            name_html = '<div style="position: absolute; left: %dpx; top: 10px; width: 236px; font-family: %s; font-size: 13px; line-height: 20px; font-weight: 600; white-space: nowrap">%s<span style="font-size: 11px; color: %s; font-weight: 600; margin-left: 6px">%s</span></div>' % (CC[0][0], MONO, c, TEAL if 'PK' in k else BLUE, k)
            inner += name_html
            inner += '<div style="position: absolute; left: %dpx; top: 10px; width: 120px; font-family: %s; font-size: 12px; line-height: 20px; color: %s; white-space: nowrap">%s</div>' % (CC[1][0], MONO, MUTED, tp)
            t, _ = text(CC[2][0], 10, 620, desc, 14, 20)
            inner += t
            t, _ = text(CC[3][0], 10, 272, ex, 13, 20, MUTED, 'font-family: %s;' % MONO)
            inner += t
            body += box(64, y, 1312, rh, inner)
            y += rh + 6
        y += 30
    save(fname, title, 1440, y + 34, body, sub)


colboard('Datos_Columnas1.dc.html', 'Columnas: eventos e invitados',
         'Qué guarda cada columna de events, event_guests y app_settings, con un ejemplo. Los códigos D y regla remiten a Notion y a CLAUDE.md.',
         ['events', 'event_guests', 'app_settings'])
colboard('Datos_Columnas2.dc.html', 'Columnas: la sesión (la toma)',
         'sessions es la tabla central. Guarda quién, cuándo, con qué ruta y plantilla, y dónde quedó el video. Las columnas video_* son las propiedades del video final.',
         ['sessions'])
colboard('Datos_Columnas3.dc.html', 'Columnas: rutas, plantillas y música',
         'Lo que la empresa diseña antes del evento. Las rutas se crean en el Studio; las plantillas y la música, en el panel de administración.',
         ['routes', 'templates', 'music_tracks'])
colboard('Datos_Columnas4.dc.html', 'Columnas: equipos, correos y telemetría',
         'edge_devices identifica a cada equipo, email_deliveries registra los envíos y arm_telemetry resume el movimiento del brazo.',
         ['edge_devices', 'email_deliveries', 'arm_telemetry'])

# ---------- 6. Glosario ----------
TERMS = [
    ('Evento', 'events', 'Una fecha con una empresa. Agrupa todas las tomas de esa jornada. Si la empresa contrata dos fechas, son dos eventos.', 'Tú, en el panel de administración.', 'Supabase. El edge guarda una copia en disco para operar sin internet.'),
    ('Invitado', 'event_guests', 'Una persona que se toma un video en un evento. Solo se conoce su correo. Si repite en el mismo evento, el operador reutiliza el mismo registro.', 'El operador, al escribir el correo en la tablet.', 'Primero en el disco del edge; en Supabase cuando hay internet.'),
    ('Sesión (una toma)', 'sessions', 'Una toma de un invitado, de principio a fin. Une el evento, el invitado, la ruta ejecutada, la plantilla y el video final (C1). Es la entidad central.', 'El edge, en cuanto el operador pulsa Go.', 'Primero en el disco del edge; en Supabase cuando hay internet.'),
    ('Ruta', 'routes', 'Un movimiento del brazo ya probado: nombre, programa Lua cargado en el controlador y sus parámetros. El edge solo elige cuál ejecutar (D2). Cada edición crea una versión nueva.', 'Tú, en el Studio, junto al robot.', 'Supabase para el catálogo y el código; el controlador para el programa cargado.'),
    ('Plantilla', 'templates', 'Cómo se ve el video final: formato vertical o amplio, factor de cámara lenta y la música. La diseña la empresa y el operador elige una antes de la toma (D32).', 'Tú, en el panel de administración.', 'Supabase.'),
    ('Pista de música', 'music_tracks', 'Una canción libre de derechos que usa una plantilla. El invitado no la cambia.', 'Tú, en el panel de administración.', 'Supabase para la fila; R2 para el audio.'),
    ('Equipo edge', 'edge_devices', 'La laptop o el mini PC junto al robot. Se identifica ante la web con un token propio.', 'Tú, al preparar el equipo.', 'Supabase.'),
    ('Envío de correo', 'email_deliveries', 'Cada intento de mandar el enlace de un video. Un reenvío es otra fila. Nunca guarda la dirección (regla 4).', 'La web, al enviar o reenviar.', 'Supabase.'),
    ('Código para compartir', 'sessions.share_code', 'El código aleatorio de la URL y del QR, por ejemplo /v/k3f9x2m7qa. Nunca es un contador ni se deriva de uno (regla 5).', 'El edge, al crear la toma, para mostrar el QR aunque no haya internet.', 'Columna de sessions.'),
    ('Ubicación en el bucket', 'video_bucket_key', 'El nombre del archivo dentro de R2. La base guarda solo este nombre; el archivo vive en R2 y puede borrarse sin perder el registro.', 'El edge, al subir el video.', 'R2 guarda el archivo; Supabase guarda el nombre.'),
    ('Retención', 'video_retention_days', 'Cuántos días sigue disponible un video. Se configura por evento y hay un valor global. Al vencer se borra el archivo, no el registro (D31).', 'Tú, en el panel de administración.', 'events y app_settings.'),
    ('Anonimización', 'email_anonymized_at', 'Pasado el plazo del evento, el correo se borra y queda el id aleatorio del invitado. Así las tomas siguen agrupadas, pero ya no se sabe de quién eran (D30).', 'La limpieza diaria.', 'event_guests.'),
]
cols = [(16, 200), (232, 480), (728, 250), (994, 302)]
body = ''
for (cx, cw), lab in zip(cols, ['Término', 'Qué es', 'Quién lo crea', 'Dónde vive']):
    body += label(64 + cx, 168, lab)
y = 196
for term, tbl, desc, who, where in TERMS:
    parts = [('**%s**\n`%s`' % (term, tbl), 200), (desc, 480), (who, 250), (where, 302)]
    hs = [text(0, 0, w, raw, 14, 20)[1] for raw, w in parts]
    rh = max(hs) + 24
    inner = ''
    for (cx, _), (raw, w) in zip(cols, parts):
        t, h = text(cx, 12, w, raw, 14, 20, MUTED if cx >= 728 else INK)
        inner += t
    body += box(64, y, 1312, rh, inner)
    y += rh + 8
H_GLOSARIO = y + 56
save('Datos_Glosario.dc.html', 'Glosario de datos', 1440, H_GLOSARIO, body,
     'Qué representa cada nombre importante, quién lo crea y dónde vive. Los códigos D y regla remiten a Notion y a CLAUDE.md.')

# ---------- 7. Cómo se usa ----------
PH = [
    ('Antes del evento', 'con internet y en el Studio', '#e9edfa', '#bac6eb', [
        ('Tú', 'Creas el evento en el panel de administración: empresa y fecha.', '`events`'),
        ('Tú', 'En el Studio, junto al robot, creas y pruebas rutas. Al aprobar una, se guarda su Lua.', '`routes`'),
        ('Tú', 'Diseñas las plantillas y subes las pistas de música libres de derechos.', '`templates`, `music_tracks`'),
        ('Edge', 'Descarga el evento, las plantillas y las rutas y las guarda en disco.', 'lee esas tablas'),
    ]),
    ('Durante la toma', 'sin internet', '#e8eef3', '#c5d0da', [
        ('Operador', 'Elige el evento y escribe el correo del invitado.', '`event_guests` (local)'),
        ('Operador', 'Elige la ruta y la plantilla y pulsa Go.', ''),
        ('Edge', 'Crea la sesión con su id y su share_code, graba, mueve el brazo, descarga el clip y lo renderiza.', '`sessions` (local)'),
        ('Edge', 'Muestra en la tablet el QR de /v/{share_code} si hay tiempo.', ''),
    ]),
    ('Cuando hay internet', 'cola de subida', '#e9edfa', '#bac6eb', [
        ('Edge', 'Sube el MP4 a R2 con el share_code como nombre.', '`video_bucket_key`'),
        ('Edge', 'Manda la sesión y el invitado a la web. Si el id ya existe, la actualiza y no la duplica.', '`sessions`, `event_guests`'),
        ('Web', 'Marca la subida como terminada y envía el correo con el enlace.', '`email_deliveries`'),
        ('Operador', 'Si el correo estaba mal escrito, lo corrige en la tablet o el admin lo corrige en la web, y reenvía.', '`event_guests`, `email_deliveries`'),
    ]),
    ('Invitado y limpieza', 'con internet', '#e9edfa', '#bac6eb', [
        ('Invitado', 'Abre /v/{share_code} desde el correo y ve, descarga o comparte el video desde R2.', 'lee `sessions`'),
        ('Edge', 'Si no hubo internet, sirve el video por su wifi con un QR local, como respaldo (D33).', ''),
        ('Sistema', 'Cada día anonimiza los correos vencidos y borra los videos vencidos.', '`email_anonymized_at`, `video_deleted_at`'),
    ]),
]
CW, GAP, X0 = 300, 32, 64
body = ''
ybottom = 0
for i, (ttl, sub, bg, bd, cards) in enumerate(PH):
    x = X0 + i * (CW + GAP)
    body += box(x, 168, CW, 52, '<div style="padding: 8px 14px; font-size: 14px; line-height: 20px"><b>%s</b><br><span style="font-size: 13px; color: %s">%s</span></div>' % (ttl, MUTED, sub), bg=bg, border='1px solid ' + bd)
    y = 236
    for actor, act, tb in cards:
        t, h = text(x + 14, y + 36, CW - 28, act, 14, 20)
        tt, th = ('', 0)
        if tb:
            tt, th = text(x + 14, y + 36 + h + 6, CW - 28, 'toca: ' + tb, 13, 18, MUTED)
        ch = 36 + h + (th + 6 if tb else 0) + 14
        body += box(x, y, CW, ch, '', bg='#ffffff')
        body += '<div style="position: absolute; left: %dpx; top: %dpx; font-size: 12px; line-height: 16px; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; color: %s">%s</div>' % (x + 14, y + 12, TEAL if actor == 'Edge' else BLUE, actor)
        body += t + tt
        y += ch + 12
    ybottom = max(ybottom, y)
ban, bh = text(64 + 16, ybottom + 20 + 14, 1312 - 32, 'Lo único que el edge necesita de internet es descargar el evento antes y subir los resultados después. Para tomar un video no depende de ninguna de las dos (regla 3). El navegador del invitado y el del administrador nunca hablan directo con la base: pasan siempre por la web.', 14, 20)
body += box(64, ybottom + 20, 1312, bh + 28, ban, bg='#e6f3f4', border='1px solid #9bd0d4')
H_USO = ybottom + 20 + bh + 28 + 56
save('Datos_Uso.dc.html', 'Cómo se usa el sistema de datos', 1440, H_USO, body,
     'Quién escribe y lee qué, en el orden en que ocurre. El camino de la toma no toca la nube: la base se llena antes y después.')

# ---------- 8. Limpieza diaria ----------
STEPS = [
    ('1 · Corre una vez al día', 'Un trabajo programado se ejecuta a una hora fija de la noche. Puede vivir dentro de Supabase (pg_cron) o en el cron de Vercel: se usa el que salga más barato.', ''),
    ('2 · Anonimiza correos', 'Para cada evento, si event_date más email_retention_days (o el valor global) ya pasó, deja `email` vacío y escribe `email_anonymized_at`. Es solo SQL, así que puede correr dentro de Postgres.', 'toca `event_guests`'),
    ('3 · Borra videos vencidos', 'Busca las tomas donde taken_at más video_retention_days ya pasó y `video_deleted_at` sigue vacío. Borra el archivo en R2 y escribe `video_deleted_at`. Borrar en R2 pide credenciales, así que lo hace un endpoint de la web que llama el cron.', 'toca `sessions` y el bucket'),
    ('4 · La página lo refleja', 'Cuando `video_deleted_at` tiene valor, /v/{share_code} dice que el video ya no está disponible. El registro de la toma, sus propiedades y `video_bucket_key` se conservan.', 'lee `sessions`'),
]
CW, GAP = 300, 32
body = ''
ymax = 0
for i, (ttl, desc, tb) in enumerate(STEPS):
    x = 64 + i * (CW + GAP)
    t, h = text(x + 14, 168 + 48, CW - 28, desc, 14, 20)
    tt, th = ('', 0)
    if tb:
        tt, th = text(x + 14, 168 + 48 + h + 8, CW - 28, tb, 13, 18, MUTED)
    ch = 48 + h + (th + 8 if tb else 0) + 16
    body += box(x, 168, CW, ch, '', bg='#ffffff')
    body += '<div style="position: absolute; left: %dpx; top: 180px; font-size: 14px; line-height: 20px; font-weight: 700">%s</div>' % (x + 14, esc(ttl))
    body += t + tt
    ymax = max(ymax, 168 + ch)
y = ymax + 32
side = [
    ('**Valores configurables**\nEl valor global se edita en `app_settings` (`default_video_retention_days` y `default_email_retention_days`). Cada evento puede sobrescribirlo en `video_retention_days` y `email_retention_days`. Un valor 0 en el video significa que no se borra nunca. Como se calcula en cada corrida, cambiar el valor se aplica también a lo ya guardado.'),
    ('**Por qué no una regla fija de R2**\nR2 puede borrar archivos por antigüedad, pero con un plazo único para todo el bucket, y aquí el plazo cambia por evento. Se puede dejar una regla larga como red de seguridad, por ejemplo 30 días, por si el trabajo falla.'),
    ('**Costo**\nEl cron de Vercel Hobby corre una vez al día con hora aproximada, y pg_cron viene dentro de Supabase. Ambos son gratis; en el plan gratis de pg_cron no verifiqué los límites en la documentación oficial. Un trabajo diario además mantiene activo el proyecto gratis de Supabase, que se pausa tras una semana sin actividad.'),
]
sw = (1312 - 2 * 32) // 3
sh = 0
parts = []
for s in side:
    t, h = text(0, 0, sw - 28, s, 14, 20)
    sh = max(sh, h)
for i, s in enumerate(side):
    x = 64 + i * (sw + 32)
    t, h = text(x + 14, y + 14, sw - 28, s, 14, 20)
    body += box(x, y, sw, sh + 28, t, bg='#e9edfa', border='1px solid #bac6eb')
H_LIMPIEZA = y + sh + 28 + 56
save('Datos_Limpieza.dc.html', 'Limpieza diaria', 1440, H_LIMPIEZA, body,
     'Cómo se aplican la retención del video y la anonimización del correo. Los plazos son configurables; los 7 días son tentativos.')

# ---------- 9. Acceso ----------
ROWS = [
    ('Edge', 'Un token propio por equipo, sobre HTTPS. En la base solo se guarda su huella (`edge_devices.api_token_hash`).', 'El evento, las plantillas activas y las rutas aprobadas que le tocan.', 'Sus sesiones, invitados y telemetría. Sube el MP4 a R2.', 'La API de la web. Nunca conecta directo con Supabase.'),
    ('Operador (tablet)', 'Ninguna por ahora: la tablet está en el wifi del propio edge (D34).', 'La copia local de eventos, rutas y plantillas.', 'El correo del invitado, la orden de Go, y corregir un correo para reenviar.', 'El panel del operador, servido por el edge.'),
    ('Administrador', 'Correo y contraseña con Supabase Auth.', 'Todo: eventos, sesiones, invitados, envíos y videos.', 'Eventos, plantillas, música, rutas, retención; corrige correos y reenvía.', 'El panel de administración de la web.'),
    ('Invitado', 'Ninguna. Solo conoce el `share_code` de su enlace.', 'Una sola sesión, la suya: el video. Nada más.', 'Nada.', 'La página /v/{share_code}. El video sale de R2.'),
    ('Servidor de la web', 'La clave de servicio de Supabase, guardada como variable de entorno del servidor.', 'Todo, pero aplica las reglas antes de responder.', 'Todo, tras validar quién llama.', 'Solo corre en el servidor; nunca llega al navegador.'),
]
cols = [(16, 150), (182, 270), (468, 290), (774, 240), (1030, 266)]
body = ''
for (cx, cw), lab in zip(cols, ['Quién', 'Cómo se identifica', 'Qué puede leer', 'Qué puede escribir', 'Por dónde pasa']):
    body += label(64 + cx, 168, lab)
y = 196
for row in ROWS:
    raws = [('**%s**' % row[0])] + list(row[1:])
    hs = [text(0, 0, w, r, 14, 20)[1] for (_, w), r in zip(cols, raws)]
    rh = max(hs) + 24
    inner = ''
    for (cx, w), raw in zip(cols, raws):
        t, h = text(cx, 12, w, raw, 14, 20)
        inner += t
    body += box(64, y, 1312, rh, inner)
    y += rh + 8
pr = ('**Principios**\nRLS activado en todas las tablas y ninguna política abierta al público.\nEl navegador nunca habla con Supabase: todo pasa por la web.\nLa clave de servicio vive solo en las variables de entorno de Vercel, nunca en el repositorio.\nEl token de R2 vive en el `.env` del edge, que Git ignora, y se limita al bucket.\n**Pospuesto durante las pruebas (D34):** protección de la red local del edge y capa de seguridad de Cloudflare para las URLs compartidas. El panel del operador no tiene login, así que cualquier dispositivo en el wifi del edge podría pulsar Go: es un riesgo aceptado mientras se prueba y hay que revisarlo antes de operar con público.')
t, h = text(64 + 16, y + 20 + 14, 1312 - 32, pr, 14, 20)
body += box(64, y + 20, 1312, h + 28, t, bg='#e9edfa', border='1px solid #bac6eb')
H_ACCESO = y + 20 + h + 28 + 56
save('Datos_Acceso.dc.html', 'Quién accede a qué', 1440, H_ACCESO, body,
     'Quién puede leer y escribir cada cosa, y por dónde pasa. Es la propuesta de la capa de datos para la fase de pruebas.')

# ---------- canvas.json ----------
cj = json.load(open('%s/canvas.json' % PROJ, encoding='utf-8'))
new_order = [
    ('Datos_Modelo.dc.html', 'Modelo de datos', H_MODELO),
    ('Datos_Glosario.dc.html', 'Glosario de datos', H_GLOSARIO),
    ('Datos_Columnas1.dc.html', 'Columnas: eventos e invitados', sizes['Datos_Columnas1.dc.html'][1]),
    ('Datos_Columnas2.dc.html', 'Columnas: la sesión', sizes['Datos_Columnas2.dc.html'][1]),
    ('Datos_Columnas3.dc.html', 'Columnas: rutas, plantillas y música', sizes['Datos_Columnas3.dc.html'][1]),
    ('Datos_Columnas4.dc.html', 'Columnas: equipos, correos y telemetría', sizes['Datos_Columnas4.dc.html'][1]),
    ('Datos_Uso.dc.html', 'Cómo se usa', H_USO),
    ('Datos_Limpieza.dc.html', 'Limpieza diaria', H_LIMPIEZA),
    ('Datos_Acceso.dc.html', 'Quién accede a qué', H_ACCESO),
]
for name in [k for k in cj['boards'] if k.startswith('Datos_')]:
    del cj['boards'][name]
cj['order'] = [n for n in cj['order'] if not n.startswith('Datos_')]
y = 0
for i in range(0, len(new_order), 2):
    row = new_order[i:i + 2]
    for j, (name, title, h) in enumerate(row):
        cj['boards'][name] = {'x': j * 1520, 'y': y, 'w': 1440, 'h': h, 'title': title, 'page': 'page-datos'}
        cj['order'].append(name)
    y += max(h for _, _, h in row) + 120
json.dump(cj, open('%s/canvas.json' % PROJ, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print(sizes)
