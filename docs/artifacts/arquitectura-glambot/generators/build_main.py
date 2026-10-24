import sys

OUT = sys.argv[1]

TEAL = '#0e7c86'
TEAL_TXT = '#0b6670'
BLUE = '#4c62c7'
BLUE_TXT = '#3a4a85'
RED = '#b42318'
RED_TXT = '#7a1f16'
GRAY = '#5b6b7a'
GRAY_TXT = '#4a5866'
DARK = '#1f2a36'
INK = '#14202b'

els_zones = []
els_lines = []
els_boxes = []
els_labels = []
_mid = [0]


def zone(x, y, w, h, bg, border, radius=16):
    els_zones.append('<div style="position: absolute; left: %dpx; top: %dpx; width: %dpx; height: %dpx; box-sizing: border-box; background: %s; border: %s; border-radius: %dpx"></div>' % (x, y, w, h, bg, border, radius))


def zlabel(x, y, text, color):
    els_labels.append('<div style="position: absolute; left: %dpx; top: %dpx; font-size: 12px; line-height: 16px; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; color: %s">%s</div>' % (x, y, color, text))


def small(x, y, w, lines, color):
    els_labels.append('<div style="position: absolute; left: %dpx; top: %dpx; width: %dpx; font-size: 12px; line-height: 16px; color: %s">%s</div>' % (x, y, w, color, '<br>'.join(lines)))


def box(x, y, w, h, lines, bg='#ffffff', border='1px solid #b8c4cf', color=INK, radius=10):
    els_boxes.append('<div style="position: absolute; left: %dpx; top: %dpx; width: %dpx; height: %dpx; box-sizing: border-box; padding: 8px; display: flex; align-items: center; justify-content: center; text-align: center; font-size: 14px; line-height: 20px; background: %s; border: %s; border-radius: %dpx; color: %s"><span>%s</span></div>' % (x, y, w, h, bg, border, radius, color, '<br>'.join(lines)))


def tech(t, color=GRAY_TXT):
    return '<span style="color: %s">[%s]</span>' % (color, t)


def person(x, y, name, techt, desc):
    w, h = 240, 96
    hx = x + w // 2 - 16
    els_boxes.append('<div style="position: absolute; left: %dpx; top: %dpx; width: 32px; height: 32px; box-sizing: border-box; background: #dde4f7; border: 1px solid #7f91cf; border-radius: 50%%"></div>' % (hx, y - 32))
    box(x, y, w, h, ['<b>%s</b>' % name, tech(techt, BLUE_TXT), desc], bg='#dde4f7', border='1px solid #7f91cf', radius=20)


def label(x, y, w, lines, color, align='left'):
    els_labels.append('<div style="position: absolute; left: %dpx; top: %dpx; width: %dpx; text-align: %s; font-size: 13px; line-height: 16px; color: %s">%s</div>' % (x, y, w, align, color, '<br>'.join(lines)))


def line(pts, color, dash=None, marker=True):
    pts = [list(p) for p in pts]
    if marker:
        (x1, y1), (x2, y2) = pts[-2], pts[-1]
        if x1 == x2:
            pts[-1][1] = y2 - 4 if y2 > y1 else y2 + 4
        else:
            pts[-1][0] = x2 - 4 if x2 > x1 else x2 + 4
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    left, top = min(xs) - 4, min(ys) - 4
    w, h = max(xs) - min(xs) + 8, max(ys) - min(ys) + 8
    d = ' '.join(('M' if i == 0 else 'L') + ' %d %d' % (p[0] - left, p[1] - top) for i, p in enumerate(pts))
    dash_css = 'stroke-dasharray: %s; ' % dash if dash else ''
    mk = me = ''
    if marker:
        _mid[0] += 1
        mid = 'dc-arrow-head-filled-%d' % _mid[0]
        mk = '<defs><marker id="%s" orient="auto" markerWidth="5" markerHeight="5" refX="2" refY="2" overflow="visible"><path d="M0 0 L4 2 L0 4 Z" fill="%s" stroke="none" style="stroke: none; fill: %s; fill: context-stroke"/></marker></defs>' % (mid, color, color)
        me = ' marker-end="url(#%s)"' % mid
    els_lines.append('<svg width="%d" height="%d" viewBox="0 0 %d %d" preserveAspectRatio="none" style="position: absolute; left: %dpx; top: %dpx; width: %dpx; height: %dpx; overflow: visible; fill: none; stroke: %s; stroke-width: 2; %sstroke-linecap: round; stroke-linejoin: round">%s<path d="%s"%s></path></svg>' % (w, h, w, h, left, top, w, h, color, dash_css, mk, d, me))


DASH = '6 6'
DOT = '1 6'

# ---------------- Rejilla ----------------
BH = 104
R0 = 264
EZ_TOP = 184
EDGE_TOP = 368
R1 = 416
R2 = R1 + BH + 64
R3 = R2 + BH + 64
R4 = R3 + BH + 80
EDGE_BOT = R4 + BH + 32
R5 = EDGE_BOT + 40
EZ_BOT = R5 + BH + 32
GAPY = EZ_BOT + 56
CL_TOP = EZ_BOT + 112
C1 = CL_TOP + 80
VER_BOT = C1 + BH + 32
PG_TOP = VER_BOT + 48
C2 = PG_TOP + 48
CF_BOT = C2 + BH + 32
PB = CF_BOT + 72
M = lambda r: r + BH // 2

# ---------------- Límites ----------------
zone(64, EZ_TOP, 1280, EZ_BOT - EZ_TOP, '#e8eef3', '1px solid #c5d0da', 18)
zlabel(88, EZ_TOP + 16, 'Zona del evento · opera con el cable de red desconectado', '#3d4b58')
zone(408, EDGE_TOP, 592, EDGE_BOT - EDGE_TOP, '#f8fafc', '2px solid %s' % TEAL, 14)
zlabel(424, EDGE_TOP + 16, 'Edge · mini PC junto al robot (laptop por ahora) · [Python]', TEAL_TXT)

zone(64, CL_TOP, 968, VER_BOT - CL_TOP, '#e9edfa', '1px solid #bac6eb')
zlabel(88, CL_TOP + 16, 'Vercel · Astro (D27)', BLUE_TXT)
small(88, CL_TOP + 36, 176, ['glam.datzoncompany.com'], BLUE_TXT)

zone(1064, CL_TOP, 280, CF_BOT - CL_TOP, '#eef1fb', '1px solid #bac6eb')
zlabel(1080, CL_TOP + 16, 'Cloudflare', BLUE_TXT)
small(1080, CL_TOP + 36, 184, ['cuenta institucional (D26)', 'dominio: DNS en Cloudflare'], BLUE_TXT)

zone(408, PG_TOP, 280, CF_BOT - PG_TOP, '#eef1fb', '1px solid #bac6eb')
zlabel(424, PG_TOP + 16, 'Supabase (D28)', BLUE_TXT)

# ---------------- Zona del evento ----------------
person(96, R0, 'Operador', 'Persona', 'pide toma y registra correo')
els_boxes.append('<div style="position: absolute; left: 736px; top: 232px; width: 576px; height: 88px; box-sizing: border-box; padding: 12px; font-size: 14px; line-height: 20px; background: #fdecea; border: 1px solid #f0b8b2; border-radius: 10px; color: %s"><b>El software no es la seguridad.</b> Protegen a las personas el paro de emergencia cableado y la parada automática del controlador. (D10)</div>' % RED_TXT)

HW = dict(bg=DARK, border='none', color='#ffffff')
TECH_HW = '#c9d3dc'
box(96, R1, 184, BH, ['<b>Tablet del operador</b>', tech('Navegador', TECH_HW), 'HTML plano por el wifi', 'del propio edge'], **HW)
box(96, R3, 184, BH, ['<b>GoPro HERO10</b>', tech('Cámara · USB', TECH_HW), 'graba y guarda el clip'], **HW)
box(1128, R3, 184, BH, ['<b>Brazo FAIRINO FR10</b>', tech('Controlador con Lua', TECH_HW), 'ejecuta la primitiva y', 'valida sus límites'], **HW)
box(1128, R4, 184, BH, ['<b>Paro de emergencia</b>', tech('Cableado', RED_TXT), 'fuera del software'], bg='#ffffff', border='2px solid %s' % RED, color=RED_TXT)
box(760, R5, 184, BH, ['<b>Router 4G/5G</b>', tech('Chip propio · D24', TECH_HW), 'solo para subir, aparte', 'de la red del edge'], **HW)

box(440, R1, 224, BH, ['<b>server/</b>', tech('Python · HTTP local'), 'operador, Studio de rutas,', 'QR, respaldo local y PWA'])
box(440, R2, 528, BH, ['<b>session/</b>', tech('Python') + ' · máquina de estados de la toma (D16)', 'un candado · idempotente por session_id · una toma a la vez', '<b style="color: %s">el brazo no se mueve hasta que la cámara confirma que graba</b>' % TEAL_TXT], border='2px solid %s' % TEAL)
box(440, R3, 224, BH, ['<b>camera/</b>', tech('Python · Open GoPro, USB'), 'graba, confirma que graba', 'y descarga el clip'])
box(744, R3, 224, BH, ['<b>robot/</b>', tech('Python · SDK FAIRINO'), 'invoca primitivas Lua y', 'lee el estado del robot'])
box(440, R4, 224, BH, ['<b>render/</b>', tech('Python · ffmpeg'), 'aplica la plantilla;', 'un archivo final por toma'])
box(744, R4, 224, BH, ['<b>uploader/</b>', tech('Python'), 'cola con reintentos,', 'persistente entre reinicios'])

line([(188, R0 + 96), (188, R1)], GRAY)
label(196, R0 + 96 + 16, 40, ['usa'], GRAY_TXT)
line([(280, M(R1) - 8), (440, M(R1) - 8)], GRAY)
label(288, M(R1) - 8 - 36, 112, ['abre la interfaz', '[HTTP · wifi]'], GRAY_TXT, 'center')
line([(552, R1 + BH), (552, R2)], TEAL)
label(560, R1 + BH + 24, 96, ['1 · pide toma'], TEAL_TXT)
line([(520, R2 + BH), (520, R3)], TEAL)
label(448, R2 + BH + 24, 64, ['2 · graba'], TEAL_TXT, 'right')
line([(600, R3), (600, R2 + BH)], TEAL)
label(608, R2 + BH + 24, 88, ['3 · ya graba'], TEAL_TXT)
line([(824, R2 + BH), (824, R3)], TEAL)
label(752, R2 + BH + 24, 64, ['4 · mueve'], TEAL_TXT, 'right')
line([(904, R3), (904, R2 + BH)], TEAL)
label(912, R2 + BH + 24, 80, ['5 · termina'], TEAL_TXT)
line([(440, M(R3)), (280, M(R3))], GRAY)
label(288, M(R3) - 36, 112, ['controla', '[USB]'], GRAY_TXT, 'center')
line([(968, M(R3)), (1128, M(R3))], GRAY)
label(1008, M(R3) - 36, 116, ['invoca primitivas', '[SDK]'], GRAY_TXT, 'center')
line([(552, R3 + BH), (552, R4)], TEAL)
label(560, R3 + BH + 32, 136, ['6 · descarga el clip'], TEAL_TXT)
line([(664, M(R4)), (744, M(R4))], TEAL)
label(668, M(R4) - 24, 72, ['7 · final'], TEAL_TXT, 'center')
line([(1160, R4), (1160, R3 + BH)], RED, DASH)
label(1168, R3 + BH + 24, 136, ['detiene el brazo', 'no pasa por el edge'], RED_TXT)
line([(856, R4 + BH), (856, R5)], BLUE, DASH)
label(864, EDGE_BOT + 12, 64, ['8 · sube'], BLUE_TXT)

# ---------------- Nube ----------------
CLOUD = dict(border='1px solid #9eaedd')
TBD = dict(border='1.5px dotted %s' % BLUE)
box(96, C1, 216, BH, ['<b>Panel de administración</b>', tech('Astro'), 'eventos, plantillas, rutas', 'y videos (solo la empresa)'], **CLOUD)
box(440, C1, 216, BH, ['<b>API de sesiones</b>', tech('Astro · endpoints'), 'recibe tomas e invitados', 'y pide los correos'], **CLOUD)
box(784, C1, 216, BH, ['<b>Página del invitado</b>', tech('Astro'), 've, descarga y comparte', 'su video'], **CLOUD)
box(1096, C1, 216, BH, ['<b>Bucket de videos</b>', tech('Cloudflare R2'), 'recibe el MP4 y lo sirve', 'con limpieza diaria'], **CLOUD)
box(1096, C2, 216, BH, ['<b>Capa de seguridad</b>', tech('Cloudflare · fase final'), 'pospuesta (D34), delante', 'de las URLs compartidas'], **TBD)
box(440, C2, 216, BH, ['<b>Base de datos</b>', tech('Postgres'), 'eventos, invitados,', 'sesiones y rutas'], **CLOUD)
box(712, C2, 200, BH, ['<b>Servicio de correo</b>', tech('Resend · por configurar'), 'envía el enlace', 'al correo del invitado'], **TBD)

line([(280, C1), (280, GAPY), (472, GAPY), (472, R4 + BH)], BLUE, DASH)
label(480, R5 + 16, 224, ['evento, plantillas y rutas,', 'antes del evento [HTTPS]'], BLUE_TXT)
line([(784, R5 + BH), (784, GAPY), (624, GAPY), (624, C1)], BLUE, DASH)
label(592, GAPY - 36, 184, ['sube tomas, invitados', 'y reenvíos [HTTPS]'], BLUE_TXT, 'right')
line([(920, R5 + BH), (920, GAPY), (1280, GAPY), (1280, C1)], BLUE, DASH)
label(936, GAPY - 20, 184, ['sube el video final [HTTPS]'], BLUE_TXT)
line([(656, M(C1)), (784, M(C1))], BLUE)
label(664, M(C1) - 40, 112, ['sirve los datos', 'de la toma'], BLUE_TXT, 'center')
line([(576, C1 + BH), (576, C2)], BLUE, DASH)
label(448, VER_BOT + 8, 120, ['guarda tomas', '[SQL]'], BLUE_TXT, 'right')
line([(280, C1 + BH), (280, M(C2)), (440, M(C2))], BLUE, DASH)
label(160, VER_BOT + 16, 112, ['lee y guarda', '[SQL]'], BLUE_TXT, 'right')
line([(640, C1 + BH), (640, VER_BOT + 24), (812, VER_BOT + 24), (812, C2)], BLUE, DASH)
label(664, VER_BOT + 3, 180, ['envía el enlace [HTTPS]'], BLUE_TXT)
line([(1204, C1 + BH), (1204, C2)], BLUE)
label(1212, C1 + BH + 40, 88, ['sirve el MP4'], BLUE_TXT)

# ---------------- Personas ----------------
person(96, PB, 'Administrador', 'Persona · navegador', 'gestiona todo el sistema')
person(928, PB, 'Invitado', 'Persona · con su celular', 'recibe el enlace y ve su video')

line([(128, PB), (128, C1 + BH)], BLUE, DASH)
label(136, CF_BOT - 24, 120, ['gestiona todo', '[HTTPS]'], BLUE_TXT)
line([(812, C2 + BH), (812, M(PB)), (928, M(PB))], BLUE, DASH)
label(820, C2 + BH + 24, 104, ['recibe el', 'enlace'], BLUE_TXT)
line([(1136, C2 + BH), (1136, PB)], BLUE)
label(1144, CF_BOT + 12, 152, ['entrega el MP4 [HTTPS]'], BLUE_TXT)
line([(960, PB), (960, C1 + BH)], BLUE)
label(966, C2, 94, ['abre el enlace', 'o el QR', '[HTTPS]'], BLUE_TXT)
line([(1168, M(PB) - 4), (1392, M(PB) - 4), (1392, M(R1) + 24), (664, M(R1) + 24)], TEAL, DOT)
label(1016, M(R1) + 24 - 52, 216, ['celular del invitado: abre la', 'página local de respaldo sin', 'internet [HTTP · wifi] (D21)'], TEAL_TXT)

# ---------------- Leyenda ----------------
LY = PB + 96 + 56
leg = []
leg.append('<div style="position: absolute; left: 64px; top: %dpx; width: 1280px; height: 232px; box-sizing: border-box; background: #ffffff; border: 1px solid #c5d0da; border-radius: 16px"></div>' % LY)
zl_leg = '<div style="position: absolute; left: %dpx; top: %dpx; font-size: 12px; line-height: 16px; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; color: #3d4b58">%s</div>'
leg.append(zl_leg % (88, LY + 16, 'Leyenda · formas'))
leg.append(zl_leg % (536, LY + 16, 'Leyenda · líneas'))
leg.append(zl_leg % (984, LY + 16, 'Notación'))


def lt(x, y, text):
    leg.append('<div style="position: absolute; left: %dpx; top: %dpx; width: 376px; font-size: 13px; line-height: 20px; color: %s">%s</div>' % (x, y, INK, text))


def sw(x, y, css):
    leg.append('<div style="position: absolute; left: %dpx; top: %dpx; width: 40px; height: 20px; box-sizing: border-box; %s"></div>' % (x, y, css))


rows = [LY + 48 + 28 * i for i in range(6)]
sw(88, rows[0], 'background: %s; border-radius: 4px' % DARK)
lt(144, rows[0], 'Hardware físico')
sw(88, rows[1], 'background: #ffffff; border: 1px solid #b8c4cf; border-radius: 4px')
lt(144, rows[1], 'Módulo del edge [Python]')
sw(88, rows[2], 'background: #ffffff; border: 1px solid #9eaedd; border-radius: 4px')
lt(144, rows[2], 'Sistema o servicio en la nube')
leg.append('<div style="position: absolute; left: 102px; top: %dpx; width: 12px; height: 8px; box-sizing: border-box; background: #dde4f7; border: 1px solid #7f91cf; border-radius: 50%%"></div>' % rows[3])
sw(88, rows[3] + 8, 'height: 12px; background: #dde4f7; border: 1px solid #7f91cf; border-radius: 6px')
lt(144, rows[3], 'Persona o dispositivo propio')
sw(88, rows[4], 'background: #ffffff; border: 1.5px dotted %s; border-radius: 4px' % BLUE)
lt(144, rows[4], 'Por definir o por registrar en Notion')
sw(88, rows[5], 'background: #e8eef3; border: 1px solid #c5d0da; border-radius: 6px')
lt(144, rows[5], 'Límite de despliegue, con su nombre arriba')


def lsw(x, y, color, dash=None):
    d = 'stroke-dasharray: %s; ' % dash if dash else ''
    leg.append('<svg width="40" height="8" viewBox="0 0 40 8" preserveAspectRatio="none" style="position: absolute; left: %dpx; top: %dpx; width: 40px; height: 8px; overflow: visible; fill: none; stroke: %s; stroke-width: 2; %sstroke-linecap: round; stroke-linejoin: round"><path d="M 2 4 L 38 4"></path></svg>' % (x, y + 6, color, d))


lsw(536, rows[0], TEAL)
lt(592, rows[0], 'Camino crítico de la toma, sin internet (pasos 1 a 7)')
lsw(536, rows[1], TEAL, DOT)
lt(592, rows[1], 'Respaldo local sin internet, no es el camino principal')
lsw(536, rows[2], BLUE, DASH)
lt(592, rows[2], 'Con la nube, después y con reintentos (paso 8)')
lsw(536, rows[3], BLUE)
lt(592, rows[3], 'Lectura del invitado')
lsw(536, rows[4], RED, DASH)
lt(592, rows[4], 'Seguridad física, fuera del software')
lsw(536, rows[5], GRAY)
lt(592, rows[5], 'Uso y conexión local con el hardware')

leg.append('<div style="position: absolute; left: 984px; top: %dpx; width: 336px; font-size: 13px; line-height: 20px; color: %s">Modelo C4 (Simon Brown), nivel 2: contenedores con límites de despliegue.<br>Caja: <b>nombre</b>, [tecnología] y responsabilidad.<br>Flecha: verbo y [protocolo] si se conoce; apunta en el sentido de los datos.<br>D#: decisión registrada en Notion.</div>' % (LY + 48, INK))

H = LY + 232 + 64

head = '''<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>Arquitectura general del glambot</title>
<script src="./support.js"></script>
</head>
<body>
<x-dc>
<helmet>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600;700&amp;display=swap" rel="stylesheet">
<style>
body{margin:0}
</style>
</helmet>
<div style="position: relative; width: 1440px; height: %dpx; background: #f3f6f8; font-family: 'IBM Plex Sans', system-ui, sans-serif; color: #14202b">
''' % H

title = '''<div style="position: absolute; left: 64px; top: 64px; font-size: 30px; line-height: 36px; font-weight: 700">Arquitectura del glambot FR10</div>
<div style="position: absolute; left: 64px; top: 108px; width: 860px; font-size: 15px; line-height: 22px; color: #4a5866">Un nodo edge junto al robot orquesta cada toma sin depender de internet. La web en la nube envía el enlace por correo y entrega el video con lo que el edge le sube después.</div>
<div style="position: absolute; left: 984px; top: 72px; width: 360px; text-align: right; font-size: 13px; line-height: 20px; color: #4a5866">Notación: modelo C4, nivel Contenedores<br>con límites de despliegue · leyenda abajo</div>'''

tail = '''</div>
</x-dc>
<script type="text/x-dc" data-dc-script data-props='{"$preview":{"width":1440,"height":%d}}'>
class Component extends DCLogic {
renderVals() {
return {};
}
}
</script>
</body>
</html>
''' % H

body = '\n'.join(els_zones) + '\n\n' + '\n'.join(els_lines) + '\n\n' + '\n'.join(els_boxes) + '\n\n' + title + '\n\n' + '\n'.join(els_labels) + '\n\n' + '\n'.join(leg) + '\n\n'
open(OUT, 'w', encoding='utf-8').write(head + '\n' + body + tail)
print('height', H, 'markers', _mid[0])
