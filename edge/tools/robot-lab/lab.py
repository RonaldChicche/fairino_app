"""Laboratorio del controlador FAIRINO: subir un Lua con hash en el nombre, correrlo con datos de entrada y leer lo que devuelve.

  uv run python tools/robot-lab/lab.py state
  uv run python tools/robot-lab/lab.py mode auto
  uv run python tools/robot-lab/lab.py upload tools/robot-lab/z_relative_dry.lua
  uv run python tools/robot-lab/lab.py run z_relative_dry_<hash>.lua --dz 100

Cada comando abre una sola conexión. Ningún comando mueve el robot: `run` solo ejecuta el programa que le indiques.
"""
import argparse
import hashlib
import shutil
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "vendor" / "fairino"))
import Robot

IP = "192.168.58.2"
PROGRAM_DIR = "/fruser/"
INPUTS = {"dz": 1, "request_id": 8}
OUTPUTS = {"status": 10, "echo_id": 11, "x": 12, "y": 13, "z": 14, "up_z": 15, "up_has_solution": 16}


def ok(result, what):
    code = result[0] if isinstance(result, tuple) else result
    if code != 0:
        raise SystemExit(f"{what} falló con el código {code}")
    return result


def sysvar(robot, number):
    return ok(robot.GetSysVarValue(number), f"leer s_var_{number}")[1]


def state(robot, _args):
    print("versión:", ok(robot.GetSDKVersion(), "versión")[1])
    print("código de error del robot:", robot.GetRobotErrorCode())
    print("articulaciones:", ok(robot.GetActualJointPosDegree(1), "articulaciones")[1])
    print("programas:", [n for n in ok(robot.GetLuaList(), "lista")[2] if n])
    print("variables 1..20:", [sysvar(robot, n) for n in range(1, 21)])
    print("estado del programa:", robot.GetProgramState())


def mode(robot, args):
    ok(robot.Mode(0 if args.target == "auto" else 1), "cambiar el modo")
    time.sleep(1)
    print("modo actual (0 auto, 1 manual):", robot.robot_state_pkg.robot_mode)


def upload(robot, args):
    source = Path(args.file)
    digest = hashlib.sha256(source.read_bytes()).hexdigest()[:8]
    name = f"{source.stem}_{digest}.lua"
    with tempfile.TemporaryDirectory() as tmp:
        copy = Path(tmp) / name
        shutil.copy(source, copy)
        for attempt in range(1, 4):
            result = robot.LuaUpload(str(copy))
            if result == 0:
                break
            print(f"intento {attempt}: {result}")
            time.sleep(2)
        else:
            raise SystemExit("la subida falló tres veces")
    names = ok(robot.GetLuaList(), "lista")[2]
    print("subido:", name, "| aparece en la lista:", name in names)


def run(robot, args):
    if "_dry_" not in args.name and not args.allow_motion:
        raise SystemExit("este programa puede mover el robot: hace falta --allow-motion")
    if robot.robot_state_pkg.robot_mode != 0:
        raise SystemExit("el robot está en modo manual: pásalo a automático con `mode auto`")
    joints = ok(robot.GetActualJointPosDegree(1), "articulaciones")[1]
    time.sleep(0.5)
    again = ok(robot.GetActualJointPosDegree(1), "articulaciones")[1]
    if max(abs(a - b) for a, b in zip(joints, again)) > 0.05:
        raise SystemExit("el brazo se está moviendo: no se ejecuta nada")
    values = {INPUTS["dz"]: args.dz, INPUTS["request_id"]: args.request_id, **{2 + i: joints[i] for i in range(6)}}
    for number in OUTPUTS.values():
        ok(robot.SetSysVarValue(number, 0), f"limpiar s_var_{number}")
    for number, value in values.items():
        ok(robot.SetSysVarValue(number, value), f"escribir s_var_{number}")
    ok(robot.ProgramLoad(args.name if "/" in args.name else f"{PROGRAM_DIR}{args.name}"), "cargar el programa")
    last = ok(robot.GetActualJointPosDegree(1), "articulaciones")[1]
    if max(abs(a - b) for a, b in zip(joints, last)) > 0.05:
        raise SystemExit("el brazo se movió desde que se leyó su posición: no se ejecuta nada")
    actions = []
    if args.pause_after is not None:
        actions += [(args.pause_after, "pausa", robot.ProgramPause),
                    (args.pause_after + args.pause_for, "reanuda", robot.ProgramResume)]
    if args.stop_after is not None:
        actions.append((args.stop_after, "detiene", robot.ProgramStop))
    ok(robot.ProgramRun(), "ejecutar el programa")
    finished = wait_finished(robot, args.timeout, sorted(actions, key=lambda a: a[0]))
    print("entradas:", values)
    print("salidas:", {name: sysvar(robot, number) for name, number in OUTPUTS.items()})
    print("código de error:", robot.GetRobotErrorCode())
    if args.then_manual:
        if finished:
            ok(robot.Mode(1), "volver a modo manual")
            time.sleep(1)
            print("modo actual (0 auto, 1 manual):", robot.robot_state_pkg.robot_mode)
        else:
            print("no se vuelve a manual: no se confirmó que el robot haya terminado")


def snapshot(robot):
    pkg = robot.robot_state_pkg
    return {"program": pkg.program_state, "motion": pkg.robot_state, "done": pkg.motion_done,
            "queue": pkg.mc_queue_len, "z": pkg.tl_cur_pos[2], "emergency_stop": pkg.EmergencyStop,
            "error": (pkg.main_code, pkg.sub_code)}


def wait_finished(robot, timeout, actions=()):
    """Terminó cuando el programa y el movimiento están parados durante 1 s seguido."""
    start = time.time()
    idle_since = None
    last_key = None
    last_print = start
    pending = list(actions)
    zs = []
    while time.time() - start < timeout:
        row = snapshot(robot)
        elapsed = time.time() - start
        zs.append(row["z"])
        while pending and elapsed >= pending[0][0]:
            _, label, call = pending.pop(0)
            print(f"{elapsed:5.1f} s  >>> {label}: {call()}")
        key = (row["program"], row["motion"], row["done"], row["queue"], row["emergency_stop"], row["error"])
        if key != last_key or (actions and time.time() - last_print >= 1.0):
            print(f"{elapsed:5.1f} s  programa={key[0]} movimiento={key[1]} en_posición={key[2]} cola={key[3]} paro={key[4]} error={key[5]} z={row['z']:.1f}")
            last_key = key
            last_print = time.time()
        idle = row["program"] == 1 and row["motion"] == 1
        idle_since = (idle_since or time.time()) if idle else None
        if idle_since and time.time() - idle_since >= 1.0 and elapsed >= 2.0:
            print(f"terminó a los {elapsed:.1f} s; z entre {min(zs):.1f} y {max(zs):.1f} mm")
            return True
        time.sleep(0.1)
    print(f"no terminó en {timeout:.0f} s")
    return False


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("state")
    sub.add_parser("mode").add_argument("target", choices=["auto", "manual"])
    sub.add_parser("upload").add_argument("file")
    run_parser = sub.add_parser("run")
    run_parser.add_argument("name")
    run_parser.add_argument("--dz", type=float, required=True)
    run_parser.add_argument("--request-id", type=float, default=1)
    run_parser.add_argument("--allow-motion", action="store_true")
    run_parser.add_argument("--then-manual", action="store_true")
    run_parser.add_argument("--pause-after", type=float)
    run_parser.add_argument("--pause-for", type=float, default=3)
    run_parser.add_argument("--stop-after", type=float)
    run_parser.add_argument("--timeout", type=float, default=60)
    args = parser.parse_args()
    robot = Robot.RPC(IP)
    {"state": state, "mode": mode, "upload": upload, "run": run}[args.command](robot, args)


if __name__ == "__main__":
    main()
