#!/usr/bin/env python3
"""Compara la réplica con datos del robot real y reporta los errores máximos.

Uso: python3 compare_golden.py datos.json
Todas las secciones del JSON son opcionales: meta, soft_limits, fk, ik, has_solution, reach.
"""
import json
import math
import sys

import kinematics_replica as rep
from kinematics_replica import fairino_rpy_to_rotation, kin


def _pose_error(a, b):
    pos = math.dist(a[:3], b[:3])
    rot = kin._rotation_error_deg(fairino_rpy_to_rotation(*a[3:]), fairino_rpy_to_rotation(*b[3:]))
    return pos, rot


def _fk(items):
    errors = [_pose_error(rep.get_forward_kin(i["joints"]), i["pose"]) for i in items]
    print(f"fk: {len(items)} casos · error máximo {max(e[0] for e in errors):.4g} mm · {max(e[1] for e in errors):.4g} °")


def _ik(items):
    worst_pos = worst_rot = 0.0
    failed = branch_hits = branch_total = 0
    for i in items:
        ref = i.get("ref")
        config = i.get("config", -1)
        try:
            joints = rep.get_inverse_kin(i["type"], i["pose"], config, ref)
        except rep.NoSolutionError:
            failed += 1
            continue
        target = rep._target_pose(i["type"], i["pose"], ref)
        pos, rot = _pose_error(rep.get_forward_kin(joints), target)
        worst_pos, worst_rot = max(worst_pos, pos), max(worst_rot, rot)
        if i.get("joints"):
            branch_total += 1
            branch_hits += rep.config_of(joints) == rep.config_of(i["joints"])
    print(f"ik: {len(items)} casos · sin solución {failed} · error de reproducción {worst_pos:.4g} mm · {worst_rot:.4g} °")
    print(f"ik: rama coincidente {branch_hits}/{branch_total}")


def _has_solution(items):
    wrong = [i for i in items if rep.get_inverse_kin_has_solution(i["type"], i["pose"], i["ref"]) != i["result"]]
    print(f"has_solution: {len(items)} casos · discrepancias {len(wrong)}")


def _reach(items):
    for n, i in enumerate(items):
        origin = rep.get_forward_kin(i["origin_joints"])
        norm = math.sqrt(sum(v * v for v in i["direction"]))
        unit = [v / norm for v in i["direction"]]

        def reachable(dist):
            pose = (*(origin[k] + unit[k] * dist for k in range(3)), *origin[3:])
            return rep.get_inverse_kin_has_solution(0, pose, i["origin_joints"])

        lo, hi = 0.0, 4000.0
        if not reachable(0.0):
            print(f"reach {n}: el origen no tiene solución en la réplica")
            continue
        for _ in range(60):
            mid = (lo + hi) / 2.0
            lo, hi = (mid, hi) if reachable(mid) else (lo, mid)
        print(f"reach {n}: réplica {lo:.2f} mm · robot {i['max_mm']:.2f} mm · diferencia {lo - i['max_mm']:+.2f} mm")


def _soft_limits(values):
    diff = max(abs(a - b) for a, b in zip(values, rep.get_joint_soft_limit_deg()))
    print(f"soft_limits: diferencia máxima {diff:.4g} °")


def main(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    print(f"meta: {data.get('meta', {})}")
    sections = [("soft_limits", _soft_limits), ("fk", _fk), ("ik", _ik),
                ("has_solution", _has_solution), ("reach", _reach)]
    for key, run in sections:
        if data.get(key):
            run(data[key])


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    main(sys.argv[1])
