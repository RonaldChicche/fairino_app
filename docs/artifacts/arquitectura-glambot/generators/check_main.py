import math
import re
import sys

src = open(sys.argv[1], encoding='utf-8').read()

m = re.search(r'position: relative; width: (\d+)px; height: (\d+)px', src)
W, H = int(m.group(1)), int(m.group(2))
pm = re.search(r'"\$preview":\{"width":(\d+),"height":(\d+)\}', src)
errors, warns = [], []
if (int(pm.group(1)), int(pm.group(2))) != (W, H):
    errors.append('preview %s,%s distinto del contenedor %s,%s' % (pm.group(1), pm.group(2), W, H))

for must in ['<!doctype html>', '<meta charset="utf-8">', '<script src="./support.js"></script>', '<x-dc>', '<helmet>', 'IBM+Plex+Sans', 'class Component extends DCLogic', 'renderVals()']:
    if must not in src:
        errors.append('falta en el archivo: %s' % must)
ids = re.findall(r'<marker id="([^"]+)"', src)
if len(ids) != len(set(ids)):
    errors.append('ids de marker repetidos')
for ref in re.findall(r'marker-end="url\(#([^)]+)\)"', src):
    if ref not in ids:
        errors.append('marker-end sin definir: %s' % ref)
if src.count('<div') != src.count('</div>'):
    errors.append('divs sin cerrar: %d abiertos, %d cerrados' % (src.count('<div'), src.count('</div>')))
if src.count('<svg') != src.count('</svg>'):
    errors.append('svg sin cerrar')
if re.search(r'[\U0001F300-\U0001FAFF☀-➿]', src):
    errors.append('hay emojis')


def px(style, key):
    mm = re.search(r'(?<![-\w])' + key + r': (-?\d+(?:\.\d+)?)px', style)
    return float(mm.group(1)) if mm else None


def strip(s):
    return re.sub(r'<[^>]+>', '', s).replace('&amp;', '&')


def char_w(style, bold=False):
    fs = px(style, 'font-size') or 14
    upper = 'uppercase' in style
    if fs >= 30:
        return 16.0
    if upper:
        return 8.2
    if fs == 12:
        return 6.2
    if fs == 13:
        return 6.5
    if fs == 15:
        return 7.6
    return 7.8 if bold else 7.2


zones, boxes, decos, labels = [], [], [], []
for style, inner in re.findall(r'<div style="([^"]*)">(.*?)</div>', src, re.S):
    if 'position: absolute' not in style:
        continue
    x, y, w, h = px(style, 'left'), px(style, 'top'), px(style, 'width'), px(style, 'height')
    text = strip(inner).strip()
    if not text:
        rect = (x, y, w, h)
        (zones if (w >= 200 and h >= 100) else decos).append((rect, style))
        continue
    lines = [l for l in re.split(r'<br\s*/?>', inner)]
    lh = px(style, 'line-height') or 20
    pad = px(style, 'padding') or 0
    if h is not None:
        bw = 0
        bm = re.search(r'border: (\d+(?:\.\d+)?)px', style)
        if bm:
            bw = float(bm.group(1))
        avail_w = w - 2 * pad - 2 * bw
        if 'display: flex' in style:
            nlines = 0
            for l in lines:
                bold = l.strip().startswith('<b') or l.strip().startswith('<span><b')
                est = len(strip(l)) * char_w(style, bold)
                if est > avail_w:
                    errors.append('texto no cabe a lo ancho (%.0f > %.0f): "%s"' % (est, avail_w, strip(l)))
                nlines += 1
        else:
            nlines = sum(max(1, math.ceil(len(strip(l)) * char_w(style) / avail_w)) for l in lines)
        if nlines * lh > h - 2 * pad - 2 * bw:
            errors.append('texto no cabe a lo alto (%d líneas en %s): "%s"' % (nlines, h, text[:40]))
        boxes.append(((x, y, w, h), text))
    else:
        cw = char_w(style, 'font-weight: 600' in style or 'font-weight: 700' in style)
        ests = [len(strip(l)) * cw for l in lines]
        wrap_ok = lh >= 20
        if w is None:
            w = max(ests)
            nlines = len(lines)
        else:
            if wrap_ok:
                nlines = sum(max(1, math.ceil(e / w)) for e in ests)
            else:
                nlines = len(lines)
                for e, l in zip(ests, lines):
                    if e > w:
                        errors.append('etiqueta no cabe (%.0f > %.0f): "%s"' % (e, w, strip(l)))
        labels.append(((x, y, w, nlines * lh), text, lh < 20 and px(style, 'font-size') == 13))

lines_ = []
for style, inner in re.findall(r'<svg [^>]*?style="([^"]*)"[^>]*>(.*?)</svg>', src, re.S):
    lx, ly = px(style, 'left'), px(style, 'top')
    for d in re.findall(r'<path d="([^"]+)"', inner):
        if 'Z' in d:
            continue
        nums = list(map(float, re.findall(r'-?\d+(?:\.\d+)?', d)))
        pts = [(lx + nums[i], ly + nums[i + 1]) for i in range(0, len(nums), 2)]
        lines_.append((pts, 'marker-end' in inner, style))


def inter(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return min(ax + aw, bx + bw) - max(ax, bx) > 0 and min(ay + ah, by + bh) - max(ay, by) > 0


def contains(o, i):
    return o[0] <= i[0] and o[1] <= i[1] and i[0] + i[2] <= o[0] + o[2] and i[1] + i[3] <= o[1] + o[3]


def name(t):
    return t[:28]


items = [(r, 'caja: ' + name(t)) for r, t in boxes] + [(r, 'deco') for r, _ in decos] + [(r, 'etiqueta: ' + name(t)) for r, t, _ in labels]

for r, n in items + [(z, 'zona') for z, _ in zones]:
    x, y, w, h = r
    if x < 0 or y < 0 or x + w > W or y + h > H:
        errors.append('fuera del tablero: %s %s' % (n, r))

for i in range(len(items)):
    for j in range(i + 1, len(items)):
        if inter(items[i][0], items[j][0]):
            errors.append('solape: %s  <->  %s' % (items[i][1], items[j][1]))

for i in range(len(zones)):
    for j in range(i + 1, len(zones)):
        a, b = zones[i][0], zones[j][0]
        if inter(a, b) and not (contains(a, b) or contains(b, a)):
            errors.append('límites que se cruzan: %s %s' % (a, b))
for r, n in items:
    for z, _ in zones:
        if inter(r, z) and not contains(z, r):
            errors.append('pisa el borde de un límite: %s %s' % (n, z))


def seg_rect(p, q, r, shrink=0.0):
    x, y, w, h = r
    x0, y0, x1, y1 = x + shrink, y + shrink, x + w - shrink, y + h - shrink
    if p[0] == q[0]:
        lo, hi = sorted((p[1], q[1]))
        return x0 < p[0] < x1 and lo < y1 and hi > y0
    lo, hi = sorted((p[0], q[0]))
    return y0 < p[1] < y1 and lo < x1 and hi > x0


def segs(pts):
    return list(zip(pts, pts[1:]))


for k, (pts, mk, st) in enumerate(lines_):
    for p, q in segs(pts):
        if p[0] != q[0] and p[1] != q[1]:
            errors.append('línea no ortogonal %s' % pts)
        for r, n in items:
            sh = 1.0 if not n.startswith('etiqueta') else -2.0
            if seg_rect(p, q, r, sh):
                errors.append('línea %d atraviesa %s' % (k, n))
        for z, _ in zones:
            pass
    for pt in pts:
        if pt[0] < 0 or pt[1] < 0 or pt[0] > W or pt[1] > H:
            errors.append('línea fuera del tablero %s' % (pts,))

crossings = []
for a in range(len(lines_)):
    for b in range(a + 1, len(lines_)):
        for p, q in segs(lines_[a][0]):
            for r_, s in segs(lines_[b][0]):
                if p[0] == q[0] and r_[1] == s[1]:
                    v, hz = (p, q), (r_, s)
                elif p[1] == q[1] and r_[0] == s[0]:
                    v, hz = (r_, s), (p, q)
                else:
                    if p[0] == q[0] == r_[0] == s[0] and max(min(p[1], q[1]), min(r_[1], s[1])) < min(max(p[1], q[1]), max(r_[1], s[1])):
                        crossings.append(('solapadas', a, b))
                    if p[1] == q[1] == r_[1] == s[1] and max(min(p[0], q[0]), min(r_[0], s[0])) < min(max(p[0], q[0]), max(r_[0], s[0])):
                        crossings.append(('solapadas', a, b))
                    continue
                vx = v[0][0]
                vlo, vhi = sorted((v[0][1], v[1][1]))
                hy = hz[0][1]
                hlo, hhi = sorted((hz[0][0], hz[1][0]))
                if hlo <= vx <= hhi and vlo <= hy <= vhi:
                    crossings.append(('cruce', a, b, (vx, hy)))


def dist_rect_seg(r, p, q):
    x, y, w, h = r
    best = 1e9
    n = 40
    for i in range(n + 1):
        t = i / n
        sx, sy = p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t
        dx = max(x - sx, 0, sx - (x + w))
        dy = max(y - sy, 0, sy - (y + h))
        best = min(best, math.hypot(dx, dy))
    return best


arrow_lines = [l for l in lines_ if l[1]]
for r, t, is_arrow_label in labels:
    if not is_arrow_label:
        continue
    d = min(dist_rect_seg(r, p, q) for pts, _, _ in arrow_lines for p, q in segs(pts))
    if d > 16:
        warns.append('etiqueta lejos de su flecha (%.0fpx): %s' % (d, name(t)))
    if d < 3:
        warns.append('etiqueta casi tocando una línea (%.0fpx): %s' % (d, name(t)))

box_rects = [r for r, _ in boxes]
for pts, mk, _ in arrow_lines:
    def on_edge(pt, tol_lo, tol_hi):
        for (x, y, w, h) in box_rects:
            for ex in (x, x + w):
                if tol_lo <= abs(pt[0] - ex) <= tol_hi and y <= pt[1] <= y + h:
                    return True
            for ey in (y, y + h):
                if tol_lo <= abs(pt[1] - ey) <= tol_hi and x <= pt[0] <= x + w:
                    return True
        return False
    if not on_edge(pts[0], 0, 1):
        warns.append('flecha que no sale del borde de una caja: %s' % (pts[0],))
    if not on_edge(pts[-1], 3, 5):
        warns.append('flecha que no llega a 4px de una caja: %s' % (pts[-1],))

def grid(v):
    return v is not None and abs(v / 8 - round(v / 8)) < 1e-6
off = [r for r, n in items if n.startswith('caja') and not all(grid(v) for v in r)]
for r in off:
    warns.append('caja fuera de la rejilla de 8px: %s' % (r,))

print('tablero %dx%d · %d límites · %d cajas · %d etiquetas · %d líneas · %d markers' % (W, H, len(zones), len(boxes), len(labels), len(lines_), len(ids)))
for c in crossings:
    print('CRUCE', c)
for w in warns:
    print('AVISO', w)
for e in errors:
    print('ERROR', e)
print('RESULTADO:', 'PASA' if not errors and not crossings else 'FALLA')
sys.exit(1 if errors or crossings else 0)
