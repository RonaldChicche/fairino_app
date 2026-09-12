#!/usr/bin/env python3
"""Valida una ruta FR10 con la IK del controlador y calcula la altura de J2..J6.

Solo usa consultas: no habilita el robot, no borra alarmas y no envía movimientos.
La geometría de los ejes sigue el URDF oficial fairino10_v6.
"""
import argparse
import json
import math
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))

from routes import _add, camera_to_flange, interpolate_pose, route_from_spec  # noqa: E402


def matmul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]


def origin(x, y, z, rx=0.0, ry=0.0, rz=0.0):
    cr, sr = math.cos(rx), math.sin(rx)
    cp, sp = math.cos(ry), math.sin(ry)
    cy, sy = math.cos(rz), math.sin(rz)
    return [
        [cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr, x],
        [sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr, y],
        [-sp, cp * sr, cp * cr, z],
        [0.0, 0.0, 0.0, 1.0],
    ]


def rotz(angle):
    c, s = math.cos(angle), math.sin(angle)
    return [[c, -s, 0.0, 0.0], [s, c, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0], [0.0, 0.0, 0.0, 1.0]]


# Orígenes de ejes en mm/radianes, copiados del URDF oficial del FR10 V6.
JOINT_ORIGINS = [
    (0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
    (0.0, 0.0, 180.0, math.pi / 2, 0.0, 0.0),
    (-700.0, 0.0, 0.0, 0.0, 0.0, 0.0),
    (-586.0, 0.0, 0.0, 0.0, 0.0, 0.0),
    (0.0, 0.0, 159.0, math.pi / 2, 0.0, 0.0),
    (0.0, 0.0, 114.0, -math.pi / 2, 0.0, 0.0),
]


def joint_positions(joints_deg):
    transform = origin(0.0, 0.0, 0.0)
    positions = []
    for joint_origin, angle in zip(JOINT_ORIGINS, joints_deg):
        transform = matmul(transform, origin(*joint_origin))
        positions.append(tuple(transform[i][3] for i in range(3)))
        transform = matmul(transform, rotz(math.radians(angle)))
    return positions


def has_solution(value):
    return value is True or value == 1 or (isinstance(value, str) and value.strip().lower() == "true")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec", type=Path)
    parser.add_argument("--ip", default=os.environ.get("FAIRINO_ROBOT_IP", "192.168.58.2"))
    parser.add_argument("--samples", type=int, default=24, help="intervalos por tramo")
    parser.add_argument("--clearance", type=float, default=50.0, help="altura mínima J2..J6, mm")
    args = parser.parse_args()

    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    target = tuple(float(v) for v in spec["target"])
    camera_route = route_from_spec(spec)
    flange_route = camera_to_flange(camera_route, float(spec["camera"]["offset_mm"]))
    waypoints = [(*_add(target, wp.offset), *wp.rpy) for wp in flange_route]
    poses = [waypoints[0]]
    for a, b in zip(waypoints, waypoints[1:]):
        poses.extend(interpolate_pose(a, b, k / args.samples) for k in range(1, args.samples + 1))

    from fairino import Robot

    robot = Robot.RPC(args.ip)
    if not getattr(robot, "is_connect", getattr(robot, "is_conect", False)):
        print("ERROR: no hay conexión con el controlador", file=sys.stderr)
        return 1
    try:
        error, raw_limits = robot.GetJointSoftLimitDeg()
        if error != 0 or len(raw_limits) != 12:
            print(f"ERROR: no se pudieron leer los límites articulares ({error})", file=sys.stderr)
            return 1
        limits = [(min(raw_limits[2 * i:2 * i + 2]), max(raw_limits[2 * i:2 * i + 2])) for i in range(6)]
        error, current = robot.GetActualJointPosDegree()
        if error != 0 or not current:
            print(f"ERROR: no se pudo leer la postura actual ({error})", file=sys.stderr)
            return 1
        current = list(current)
        print("ACTUAL " + " ".join(f"{value:.4f}" for value in current))
        candidates = []
        for config in range(8):
            error, seed = robot.GetInverseKin(0, list(poses[0]), config)
            if error == 0 and seed:
                candidates.append((config, list(seed)))

        valid = []
        for config, seed in candidates:
            ref = seed
            rows = []
            reason = None
            max_jump = 0.0
            min_margin = math.inf
            for index, pose in enumerate(poses):
                error, result = robot.GetInverseKinHasSolution(0, list(pose), ref)
                if error != 0 or not has_solution(result):
                    reason = f"IK {error} en muestra {index}"
                    break
                error, joints = robot.GetInverseKinRef(0, list(pose), ref)
                if error != 0 or not joints:
                    reason = f"IKRef {error} en muestra {index}"
                    break
                if index:
                    max_jump = max(max_jump, max(abs(a - b) for a, b in zip(joints, ref)))
                margin = min(min(value - low, high - value) for value, (low, high) in zip(joints, limits))
                min_margin = min(min_margin, margin)
                if margin < 0:
                    reason = f"fuera de límite articular en muestra {index}"
                    break
                points = joint_positions(joints)
                rows.append((index, list(joints), points))
                ref = list(joints)
            if reason is not None:
                print(f"config {config}: {reason}")
                continue
            minimum = min(point[2] for _, _, points in rows for point in points[1:])
            worst = min(
                ((point[2], index, joint + 1) for index, _, points in rows for joint, point in enumerate(points[1:], 1)),
                key=lambda item: item[0],
            )
            approach = [
                [a + (b - a) * step / 100 for a, b in zip(current, seed)]
                for step in range(101)
            ]
            approach_min = min(point[2] for joints in approach for point in joint_positions(joints)[1:])
            print(
                f"config {config}: altura mínima {minimum:.1f} mm (muestra {worst[1]}, J{worst[2]}), "
                f"aproximación MoveJ {approach_min:.1f} mm, margen articular {min_margin:.1f}°, "
                f"salto máximo {max_jump:.1f}°"
            )
            if min(minimum, approach_min) >= args.clearance:
                valid.append((min(minimum, approach_min), min_margin, config, seed, rows))

        if not valid:
            print(f"NINGUNA configuración mantiene J2..J6 a {args.clearance:.1f} mm o más")
            return 2

        minimum, min_margin, config, seed, rows = max(valid, key=lambda item: (item[1], item[0]))
        waypoint_indices = [i * args.samples for i in range(len(waypoints))]
        print(f"ELEGIDA config {config}; mínimo global {minimum:.1f} mm; margen articular {min_margin:.1f}°")
        print("SEMILLA " + " ".join(f"{value:.4f}" for value in seed))
        for number, index in enumerate(waypoint_indices, 1):
            _, joints, points = rows[index]
            heights = " ".join(f"J{i + 1}={point[2]:.1f}" for i, point in enumerate(points))
            print(f"P{number} JOINTS " + " ".join(f"{value:.3f}" for value in joints))
            print(f"P{number} HEIGHTS {heights}")
        for index, joints, points in rows:
            camera = poses[index][:3]
            print("DATA " + json.dumps({
                "i": index,
                "tcp": [round(v, 3) for v in camera],
                "joints": [[round(v, 3) for v in point] for point in points],
                "angles": [round(v, 3) for v in joints],
            }, separators=(",", ":")))
    finally:
        robot.CloseRPC()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
