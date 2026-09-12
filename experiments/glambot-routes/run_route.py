#!/usr/bin/env python3
"""Ejecuta un Lua de ruta de glambot en un controlador FAIRINO (SimMachine) y mide su fidelidad.

Emula el lado del PC del protocolo: escribe el objetivo y el ID de toma, lanza el programa, espera a que el
robot pida la cámara y confirma la "grabación" tras un retardo. Registra la pose real de la brida mientras el
robot se mueve (según el estado en tiempo real, no según la variable de estado del Lua) hasta que queda quieto,
y guarda una línea de tiempo de estados para comparar cuándo termina el programa y cuándo termina el movimiento.

La fidelidad (desviación del eje óptico respecto al objetivo) se mide solo sobre la ruta: desde que la brida
llega al primer punto hasta el final, sin el acercamiento con MoveJ.

  python3 run_route.py --ip 192.168.58.2 --sdk ~/fairino_sdk_v2.2.3 --lua crane_fr5.lua \\
      --target -900 0 350 --standoff 350 --dz-start -150 --dz-end 250 --steps 6 --camera-offset 100 \\
      --take-id 19 --camera-delay 1.5 --csv crane_fr5_track.csv
"""
import argparse
import csv
import math
import os
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from routes import _add, aim_errors, camera_to_flange, crane_route  # noqa: E402

PROGRAM_DIRS = ("/fruser/", "/usr/local/etc/controller/lua/")
UPLOAD_ATTEMPTS = 4
STATUS = {0: "iniciado", 1: "esperando cámara", 2: "moviendo", 3: "terminado",
          -1: "punto inalcanzable", -2: "la cámara no confirmó a tiempo"}
VAR_TARGET, VAR_TAKE, VAR_CAMERA, VAR_STATUS, VAR_TAKE_ECHO = (1, 2, 3), 4, 5, 6, 7
STILL_SECONDS = 1.0       # sin cambios de pose durante este tiempo = robot quieto
ROUTE_START_TOL_MM = 1.0  # distancia para considerar que la brida llegó al primer punto


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ip", default=os.environ.get("FAIRINO_ROBOT_IP"))
    parser.add_argument("--sdk", default=os.environ.get("FAIRINO_SDK_PATH"))
    parser.add_argument("--lua", required=True)
    parser.add_argument("--target", type=float, nargs=3, required=True, metavar=("X", "Y", "Z"))
    parser.add_argument("--standoff", type=float, required=True)
    parser.add_argument("--azimuth", type=float, default=None)
    parser.add_argument("--dz-start", type=float, required=True)
    parser.add_argument("--dz-end", type=float, required=True)
    parser.add_argument("--steps", type=int, required=True)
    parser.add_argument("--camera-offset", type=float, required=True, help="el mismo usado al generar el Lua")
    parser.add_argument("--take-id", type=int, required=True)
    parser.add_argument("--camera-delay", type=float, required=True, help="segundos hasta confirmar la cámara")
    parser.add_argument("--start-joints", type=float, nargs=6, metavar="J",
                        help="mueve el robot a esta postura (SDK MoveJ) antes de lanzar el Lua")
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--csv", help="guarda la trayectoria registrada")
    args = parser.parse_args()
    if not args.ip or not args.sdk:
        parser.error("faltan --ip y/o --sdk (o FAIRINO_ROBOT_IP / FAIRINO_SDK_PATH)")
    return args


def upload_and_load(robot, lua_path):
    for attempt in range(1, UPLOAD_ATTEMPTS + 1):
        try:
            result = robot.LuaUpload(str(lua_path))
        except Exception as exc:  # respuesta XML-RPC vacía, intermitente
            result = f"excepción {type(exc).__name__}"
        if result == 0 or isinstance(result, tuple):
            break
        time.sleep(2.0)
    print(f"LuaUpload: {result} (intento {attempt})")
    if result != 0:
        return False
    for program_dir in PROGRAM_DIRS:
        if robot.ProgramLoad(f"{program_dir}{lua_path.name}") == 0:
            print("ProgramLoad:", f"{program_dir}{lua_path.name}")
            return True
    print("ProgramLoad: no se encontró el programa en", PROGRAM_DIRS)
    return False


def status_name(value):
    return STATUS.get(int(value), "?") if value is not None else "lectura fallida"


def main():
    args = parse_args()
    sys.path.insert(0, os.path.expanduser(args.sdk))
    from fairino import Robot

    lua_path = Path(args.lua).resolve()
    target = tuple(args.target)
    azimuth = args.azimuth if args.azimuth is not None else math.degrees(math.atan2(-target[1], -target[0]))
    flange = camera_to_flange(crane_route(args.standoff, azimuth, args.dz_start, args.dz_end, args.steps),
                              args.camera_offset)
    first_waypoint = _add(target, flange[0].offset)
    last_waypoint = (*_add(target, flange[-1].offset), *flange[-1].rpy)

    robot = Robot.RPC(args.ip)
    if not getattr(robot, "is_connect", getattr(robot, "is_conect", False)):
        print("ERROR: no hay conexión con el controlador", file=sys.stderr)
        return 1

    read_errors = {}

    def var(var_id):
        err, value = robot.GetSysVarValue(var_id)
        if err != 0:
            read_errors[err] = read_errors.get(err, 0) + 1
            return None
        return value

    final = None
    try:
        robot.ResetAllError()
        robot.Mode(0)
        time.sleep(0.5)
        robot.RobotEnable(1)
        time.sleep(0.5)
        if args.start_joints:
            print("MoveJ previo (SDK) a", list(args.start_joints), "→", robot.MoveJ(list(args.start_joints), 0, 0, vel=30))
            previous, still_since, t0 = None, time.time(), time.time()
            while time.time() - t0 < 60:
                err, current = robot.GetActualTCPPose()
                if current != previous:
                    previous, still_since = current, time.time()
                elif time.time() - still_since > STILL_SECONDS:
                    break
                time.sleep(0.05)
            print("  pose de partida:", [round(v, 1) for v in previous])
        for var_id, value in zip(VAR_TARGET, target):
            robot.SetSysVarValue(var_id, value)
        robot.SetSysVarValue(VAR_TAKE, args.take_id)
        robot.SetSysVarValue(VAR_CAMERA, -1)
        robot.SetSysVarValue(VAR_STATUS, -99)
        robot.SetSysVarValue(VAR_TAKE_ECHO, -99)

        if not upload_and_load(robot, lua_path):
            return 1
        print("ProgramRun:", robot.ProgramRun())

        start = time.time()
        timeline, track = [], []
        last = {}
        camera_sent_at = program_ended_at = None
        seen_program_running = False
        last_pose_change = time.time()

        def mark(key, value, now):
            if last.get(key) != value:
                timeline.append((now, key, value))
                last[key] = value

        while time.time() - start < args.timeout:
            now = time.time() - start
            # El hilo de estado del SDK puede sustituir el objeto en cada paquete: leerlo siempre de nuevo
            pkg = robot.robot_state_pkg
            status = var(VAR_STATUS)
            mark("estado Lua", status, now)
            mark("program_state", pkg.program_state, now)
            mark("robot_state", pkg.robot_state, now)
            mark("motion_done", pkg.motion_done, now)

            if status == 1 and camera_sent_at is None:
                time.sleep(args.camera_delay)  # la cámara tarda en arrancar (D18)
                robot.SetSysVarValue(VAR_CAMERA, args.take_id)
                camera_sent_at = time.time() - start
                timeline.append((camera_sent_at, "PC", f"cámara grabando → s_var_{VAR_CAMERA} = {args.take_id}"))

            # Pose por RPC: el paquete de estado en tiempo real no refrescó la posición durante un programa Lua
            err, tcp = robot.GetActualTCPPose()
            pose = list(tcp) if err == 0 and tcp else None
            if pose is not None and (not track or pose != track[-1][1]):
                track.append((now, pose, list(pkg.jt_cur_pos)))
                last_pose_change = time.time()
            if len(track) == 1 and "pkg_first" not in last:
                last["pkg_first"] = (list(pkg.flange_cur_pos), pose)

            if pkg.program_state == 2:
                seen_program_running = True
            elif seen_program_running and pkg.program_state == 1 and program_ended_at is None:
                program_ended_at = now
            if (program_ended_at is not None and pkg.robot_state == 1
                    and time.time() - last_pose_change > STILL_SECONDS):
                break
            time.sleep(0.004)

        final = var(VAR_STATUS)
        pkg = robot.robot_state_pkg
        if "pkg_first" in last:
            first_pkg, first_rpc = last["pkg_first"]
            err, last_rpc = robot.GetActualTCPPose()
            print("Comparación de fuentes de pose (inicio → fin):")
            print("  paquete flange_cur_pos:", [round(v, 1) for v in first_pkg], "→", [round(v, 1) for v in pkg.flange_cur_pos])
            print("  RPC GetActualTCPPose:  ", [round(v, 1) for v in first_rpc], "→", [round(v, 1) for v in last_rpc])
        print("\nLínea de tiempo:")
        for t, key, value in timeline:
            detail = f" ({status_name(value)})" if key == "estado Lua" else ""
            print(f"  t={t:6.2f} s · {key}: {value}{detail}")
        print(f"\nEstado final: {final} ({status_name(final)}) · ID aceptado: {var(VAR_TAKE_ECHO)} · "
              f"error main/sub: {pkg.main_code}/{pkg.sub_code} · errores de lectura: {read_errors or 'ninguno'}")

        moving_from = next((t for t, k, v in timeline if k == "robot_state" and v == 2), None)
        moving_to = next((t for t, k, v in timeline if k == "robot_state" and v == 1 and moving_from is not None
                          and t > moving_from), None)
        if moving_from is not None and moving_to is not None:
            inside = [s for s in track if moving_from <= s[0] <= moving_to]
            print(f"Poses distintas leídas por RPC mientras robot_state = 2 ({moving_to - moving_from:.2f} s): {len(inside)}")
        moving = [s for s in track if camera_sent_at is None or s[0] >= camera_sent_at]
        if len(moving) > 1:
            motion_start, motion_end = moving[1][0], moving[-1][0]
            lua_done = next((t for t, k, v in timeline if k == "estado Lua" and v == 3), None)
            print(f"Movimiento: de t={motion_start:.2f} s a t={motion_end:.2f} s · programa terminó en "
                  f"t={program_ended_at if program_ended_at is None else round(program_ended_at, 2)} s · "
                  f"Lua marcó 'terminado' en t={lua_done if lua_done is None else round(lua_done, 2)} s")
            if lua_done is not None and lua_done < motion_end:
                print(f"  → el Lua marcó 'terminado' {motion_end - lua_done:.2f} s ANTES de que el brazo se detuviera")

        route = []
        for i, sample in enumerate(track):
            if math.dist(sample[1][:3], first_waypoint) < ROUTE_START_TOL_MM:
                route = track[i:]
                break
        if len(route) > 1:
            errors = [aim_errors(pose, target, args.camera_offset) for _, pose, _ in route]
            aims = sorted(e[0] for e in errors)
            tilts = [abs(e[1]) for e in errors]
            p95 = aims[int(0.95 * (len(aims) - 1))]
            end_error = math.dist(route[-1][1][:3], last_waypoint[:3])
            print(f"\nRuta (desde el primer punto): {len(route)} poses en {route[-1][0] - route[0][0]:.2f} s")
            print(f"Eje óptico vs objetivo: medio {statistics.mean(aims):.3f}° · p95 {p95:.3f}° · máximo {aims[-1]:.3f}°")
            print(f"Inclinación del horizonte: máxima {max(tilts):.3f}°")
            print(f"Distancia final al último punto: {end_error:.2f} mm")
            if args.csv:
                with open(args.csv, "w", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow(["t_s", "x", "y", "z", "rx", "ry", "rz", "j1", "j2", "j3", "j4", "j5", "j6",
                                     "aim_deg", "tilt_deg"])
                    for (t, pose, joints), (aim, tilt) in zip(route, errors):
                        writer.writerow([f"{t:.3f}", *pose, *joints, f"{aim:.4f}", f"{tilt:.4f}"])
                print("CSV:", args.csv)
        else:
            print("\nAVISO: la brida nunca llegó al primer punto de la ruta; no se mide la fidelidad")
    finally:
        robot.CloseRPC()
    return 0 if final == 3 else 2


if __name__ == "__main__":
    sys.exit(main())
