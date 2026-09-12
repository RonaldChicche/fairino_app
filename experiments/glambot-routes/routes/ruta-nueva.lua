-- Glambot: grúa vertical relativa al objetivo. Generado por experiments/glambot-routes/routes.py; no editar a mano.
-- Parámetros: ruta-nueva · 3 puntos · cámara a 100.0 mm · velocidad 10% · blend 10 mm · generado desde el simulador de toma (sim/)
--
-- Objetivo fijo en la base del robot: {-1000.0, 0.0, 89.5} mm.
-- Estado: s_var_6 = 0 iniciado · 2 moviendo · 3 terminado · -1 punto inalcanzable.
-- Esta variante no espera confirmación externa: tras validar la ruta, comienza inmediatamente.

local REVIEW_ONLY = true
if REVIEW_ONLY then
  return
end

local ROUTE = {  -- brida relativa al objetivo: {dx, dy, dz, rx, ry, rz} [mm, grados]
  {1045.5715, 975.9450, 654.6168, -114.5929, -0.0000, 133.0274},
  {241.4430, 676.5207, 342.3206, -115.4807, -0.0000, 160.3591},
  {237.4622, -801.0271, 336.6766, -111.9481, 0.0000, 16.5123}
}
local SEED = {-105.0809, -53.7500, 39.5179, -14.0952, -61.2890, -165.4817}  -- postura de referencia para elegir la solución de cinemática inversa
local TOOL = 0
local USER = 0
local SPEED = 10
local ACC = 50
local BLEND_R = 10

-- El controlador ejecuta el script al subirlo para validarlo; ahí la cinemática devuelve nil y no se mueve nada
local check = GetForwardKin(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
if check == nil then
  return
end

SetSysVarValue(s_var_6, 0)
local tx = -1000.0
local ty = 0.0
local tz = 89.5

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
