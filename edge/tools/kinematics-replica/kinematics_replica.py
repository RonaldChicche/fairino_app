#!/usr/bin/env python3
"""Réplica cinemática del FAIRINO FR10: las funciones del SDK en snake_case sin robot.

Reutiliza `glambot-routes/kinematics.py` (FK y IK analítica de 8 ramas) y le pone la interfaz del
SDK. Unidades FAIRINO: mm y grados; pose = (x, y, z, rx, ry, rz) de la brida respecto a la base.
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "glambot-routes"))
import kinematics as kin  # noqa: E402
from routes import fairino_rpy_to_rotation, rotation_to_fairino_rpy  # noqa: E402

ABSOLUTE, RELATIVE_BASE, RELATIVE_TOOL = 0, 1, 2

# Rama (hombro, codo, muñeca) -> config 0..7. Cada índice es 0 si: hombro con la muñeca por delante
# del eje de j1, codo con j3 >= 0, muñeca con j5 >= 0. SUPOSICIÓN: orden binario hombro*4 + codo*2 +
# muñeca; falta validarlo con datos del robot real (editar aquí si no coincide).
CONFIG_BY_BRANCH = {
    (0, 0, 0): 0, (0, 0, 1): 1, (0, 1, 0): 2, (0, 1, 1): 3,
    (1, 0, 0): 4, (1, 0, 1): 5, (1, 1, 0): 6, (1, 1, 1): 7,
}


class NoSolutionError(ValueError):
    pass


def get_joint_soft_limit_deg():
    """[j1 min, j1 max, j2 min, j2 max, ...] en grados."""
    return [v for pair in kin.JOINT_LIMITS_DEG for v in pair]


def get_forward_kin(joints):
    return list(kin.forward(joints))


def config_of(joints):
    """Número de rama (0 a 7) de una postura, según CONFIG_BY_BRANCH."""
    wrist = kin._chain(joints)[4][1]
    t1 = math.radians(joints[0])
    front = wrist[0] * math.cos(t1) + wrist[1] * math.sin(t1) >= 0.0
    return CONFIG_BY_BRANCH[(0 if front else 1, 0 if joints[2] >= 0 else 1, 0 if joints[4] >= 0 else 1)]


def _target_pose(type, pose, ref):
    if type == ABSOLUTE:
        return tuple(pose)
    if type not in (RELATIVE_BASE, RELATIVE_TOOL):
        raise ValueError(f"type debe ser 0, 1 o 2, no {type!r}")
    if ref is None:
        raise ValueError("los tipos relativos necesitan ref (la postura actual)")
    base = kin.forward(ref)
    base_rot = fairino_rpy_to_rotation(*base[3:])
    delta_rot = fairino_rpy_to_rotation(*pose[3:])
    if type == RELATIVE_BASE:
        move = pose[:3]
        rot = kin._mat_mul(delta_rot, base_rot)
    else:
        move = kin._mat_vec(base_rot, pose[:3])
        rot = kin._mat_mul(base_rot, delta_rot)
    return (*(base[i] + move[i] for i in range(3)), *rotation_to_fairino_rpy(rot))


def _solutions(type, pose, ref):
    return kin.inverse(_target_pose(type, pose, ref), ref)


def get_inverse_kin(type, pose, config=-1, ref=None):
    """Postura articular para la pose. config -1: la rama más cercana a ref (o la primera sin ref)."""
    solutions = _solutions(type, pose, ref)
    if config != -1:
        if not 0 <= config <= 7:
            raise ValueError(f"config debe ser -1 o 0 a 7, no {config!r}")
        solutions = [j for j in solutions if config_of(j) == config]
    if not solutions:
        raise NoSolutionError("sin solución dentro de límites" + (f" en la rama {config}" if config != -1 else ""))
    return solutions[0]


def get_inverse_kin_ref(type, pose, ref):
    return get_inverse_kin(type, pose, -1, ref)


def get_inverse_kin_has_solution(type, pose, ref):
    return bool(_solutions(type, pose, ref))
