#!/usr/bin/env python3
"""Cinemática directa e inversa del FAIRINO FR10 en Python puro, para validar rutas sin robot.

Unidades FAIRINO: mm y grados. Las poses son de la BRIDA respecto a la base, con la orientación
en la convención de `routes.py`: R = Rz(rz) · Ry(ry) · Rx(rx).

Geometría deducida del URDF oficial del fabricante, repo `FAIR-INNOVATION/frcobot_ros2`,
commit 5bed0b0263c8f1e95f51aa45079f904d463c5c50, `fairino_description/urdf/fairino10_v6.urdf`
(metros y radianes en el origen; aquí ya convertidos).

La cadena del URDF es la de un brazo colaborativo tipo UR: los ejes 4, 5 y 6 NO se cortan en un
punto (la muñeca no es esférica), pero los ejes 2, 3 y 4 son paralelos y los pares 4-5 y 5-6 son
perpendiculares, así que sigue habiendo solución cerrada con 8 ramas. La excepción es j5 = 0: ahí
los ejes 4 y 6 se alinean, las soluciones dejan de ser 8 puntos y pasan a ser una familia continua,
y `_ik_branches` recorre el parámetro libre en lugar de resolverlo.

La correspondencia de ceros y signos entre los ángulos del URDF y los del controlador FAIRINO NO
está verificada contra el robot: todo lo de aquí es coherente consigo mismo y con el URDF, nada más.

Uso:
  python3 kinematics.py            # demostración rápida
"""
import math
import os
import sys

# routes.py vive junto a este archivo, pero quien nos importe puede estar en otro directorio.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from routes import fairino_rpy_to_rotation, rotation_to_fairino_rpy  # noqa: E402

# Límites `lower`/`upper` del URDF, redondeados al grado (los valores en radianes son grados
# exactos con 5 cifras). Coinciden con los límites blandos medidos en el FR5 salvo j3 (±160° allí).
JOINT_LIMITS_DEG = [
    (-175.0, 175.0),
    (-265.0, 85.0),
    (-162.0, 162.0),
    (-265.0, 85.0),
    (-175.0, 175.0),
    (-175.0, 175.0),
]

# Denavit-Hartenberg clásico: T_i = Rz(theta_i) · Tz(d_i) · Tx(a_i) · Rx(alpha_i).
# d1 del origen de j2; a2, a3 de los `xyz` negativos de j3 y j4; d4, d5 de los de j5 y j6.
D1 = 180.0
A2 = -700.0
A3 = -586.0
D4 = 159.0
D5 = 114.0
# El URDF termina en wrist3_link: no hay ni articulación ni eslabón después de j6, así que la brida
# del modelo coincide con el origen de ese marco. (Que |A2| + |A3| + D5 dé los 1400 mm de catálogo
# no lo confirma: el radio horizontal máximo de esta cadena es 1409 mm, no 1400.)
D6 = 0.0

ALPHA = (math.pi / 2, 0.0, 0.0, math.pi / 2, -math.pi / 2, 0.0)
D = (D1, 0.0, 0.0, D4, D5, D6)
A = (0.0, A2, A3, 0.0, 0.0, 0.0)

# En el plano del brazo, la brida queda entre NEAR_MM y REACH_MM del hombro. El máximo es el brazo
# estirado; el mínimo, el codo plegado hasta el límite de j3 (con j3 = ±180 sería 0, pero no llega).
REACH_MM = abs(A2) + abs(A3) + D5
_J3_MAX_DEG = min(180.0, max(abs(JOINT_LIMITS_DEG[2][0]), abs(JOINT_LIMITS_DEG[2][1])))
NEAR_MM = max(math.sqrt(A2 * A2 + A3 * A3 + 2 * A2 * A3 * math.cos(math.radians(_J3_MAX_DEG))) - D5, 0.0)

_EPS = 1e-9
_POS_TOL_MM = 1e-4
_ROT_TOL_DEG = 1e-4
# Por debajo de este |sin(j5)| la muñeca es singular y t6 deja de estar determinado (ver `_ik_branches`).
_SINGULAR_SIN5 = 1e-7
_WRIST_FAMILY_STEP_DEG = 2.0


def _rz(t):
    c, s = math.cos(t), math.sin(t)
    return ((c, -s, 0.0), (s, c, 0.0), (0.0, 0.0, 1.0))


def _rx(t):
    c, s = math.cos(t), math.sin(t)
    return ((1.0, 0.0, 0.0), (0.0, c, -s), (0.0, s, c))


def _mat_mul(a, b):
    return tuple(tuple(sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)) for i in range(3))


def _mat_vec(m, v):
    return tuple(sum(m[i][k] * v[k] for k in range(3)) for i in range(3))


def _transpose(m):
    return tuple(tuple(m[j][i] for j in range(3)) for i in range(3))


def _clamp(v, lo=-1.0, hi=1.0):
    return lo if v < lo else hi if v > hi else v


def _wrap180(deg):
    return (deg + 180.0) % 360.0 - 180.0


def _dh_frame(theta, d, a, alpha):
    rot = _mat_mul(_rz(theta), _rx(alpha))
    pos = (a * math.cos(theta), a * math.sin(theta), d)
    return rot, pos


def _chain(joints_deg):
    """Rotación y origen acumulados de cada marco DH, desde la base hasta la brida."""
    rot = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
    pos = (0.0, 0.0, 0.0)
    frames = [(rot, pos)]
    for i, q in enumerate(joints_deg):
        r_i, p_i = _dh_frame(math.radians(q), D[i], A[i], ALPHA[i])
        moved = _mat_vec(rot, p_i)
        pos = tuple(pos[k] + moved[k] for k in range(3))
        rot = _mat_mul(rot, r_i)
        frames.append((rot, pos))
    return frames


def forward(joints_deg):
    """Ángulos articulares en grados → pose de la brida (x, y, z, rx, ry, rz) en mm y grados."""
    rot, pos = _chain(joints_deg)[-1]
    return (*pos, *rotation_to_fairino_rpy(rot))


def link_points(joints_deg):
    """Orígenes de los marcos, de la base a la brida, para dibujar el brazo "en palitos"."""
    # El marco 6 coincide con el 5 porque D6 = 0: se omite para no dibujar un segmento nulo.
    return [frame[1] for frame in _chain(joints_deg)[:6]]


def _pose_parts(pose):
    x, y, z, rx, ry, rz = pose
    return (x, y, z), fairino_rpy_to_rotation(rx, ry, rz)


def _rotation_error_deg(a, b):
    prod = _mat_mul(_transpose(a), b)
    trace = prod[0][0] + prod[1][1] + prod[2][2]
    return math.degrees(math.acos(_clamp((trace - 1.0) / 2.0)))


def _wrist_family_t6(seed6):
    """Muestreo del parámetro libre de la muñeca singular, empezando por el valor de la semilla."""
    step = math.radians(_WRIST_FAMILY_STEP_DEG)
    count = int(round(2.0 * math.pi / step))
    return [seed6 + k * step for k in range(count)]


def _pick_per_elbow(candidates, seed_joints_deg):
    """De cada rama de codo del abanico singular, la muestra que mejor entra en límites."""
    best = {}
    for key, branch in candidates:
        fitted = [_fit_to_limits(i, v) for i, v in enumerate(branch)]
        excess = sum(e for _, e in fitted)
        gap = sum((v - s) ** 2 for (v, _), s in zip(fitted, seed_joints_deg)) if seed_joints_deg else 0.0
        if key not in best or (excess, gap) < best[key][0]:
            best[key] = ((excess, gap), branch)
    return [branch for _, branch in best.values()]


def _ik_branches(pose, seed_joints_deg=None):
    """Las hasta 8 ramas, en grados y sin filtrar por límites (4 si la muñeca es singular)."""
    pos, rot = _pose_parts(pose)
    (r11, r12, r13), (r21, r22, r23), _ = rot
    seed6 = math.radians(seed_joints_deg[5]) if seed_joints_deg else 0.0

    radius = math.hypot(pos[0], pos[1])
    if radius < abs(D4) - _EPS:
        return []

    # j1 sale de que, en el marco 1, la brida siempre queda a una altura fija D4.
    phi = math.atan2(pos[1], pos[0])
    offset = math.asin(_clamp(D4 / radius))
    out = []
    for t1 in (phi + offset, phi + math.pi - offset):
        c1, s1 = math.cos(t1), math.sin(t1)
        r01 = _mat_mul(_rz(t1), _rx(math.pi / 2))
        shifted = _mat_vec(_rz(-t1), pos)
        p15 = _mat_vec(_rx(-math.pi / 2), (shifted[0], shifted[1], shifted[2] - D1))
        # cos(j5) es el coseno del ángulo entre el eje Z de la brida y el eje de j2.
        cos5 = _clamp(s1 * r13 - c1 * r23)
        half = math.acos(cos5)
        # Con sin(j5) = 0 las dos ramas de muñeca coinciden: recorrerlas dos veces solo duplica trabajo.
        for t5 in ((half,) if abs(math.sin(half)) < _SINGULAR_SIN5 else (half, -half)):
            s5 = math.sin(t5)
            # Con j5 = 0 los ejes 4 y 6 se alinean y la orientación solo fija la suma t234 + t6: las
            # soluciones son una familia continua, no un conjunto discreto que se pueda cerrar en una
            # fórmula. Se recorre el parámetro libre y se conserva la muestra que entre en límites;
            # fijar t6 = semilla dejaba fuera poses alcanzables (~5 % de las que tienen j5 = 0).
            singular = abs(s5) < _SINGULAR_SIN5
            if singular:
                t6_options = _wrist_family_t6(seed6)
            else:
                t6_options = (math.atan2((r22 * c1 - r12 * s1) / s5, (r11 * s1 - r21 * c1) / s5),)
            family = []
            for t6 in t6_options:
                r46 = _mat_mul(_mat_mul(_rz(t5), _rx(-math.pi / 2)), _rz(t6))
                r14 = _mat_mul(_mat_mul(_transpose(r01), rot), _transpose(r46))
                t234 = math.atan2(r14[1][0], r14[0][0])

                px = p15[0] - D5 * math.sin(t234)
                py = p15[1] + D5 * math.cos(t234)

                cos3 = (px * px + py * py - A2 * A2 - A3 * A3) / (2.0 * A2 * A3)
                if abs(cos3) > 1.0 + 1e-9:
                    continue
                for elbow, t3 in enumerate((math.acos(_clamp(cos3)), -math.acos(_clamp(cos3)))):
                    t2 = math.atan2(py, px) - math.atan2(A3 * math.sin(t3), A2 + A3 * math.cos(t3))
                    t4 = t234 - t2 - t3
                    branch = [math.degrees(v) for v in (t1, t2, t3, t4, t5, t6)]
                    if singular:
                        family.append((elbow, branch))
                    else:
                        out.append(branch)
            if singular:
                out.extend(_pick_per_elbow(family, seed_joints_deg))
    return out


def _fit_to_limits(index, deg):
    """Representante del ángulo dentro de los límites y cuánto se pasa (0 si entra)."""
    lo, hi = JOINT_LIMITS_DEG[index]
    base = _wrap180(deg)
    best = None
    for k in (-1, 0, 1):
        v = base + 360.0 * k
        excess = max(lo - v, v - hi, 0.0)
        if best is None or excess < best[1]:
            best = (v, excess)
    return best


def _reproduces(joints_deg, pose):
    pos, rot = _pose_parts(pose)
    got_rot, got_pos = _chain(joints_deg)[-1]
    err_mm = math.dist(got_pos, pos)
    return err_mm < _POS_TOL_MM and _rotation_error_deg(got_rot, rot) < _ROT_TOL_DEG


def inverse(pose, seed_joints_deg=None):
    """Pose de la brida → todas las soluciones dentro de límites, la más cercana a la semilla primero."""
    solutions = []
    for branch in _ik_branches(pose, seed_joints_deg):
        fitted = [_fit_to_limits(i, v) for i, v in enumerate(branch)]
        if any(excess > _EPS for _, excess in fitted):
            continue
        joints = [v for v, _ in fitted]
        if not _reproduces(joints, pose):
            continue
        if any(all(abs(a - b) < 1e-4 for a, b in zip(joints, prev)) for prev in solutions):
            continue
        solutions.append(joints)

    if seed_joints_deg:
        solutions.sort(key=lambda j: sum((a - b) ** 2 for a, b in zip(j, seed_joints_deg)))
    return solutions


def _out_of_reach(pose):
    """Por qué lado de la envolvente cae la brida ("eje", "cerca", "lejos" o None) y a cuánto.

    La brida está siempre a D4 del plano del brazo, que contiene el eje de j1: de ahí salen dos
    cotas exactas, que nunca se acerque más de D4 a ese eje y que en el plano quede entre NEAR_MM
    y REACH_MM del hombro. Las tres son necesarias, así que no rechazan nada alcanzable.
    """
    x, y, z, _, _, _ = pose
    radius = math.hypot(x, y)
    if radius < abs(D4) - _EPS:
        return "eje", radius
    span = math.sqrt(x * x + y * y + (z - D1) * (z - D1))
    planar = math.sqrt(max(span * span - D4 * D4, 0.0))
    if planar < NEAR_MM - _EPS:
        return "cerca", planar
    if planar > REACH_MM + _EPS:
        return "lejos", planar
    return None, planar


def check(pose, seed_joints_deg=None):
    """Diagnóstico de un punto de ruta: si es alcanzable y, si no, por qué."""
    if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in pose):
        return {"ok": False, "joints": None, "reason": "sin solución",
                "detail": "la pose no es un sexteto de números finitos"}

    side, distance = _out_of_reach(pose)
    details = {
        "lejos": f"el punto queda a {distance:.1f} mm del hombro en el plano del brazo y el alcance "
                 f"es {REACH_MM:.0f} mm",
        "cerca": f"el punto queda a {distance:.1f} mm del hombro en el plano del brazo y el brazo no "
                 f"se pliega por debajo de {NEAR_MM:.0f} mm",
        "eje": f"el punto queda a {distance:.1f} mm del eje de j1 y la brida nunca se le acerca a "
               f"menos de {abs(D4):.0f} mm",
    }
    if side is not None:
        return {"ok": False, "joints": None, "reason": "fuera de alcance", "detail": details[side]}

    solutions = inverse(pose, seed_joints_deg)
    if solutions:
        return {"ok": True, "joints": solutions[0], "reason": None, "detail": ""}

    branches = _ik_branches(pose, seed_joints_deg)
    if not branches:
        return {"ok": False, "joints": None, "reason": "sin solución",
                "detail": "la geometría del brazo no llega a esa pose con esa orientación"}

    # Solo puede culparse a un límite una rama que de verdad sea solución: las que salen de recortar
    # un coseno al borde reproducen otra pose y culparían a la articulación equivocada.
    scored = []
    for branch in branches:
        fitted = [_fit_to_limits(i, v) for i, v in enumerate(branch)]
        if _reproduces([v for v, _ in fitted], pose):
            scored.append((sum(e for _, e in fitted), fitted))
    if not scored:
        return {"ok": False, "joints": None, "reason": "sin solución",
                "detail": "ninguna rama analítica reproduce la pose pedida"}

    _, fitted = min(scored, key=lambda item: item[0])
    index = max(range(6), key=lambda i: fitted[i][1])
    value, _ = fitted[index]
    lo, hi = JOINT_LIMITS_DEG[index]
    bound, verb = (hi, "supera el límite de") if value > hi else (lo, "queda por debajo del límite de")
    return {"ok": False, "joints": None, "reason": "límite articular",
            "detail": f"j{index + 1} = {value:.1f}° {verb} {bound:.0f}°"}


def main():
    home = [0.0, -90.0, 90.0, -90.0, -90.0, 0.0]
    pose = forward(home)
    print("postura inicial  ", " ".join(f"{v:8.2f}" for v in home))
    print("pose de la brida ", " ".join(f"{v:8.2f}" for v in pose))
    print("palitos          ", " ".join(f"({p[0]:.0f},{p[1]:.0f},{p[2]:.0f})" for p in link_points(home)))
    print(f"soluciones de IK : {len(inverse(pose, home))}")
    print("fuera de alcance :", check((3000.0, 0.0, 500.0, 0.0, 0.0, 0.0)))


if __name__ == "__main__":
    main()
