"""Reduce las mallas STL oficiales del FR10 a un JSON liviano para visualizarlas en el navegador.

Requiere numpy, trimesh y fast-simplification. Posiciones en décimas de milímetro (enteros).
Uso: python3 make_lite.py
"""
import json
from pathlib import Path

import numpy as np
import trimesh
import fast_simplification

AQUI = Path(__file__).parent
TRIANGULOS = {
    "base_link": 900,
    "shoulder_link": 1800,
    "upperarm_link": 2600,
    "forearm_link": 1800,
    "wrist1_link": 900,
    "wrist2_link": 900,
    "wrist3_link": 800,
}
ESCALA = 10000  # metros a décimas de milímetro

links = []
for nombre, objetivo in TRIANGULOS.items():
    malla = trimesh.load(AQUI / "meshes" / f"{nombre}.STL")
    malla.merge_vertices()
    v, f = fast_simplification.simplify(
        np.asarray(malla.vertices, dtype=np.float32),
        np.asarray(malla.faces, dtype=np.int32),
        target_count=objetivo,
    )
    links.append({
        "name": nombre,
        "v": np.round(v * ESCALA).astype(int).ravel().tolist(),
        "f": f.astype(int).ravel().tolist(),
    })
    print(nombre, len(malla.faces), "->", len(f))

salida = AQUI / "fr10_lite.json"
salida.write_text(json.dumps({"scale": 1 / ESCALA, "links": links}, separators=(",", ":")))
print(salida, salida.stat().st_size // 1024, "KB")
