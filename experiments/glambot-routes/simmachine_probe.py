#!/usr/bin/env python3
"""Ejecuta en un controlador FAIRINO (SimMachine o real) los programas Lua de lua_probes/ y reporta resultados.

Ningún programa de prueba mueve el robot. Cada prueba: escribe entradas en variables de sistema, sube el .lua,
lo carga y ejecuta, espera a que termine y lee las salidas y los códigos de error.

  python3 simmachine_probe.py --ip 192.168.58.2 --sdk ~/fairino_sdk_v2.2.3
"""
import argparse
import os
import sys
import time
from pathlib import Path

PROBES_DIR = Path(__file__).resolve().parent / "lua_probes"
STATE_NAMES = {1: "detenido", 2: "corriendo", 3: "pausado"}
# Carpeta de programas según el tipo de controlador (SDKManual, ProgramLoad): QX usa /fruser/, LA la de abajo
PROGRAM_DIRS = ("/fruser/", "/usr/local/etc/controller/lua/")
UPLOAD_ATTEMPTS = 4


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ip", default=os.environ.get("FAIRINO_ROBOT_IP"),
                        help="IP del controlador (o variable FAIRINO_ROBOT_IP)")
    parser.add_argument("--sdk", default=os.environ.get("FAIRINO_SDK_PATH"),
                        help="carpeta que contiene el paquete 'fairino' (o variable FAIRINO_SDK_PATH)")
    parser.add_argument("--timeout", type=float, default=20.0, help="segundos máximos por programa")
    args = parser.parse_args()
    if not args.ip or not args.sdk:
        parser.error("faltan --ip y/o --sdk (o FAIRINO_ROBOT_IP / FAIRINO_SDK_PATH)")
    return args


class Probe:
    def __init__(self, robot, timeout):
        self.robot = robot
        self.timeout = timeout

    def state(self):
        pkg = self.robot.robot_state_pkg
        return pkg.program_state, pkg.main_code, pkg.sub_code

    def set_vars(self, values):
        for var_id, value in values.items():
            err = self.robot.SetSysVarValue(var_id, value)
            if err != 0:
                raise RuntimeError(f"SetSysVarValue({var_id}) devolvió {err}")

    def get_var(self, var_id):
        err, value = self.robot.GetSysVarValue(var_id)
        return value if err == 0 else f"error {err}"

    def run(self, name, inputs, outputs, during=None):
        path = PROBES_DIR / name
        print(f"\n=== {name} ===")
        self.robot.ResetAllError()
        self.set_vars({**{v: -1 for v in outputs}, **inputs})
        # La subida falla de forma intermitente con subidas seguidas (-1, o respuesta XML-RPC vacía): se reintenta
        for attempt in range(1, UPLOAD_ATTEMPTS + 1):
            try:
                upload = self.robot.LuaUpload(str(path))
            except Exception as exc:  # respuesta vacía del servidor XML-RPC del controlador
                upload = f"excepción {type(exc).__name__}"
            if upload == 0 or isinstance(upload, tuple):
                break
            print(f"  LuaUpload intento {attempt}: {upload}")
            time.sleep(2.0)
        print(f"  LuaUpload: {upload} (intento {attempt})")
        # El controlador ejecuta el script al subirlo para validarlo: ¿esa ejecución escribe variables de sistema?
        print("  tras subir, antes de ejecutar:", ", ".join(f"s_var_{v}={self.get_var(v)}" for v in outputs))
        if upload != 0:
            print("  la subida no fue aceptada: no se ejecuta")
            return
        for program_dir in PROGRAM_DIRS:
            load = self.robot.ProgramLoad(f"{program_dir}{name}")
            print(f"  ProgramLoad('{program_dir}{name}'): {load}")
            if load == 0:
                break
        print("  GetLoadedProgram:", self.robot.GetLoadedProgram())
        if load != 0:
            print("  no se pudo cargar el programa: no se ejecuta")
            return
        run = self.robot.ProgramRun()
        print("  ProgramRun:", run)

        start = time.time()
        seen_running = False
        while time.time() - start < self.timeout:
            program_state, main_code, sub_code = self.state()
            if program_state == 2:
                seen_running = True
                if during:
                    during(self)
            if program_state == 1 and (seen_running or time.time() - start > 2.0):
                break
            time.sleep(0.05)
        program_state, main_code, sub_code = self.state()
        elapsed = time.time() - start
        print(f"  estado final: {STATE_NAMES.get(program_state, program_state)} · se vio corriendo: {seen_running} · "
              f"{elapsed:.2f} s · error main/sub: {main_code}/{sub_code} · GetRobotErrorCode: {self.robot.GetRobotErrorCode()}")
        if program_state != 1:
            print("  ProgramStop:", self.robot.ProgramStop())
        for var_id in outputs:
            print(f"  s_var_{var_id} = {self.get_var(var_id)}")


def main():
    args = parse_args()
    sys.path.insert(0, os.path.expanduser(args.sdk))
    from fairino import Robot

    robot = Robot.RPC(args.ip)
    if not getattr(robot, "is_connect", getattr(robot, "is_conect", False)):
        print("ERROR: no hay conexión con el controlador", file=sys.stderr)
        return 1
    print("SDK:", robot.GetSDKVersion(), "· software:", robot.GetSoftwareVersion())
    print("Mode(0) automático:", robot.Mode(0))
    time.sleep(0.5)
    print("RobotEnable(1):", robot.RobotEnable(1))
    time.sleep(0.5)

    probe = Probe(robot, args.timeout)
    try:
        probe.run("probe_sysvar.lua", inputs={1: 41.5}, outputs=[2])
        probe.run("probe_math.lua", inputs={}, outputs=[3])
        probe.run("probe_version.lua", inputs={}, outputs=[4])
        probe.run("probe_ik.lua", inputs={}, outputs=[5, 6, 7, 8])
        probe.run("probe_ikref.lua", inputs={}, outputs=list(range(11, 20)))

        track = []

        def record_tcp(p):
            err, pose = p.robot.GetActualTCPPose()
            if err == 0 and pose:
                track.append((time.time(), list(pose)))

        print("\nPose TCP antes del movimiento:", robot.GetActualTCPPose())
        probe.run("probe_movel.lua", inputs={}, outputs=[20], during=record_tcp)
        print("  Pose TCP después:", robot.GetActualTCPPose())
        if track:
            zs = [pose[2] for _, pose in track]
            print(f"  muestras de TCP durante la ejecución: {len(track)} · z mín {min(zs):.1f} · z máx {max(zs):.1f} · "
                  f"duración {track[-1][0] - track[0][0]:.2f} s")

        def send_signal_when_waiting(p):
            if p.get_var(9) == 1 and p.get_var(10) != 42:
                time.sleep(0.5)  # que el programa itere un rato esperando
                p.set_vars({10: 42})
                print("  (PC) vio s_var_9 = 1 y escribió s_var_10 = 42")

        probe.run("probe_wait.lua", inputs={10: 0}, outputs=[9, 10], during=send_signal_when_waiting)
        print("\nGetLuaList:", robot.GetLuaList())
    finally:
        robot.CloseRPC()
    return 0


if __name__ == "__main__":
    sys.exit(main())
