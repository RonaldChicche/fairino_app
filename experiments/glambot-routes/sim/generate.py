#!/usr/bin/env python3
"""Genera el Lua de una ruta del simulador sin pasar por el navegador.

  python3 generate.py ../routes/grua-lateral.json [salida.lua]

La geometría vive en routes.py; esto es solo la línea de comandos.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import routes as geometry  # noqa: E402


def main():
    if not 2 <= len(sys.argv) <= 3:
        print(__doc__)
        return 2
    spec_path = Path(sys.argv[1])
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    try:
        lua, points = geometry.lua_from_spec(spec)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    out = Path(sys.argv[2]) if len(sys.argv) == 3 else spec_path.with_suffix(".lua")
    out.write_text(lua, encoding="utf-8")
    print(f"{points} puntos → {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
