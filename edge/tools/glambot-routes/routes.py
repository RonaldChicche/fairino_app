#!/usr/bin/env python3
"""Rutas de glambot para el FR10: geometría "mirar siempre a un punto" en la convención de FAIRINO.

Unidades FAIRINO: mm y grados. La orientación rx, ry, rz es una rotación ZYX del sistema flotante
(CobotsManual/robot_brief_introduction.rst), es decir R = Rz(rz) · Ry(ry) · Rx(rx).

Marco de la cámara (TCP): Z = eje óptico, X = derecha de la imagen, Y = abajo de la imagen.
Horizonte nivelado: el eje X de la cámara se mantiene horizontal.

Las rutas se definen RELATIVAS al objetivo: la orientación de cada punto depende solo del vector
objetivo → cámara, así que trasladar la ruta junto con el objetivo conserva el "mirar a". El
programa Lua solo tiene que sumar el objetivo (recibido por variables de sistema) a los offsets.

Uso:
  python3 routes.py --target 1300 0 1100 --standoff 500 --dz-start -300 --dz-end 300 --steps 5
"""
import argparse
import math
from collections import Counter
from dataclasses import dataclass

WORLD_UP = (0.0, 0.0, 1.0)
ORIGIN = (0.0, 0.0, 0.0)


def _sub(a, b):
    return tuple(ai - bi for ai, bi in zip(a, b))


def _add(a, b):
    return tuple(ai + bi for ai, bi in zip(a, b))


def _dot(a, b):
    return sum(ai * bi for ai, bi in zip(a, b))


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _norm(a):
    return math.sqrt(_dot(a, a))


def _normalize(a):
    n = _norm(a)
    if n < 1e-9:
        raise ValueError("vector nulo: la cámara coincide con el objetivo")
    return tuple(ai / n for ai in a)


def _column(rotation, i):
    return tuple(rotation[r][i] for r in range(3))


def look_at_rotation(camera, target, up=WORLD_UP):
    """Rotación (filas de una matriz 3x3) cuyo eje Z apunta de la cámara al objetivo, con X horizontal."""
    z = _normalize(_sub(target, camera))
    x = _cross(z, up)
    if _norm(x) < 1e-6:
        raise ValueError("la cámara mira en vertical: el horizonte queda indefinido")
    x = _normalize(x)
    y = _cross(z, x)
    return tuple((x[r], y[r], z[r]) for r in range(3))


def rotation_to_fairino_rpy(rotation):
    """Matriz → (rx, ry, rz) en grados con R = Rz(rz) · Ry(ry) · Rx(rx)."""
    r = rotation
    ry = math.atan2(-r[2][0], math.hypot(r[0][0], r[1][0]))
    rx = math.atan2(r[2][1], r[2][2])
    rz = math.atan2(r[1][0], r[0][0])
    return tuple(math.degrees(a) for a in (rx, ry, rz))


def fairino_rpy_to_rotation(rx, ry, rz):
    """(rx, ry, rz) en grados → matriz con R = Rz(rz) · Ry(ry) · Rx(rx)."""
    a, b, c = (math.radians(v) for v in (rx, ry, rz))
    ca, sa, cb, sb, cc, sc = math.cos(a), math.sin(a), math.cos(b), math.sin(b), math.cos(c), math.sin(c)
    return (
        (cc * cb, cc * sb * sa - sc * ca, cc * sb * ca + sc * sa),
        (sc * cb, sc * sb * sa + cc * ca, sc * sb * ca - cc * sa),
        (-sb, cb * sa, cb * ca),
    )


def rotation_to_quaternion(rotation):
    """Matriz → cuaternión (w, x, y, z) normalizado."""
    r = rotation
    trace = r[0][0] + r[1][1] + r[2][2]
    if trace > 0:
        s = 0.5 / math.sqrt(trace + 1.0)
        q = (0.25 / s, (r[2][1] - r[1][2]) * s, (r[0][2] - r[2][0]) * s, (r[1][0] - r[0][1]) * s)
    elif r[0][0] > r[1][1] and r[0][0] > r[2][2]:
        s = 2.0 * math.sqrt(1.0 + r[0][0] - r[1][1] - r[2][2])
        q = ((r[2][1] - r[1][2]) / s, 0.25 * s, (r[1][0] + r[0][1]) / s, (r[0][2] + r[2][0]) / s)
    elif r[1][1] > r[2][2]:
        s = 2.0 * math.sqrt(1.0 + r[1][1] - r[0][0] - r[2][2])
        q = ((r[0][2] - r[2][0]) / s, (r[1][0] + r[0][1]) / s, 0.25 * s, (r[2][1] + r[1][2]) / s)
    else:
        s = 2.0 * math.sqrt(1.0 + r[2][2] - r[0][0] - r[1][1])
        q = ((r[1][0] - r[0][1]) / s, (r[0][2] + r[2][0]) / s, (r[2][1] + r[1][2]) / s, 0.25 * s)
    n = math.sqrt(sum(v * v for v in q))
    return tuple(v / n for v in q)


def quaternion_to_rotation(q):
    w, x, y, z = q
    return (
        (1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)),
        (2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)),
        (2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)),
    )


def slerp(q0, q1, t):
    """Interpolación esférica entre cuaternientos (camino corto)."""
    d = sum(a * b for a, b in zip(q0, q1))
    if d < 0:
        q1, d = tuple(-v for v in q1), -d
    if d > 0.9995:
        q = tuple(a + t * (b - a) for a, b in zip(q0, q1))
    else:
        theta = math.acos(d)
        s0, s1 = math.sin((1 - t) * theta) / math.sin(theta), math.sin(t * theta) / math.sin(theta)
        q = tuple(s0 * a + s1 * b for a, b in zip(q0, q1))
    n = math.sqrt(sum(v * v for v in q))
    return tuple(v / n for v in q)


def interpolate_pose(pose_a, pose_b, t):
    """Pose intermedia (x, y, z, rx, ry, rz): posición lineal y orientación por slerp, como un MoveL sin blending."""
    position = tuple(a + t * (b - a) for a, b in zip(pose_a[:3], pose_b[:3]))
    qa = rotation_to_quaternion(fairino_rpy_to_rotation(*pose_a[3:6]))
    qb = rotation_to_quaternion(fairino_rpy_to_rotation(*pose_b[3:6]))
    return (*position, *rotation_to_fairino_rpy(quaternion_to_rotation(slerp(qa, qb, t))))


@dataclass(frozen=True)
class RelativeWaypoint:
    offset: tuple  # mm: vector objetivo → cámara (TCP)
    rpy: tuple     # grados, convención FAIRINO


def crane_route(standoff_mm, azimuth_deg, dz_start_mm, dz_end_mm, steps):
    """Grúa vertical: la cámara sube o baja a distancia horizontal fija del objetivo, mirándolo."""
    if steps < 2:
        raise ValueError("la ruta necesita al menos 2 puntos")
    az = math.radians(azimuth_deg)
    horizontal = (standoff_mm * math.cos(az), standoff_mm * math.sin(az))
    route = []
    for i in range(steps):
        dz = dz_start_mm + (dz_end_mm - dz_start_mm) * i / (steps - 1)
        offset = (horizontal[0], horizontal[1], dz)
        rotation = look_at_rotation(offset, ORIGIN)
        route.append(RelativeWaypoint(offset, rotation_to_fairino_rpy(rotation)))
    return route


def absolute_poses(route, target):
    """Poses del TCP en la base del robot: objetivo + offset, con la orientación precalculada."""
    return [(*_add(target, wp.offset), *wp.rpy) for wp in route]


def camera_to_flange(route, camera_offset_mm):
    """Ruta de la brida a partir de la de la cámara.

    Supuesto provisional (B3 en Notion): la cámara está sobre el eje Z de la brida, a camera_offset_mm,
    mirando en +Z. La orientación coincide y la brida queda camera_offset_mm detrás a lo largo del eje óptico.
    La traslación sigue siendo invariante: la ruta de la brida también es relativa al objetivo.
    """
    flange = []
    for wp in route:
        optical = _column(fairino_rpy_to_rotation(*wp.rpy), 2)
        offset = tuple(o - camera_offset_mm * a for o, a in zip(wp.offset, optical))
        flange.append(RelativeWaypoint(offset, wp.rpy))
    return flange


def flange_to_camera_point(flange_pose, camera_offset_mm):
    """Posición de la cámara y su eje óptico a partir de una pose de brida (x, y, z, rx, ry, rz)."""
    rotation = fairino_rpy_to_rotation(*flange_pose[3:6])
    optical = _column(rotation, 2)
    position = tuple(p + camera_offset_mm * a for p, a in zip(flange_pose[:3], optical))
    return position, rotation


def aim_errors(flange_pose, target, camera_offset_mm):
    """(error del eje óptico respecto al objetivo, inclinación del horizonte) en grados para una pose de brida."""
    position, rotation = flange_to_camera_point(flange_pose, camera_offset_mm)
    to_target = _normalize(_sub(target, position))
    aim = math.degrees(math.acos(max(-1.0, min(1.0, _dot(_column(rotation, 2), to_target)))))
    tilt = math.degrees(math.asin(max(-1.0, min(1.0, _column(rotation, 0)[2]))))
    return aim, tilt


def _chord_normal(a, b):
    """Dirección perpendicular a la cuerda a→b que se aleja del objetivo (el origen)."""
    chord = _sub(b, a)
    if _norm(chord) < 1e-9:
        return WORLD_UP
    u = _normalize(chord)
    mid = tuple((ai + bi) / 2 for ai, bi in zip(a, b))
    radial = _sub(mid, tuple(_dot(mid, u) * ui for ui in u))
    if _norm(radial) < 1e-6:  # la cuerda pasa por el objetivo: el arco se abomba hacia arriba
        radial = _sub(WORLD_UP, tuple(_dot(WORLD_UP, u) * ui for ui in u))
    return _normalize(radial)


def arc_offsets(a, b, bulge_mm, samples):
    """Puntos intermedios de un arco entre a y b, abombado bulge_mm perpendicular a la cuerda.

    Es una Bézier cuadrática que pasa exactamente por el punto de abombado en la mitad, no un arco
    circular exacto: para diseñar una toma la diferencia es invisible, y la puntería no depende de
    esto porque la orientación de cada punto se recalcula con look_at.
    """
    if samples < 1 or abs(bulge_mm) < 1e-9:
        return []
    mid = tuple((ai + bi) / 2 for ai, bi in zip(a, b))
    via = _add(mid, tuple(bulge_mm * ni for ni in _chord_normal(a, b)))
    control = _sub(tuple(2 * v for v in via), mid)
    points = []
    for i in range(1, samples + 1):
        t = i / (samples + 1)
        s = 1 - t
        points.append(tuple(s * s * ai + 2 * s * t * ci + t * t * bi for ai, ci, bi in zip(a, control, b)))
    return points


def _spec_points(spec):
    """[(offset, id)] de la ruta de cámara ya densificada; id es None en los puntos que genera un arco."""
    waypoints = spec["waypoints"]
    if len(waypoints) < 2:
        raise ValueError("la ruta necesita al menos 2 puntos")
    offsets_by_id = {w["id"]: tuple(float(v) for v in w["offset"]) for w in waypoints}
    order = [w["id"] for w in waypoints]
    segments = {(s["from"], s["to"]): s for s in spec.get("segments", [])}

    points = []
    for i, wid in enumerate(order):
        points.append((offsets_by_id[wid], wid))
        if i + 1 == len(order):
            continue
        nxt = order[i + 1]
        segment = segments.get((wid, nxt), {"type": "line"})
        if segment.get("type") == "arc":
            points.extend((o, None) for o in arc_offsets(offsets_by_id[wid], offsets_by_id[nxt],
                                                         float(segment.get("bulge_mm", 0.0)),
                                                         int(segment.get("samples", 6))))
    return points


def route_from_spec(spec):
    """Ruta de cámara a partir del JSON del simulador: densifica los arcos y calcula las orientaciones."""
    return [RelativeWaypoint(o, rotation_to_fairino_rpy(look_at_rotation(o, ORIGIN)))
            for o, _ in _spec_points(spec)]


VALID_REASONS = ("fuera de alcance", "sin solución", "límite articular")
# Robot que modela kinematics.py, si él mismo no lo dice: su geometría sale del URDF del FR10.
KINEMATICS_ROBOT = "FR10"
DEFAULT_SEED_DEG = [0.0] * 6
SUGGEST_COARSE_MM = 25.0
SUGGEST_FINE_MM = 1.0
MIN_RADIUS_MM = 1.0


def load_kinematics():
    """Módulo `kinematics`, o None si no está. Se importa aquí porque él importa de routes: a nivel
    de módulo el ciclo lo dejaría a medio inicializar."""
    try:
        import kinematics
    except ImportError:  # sin él no se valida nada: aquí no se improvisa una cinemática propia
        return None
    return kinematics


def _flange_pose(offset, camera_offset_mm, target):
    """Pose absoluta de la brida (x, y, z, rx, ry, rz) del punto de cámara en offset respecto al objetivo."""
    rpy = rotation_to_fairino_rpy(look_at_rotation(offset, ORIGIN))
    wp = camera_to_flange([RelativeWaypoint(offset, rpy)], camera_offset_mm)[0]
    return (*_add(target, wp.offset), *wp.rpy)


def _nearest_valid_offset(kin, offset, camera_offset_mm, target, seed):
    """Offset alcanzable más cercano sobre la recta punto↔objetivo.

    Acercar o alejar el punto al objetivo conserva la dirección de la toma, no el encuadre: al cambiar
    la distancia el sujeto crece o mengua en el cuadro, y `desplazamiento_mm` es lo único que lo delata.
    Barrido grueso para acotar el lado y la distancia, y luego fino dentro de ese tramo.
    """
    radius = _norm(offset)
    if radius < MIN_RADIUS_MM:
        return None
    direction = _normalize(offset)

    def valid(shift):
        if radius + shift < MIN_RADIUS_MM:
            return False
        moved = tuple((radius + shift) * u for u in direction)
        return bool(kin.check(_flange_pose(moved, camera_offset_mm, target), seed).get("ok"))

    bracket = None
    for k in range(1, int(kin.REACH_MM // SUGGEST_COARSE_MM) + 1):
        for shift in (-k * SUGGEST_COARSE_MM, k * SUGGEST_COARSE_MM):
            if valid(shift):
                bracket = shift
                break
        if bracket is not None:
            break
    if bracket is None:
        return None

    best, fine = bracket, SUGGEST_FINE_MM
    while fine < abs(bracket):
        for shift in (-fine, fine):
            if valid(shift):
                best = shift
                break
        if best != bracket:
            break
        fine += SUGGEST_FINE_MM
    moved = tuple((radius + best) * u for u in direction)
    return {"offset": [round(v, 3) for v in moved], "desplazamiento_mm": round(abs(best), 1)}


def _validation_error(resumen):
    return {"ok": False, "reach_mm": 0.0, "resumen": resumen, "puntos": [],
            "robot_validado": None, "robot_declarado": None, "aviso": resumen}


def _declared_robot(spec):
    """(modelo, reach_mm) que el spec declara, o (None, None). No se deduce nada que no venga escrito."""
    robot = spec.get("robot")
    if not isinstance(robot, dict):
        return None, None
    modelo = robot.get("model") or robot.get("modelo")
    try:
        reach = float(robot["reach_mm"])
    except (KeyError, TypeError, ValueError):
        reach = None
    return (str(modelo) if modelo else None), reach


def _robot_warning(declared, used):
    """Aviso si el spec declara un robot distinto del que modela `kinematics`, o None.

    No hay cinemática de otros modelos en el repo (solo la del FR10), así que aquí no se valida contra
    el robot declarado: se avisa de que el informe no habla de él. Callarlo sería peor que no validar,
    porque la ruta escalada para un brazo más corto saldría marcada como alcanzable.
    """
    declared_model, declared_reach = declared
    used_model, used_reach = used
    distinto_modelo = bool(declared_model) and declared_model.upper() != used_model.upper()
    distinto_reach = declared_reach is not None and abs(declared_reach - used_reach) > 1.0
    if not (distinto_modelo or distinto_reach):
        return None
    dice = declared_model or "otro robot"
    if declared_reach is not None:
        dice += f" ({declared_reach:.0f} mm de alcance)"
    return (f"AVISO: la ruta declara {dice}, pero se ha validado con la cinemática del {used_model} "
            f"({used_reach:.0f} mm). Este informe NO dice si ese robot alcanza los puntos: los `joints`, "
            f"los `eslabones` y las sugerencias son del {used_model}. No hay cinemática del robot "
            f"declarado en el repo.")


def validate_spec(spec):
    """Comprueba punto a punto que la brida de la ruta es alcanzable, con el modelo de `kinematics`.

    Valida los puntos de brida ya densificados (arcos incluidos), que son los que acaban en la tabla
    ROUTE del Lua. Cada solución sirve de semilla de la siguiente para que la postura sea continua.
    """
    kin = load_kinematics()
    if kin is None:
        return _validation_error("falta el módulo kinematics.py junto a routes.py: sin él no se puede "
                                 "validar si el robot alcanza los puntos")
    try:
        points = _spec_points(spec)
        camera_offset = float(spec["camera"]["offset_mm"])
        target = tuple(float(v) for v in spec["target"])
    except (KeyError, TypeError, ValueError) as exc:
        return _validation_error(f"la ruta está incompleta o mal formada: {exc}")

    seed = list(spec.get("seed_joints") or DEFAULT_SEED_DEG)
    if len(seed) != 6:
        seed = list(DEFAULT_SEED_DEG)

    result = []
    for index, (offset, wid) in enumerate(points):
        outcome = kin.check(_flange_pose(offset, camera_offset, target), seed)
        ok = bool(outcome.get("ok"))
        joints = [float(v) for v in outcome["joints"]] if ok and outcome.get("joints") else None
        raw_reason = (outcome.get("reason") or "").strip()
        detalle = (outcome.get("detail") or "").strip()
        motivo = None
        if not ok:
            motivo = raw_reason if raw_reason in VALID_REASONS else "sin solución"
            if raw_reason and raw_reason not in VALID_REASONS:
                detalle = f"{raw_reason}: {detalle}" if detalle else raw_reason
        result.append({
            "indice": index,
            "id": wid,
            "ok": ok,
            "joints": joints,
            "motivo": motivo,
            "detalle": detalle or ("alcanzable" if ok else motivo),
            "sugerencia": None if ok else _nearest_valid_offset(kin, offset, camera_offset, target, seed),
            "eslabones": [[float(v) for v in p] for p in kin.link_points(joints)] if joints else None,
        })
        if joints:
            seed = joints

    failures = [p for p in result if not p["ok"]]
    if failures:
        counts = Counter(p["motivo"] for p in failures)
        resumen = (f"{len(failures)} de {len(result)} puntos no son alcanzables: "
                   + ", ".join(f"{n} por {motivo}" for motivo, n in counts.most_common()))
    else:
        resumen = f"los {len(result)} puntos de la ruta son alcanzables"

    used = (getattr(kin, "ROBOT_MODEL", KINEMATICS_ROBOT), float(kin.REACH_MM))
    declared = _declared_robot(spec)
    aviso = _robot_warning(declared, used)
    resumen = f"[{used[0]}] {resumen}"
    if aviso:  # marca corta: el texto entero va en `aviso`, que la interfaz pinta aparte
        resumen = f"⚠ validado con otro robot · {resumen}"
    return {"ok": not failures, "reach_mm": used[1], "resumen": resumen, "puntos": result,
            "robot_validado": {"modelo": used[0], "reach_mm": used[1]},
            "robot_declarado": None if declared == (None, None) else
                               {"modelo": declared[0], "reach_mm": declared[1]},
            "aviso": aviso}


def validation_message(report, limit=10):
    """Texto de error de una validación fallida, con los puntos culpables y su motivo."""
    failures = [p for p in report["puntos"] if not p["ok"]]
    detalle = "; ".join(
        f"punto {p['indice']}" + (f" (id {p['id']})" if p["id"] is not None else " (intermedio de un arco)")
        + f": {p['motivo']} — {p['detalle']}" for p in failures[:limit])
    if len(failures) > limit:
        detalle += f"; y {len(failures) - limit} más"
    return f"no se genera el Lua: {report['resumen']}" + (f". {detalle}" if detalle else "")


def lua_from_spec(spec, report=None):
    """Programa Lua de una ruta del simulador. Devuelve (texto, número de puntos)."""
    report = report if report is not None else validate_spec(spec)
    if not report["ok"]:
        raise ValueError(validation_message(report))
    seed = spec.get("seed_joints")
    if not seed or len(seed) != 6:
        raise ValueError("falta 'seed_joints' (6 valores). Sale de planner.py, que corre en la instancia "
                         "contra el controlador: ese es el paso que valida que la ruta es alcanzable")
    route = route_from_spec(spec)
    motion = spec["motion"]
    flange = camera_to_flange(route, float(spec["camera"]["offset_mm"]))
    lua = render_lua(flange, seed, motion["speed"], motion["acc"], motion["blend_mm"],
                     motion.get("camera_timeout_s", 30))
    return lua, len(route)


# El .lua sale sin comentarios a propósito: el controlador los rechaza al cargar el programa.
# Protocolo por variables de sistema (documentado en NOTAS.md):
#   PC → robot: s_var_1..3 = objetivo x, y, z [mm, base] · s_var_4 = ID de toma
#               s_var_5 = cámara grabando: el PC escribe aquí el ID de toma cuando la cámara lo confirma
#   robot → PC: s_var_6 = estado (0 iniciado · 1 esperando cámara · 2 moviendo · 3 terminado
#               -1 punto inalcanzable · -2 la cámara no confirmó a tiempo) · s_var_7 = ID aceptado
# El robot no se mueve hasta que s_var_5 coincide con el ID de toma (regla dura de CLAUDE.md).
# GetForwardKin devuelve nil en la pasada de validación que hace el controlador al subir el script:
# ahí el programa tiene que terminar sin mover nada.
LUA_TEMPLATE = """local ROUTE = {{
{route_rows}
}}
local SEED = {{{seed}}}
local TOOL = 0
local USER = 0
local SPEED = {speed}
local ACC = {acc}
local BLEND_R = {blend}
local CAMERA_TIMEOUT_TICKS = {camera_ticks}

local check = GetForwardKin(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
if check == nil then
  return
end

SetSysVarValue(s_var_6, 0)
local tx = GetSysVarValue(s_var_1)
local ty = GetSysVarValue(s_var_2)
local tz = GetSysVarValue(s_var_3)
local take_id = GetSysVarValue(s_var_4)
SetSysVarValue(s_var_7, take_id)

local joints = {{}}
local ref = SEED
for i, p in ipairs(ROUTE) do
  local pose = {{tx + p[1], ty + p[2], tz + p[3], p[4], p[5], p[6]}}
  if GetInverseKinHasSolution(0, pose, ref) ~= 1 then
    SetSysVarValue(s_var_6, -1)
    return
  end
  local solution = GetInverseKinRef(0, pose, ref)
  joints[i] = solution
  ref = solution
end

SetSysVarValue(s_var_6, 1)
local ready = false
for _ = 1, CAMERA_TIMEOUT_TICKS do
  if GetSysVarValue(s_var_5) == take_id then
    ready = true
    break
  end
  WaitMs(10)
end
if not ready then
  SetSysVarValue(s_var_6, -2)
  return
end

SetSysVarValue(s_var_6, 2)
local j = joints[1]
local p = ROUTE[1]
MoveJ(j[1], j[2], j[3], j[4], j[5], j[6], tx + p[1], ty + p[2], tz + p[3], p[4], p[5], p[6], TOOL, USER, SPEED, ACC, 100, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
for i = 2, #ROUTE do
  j = joints[i]
  p = ROUTE[i]
  local blend = BLEND_R
  if i == #ROUTE then
    blend = -1
  end
  MoveL(j[1], j[2], j[3], j[4], j[5], j[6], tx + p[1], ty + p[2], tz + p[3], p[4], p[5], p[6], TOOL, USER, SPEED, ACC, 100, blend, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 100, 0)
end
SetSysVarValue(s_var_6, 3)
"""


def render_lua(flange_route, seed_joints, speed, acc, blend_mm, camera_timeout_s):
    rows = ",\n".join("  {" + ", ".join(f"{v:.4f}" for v in (*wp.offset, *wp.rpy)) + "}" for wp in flange_route)
    return LUA_TEMPLATE.format(
        route_rows=rows,
        seed=", ".join(f"{v:.4f}" for v in seed_joints),
        speed=speed,
        acc=acc,
        blend=blend_mm,
        camera_ticks=int(round(camera_timeout_s * 100)),
    )


def check_route(route, target):
    """Errores máximos (grados) del eje óptico respecto al objetivo y de inclinación del horizonte."""
    max_aim = max_tilt = 0.0
    for x, y, z, rx, ry, rz in absolute_poses(route, target):
        rotation = fairino_rpy_to_rotation(rx, ry, rz)
        optical = _column(rotation, 2)
        to_target = _normalize(_sub(target, (x, y, z)))
        aim = math.degrees(math.acos(max(-1.0, min(1.0, _dot(optical, to_target)))))
        tilt = math.degrees(math.asin(max(-1.0, min(1.0, _column(rotation, 0)[2]))))
        max_aim, max_tilt = max(max_aim, aim), max(max_tilt, abs(tilt))
    return max_aim, max_tilt


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--target", type=float, nargs=3, metavar=("X", "Y", "Z"), required=True,
                        help="punto al que mira la cámara, en mm, en la base del robot")
    parser.add_argument("--standoff", type=float, required=True, help="distancia horizontal cámara-objetivo, mm")
    parser.add_argument("--azimuth", type=float, default=None,
                        help="dirección objetivo → cámara en el plano XY, grados (por defecto: hacia la base)")
    parser.add_argument("--dz-start", type=float, required=True, help="altura inicial de la cámara respecto al objetivo, mm")
    parser.add_argument("--dz-end", type=float, required=True, help="altura final de la cámara respecto al objetivo, mm")
    parser.add_argument("--steps", type=int, default=5)
    parser.add_argument("--lua", help="escribe aquí el programa Lua de la ruta")
    parser.add_argument("--camera-offset", type=float, help="mm de la brida a la cámara sobre el eje Z (provisional, B3)")
    parser.add_argument("--seed-joints", type=float, nargs=6, metavar="J", help="postura de referencia para la IK, grados")
    parser.add_argument("--speed", type=float, help="velocidad en %% [0-100]")
    parser.add_argument("--acc", type=float, help="aceleración en %% [0-100]")
    parser.add_argument("--blend", type=float, help="radio de blending de MoveL en mm (-1 = detenerse en cada punto)")
    parser.add_argument("--camera-timeout", type=float, help="segundos máximos esperando la confirmación de la cámara")
    args = parser.parse_args()
    lua_args = (args.camera_offset, args.seed_joints, args.speed, args.acc, args.blend, args.camera_timeout)
    if args.lua and any(v is None for v in lua_args):
        parser.error("--lua requiere --camera-offset, --seed-joints, --speed, --acc, --blend y --camera-timeout")

    target = tuple(args.target)
    azimuth = args.azimuth if args.azimuth is not None else math.degrees(math.atan2(-target[1], -target[0]))
    route = crane_route(args.standoff, azimuth, args.dz_start, args.dz_end, args.steps)

    print(f"Objetivo {target} mm · standoff {args.standoff} mm · azimut {azimuth:.1f}°")
    print(f"{'#':>2} {'offset x':>9} {'offset y':>9} {'offset z':>9} | {'x':>8} {'y':>8} {'z':>8} {'rx':>8} {'ry':>8} {'rz':>8}")
    for i, (wp, pose) in enumerate(zip(route, absolute_poses(route, target))):
        print(f"{i:>2} {wp.offset[0]:>9.1f} {wp.offset[1]:>9.1f} {wp.offset[2]:>9.1f} | "
              + " ".join(f"{v:>8.2f}" for v in pose))
    aim, tilt = check_route(route, target)
    print(f"Error máximo del eje óptico: {aim:.2e}° · inclinación máxima del horizonte: {tilt:.2e}°")

    if args.lua:
        flange = camera_to_flange(route, args.camera_offset)
        worst = max(aim_errors((*_add(target, wp.offset), *wp.rpy), target, args.camera_offset)[0] for wp in flange)
        print(f"Brida (cámara a {args.camera_offset} mm): error máximo del eje óptico reconstruido {worst:.2e}°")
        lua = render_lua(flange, args.seed_joints, args.speed, args.acc, args.blend, args.camera_timeout)
        with open(args.lua, "w", encoding="utf-8") as f:
            f.write(lua)
        print(f"Lua escrito en {args.lua} ({len(lua.splitlines())} líneas)")


if __name__ == "__main__":
    main()
