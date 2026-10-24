import json, re, sys

PROJ = None
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


