#!/usr/bin/env python3
"""Pruebas de `kinematics.py`. Se ejecutan con `python3 test_kinematics.py`.

Cubre ida y vuelta FK→IK, respeto de los límites articulares, un punto inalcanzable y un contraste
de convención contra la única ejecución real documentada (un FR5, ver NOTAS.md).
"""
import math
import random

import kinematics as kin
from routes import fairino_rpy_to_rotation, rotation_to_fairino_rpy

SAMPLES = 2000
POS_TOL_MM = 0.1
ROT_TOL_DEG = 0.01


def _rotation_error_deg(a, b):
    prod = [[sum(a[k][i] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
    trace = prod[0][0] + prod[1][1] + prod[2][2]
    return math.degrees(math.acos(max(-1.0, min(1.0, (trace - 1.0) / 2.0))))


def _pose_error(pose_a, pose_b):
    pos = math.dist(pose_a[:3], pose_b[:3])
    rot = _rotation_error_deg(fairino_rpy_to_rotation(*pose_a[3:]), fairino_rpy_to_rotation(*pose_b[3:]))
    return pos, rot


def _random_joints(rng):
    return [rng.uniform(lo, hi) for lo, hi in kin.JOINT_LIMITS_DEG]


def test_roundtrip(rng):
    print(f"\n1) Ida y vuelta sobre {SAMPLES} posturas aleatorias dentro de límites")
    # Sin semilla: con `joints` de semilla la solución exacta queda siempre la primera y el error
    # de `solutions[0]` sale trivialmente cero. Se miden TODAS las ramas, no solo la primera.
    worst_pos = worst_rot = 0.0
    empty = 0
    unrecovered = 0
    worst_gap = 0.0
    worst_case = None
    for _ in range(SAMPLES):
        joints = _random_joints(rng)
        pose = kin.forward(joints)
        solutions = kin.inverse(pose)
        if not solutions:
            empty += 1
            continue
        for solution in solutions:
            pos, rot = _pose_error(kin.forward(solution), pose)
            if pos > worst_pos:
                worst_pos = pos
            if rot > worst_rot:
                worst_rot = rot
                worst_case = joints
        gap = min(max(abs(a - b) for a, b in zip(joints, s)) for s in solutions)
        worst_gap = max(worst_gap, gap)
        if gap > 1e-3:
            unrecovered += 1
    print(f"   sin solución: {empty} de {SAMPLES}")
    print(f"   la postura original no aparece entre las soluciones: {unrecovered} de {SAMPLES}")
    print(f"   peor distancia articular a la postura original: {worst_gap:.3e} °")
    print(f"   error máximo de posición: {worst_pos:.3e} mm  (tolerancia {POS_TOL_MM} mm)")
    print(f"   error máximo de orientación: {worst_rot:.3e} °  (tolerancia {ROT_TOL_DEG} °)")
    if worst_case:
        print(f"   peor postura: {' '.join(f'{v:.2f}' for v in worst_case)}")
    ok = empty == 0 and unrecovered == 0 and worst_pos < POS_TOL_MM and worst_rot < ROT_TOL_DEG
    print(f"   {'OK' if ok else 'FALLO'}")
    return ok


def test_limits(rng):
    print(f"\n2) Ninguna solución de `inverse` se sale de los límites ({SAMPLES} posturas)")
    checked = 0
    worst_margin = 1e9
    bad = []
    for _ in range(SAMPLES):
        pose = kin.forward(_random_joints(rng))
        for solution in kin.inverse(pose):
            checked += 1
            for i, value in enumerate(solution):
                lo, hi = kin.JOINT_LIMITS_DEG[i]
                worst_margin = min(worst_margin, value - lo, hi - value)
                if value < lo or value > hi:
                    bad.append((i + 1, value))
    print(f"   soluciones revisadas: {checked}")
    print(f"   margen mínimo al límite: {worst_margin:.4f} °")
    print(f"   soluciones fuera de límites: {len(bad)}")
    ok = not bad
    print(f"   {'OK' if ok else 'FALLO'}")
    return ok


def test_unreachable():
    print("\n3) Punto claramente inalcanzable (3000 mm de la base)")
    ok = True
    for pose in [(3000.0, 0.0, 400.0, 0.0, 0.0, 0.0),
                 (0.0, 3000.0, 400.0, 0.0, 90.0, 0.0),
                 (-2000.0, 2000.0, 1500.0, 10.0, 20.0, 30.0)]:
        result = kin.check(pose)
        good = result["ok"] is False and result["reason"] == "fuera de alcance"
        ok = ok and good
        print(f"   {pose[:3]} -> ok={result['ok']} reason={result['reason']!r}")
        print(f"      {result['detail']}")
    reachable = kin.check(kin.forward([0.0, -90.0, 90.0, -90.0, -90.0, 0.0]))
    ok = ok and reachable["ok"]
    print(f"   contraste, postura inicial alcanzable: ok={reachable['ok']}")
    print(f"   {'OK' if ok else 'FALLO'}")
    return ok


def test_fr5_convention():
    """Contraste de convención con la ejecución real del FR5 (NOTAS.md): NO valida números del FR10.

    El controlador terminó en (−468,6; 0; 658,1; −125,5°) apuntando al objetivo (−900, 0, 350) con
    la cámara a 100 mm sobre el eje Z de la brida y un standoff de 350 mm, 250 mm por encima del
    objetivo. Si el criterio de ejes o el signo de los ángulos estuviera invertido, el eje óptico
    apuntaría a otro lado.
    """
    print("\n4) Contraste de convención con la ejecución real del FR5 (no valida el FR10)")
    flange = (-468.6, 0.0, 658.1)
    pose = (*flange, 0.0, -125.5, 0.0)
    target = (-900.0, 0.0, 350.0)

    rot = fairino_rpy_to_rotation(*pose[3:])
    optical = tuple(rot[r][2] for r in range(3))
    to_target = [t - f for t, f in zip(target, flange)]
    length = math.dist(target, flange)
    to_target = [v / length for v in to_target]
    aim_deg = math.degrees(math.acos(max(-1.0, min(1.0, sum(a * b for a, b in zip(optical, to_target))))))

    camera = tuple(f + 100.0 * o for f, o in zip(flange, optical))
    standoff = math.hypot(camera[0] - target[0], camera[1] - target[1])
    rise = camera[2] - target[2]

    print(f"   eje óptico de la brida: ({optical[0]:.4f}, {optical[1]:.4f}, {optical[2]:.4f})")
    print(f"   error de apuntado al objetivo: {aim_deg:.4f} °")
    print(f"   cámara reconstruida: ({camera[0]:.1f}, {camera[1]:.1f}, {camera[2]:.1f})")
    print(f"   standoff {standoff:.1f} mm (documentado 350) · altura {rise:.1f} mm (documentado 250)")

    fk_ok = True
    solutions = kin.inverse(pose)
    print(f"   ramas del FR10 para esa pose: {len(solutions)}")
    if solutions:
        pos_err, rot_err = _pose_error(kin.forward(solutions[0]), pose)
        print(f"   FK(IK) sobre la pose real: {pos_err:.3e} mm · {rot_err:.3e} °")
        fk_ok = pos_err < POS_TOL_MM and rot_err < ROT_TOL_DEG

    # NOTAS.md redondea la pose a 0,1 mm y 0,1°, lo que ya vale ~0,03° de apuntado a 530 mm.
    # Un criterio de ejes o un signo invertidos darían decenas de grados, no centésimas.
    ok = aim_deg < 0.1 and abs(standoff - 350.0) < 1.0 and abs(rise - 250.0) < 1.0 and fk_ok
    print(f"   {'OK' if ok else 'FALLO'}")
    return ok


def test_seed_order():
    print("\n5) `inverse` ordena por cercanía a la semilla")
    seed = [10.0, -100.0, 80.0, -70.0, -95.0, 15.0]
    pose = kin.forward(seed)
    solutions = kin.inverse(pose, seed)
    distances = [math.dist(s, seed) for s in solutions]
    print(f"   {len(solutions)} soluciones, distancias: {' '.join(f'{d:.1f}' for d in distances)}")
    ok = bool(solutions) and distances == sorted(distances) and distances[0] < 1e-6
    print(f"   {'OK' if ok else 'FALLO'}")
    return ok


# `<origin xyz rpy>` de las 6 articulaciones, copiados literalmente del URDF (metros y radianes).
# El `rpy` del URDF es Rz(y)·Ry(p)·Rx(r) y aquí solo el primer valor es distinto de cero.
URDF_ORIGINS = [
    ((0.0, 0.0, 0.0), 0.0),
    ((0.0, 0.0, 0.18), 1.5708),
    ((-0.7, 0.0, 0.0), 0.0),
    ((-0.586, 0.0, 0.0), 0.0),
    ((0.0, 0.0, 0.159), 1.5708),
    ((0.0, 0.0, 0.114), -1.5708),
]


def _urdf_forward(joints_deg):
    """FK construida directamente desde la cadena del URDF, sin pasar por los parámetros DH."""
    def rz(t):
        c, s = math.cos(t), math.sin(t)
        return ((c, -s, 0.0), (s, c, 0.0), (0.0, 0.0, 1.0))

    def rx(t):
        c, s = math.cos(t), math.sin(t)
        return ((1.0, 0.0, 0.0), (0.0, c, -s), (0.0, s, c))

    def mul(a, b):
        return tuple(tuple(sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)) for i in range(3))

    def vec(m, v):
        return tuple(sum(m[i][k] * v[k] for k in range(3)) for i in range(3))

    rot = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
    pos = (0.0, 0.0, 0.0)
    for (xyz, roll), q in zip(URDF_ORIGINS, joints_deg):
        moved = vec(rot, tuple(v * 1000.0 for v in xyz))
        pos = tuple(pos[k] + moved[k] for k in range(3))
        rot = mul(mul(rot, rx(roll)), rz(math.radians(q)))
    return rot, pos


def test_against_urdf(rng):
    print("\n6) FK contra la cadena cruda del URDF (valida la reducción a parámetros DH)")
    worst_pos = worst_rot = 0.0
    for _ in range(500):
        joints = _random_joints(rng)
        rot, pos = _urdf_forward(joints)
        pose = kin.forward(joints)
        worst_pos = max(worst_pos, math.dist(pose[:3], pos))
        worst_rot = max(worst_rot, _rotation_error_deg(fairino_rpy_to_rotation(*pose[3:]), rot))
    print(f"   diferencia máxima de posición: {worst_pos:.4f} mm")
    print(f"   diferencia máxima de orientación: {worst_rot:.6f} °")
    # No puede dar cero: el URDF escribe π/2 como 1.5708, y `kinematics.py` usa π/2 exacto.
    ok = worst_pos < 0.5 and worst_rot < 0.01
    print(f"   {'OK' if ok else 'FALLO'}")
    return ok


def test_check_reasons():
    print("\n7) `check` distingue los tres motivos de fallo")
    cases = [
        ("fuera de alcance", (2500.0, 0.0, 500.0, 0.0, 0.0, 0.0)),
        ("límite articular", (-816.95, 795.41, 810.73, 92.03, -1.92, -166.83)),
        ("sin solución", (-493.27, -977.62, 1032.06, -153.92, 6.46, -48.35)),
    ]
    ok = True
    for expected, pose in cases:
        result = kin.check(pose)
        good = result["ok"] is False and result["reason"] == expected
        ok = ok and good
        print(f"   esperado {expected!r} -> {result['reason']!r}: {result['detail']}")
    good_pose = kin.forward([20.0, -120.0, 100.0, -80.0, -90.0, 30.0])
    result = kin.check(good_pose)
    ok = ok and result["ok"] and result["reason"] is None and result["joints"]
    print(f"   pose válida -> ok={result['ok']} joints={[round(v, 2) for v in result['joints']]}")
    print(f"   {'OK' if ok else 'FALLO'}")
    return ok


def test_wrist_singularity(rng):
    """Con j5 = 0 los ejes 4 y 6 se alinean y las soluciones son una familia continua.

    Fijar un j6 arbitrario (lo que hacía la versión anterior) deja fuera poses perfectamente
    alcanzables: ~5 % con semilla nula y ~4 % con semilla cualquiera. Como `routes.py` encadena la
    solución de un punto como semilla del siguiente, la semilla hostil es el caso real, no el raro.
    """
    print("\n8) Singularidad de muñeca: j5 = 0 y su entorno")
    ok = True
    for label, eps in [("j5 = 0 exacto", 0.0), ("j5 = 1e-9", 1e-9), ("j5 = 1e-6", 1e-6), ("j5 = 0.01", 0.01)]:
        rejected_blind = rejected_seeded = 0
        for _ in range(300):
            joints = _random_joints(rng)
            joints[4] = eps
            pose = kin.forward(joints)
            if not kin.check(pose)["ok"]:
                rejected_blind += 1
            if not kin.check(pose, _random_joints(rng))["ok"]:
                rejected_seeded += 1
        ok = ok and rejected_blind == 0 and rejected_seeded == 0
        print(f"   {label:<14} rechazadas sin semilla: {rejected_blind}/300 · con semilla hostil: {rejected_seeded}/300")
    print(f"   {'OK' if ok else 'FALLO'}")
    return ok


def test_singular_poses(rng):
    """Codo estirado, codo plegado al límite y brida sobre el eje de j1: ni `nan` ni excepciones."""
    print("\n9) Codo y hombro singulares")
    ok = True

    stretched = [15.0, -100.0, 0.0, -80.0, -70.0, 25.0]
    folded = [15.0, -100.0, 162.0, -80.0, -70.0, 25.0]
    for label, joints in [("codo estirado j3=0", stretched), ("codo plegado j3=162", folded)]:
        pose = kin.forward(joints)
        result = kin.check(pose, joints)
        clean = result["ok"] and all(v == v for v in result["joints"])
        ok = ok and clean
        print(f"   {label:<22} ok={result['ok']} joints={[round(v, 2) for v in result['joints'] or []]}")

    # La brida nunca se acerca al eje de j1 más de D4: hypot(x, y) = D4 es una tangencia, no un
    # cruce, así que no se puede bisectar sobre el radio. Sí cambia de signo la coordenada de la
    # brida a lo largo del plano del brazo, x·cos(j1) + y·sin(j1), y vale cero justo en el borde.
    def in_plane(joints, j4):
        x, y = kin.forward(joints[:3] + [j4] + joints[4:])[:2]
        angle = math.radians(joints[0])
        return x * math.cos(angle) + y * math.sin(angle)

    lo, hi = kin.JOINT_LIMITS_DEG[3]
    step = (hi - lo) / 180.0
    built = failed = 0
    worst_radius = 0.0
    for _ in range(400):
        joints = _random_joints(rng)
        bracket = None
        previous = in_plane(joints, lo)
        for k in range(1, 181):
            j4 = lo + step * k
            current = in_plane(joints, j4)
            if previous * current <= 0:
                bracket = (j4 - step, j4, previous)
                break
            previous = current
        if bracket is None:
            continue
        a, b, f_a = bracket
        for _ in range(120):
            mid = (a + b) / 2.0
            f_mid = in_plane(joints, mid)
            if f_a * f_mid <= 0:
                b = mid
            else:
                a, f_a = mid, f_mid
        singular = joints[:3] + [(a + b) / 2.0] + joints[4:]
        pose = kin.forward(singular)
        built += 1
        worst_radius = max(worst_radius, abs(math.hypot(pose[0], pose[1]) - kin.D4))
        if not kin.check(pose, singular)["ok"]:
            failed += 1
    ok = ok and built > 0 and failed == 0
    print(f"   brida sobre el eje de j1: {built} poses construidas (|radio-D4| <= {worst_radius:.2e} mm), rechazadas {failed}")
    print(f"   {'OK' if ok else 'FALLO'}")
    return ok


def test_reach_envelope(rng):
    """`REACH_MM` y `NEAR_MM` tienen que ser cotas válidas: ninguna postura real puede salirse."""
    print("\n10) Bordes del alcance: la envolvente no rechaza nada alcanzable")
    lowest, highest, closest = 1e9, -1e9, 1e9
    rejected = 0
    for _ in range(20000):
        pose = kin.forward(_random_joints(rng))
        side, planar = kin._out_of_reach(pose)
        if side is None:
            lowest, highest = min(lowest, planar), max(highest, planar)
        else:
            rejected += 1
        closest = min(closest, math.hypot(pose[0], pose[1]))
    print(f"   cotas del módulo: eje>={abs(kin.D4):.0f} · NEAR_MM={kin.NEAR_MM:.3f} · REACH_MM={kin.REACH_MM:.1f}")
    print(f"   en 20000 posturas: plano [{lowest:.3f}, {highest:.3f}] mm · eje de j1 desde {closest:.3f} mm")
    print(f"   posturas reales rechazadas por la envolvente: {rejected}")

    cases = [("demasiado lejos", (0.0, 1450.0, 200.0, 0.0, 0.0, 0.0)),
             ("demasiado cerca", (170.0, 0.0, 180.0, 0.0, 0.0, 0.0)),
             ("sobre el eje de j1", (0.0, 0.0, 800.0, 0.0, 0.0, 0.0))]
    ok = (rejected == 0 and lowest >= kin.NEAR_MM and highest <= kin.REACH_MM
          and closest >= abs(kin.D4) - 1e-6)
    for label, pose in cases:
        result = kin.check(pose)
        ok = ok and result["reason"] == "fuera de alcance"
        print(f"   {label:<19} -> {result['reason']!r}: {result['detail']}")
    print(f"   {'OK' if ok else 'FALLO'}")
    return ok


def _rz_ry_rx(rx, ry, rz):
    """R = Rz·Ry·Rx montada desde cero, sin usar nada de `routes.py`."""
    def mul(a, b):
        return tuple(tuple(sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)) for i in range(3))

    a, b, c = (math.radians(v) for v in (rx, ry, rz))
    mx = ((1.0, 0.0, 0.0), (0.0, math.cos(a), -math.sin(a)), (0.0, math.sin(a), math.cos(a)))
    my = ((math.cos(b), 0.0, math.sin(b)), (0.0, 1.0, 0.0), (-math.sin(b), 0.0, math.cos(b)))
    mz = ((math.cos(c), -math.sin(c), 0.0), (math.sin(c), math.cos(c), 0.0), (0.0, 0.0, 1.0))
    return mul(mul(mz, my), mx)


def test_rpy_convention(rng):
    """`forward` tiene que hablar la misma convención que `routes.py`, comprobado por fuera."""
    print("\n11) Convención rx/ry/rz: R = Rz·Ry·Rx, contrastada sin `routes.py`")
    worst_helper = 0.0
    for _ in range(2000):
        angles = [rng.uniform(-180.0, 180.0) for _ in range(3)]
        mine = _rz_ry_rx(*angles)
        theirs = fairino_rpy_to_rotation(*angles)
        worst_helper = max(worst_helper, max(abs(mine[i][j] - theirs[i][j]) for i in range(3) for j in range(3)))

    worst_fk = 0.0
    for _ in range(500):
        joints = _random_joints(rng)
        rot, _ = _urdf_forward(joints)
        worst_fk = max(worst_fk, _rotation_error_deg(_rz_ry_rx(*kin.forward(joints)[3:]), rot))

    # Bloqueo de cardán: con ry = ±90 el par (rx, rz) deja de ser único, pero la matriz sí lo es.
    worst_lock = 0.0
    for ry in (90.0, -90.0):
        for rx, rz in ((0.0, 0.0), (30.0, 50.0), (-170.0, 120.0)):
            target = _rz_ry_rx(rx, ry, rz)
            back = rotation_to_fairino_rpy(target)
            worst_lock = max(worst_lock, _rotation_error_deg(_rz_ry_rx(*back), target))

    print(f"   `fairino_rpy_to_rotation` vs Rz·Ry·Rx montada aparte: {worst_helper:.3e}")
    print(f"   rpy de `forward` vs la rotación cruda del URDF: {worst_fk:.6f} °")
    print(f"   ida y vuelta con ry = ±90 (bloqueo de cardán): {worst_lock:.3e} °")
    ok = worst_helper < 1e-12 and worst_fk < 0.01 and worst_lock < 1e-4
    print(f"   {'OK' if ok else 'FALLO'}")
    return ok


def test_hostile_input():
    """Una pose con `nan`, `inf` o mal formada no puede colarse como diagnóstico con sentido."""
    print("\n12) Entradas degeneradas")
    ok = True
    valid_reasons = ("fuera de alcance", "sin solución", "límite articular")
    for label, pose in [("nan", (float("nan"), 0.0, 500.0, 0.0, 0.0, 0.0)),
                        ("inf", (float("inf"), 0.0, 500.0, 0.0, 0.0, 0.0)),
                        ("nan en rx", (400.0, 0.0, 500.0, float("nan"), 0.0, 0.0)),
                        ("1e300", (1e300, 0.0, 500.0, 0.0, 0.0, 0.0))]:
        try:
            result = kin.check(pose)
        except Exception as exc:  # noqa: BLE001 - cualquier excepción aquí ya es el fallo
            print(f"   {label:<10} EXCEPCIÓN {type(exc).__name__}: {exc}")
            ok = False
            continue
        good = result["ok"] is False and result["reason"] in valid_reasons and result["joints"] is None
        ok = ok and good
        print(f"   {label:<10} ok={result['ok']} reason={result['reason']!r}: {result['detail']}")
    print(f"   {'OK' if ok else 'FALLO'}")
    return ok


def main():
    print("Parámetros deducidos del URDF fairino10_v6 (commit 5bed0b0):")
    print(f"   d1={kin.D1} a2={kin.A2} a3={kin.A3} d4={kin.D4} d5={kin.D5} d6={kin.D6} mm")
    print(f"   envolvente en el plano del brazo: NEAR_MM={kin.NEAR_MM:.1f} … REACH_MM={kin.REACH_MM:.1f}")
    print(f"   límites: {kin.JOINT_LIMITS_DEG}")

    rng = random.Random(20260913)
    results = [
        ("ida y vuelta", test_roundtrip(rng)),
        ("límites articulares", test_limits(rng)),
        ("fuera de alcance", test_unreachable()),
        ("convención contra el FR5", test_fr5_convention()),
        ("orden por semilla", test_seed_order()),
        ("FK contra el URDF", test_against_urdf(rng)),
        ("motivos de `check`", test_check_reasons()),
        ("singularidad de muñeca", test_wrist_singularity(rng)),
        ("codo y hombro singulares", test_singular_poses(rng)),
        ("bordes del alcance", test_reach_envelope(rng)),
        ("convención rx/ry/rz", test_rpy_convention(rng)),
        ("entradas degeneradas", test_hostile_input()),
    ]
    print("\nResumen")
    for name, ok in results:
        print(f"   {'OK   ' if ok else 'FALLO'} {name}")
    return 0 if all(ok for _, ok in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
