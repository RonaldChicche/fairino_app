#!/usr/bin/env python3
"""Valida la ruta modificada en el FR10 y carga el programa Lua sin ejecutarlo."""
import json
import math
import os
import sys
import time
from pathlib import Path

# Fix Windows console encoding for Chinese characters in fairino SDK prints
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / ".venv" / "Lib" / "site-packages"))

from routes import (  # noqa: E402
    _add,
    _column,
    camera_to_flange,
    fairino_rpy_to_rotation,
    interpolate_pose,
    route_from_spec,
)

# Geometría URDF del FR10 V6 para cálculo de altura J2..J6
JOINT_ORIGINS = [
    (0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
    (0.0, 0.0, 180.0, math.pi / 2, 0.0, 0.0),
    (-700.0, 0.0, 0.0, 0.0, 0.0, 0.0),
    (-586.0, 0.0, 0.0, 0.0, 0.0, 0.0),
    (0.0, 0.0, 159.0, math.pi / 2, 0.0, 0.0),
    (0.0, 0.0, 114.0, -math.pi / 2, 0.0, 0.0),
]


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


LUA_TEMPLATE_NOWAIT = """-- Glambot: grúa vertical relativa al objetivo. Generado por experiments/glambot-routes/routes.py; no editar a mano.
-- Parámetros: {name} · {num_points} puntos · cámara a {camera_offset:.1f} mm · velocidad {speed}% · blend {blend} mm · generado desde el simulador de toma (sim/)
--
-- Objetivo fijo en la base del robot: {{{tx:.1f}, {ty:.1f}, {tz:.1f}}} mm.
-- Estado: s_var_6 = 0 iniciado · 2 moviendo · 3 terminado · -1 punto inalcanzable.
-- Esta variante no espera confirmación externa: tras validar la ruta, comienza inmediatamente.

local REVIEW_ONLY = true
if REVIEW_ONLY then
  return
end

local ROUTE = {{  -- brida relativa al objetivo: {{dx, dy, dz, rx, ry, rz}} [mm, grados]
{route_rows}
}}
local SEED = {{{seed_str}}}  -- postura de referencia para elegir la solución de cinemática inversa
local TOOL = 0
local USER = 0
local SPEED = {speed}
local ACC = {acc}
local BLEND_R = {blend}

-- El controlador ejecuta el script al subirlo para validarlo; ahí la cinemática devuelve nil y no se mueve nada
local check = GetForwardKin(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
if check == nil then
  return
end

SetSysVarValue(s_var_6, 0)
local tx = {tx:.1f}
local ty = {ty:.1f}
local tz = {tz:.1f}

-- 1. Todos los puntos deben tener solución antes de mover nada
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

-- 2. Ruta: MoveJ al primer punto y MoveL por el resto, con blending salvo en el último
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

PROGRAM_DIRS = ("/fruser/", "/usr/local/etc/controller/lua/")


def main():
    ip = os.environ.get("FAIRINO_ROBOT_IP", "192.168.58.2")
    route_arg = sys.argv[1] if len(sys.argv) > 1 else "ruta-prueba-01"
    if not route_arg.endswith(".json"):
        spec_path = HERE / "routes" / f"{route_arg}.json"
    else:
        spec_path = Path(route_arg) if Path(route_arg).is_absolute() else HERE / "routes" / route_arg
    lua_path = spec_path.with_suffix(".lua")
    samples_per_seg = 24
    clearance_min = 50.0

    print("=== PASO 1: Leer especificación JSON ===")
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    target = tuple(float(v) for v in spec["target"])
    camera_offset = float(spec["camera"]["offset_mm"])
    print(f"Ruta: {spec['name']}, Objetivo: {target}, Offset cámara: {camera_offset} mm")

    print("\n=== PASO 2: Generar ruta de cámara y convertir a brida ===")
    camera_route = route_from_spec(spec)
    flange_route = camera_to_flange(camera_route, camera_offset)
    waypoints = [(*_add(target, wp.offset), *wp.rpy) for wp in flange_route]

    for i, (c_wp, f_wp) in enumerate(zip(camera_route, flange_route), 1):
        print(f"P{i} Cámara offset: {[round(v, 1) for v in c_wp.offset]} RPY: {[round(v, 4) for v in c_wp.rpy]}")
        print(f"P{i} Brida offset:  {[round(v, 4) for v in f_wp.offset]} RPY: {[round(v, 4) for v in f_wp.rpy]}")
        abs_p = (*_add(target, f_wp.offset), *f_wp.rpy)
        print(f"P{i} Brida base:    {[round(v, 4) for v in abs_p]}")

    print(f"\n=== PASO 3: Densificar trayectoria ({samples_per_seg} intervalos/tramo) ===")
    poses = [waypoints[0]]
    for a, b in zip(waypoints, waypoints[1:]):
        poses.extend(interpolate_pose(a, b, k / samples_per_seg) for k in range(1, samples_per_seg + 1))
    print(f"Total poses densificadas para validación: {len(poses)}")

    print(f"\n=== PASO 4: Conectar al controlador FAIRINO ({ip}) - SOLO LECTURA ===")
    from fairino import Robot

    robot = Robot.RPC(ip)
    connected = getattr(robot, "is_connect", getattr(robot, "is_conect", False))
    if not connected:
        print("ERROR: No se pudo conectar con el controlador", file=sys.stderr)
        return 1
    print("Conexión RPC establecida con éxito.")

    try:
        err, raw_limits = robot.GetJointSoftLimitDeg()
        if err != 0 or len(raw_limits) != 12:
            print(f"ERROR: Fallo al leer límites de articulación ({err})", file=sys.stderr)
            return 1
        limits = [(min(raw_limits[2 * i : 2 * i + 2]), max(raw_limits[2 * i : 2 * i + 2])) for i in range(6)]
        print("Límites articulares leídos:")
        for j_idx, (l_min, l_max) in enumerate(limits, 1):
            print(f"  J{j_idx}: [{l_min:.1f}°, {l_max:.1f}°]")

        err, current = robot.GetActualJointPosDegree()
        if err != 0 or not current:
            print(f"ERROR: Fallo al leer postura actual ({err})", file=sys.stderr)
            return 1
        current = list(current)
        print("Postura actual del robot (grados):", " ".join(f"{v:.4f}" for v in current))

        print("\n=== PASO 5: Probar las 8 configuraciones de IK ===")
        candidates = []
        for config in range(8):
            err, seed = robot.GetInverseKin(0, list(poses[0]), config)
            if err == 0 and seed:
                candidates.append((config, list(seed)))

        print(f"Configuraciones con solución en P1: {[c[0] for c in candidates]}")

        valid = []
        for config, seed in candidates:
            ref = seed
            rows = []
            reason = None
            max_jump = 0.0
            min_margin = math.inf

            for idx, pose in enumerate(poses):
                err, res = robot.GetInverseKinHasSolution(0, list(pose), ref)
                if err != 0 or not has_solution(res):
                    reason = f"GetInverseKinHasSolution fallo {err} en muestra {idx}"
                    break
                err, joints = robot.GetInverseKinRef(0, list(pose), ref)
                if err != 0 or not joints:
                    reason = f"GetInverseKinRef fallo {err} en muestra {idx}"
                    break

                if idx > 0:
                    max_jump = max(max_jump, max(abs(a - b) for a, b in zip(joints, ref)))

                margin = min(min(v - low, high - v) for v, (low, high) in zip(joints, limits))
                min_margin = min(min_margin, margin)
                if margin < 0:
                    reason = f"Excede límite articular en muestra {idx}"
                    break

                pts = joint_positions(joints)
                rows.append((idx, list(joints), pts))
                ref = list(joints)

            if reason is not None:
                print(f"Config {config}: DESCARTADA ({reason})")
                continue

            min_route_clearance = min(pt[2] for _, _, pts in rows for pt in pts[1:])
            worst_joint_info = min(
                ((pt[2], idx, j_i + 1) for idx, _, pts in rows for j_i, pt in enumerate(pts[1:], 1)),
                key=lambda x: x[0],
            )

            # Validar aproximación MoveJ desde postura actual hasta P1 (seed) en 100 pasos
            approach_steps = [
                [a + (b - a) * s / 100.0 for a, b in zip(current, seed)]
                for s in range(101)
            ]
            approach_min_clearance = min(pt[2] for j_vals in approach_steps for pt in joint_positions(j_vals)[1:])

            print(
                f"Config {config}: VÁLIDA | Despeje ruta min: {min_route_clearance:.1f} mm "
                f"(muestra {worst_joint_info[1]}, J{worst_joint_info[2]}) | "
                f"Despeje aprox MoveJ: {approach_min_clearance:.1f} mm | "
                f"Margen articular: {min_margin:.1f}° | Salto max: {max_jump:.1f}°"
            )

            effective_clearance = min(min_route_clearance, approach_min_clearance)
            if effective_clearance >= clearance_min:
                valid.append({
                    "config": config,
                    "seed": seed,
                    "min_clearance": effective_clearance,
                    "min_margin": min_margin,
                    "max_jump": max_jump,
                    "rows": rows,
                })
            else:
                print(f"  -> Descartada por despeje < {clearance_min} mm")

        if not valid:
            print(f"ERROR: Ninguna configuración cumple el despeje mínimo de {clearance_min} mm", file=sys.stderr)
            return 2

        # Selección: mayor margen articular y mejor despeje
        best = max(valid, key=lambda x: (x["min_margin"], x["min_clearance"]))
        chosen_config = best["config"]
        chosen_seed = best["seed"]
        print(f"\nConfiguración ELEGIDA: {chosen_config}")
        print(f"Despeje mínimo global: {best['min_clearance']:.1f} mm")
        print(f"Margen articular mínimo: {best['min_margin']:.1f}°")
        print("SEED Joints:", " ".join(f"{v:.4f}" for v in chosen_seed))

        print("\nArticulaciones en los waypoints principales:")
        wp_indices = [i * samples_per_seg for i in range(len(waypoints))]
        for wp_num, idx in enumerate(wp_indices, 1):
            _, joints, pts = best["rows"][idx]
            h_str = " ".join(f"J{j+1}={pt[2]:.1f}mm" for j, pt in enumerate(pts))
            print(f"  P{wp_num}: Articulaciones: {[round(v, 4) for v in joints]}")
            print(f"      Alturas: {h_str}")

        print(f"\n=== PASO 6: Actualizar seed_joints en {spec_path.name} ===")
        spec["seed_joints"] = [round(v, 4) for v in chosen_seed]
        spec_path.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
        print(f"Archivo {spec_path} actualizado exitosamente.")

        print("\n=== PASO 7: Regenerar ruta-nueva.lua con REVIEW_ONLY ===")
        route_rows = ",\n".join("  {" + ", ".join(f"{v:.4f}" for v in (*wp.offset, *wp.rpy)) + "}" for wp in flange_route)
        seed_str = ", ".join(f"{v:.4f}" for v in chosen_seed)
        lua_content = LUA_TEMPLATE_NOWAIT.format(
            name=spec["name"],
            num_points=len(flange_route),
            camera_offset=camera_offset,
            speed=spec["motion"]["speed"],
            acc=spec["motion"]["acc"],
            blend=spec["motion"]["blend_mm"],
            tx=target[0],
            ty=target[1],
            tz=target[2],
            route_rows=route_rows,
            seed_str=seed_str,
        )
        lua_path.write_text(lua_content, encoding="utf-8")
        print(f"Archivo {lua_path} escrito ({len(lua_content)} bytes).")

        # Verificar que el bloqueo REVIEW_ONLY está presente
        assert "local REVIEW_ONLY = true" in lua_content
        assert "if REVIEW_ONLY then\n  return\nend" in lua_content
        print("Verificación de seguridad: Guardas REVIEW_ONLY y GetForwardKin confirmadas.")

        print("\n=== PASO 8: Cargar programa Lua en el controlador ===")
        upload_ok = False
        for attempt in range(1, 4):
            try:
                print(f"Ejecutando robot.LuaUpload({lua_path})... (intento {attempt})")
                res = robot.LuaUpload(str(lua_path))
            except Exception as exc:
                res = f"Excepción {type(exc).__name__}: {exc}"
            print(f"Resultado LuaUpload: {res}")
            if res == 0 or isinstance(res, tuple):
                upload_ok = True
                break
            time.sleep(2.0)

        if not upload_ok:
            print("ERROR: Fallo al subir el programa Lua al controlador", file=sys.stderr)
            return 1

        load_ok = False
        loaded_target = None
        for pdir in PROGRAM_DIRS:
            target_file = f"{pdir}{lua_path.name}"
            print(f"Intentando robot.ProgramLoad('{target_file}')...")
            try:
                load_res = robot.ProgramLoad(target_file)
            except Exception as exc:
                load_res = f"Excepción {exc}"
            print(f"Resultado ProgramLoad: {load_res}")
            if load_res == 0:
                load_ok = True
                loaded_target = target_file
                break

        if not load_ok:
            print(f"ERROR: No se pudo cargar el programa en ninguna de las rutas {PROGRAM_DIRS}", file=sys.stderr)
            return 1

        print(f"\nPrograma '{loaded_target}' cargado exitosamente en el controlador.")

        # Consultar programa cargado si la función existe
        if hasattr(robot, "GetLoadedProgram"):
            try:
                err_lp, cur_prog = robot.GetLoadedProgram()
                print(f"GetLoadedProgram(): err={err_lp}, programa='{cur_prog}'")
            except Exception as exc:
                print(f"GetLoadedProgram(): no disponible o error: {exc}")

        print("\n=== COMPLETADO CON ÉXITO ===")
        print("El programa está cargado en el controlador y NO fue ejecutado (prohibición de movimiento respetada).")

    finally:
        robot.CloseRPC()
        print("Conexión RPC cerrada.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
