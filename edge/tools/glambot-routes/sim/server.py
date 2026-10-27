#!/usr/bin/env python3
"""Servidor local del simulador de toma.

Sirve el visor y guarda las rutas en edge/tools/glambot-routes/routes/. El Lua lo genera routes.py,
que es el único lugar con la geometría: el visor dibuja, Python calcula.

  python3 server.py [--port 8765]

API:
  GET  /api/routes             · nombres de las rutas guardadas
  GET  /api/routes/<nombre>    · el JSON de una ruta
  POST /api/routes/<nombre>    · guarda el JSON de una ruta
  POST /api/validate/<nombre>  · informe de alcance punto a punto (routes.validate_spec)
  POST /api/generate/<nombre>  · valida y escribe routes/<nombre>.lua; 400 con el informe si algo falla
  POST /api/upload/<nombre>    · sube ese .lua al controlador, por `fr10 ssh` dentro de la instancia EC2

Solo escucha en 127.0.0.1. Es una herramienta de desarrollo, no parte del sistema del evento.
"""
import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

SIM_DIR = Path(__file__).resolve().parent
ROUTES_DIR = SIM_DIR.parent / "routes"
VALID_NAME = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

sys.path.insert(0, str(SIM_DIR.parent))
import routes as geometry  # noqa: E402

# El controlador FAIRINO vive en la red privada de la instancia EC2: desde este Mac no hay ruta hasta él.
# La subida se ejecuta dentro de la instancia por `fr10 ssh`, que es la única vía real.
FR10_CLI = os.environ.get("FR10_CLI", "fr10")
ROBOT_IP = os.environ.get("FAIRINO_ROBOT_IP", "192.168.58.2")
REMOTE_DIR = "glambot-routes"
REMOTE_SDK = "fairino_sdk_v2.2.3"
UPLOAD_TIMEOUT_S = 180
# Confirmaciones que tiene que imprimir la instancia. Un código de salida 0 no basta: cualquier `fr10`
# que conecte y no haga nada sale 0, y el endpoint cantaría "subido" sin que nada se haya subido.
COPY_OK = "COPIADO"
UPLOAD_OK = "SUBIDO_OK"

COMO_ARRANCAR = (f"El controlador solo es accesible desde la instancia EC2, nunca desde este equipo: "
                 f"enciéndela con `fr10 up` (hace falta `aws login` vigente), arranca el contenedor con "
                 f"`fr10 ssh 'sudo docker start fairino-container'` y ten esta carpeta copiada en "
                 f"~/{REMOTE_DIR} de la instancia (ver NOTAS.md, «Cómo reproducir»).")

# Se ejecuta EN la instancia: reutiliza upload_and_load de run_route.py y el SDK v2.2.3 ya instalado allí.
REMOTE_UPLOAD_PY = f'''
import sys
from pathlib import Path
sys.path.insert(0, str(Path.home() / "{REMOTE_SDK}"))
sys.path.insert(0, str(Path.home() / "{REMOTE_DIR}"))
try:
    from fairino import Robot
except Exception as exc:
    print("SDK_FALTA: " + repr(exc))
    raise SystemExit(3)
try:
    from run_route import upload_and_load
except Exception as exc:
    print("FALTA_CODIGO: " + repr(exc))
    raise SystemExit(6)

lua = Path.home() / "{REMOTE_DIR}" / "routes" / (sys.argv[1] + ".lua")
robot = Robot.RPC(sys.argv[2])
if not getattr(robot, "is_connect", getattr(robot, "is_conect", False)):
    print("SIN_CONTROLADOR")
    raise SystemExit(4)
try:
    ok = upload_and_load(robot, lua)
finally:
    robot.CloseRPC()
if not ok:
    raise SystemExit(5)
print("{UPLOAD_OK}")
'''

REMOTE_ERRORS = {
    3: f"el SDK de FAIRINO no está en ~/{REMOTE_SDK} dentro de la instancia (ver NOTAS.md, «Cómo reproducir»)",
    4: f"la instancia no ve al controlador en {ROBOT_IP}: arráncalo con "
       f"`fr10 ssh 'sudo docker start fairino-container'`",
    5: "el controlador rechazó LuaUpload o ProgramLoad",
    6: f"falta el código de glambot-routes en ~/{REMOTE_DIR} de la instancia: cópialo con el scp de NOTAS.md",
}


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
        # fullmatch y no match: con `$`, "toma\n" pasaría el filtro y el salto de línea partiría en dos
        # la orden de shell remota de _upload. Hoy http.server rechaza esa petición, pero el nombre
        # llega hasta un shell en la instancia y ese filtro es lo único que hay en medio.
        if not VALID_NAME.fullmatch(name):
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
        elif self.path.startswith("/api/validate/"):
            self._validate(self.path[len("/api/validate/"):], payload)
        elif self.path.startswith("/api/generate/"):
            self._generate(self.path[len("/api/generate/"):], payload)
        elif self.path.startswith("/api/upload/"):
            self._upload(self.path[len("/api/upload/"):])
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

    def _validate(self, name, spec):
        if self._route_path(name) is None:
            self._send_json({"error": "nombre inválido"}, 400)
            return
        self._send_json(geometry.validate_spec(spec))

    def _generate(self, name, spec):
        path = self._route_path(name)
        if path is None:
            self._send_json({"error": "nombre inválido"}, 400)
            return
        report = geometry.validate_spec(spec)
        if not report["ok"]:
            self._send_json(report, 400)
            return
        try:
            lua, points = geometry.lua_from_spec(spec, report)
        except Exception as exc:  # el error del generador se muestra tal cual en el visor
            self._send_json({"error": str(exc)}, 400)
            return
        lua_path = path.with_suffix(".lua")
        lua_path.write_text(lua, encoding="utf-8")
        mensaje = f"{points} puntos → routes/{name}.lua"
        aviso = report.get("aviso")
        self._send_json({"ok": True, "puntos": points, "aviso": aviso,
                         "mensaje": f"{aviso} {mensaje}" if aviso else mensaje})

    def _upload(self, name):
        path = self._route_path(name)
        if path is None:
            self._send_json({"error": "nombre inválido"}, 400)
            return
        lua_path = path.with_suffix(".lua")
        if not lua_path.exists():
            self._send_json({"error": f"no existe routes/{name}.lua: genera la ruta antes de subirla"}, 400)
            return
        payload, status = upload_to_controller(name, lua_path)
        self._send_json(payload, status)


def _fr10_ssh(remote_command, stdin_text=None):
    """Ejecuta un comando dentro de la instancia EC2. Devuelve (returncode, stdout, stderr)."""
    # Sin entrada propia se le cierra la stdin: ssh heredaría la del servidor y se la comería
    extra = {"input": stdin_text} if stdin_text is not None else {"stdin": subprocess.DEVNULL}
    try:
        done = subprocess.run([FR10_CLI, "ssh", remote_command], text=True, capture_output=True,
                              timeout=UPLOAD_TIMEOUT_S, **extra)
    except subprocess.TimeoutExpired:
        return None, "", f"sin respuesta en {UPLOAD_TIMEOUT_S} s"
    return done.returncode, done.stdout, done.stderr


def _copied_bytes(stdout):
    """Bytes que la instancia dice tener en el .lua copiado, o None si no lo confirmó."""
    for line in reversed(stdout.splitlines()):
        if line.startswith(COPY_OK):
            try:
                return int(line[len(COPY_OK):].strip())
            except ValueError:
                return None
    return None


def upload_to_controller(name, lua_path):
    """Copia el .lua a la instancia y lo sube al controlador desde allí. Devuelve (payload, status HTTP).

    Cada paso exige una confirmación positiva de la instancia (los bytes copiados, y luego UPLOAD_OK),
    no solo un código de salida 0: por aquí se carga el programa que mueve un brazo industrial y
    "subido" tiene que significar subido.
    """
    if shutil.which(FR10_CLI) is None:
        return {"error": f"no encuentro el comando `{FR10_CLI}` en el PATH. El controlador FAIRINO solo es "
                         f"accesible desde la instancia EC2, así que la subida pasa por `fr10 ssh`: instala "
                         f"experiments/fr10-sim/fr10 o define FR10_CLI con su ruta."}, 503

    # name ya pasó VALID_NAME, pero acaba dentro de una orden de shell en la instancia: se cita igual,
    # para que el filtro no sea lo único que separa un nombre de una inyección de comandos.
    quoted = shlex.quote(f"{name}.lua")
    remote_lua = f"~/{REMOTE_DIR}/routes/{quoted}"
    lua_text = lua_path.read_text(encoding="utf-8")
    expected = len(lua_text.encode("utf-8"))

    code, out, err = _fr10_ssh(f"mkdir -p ~/{REMOTE_DIR}/routes && cat > {remote_lua} "
                               f"&& printf '{COPY_OK} %s\\n' \"$(wc -c < {remote_lua})\"", lua_text)
    if code != 0:
        return {"error": f"no pude copiar el .lua a la instancia. {COMO_ARRANCAR}",
                "detalle": (err or out).strip()}, 503
    copied = _copied_bytes(out)
    if copied != expected:
        visto = "nada" if copied is None else f"{copied} bytes"
        return {"error": f"la copia del .lua a la instancia no cuadra: enviados {expected} bytes, "
                         f"confirmados {visto}. No se sube al controlador un programa que no es el "
                         f"generado. {COMO_ARRANCAR}",
                "detalle": (out + err).strip()}, 503

    code, out, err = _fr10_ssh(f"python3 - {shlex.quote(name)} {ROBOT_IP} <<'PYEOF'\n{REMOTE_UPLOAD_PY}\nPYEOF")
    if code == 0 and UPLOAD_OK in out:
        return {"ok": True, "mensaje": f"routes/{name}.lua subido y cargado en el controlador {ROBOT_IP}",
                "detalle": out.replace(UPLOAD_OK, "").strip()}, 200
    if code == 0:
        return {"error": f"la instancia terminó sin error pero no confirmó la subida: no se ha cargado "
                         f"nada en el controlador. {COMO_ARRANCAR}",
                "detalle": (out + err).strip()}, 503
    motivo = REMOTE_ERRORS.get(code, f"la subida falló en la instancia (código {code})")
    return {"error": f"no se subió al controlador: {motivo}. {COMO_ARRANCAR}",
            "detalle": (out + err).strip()}, 503


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
