#!/usr/bin/env python3
"""Genera un plano cartesiano interactivo y visual en SVG comparando las rutas."""
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / ".venv" / "Lib" / "site-packages"))

from routes import route_from_spec, _add

# Cargar especificaciones
target = (-1500.0, 0.0)

# 1. Puntos Originales (con Y extendido hasta +/-770 y bulge 100mm)
orig_cam = [
    (-1500 + 1100.0, 1000.0),
    (-1500 + 770.0, 770.0),
    (-1500 + 861.0, 663.2),
    (-1500 + 936.7, 550.8),
    (-1500 + 997.1, 432.8),
    (-1500 + 1042.1, 309.3),
    (-1500 + 1071.8, 180.1),
    (-1500 + 1086.2, 45.4),
    (-1500 + 1085.2, -94.9),
    (-1500 + 1084.5, -212.0),
    (-1500 + 1069.1, -322.3),
    (-1500 + 1038.8, -425.6),
    (-1500 + 993.8, -522.1),
    (-1500 + 934.0, -611.6),
    (-1500 + 859.4, -694.3),
    (-1500 + 770.0, -770.0)
]

# 2. Puntos Reducidos Validados
spec_red = json.loads((HERE / "routes" / "ruta-prueba-01.json").read_text(encoding="utf-8"))
cam_red = route_from_spec(spec_red)
red_cam = [(_add(target, wp.offset)[0], _add(target, wp.offset)[1]) for wp in cam_red]

# Parámetros del Canvas
WIDTH = 1100
HEIGHT = 850
SCALE = 0.35  # px por mm
CX = 560      # centro X en px para x_mm = -700
CY = 425      # centro Y en px para y_mm = 0


def to_screen(x_mm, y_mm):
    sx = CX + (x_mm - (-700.0)) * SCALE
    sy = CY - y_mm * SCALE
    return sx, sy


def build_svg():
    lines = []
    lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {HEIGHT}" width="100%" height="100%" style="background-color:#0d1117; font-family:Inter,-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif;">')

    # Defs: gradientes, marcadores de flecha y filtros
    lines.append('''<defs>
      <linearGradient id="origGrad" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stop-color="#ff5252" />
        <stop offset="100%" stop-color="#ff1744" />
      </linearGradient>
      <linearGradient id="redGrad" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stop-color="#00e5ff" />
        <stop offset="100%" stop-color="#00e676" />
      </linearGradient>
      <marker id="arrowRed" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
        <path d="M 0 1 L 10 5 L 0 9 z" fill="#ff5252" />
      </marker>
      <marker id="arrowGreen" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
        <path d="M 0 1 L 10 5 L 0 9 z" fill="#00e5ff" />
      </marker>
      <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
        <feGaussianBlur stdDeviation="3" result="blur" />
        <feComposite in="SourceGraphic" in2="blur" operator="over" />
      </filter>
    </defs>''')

    # Rejilla (Grid de 200 mm)
    lines.append('<g opacity="0.15" stroke="#8b949e" stroke-width="1">')
    for x_val in range(-1600, 400, 200):
        sx, _ = to_screen(x_val, 0)
        lines.append(f'<line x1="{sx:.1f}" y1="50" x2="{sx:.1f}" y2="780" />')
    for y_val in range(-1000, 1200, 200):
        _, sy = to_screen(0, y_val)
        lines.append(f'<line x1="60" y1="{sy:.1f}" x2="1020" y2="{sy:.1f}" />')
    lines.append('</g>')

    # Ejes Cartesianos Principales (X=0 y Y=0 de la base del robot)
    rx_zero, ry_zero = to_screen(0, 0)
    lines.append(f'<line x1="60" y1="{ry_zero:.1f}" x2="1020" y2="{ry_zero:.1f}" stroke="#58a6ff" stroke-width="2" opacity="0.7" />')
    lines.append(f'<line x1="{rx_zero:.1f}" y1="50" x2="{rx_zero:.1f}" y2="780" stroke="#58a6ff" stroke-width="2" opacity="0.7" />')

    # Etiquetas numéricas en los ejes (ticks cada 400 mm)
    lines.append('<g font-size="11" fill="#8b949e" text-anchor="middle">')
    for x_val in range(-1600, 400, 400):
        sx, _ = to_screen(x_val, 0)
        lines.append(f'<text x="{sx:.1f}" y="{ry_zero + 18:.1f}">{x_val}</text>')
        lines.append(f'<line x1="{sx:.1f}" y1="{ry_zero - 4:.1f}" x2="{sx:.1f}" y2="{ry_zero + 4:.1f}" stroke="#58a6ff" stroke-width="2" />')
    for y_val in range(-1000, 1200, 400):
        if y_val == 0:
            continue
        _, sy = to_screen(0, y_val)
        lines.append(f'<text x="{rx_zero - 22:.1f}" y="{sy + 4:.1f}">{y_val:+d}</text>')
        lines.append(f'<line x1="{rx_zero - 4:.1f}" y1="{sy:.1f}" x2="{rx_zero + 4:.1f}" y2="{sy:.1f}" stroke="#58a6ff" stroke-width="2" />')
    lines.append(f'<text x="1010" y="{ry_zero - 10:.1f}" font-weight="bold" fill="#58a6ff">X (mm)</text>')
    lines.append(f'<text x="{rx_zero + 15:.1f}" y="65" font-weight="bold" fill="#58a6ff">Y (mm)</text>')
    lines.append('</g>')

    # Alcance máximo del FR10 (Círculo de radio 1400 mm)
    reach_r = 1400.0 * SCALE
    lines.append(f'<circle cx="{rx_zero:.1f}" cy="{ry_zero:.1f}" r="{reach_r:.1f}" fill="none" stroke="#f0883e" stroke-width="1.5" stroke-dasharray="8 6" opacity="0.4" />')
    lines.append(f'<text x="{rx_zero - reach_r + 20:.1f}" y="{ry_zero - 15:.1f}" fill="#f0883e" font-size="11" opacity="0.6">Límite de alcance FR10 (R=1400 mm)</text>')

    # Radio de distancia focal constante desde el objetivo (R ≈ 1090 mm)
    tx, ty = to_screen(-1500, 0)
    focus_r = 1089.6 * SCALE
    lines.append(f'<circle cx="{tx:.1f}" cy="{ty:.1f}" r="{focus_r:.1f}" fill="none" stroke="#7ee787" stroke-width="1" stroke-dasharray="3 4" opacity="0.3" />')

    # Marcador: Robot Base (0, 0)
    lines.append(f'''<g transform="translate({rx_zero:.1f}, {ry_zero:.1f})">
      <circle r="12" fill="#1f6feb" opacity="0.3" />
      <circle r="6" fill="#58a6ff" />
      <text x="15" y="-12" fill="#58a6ff" font-size="13" font-weight="bold">Base Robot FR10 (0, 0)</text>
    </g>''')

    # Marcador: Objetivo (-1500, 0)
    lines.append(f'''<g transform="translate({tx:.1f}, {ty:.1f})">
      <circle r="18" fill="none" stroke="#f85149" stroke-width="1.5" stroke-dasharray="4 2" />
      <circle r="10" fill="none" stroke="#f85149" stroke-width="1.5" />
      <circle r="4" fill="#f85149" />
      <line x1="-22" y1="0" x2="22" y2="0" stroke="#f85149" stroke-width="1.5" />
      <line x1="0" y1="-22" x2="0" y2="22" stroke="#f85149" stroke-width="1.5" />
      <text x="-15" y="-26" fill="#f85149" font-size="13" font-weight="bold" text-anchor="middle">Objetivo / Sujeto (-1500, 0)</text>
    </g>''')

    # 1. Trazo de la Ruta Original (En Rojo discontinua)
    orig_path_d = []
    for idx, (x, y) in enumerate(orig_cam):
        sx, sy = to_screen(x, y)
        orig_path_d.append(f"{'M' if idx == 0 else 'L'} {sx:.1f} {sy:.1f}")
    lines.append(f'<path d="{" ".join(orig_path_d)}" fill="none" stroke="#ff5252" stroke-width="2.5" stroke-dasharray="6 4" opacity="0.65" />')

    # Puntos de la Ruta Original
    for idx, (x, y) in enumerate(orig_cam):
        sx, sy = to_screen(x, y)
        if idx in [0, 1, 8, 15]:  # Waypoints clave
            labels = {0: "Orig WP2 (+1000 Y)", 1: "Orig WP3 (+770 Y)", 8: "Orig WP4 (-95 Y)", 15: "Orig WP5 (-770 Y)"}
            lines.append(f'<circle cx="{sx:.1f}" cy="{sy:.1f}" r="5" fill="#ff5252" />')
            lines.append(f'<text x="{sx + 10:.1f}" y="{sy + 4:.1f}" fill="#ff7b72" font-size="10" opacity="0.9">{labels[idx]}</text>')

    # Marcador de singularidad en la ruta original (P7: x=-314, y=49.6 donde J5=2.9°)
    sing_sx, sing_sy = to_screen(-314.0, 49.6)
    lines.append(f'''<g transform="translate({sing_sx:.1f}, {sing_sy:.1f})">
      <circle r="9" fill="#ff1744" filter="url(#glow)" opacity="0.8" />
      <circle r="4" fill="#ffffff" />
      <line x1="12" y1="0" x2="70" y2="-25" stroke="#ff1744" stroke-width="1.5" />
      <rect x="72" y="-45" width="220" height="38" rx="5" fill="#21262d" stroke="#ff1744" stroke-width="1.5" />
      <text x="80" y="-28" fill="#ff7b72" font-size="11" font-weight="bold">❌ Singularidad Muñeca J5 ≈ 2.9°</text>
      <text x="80" y="-13" fill="#8b949e" font-size="10">Error IK 112 / Giro J4 &gt; 200°</text>
    </g>''')

    # 2. Trazo de la Ruta Reducida (En Cyan/Verde continuo con resplandor)
    red_path_d = []
    for idx, (x, y) in enumerate(red_cam):
        sx, sy = to_screen(x, y)
        red_path_d.append(f"{'M' if idx == 0 else 'L'} {sx:.1f} {sy:.1f}")
    lines.append(f'<path d="{" ".join(red_path_d)}" fill="none" stroke="url(#redGrad)" stroke-width="4" filter="url(#glow)" opacity="0.9" />')

    # Flechas de dirección en la ruta reducida
    p_mid1_x, p_mid1_y = to_screen(red_cam[5][0], red_cam[5][1])
    p_mid2_x, p_mid2_y = to_screen(red_cam[11][0], red_cam[11][1])

    # Puntos de la Ruta Reducida
    for idx, (x, y) in enumerate(red_cam):
        sx, sy = to_screen(x, y)
        if idx in [0, 1, 8, 15]:  # Waypoints clave reducidos
            labels = {
                0: "WP2: (+450.0 Y)",
                1: "WP3 Inicio: (+346.5 Y)",
                8: "WP4 Vértice: (-42.7 Y)",
                15: "WP5 Fin: (-346.5 Y)"
            }
            lines.append(f'<circle cx="{sx:.1f}" cy="{sy:.1f}" r="6" fill="#00e5ff" stroke="#ffffff" stroke-width="1.5" />')
            dx_offset = -140 if idx == 15 else 12
            dy_offset = 15 if idx == 15 else -5
            lines.append(f'<text x="{sx + dx_offset:.1f}" y="{sy + dy_offset:.1f}" fill="#79c0ff" font-size="11" font-weight="bold">{labels[idx]}</text>')
        else:
            lines.append(f'<circle cx="{sx:.1f}" cy="{sy:.1f}" r="3" fill="#00e676" opacity="0.8" />')

    # Ángulos de barrido visual (líneas radiales desde objetivo)
    lines.append(f'<line x1="{tx:.1f}" y1="{ty:.1f}" x2="{to_screen(red_cam[1][0], red_cam[1][1])[0]:.1f}" y2="{to_screen(red_cam[1][0], red_cam[1][1])[1]:.1f}" stroke="#7ee787" stroke-width="1" stroke-dasharray="4 4" opacity="0.5" />')
    lines.append(f'<line x1="{tx:.1f}" y1="{ty:.1f}" x2="{to_screen(red_cam[15][0], red_cam[15][1])[0]:.1f}" y2="{to_screen(red_cam[15][0], red_cam[15][1])[1]:.1f}" stroke="#7ee787" stroke-width="1" stroke-dasharray="4 4" opacity="0.5" />')
    lines.append(f'<text x="{tx + 120:.1f}" y="{ty - 15:.1f}" fill="#7ee787" font-size="12" font-weight="bold">Ángulo: 38°</text>')

    # Panel de Leyenda y Título
    lines.append('''<g transform="translate(60, 40)">
      <rect width="420" height="135" rx="8" fill="#161b22" stroke="#30363d" stroke-width="1.5" opacity="0.95" />
      <text x="16" y="24" fill="#f0f6fc" font-size="14" font-weight="bold">PLANO CARTESIANO DE TRAYECTORIAS (VISTA SUPERIOR XY)</text>
      <text x="16" y="42" fill="#8b949e" font-size="11">Base del Robot en (0, 0) · Objetivo fijo en (-1500, 0) mm</text>
      
      <!-- Item 1: Original -->
      <line x1="16" y1="65" x2="50" y2="65" stroke="#ff5252" stroke-width="2.5" stroke-dasharray="5 3" />
      <circle cx="33" cy="65" r="4" fill="#ff5252" />
      <text x="60" y="69" fill="#ff7b72" font-size="11">Ruta Original: 90° azimut (+770 a -770 Y) → Inviable (Error 112)</text>
      
      <!-- Item 2: Reducida -->
      <line x1="16" y1="92" x2="50" y2="92" stroke="#00e5ff" stroke-width="3.5" />
      <circle cx="33" cy="92" r="4" fill="#00e676" />
      <text x="60" y="96" fill="#7ee787" font-size="11" font-weight="bold">Ruta Reducida: 38° azimut (+346.5 a -346.5 Y) → 100% Continua</text>
      
      <!-- Item 3: Métricas -->
      <text x="16" y="122" fill="#e6edf3" font-size="10.5">Config 0 elegida · Despeje mín: 94.0 mm · Margen: 3.2° · Salto máx: 3.8°</text>
    </g>''')

    lines.append('</svg>')
    return "\n".join(lines)


def main():
    svg = build_svg()
    svg_path = HERE / "plano_cartesiano_rutas.svg"
    svg_path.write_text(svg, encoding="utf-8")
    print(f"SVG guardado en: {svg_path}")

    # También escribir en los artefactos
    art_path = Path(r"C:\Users\zamor\.gemini\antigravity-ide\brain\035c9b97-298e-481f-9afe-636cca41103b\plano_cartesiano_rutas.svg")
    art_path.write_text(svg, encoding="utf-8")
    print(f"SVG copiado a artefactos: {art_path}")


if __name__ == "__main__":
    main()
