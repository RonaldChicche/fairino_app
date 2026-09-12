#!/usr/bin/env python3
"""Servidor local del simulador de toma.

Sirve el visor y guarda las rutas en experiments/glambot-routes/routes/. El Lua lo genera routes.py,
que es el único lugar con la geometría: el visor dibuja, Python calcula.

  python3 server.py [--port 8765]

Solo escucha en 127.0.0.1. Es una herramienta de desarrollo, no parte del sistema del evento.
"""
import argparse
import json
import re
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

SIM_DIR = Path(__file__).resolve().parent
ROUTES_DIR = SIM_DIR.parent / "routes"
VALID_NAME = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

sys.path.insert(0, str(SIM_DIR.parent))
import routes as geometry  # noqa: E402


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(SIM_DIR), **kwargs)

    def log_message(self, fmt, *args):  # menos ruido: solo errores
        if not args or not str(args[0]).startswith(("GET /api", "POST /api")):
            return
        super().log_message(fmt, *args)

    def _send_json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _route_path(self, name):
        if not VALID_NAME.match(name):
            return None
        return ROUTES_DIR / f"{name}.json"

    def do_GET(self):
        if self.path == "/api/routes":
            ROUTES_DIR.mkdir(exist_ok=True)
            self._send_json(sorted(p.stem for p in ROUTES_DIR.glob("*.json")))
        elif self.path.startswith("/api/routes/"):
            path = self._route_path(self.path[len("/api/routes/"):])
            if path is None or not path.exists():
                self._send_json({"error": "no existe esa ruta"}, 404)
            else:
                self._send_json(json.loads(path.read_text(encoding="utf-8")))
        else:
            super().do_GET()

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            self._send_json({"error": f"JSON inválido: {exc}"}, 400)
            return

        if self.path.startswith("/api/routes/"):
            self._save(self.path[len("/api/routes/"):], payload)
        elif self.path.startswith("/api/generate/"):
            self._generate(self.path[len("/api/generate/"):], payload)
        else:
            self._send_json({"error": "ruta desconocida"}, 404)

    def _save(self, name, spec):
        path = self._route_path(name)
        if path is None:
            self._send_json({"error": "nombre inválido: solo letras, números, guion y guion bajo"}, 400)
            return
        ROUTES_DIR.mkdir(exist_ok=True)
        path.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
        self._send_json({"ok": True, "mensaje": f"guardada en routes/{name}.json"})

    def _generate(self, name, spec):
        path = self._route_path(name)
        if path is None:
            self._send_json({"error": "nombre inválido"}, 400)
            return
        try:
            lua, points = geometry.lua_from_spec(spec)
        except Exception as exc:  # el error del generador se muestra tal cual en el visor
            self._send_json({"error": str(exc)}, 400)
            return
        lua_path = path.with_suffix(".lua")
        lua_path.write_text(lua, encoding="utf-8")
        self._send_json({"ok": True, "puntos": points,
                         "mensaje": f"{points} puntos → routes/{name}.lua"})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    ROUTES_DIR.mkdir(exist_ok=True)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Simulador de toma en http://localhost:{args.port}  ·  rutas en {ROUTES_DIR}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nadiós")


if __name__ == "__main__":
    main()
