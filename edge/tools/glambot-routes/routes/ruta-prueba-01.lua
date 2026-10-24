-- Glambot: grúa vertical relativa al objetivo. Generado por experiments/glambot-routes/routes.py; no editar a mano.
-- Parámetros: ruta-prueba-01 · 16 puntos · cámara a 100.0 mm · velocidad 20% · blend 10 mm · generado desde el simulador de toma (sim/)
--
-- Objetivo fijo en la base del robot: {-1500.0, 0.0, 796.0} mm.
-- Estado: s_var_6 = 0 iniciado · 2 moviendo · 3 terminado · -1 punto inalcanzable.
-- Esta variante no espera confirmación externa: tras validar la ruta, comienza inmediatamente.

local REVIEW_ONLY = true
if REVIEW_ONLY then
  return
end

local ROUTE = {  -- brida relativa al objetivo: {dx, dy, dz, rx, ry, rz} [mm, grados]
  {1192.4662, 487.8271, -56.3711, -87.4947, -0.0000, 112.2490},
  {1127.7509, 378.2824, -41.4855, -88.0025, -0.0000, 108.5430},
  {1149.3744, 319.3942, -41.9481, -87.9861, -0.0000, 105.5298},
  {1166.6777, 259.9270, -42.2562, -87.9753, -0.0000, 102.5599},
  {1179.6740, 199.8675, -42.4101, -87.9700, -0.0000, 99.6161},
  {1188.3710, 139.2001, -42.4101, -87.9700, -0.0000, 96.6809},
  {1192.7711, 77.9082, -42.2561, -87.9754, -0.0000, 93.7371},
  {1192.8712, 15.9750, -41.9480, -87.9862, -0.0000, 90.7673},
  {1188.6625, -46.6164, -41.4853, -88.0027, 0.0000, 87.7542},
  {1192.4785, -96.3602, -41.9341, -87.9925, 0.0000, 85.3802},
  {1192.1214, -145.2737, -42.2330, -87.9859, 0.0000, 83.0521},
  {1187.5965, -193.3833, -42.3824, -87.9827, 0.0000, 80.7514},
  {1178.9039, -240.7147, -42.3825, -87.9826, 0.0000, 78.4597},
  {1166.0391, -287.2926, -42.2331, -87.9859, 0.0000, 76.1590},
  {1148.9929, -333.1409, -41.9343, -87.9924, 0.0000, 73.8309},
  {1127.7509, -378.2824, -41.4855, -88.0025, 0.0000, 71.4570}
}
local SEED = {-84.6097, -7.9286, -94.9921, -248.5000, -17.0385, 171.7920}  -- postura de referencia para elegir la solución de cinemática inversa
local TOOL = 0
local USER = 0
local SPEED = 20
local ACC = 50
local BLEND_R = 10

-- El controlador ejecuta el script al subirlo para validarlo; ahí la cinemática devuelve nil y no se mueve nada
local check = GetForwardKin(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
if check == nil then
  return
end

SetSysVarValue(s_var_6, 0)
local tx = -1500.0
local ty = 0.0
local tz = 796.0

-- 1. Todos los puntos deben tener solución antes de mover nada
local joints = {}
local ref = SEED
for i, p in ipairs(ROUTE) do
  local pose = {tx + p[1], ty + p[2], tz + p[3], p[4], p[5], p[6]}
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
