#!/usr/bin/env python3
"""Elige la semilla de cinemática inversa de una ruta de grúa usando la IK del propio controlador FAIRINO.

Recorre la ruta de la brida con puntos intermedios en cada tramo MoveL (posición lineal, orientación por slerp)
y, para cada semilla candidata (las 8 configuraciones de GetInverseKin en el primer punto y las posturas que se
pasen con --extra-seed), encadena GetInverseKinRef punto a punto. Descarta las semillas sin solución o con saltos
bruscos de articulación y elige la que deja más margen respecto a los límites blandos del controlador.

  python3 planner.py --ip 192.168.58.2 --sdk ~/fairino_sdk_v2.2.3 --target -900 0 350 --standoff 350 \\
      --dz-start -150 --dz-end 250 --steps 6 --camera-offset 100 --samples 10 --max-jump 15 \\
      --extra-seed 0 -90 90 -90 -90 0
"""
import argparse
import math
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from routes import _add, camera_to_flange, crane_route, interpolate_pose  # noqa: E402


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ip", default=os.environ.get("FAIRINO_ROBOT_IP"))
    parser.add_argument("--sdk", default=os.environ.get("FAIRINO_SDK_PATH"))
    parser.add_argument("--target", type=float, nargs=3, required=True, metavar=("X", "Y", "Z"))
    parser.add_argument("--standoff", type=float, required=True)
    parser.add_argument("--azimuth", type=float, default=None)
    parser.add_argument("--dz-start", type=float, required=True)
    parser.add_argument("--dz-end", type=float, required=True)
    parser.add_argument("--steps", type=int, required=True)
    parser.add_argument("--camera-offset", type=float, required=True)
    parser.add_argument("--samples", type=int, required=True, help="puntos intermedios por tramo MoveL")
    parser.add_argument("--max-jump", type=float, required=True, help="salto máximo aceptable entre muestras, grados")
    parser.add_argument("--extra-seed", type=float, nargs=6, action="append", default=[], metavar="J")
    args = parser.parse_args()
    if not args.ip or not args.sdk:
        parser.error("faltan --ip y/o --sdk (o FAIRINO_ROBOT_IP / FAIRINO_SDK_PATH)")
    return args


def parse_limits(raw):
    """GetJointSoftLimitDeg → [(mín, máx)] por articulación; acepta lista plana de 12 o pares."""
    values = list(raw)
    if len(values) == 12:
        return [(min(values[2 * i], values[2 * i + 1]), max(values[2 * i], values[2 * i + 1])) for i in range(6)]
    raise ValueError(f"formato de límites no reconocido: {raw}")


def has_solution(result):
    return result is True or result == 1 or (isinstance(result, str) and result.strip().lower() == "true")


def main():
    args = parse_args()
    sys.path.insert(0, os.path.expanduser(args.sdk))
    from fairino import Robot

    target = tuple(args.target)
    azimuth = args.azimuth if args.azimuth is not None else math.degrees(math.atan2(-target[1], -target[0]))
    flange = camera_to_flange(crane_route(args.standoff, azimuth, args.dz_start, args.dz_end, args.steps),
                              args.camera_offset)
    waypoints = [(*_add(target, wp.offset), *wp.rpy) for wp in flange]
    samples = [waypoints[0]]
    for a, b in zip(waypoints, waypoints[1:]):
        samples += [interpolate_pose(a, b, k / args.samples) for k in range(1, args.samples + 1)]

    robot = Robot.RPC(args.ip)
    if not getattr(robot, "is_connect", getattr(robot, "is_conect", False)):
        print("ERROR: no hay conexión con el controlador", file=sys.stderr)
        return 1
    try:
        robot.ResetAllError()
        err, raw_limits = robot.GetJointSoftLimitDeg()
        print("GetJointSoftLimitDeg:", err, raw_limits)
        limits = parse_limits(raw_limits)

        seeds = []
        for config in range(8):
            err, joints = robot.GetInverseKin(0, list(waypoints[0]), config)
            if err == 0 and joints:
                seeds.append((f"config {config}", list(joints)))
        seeds += [(f"extra {i + 1}", list(s)) for i, s in enumerate(args.extra_seed)]

        print(f"{len(samples)} muestras de pose · {len(seeds)} semillas candidatas")
        results = []
        for name, seed in seeds:
            ref, reason, worst_margin, worst_joint, max_jump = seed, None, math.inf, None, 0.0
            for index, pose in enumerate(samples):
                err, result = robot.GetInverseKinHasSolution(0, list(pose), ref)
                if err != 0 or not has_solution(result):
                    reason = f"sin solución en la muestra {index}"
                    break
                err, joints = robot.GetInverseKinRef(0, list(pose), ref)
                if err != 0 or not joints:
                    reason = f"GetInverseKinRef falló ({err}) en la muestra {index}"
                    break
                jump = max(abs(a - b) for a, b in zip(joints, ref))
                if index > 0:
                    max_jump = max(max_jump, jump)
                for k, (value, (low, high)) in enumerate(zip(joints, limits)):
                    margin = min(value - low, high - value)
                    if margin < worst_margin:
                        worst_margin, worst_joint = margin, k + 1
                ref = list(joints)
            if reason is None and max_jump > args.max_jump:
                reason = f"salto de {max_jump:.1f}° entre muestras"
            results.append((name, seed, reason, worst_margin, worst_joint, max_jump, ref))

        print(f"{'semilla':<10} {'resultado':<34} {'margen mín':>11} {'art.':>5} {'salto máx':>10}  semilla (°)")
        for name, seed, reason, margin, joint, jump, _ in results:
            verdict = reason or "válida"
            margin_txt = f"{margin:.1f}°" if margin != math.inf else "-"
            print(f"{name:<10} {verdict:<34} {margin_txt:>11} {('j' + str(joint)) if joint else '-':>5} {jump:>9.1f}°  "
                  + ", ".join(f"{v:.2f}" for v in seed))

        valid = [r for r in results if r[2] is None and r[3] > 0]
        if not valid:
            print("\nNinguna semilla recorre la ruta dentro de los límites: cambia objetivo, standoff o alturas.")
            return 2
        best = max(valid, key=lambda r: r[3])
        print(f"\nMejor semilla: {best[0]} · margen mínimo {best[3]:.1f}° (j{best[4]}) · salto máximo {best[5]:.1f}°")
        print("--seed-joints " + " ".join(f"{v:.3f}" for v in best[1]))
    finally:
        robot.CloseRPC()
    return 0


if __name__ == "__main__":
    sys.exit(main())
