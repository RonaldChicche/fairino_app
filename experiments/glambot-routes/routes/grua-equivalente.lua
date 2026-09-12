-- Glambot: grúa vertical relativa al objetivo. Generado por experiments/glambot-routes/routes.py; no editar a mano.
-- Parámetros: grua-equivalente · 6 puntos · cámara a 100.0 mm · velocidad 20.0% · blend 10.0 mm · generado desde el simulador de toma (sim/) · error del eje óptico 0.00e+00°
--
-- Protocolo por variables de sistema:
--   PC → robot: s_var_1..3 = objetivo x, y, z [mm, base] · s_var_4 = ID de toma
--               s_var_5 = cámara grabando: el PC escribe aquí el ID de toma cuando la cámara lo confirma
--   robot → PC: s_var_6 = estado · s_var_7 = ID de toma aceptado
--   Estados: 0 iniciado · 1 esperando cámara · 2 moviendo · 3 terminado
--            -1 punto inalcanzable · -2 la cámara no confirmó a tiempo
-- El robot no se mueve hasta que s_var_5 coincide con el ID de toma (regla dura de CLAUDE.md).

local ROUTE = {  -- brida relativa al objetivo: {dx, dy, dz, rx, ry, rz} [mm, grados]
  {441.9145, -0.0000, -189.3919, -66.8014, 0.0000, 90.0000},
  {448.0581, -0.0000, -89.6116, -78.6901, 0.0000, 90.0000},
  {449.9592, -0.0000, 12.8560, -91.6366, 0.0000, 90.0000},
  {446.8493, -0.0000, 114.9041, -104.4208, 0.0000, 90.0000},
  {439.9508, -0.0000, 213.6904, -115.9065, 0.0000, 90.0000},
  {431.3733, -0.0000, 308.1238, -125.5377, 0.0000, 90.0000}
}
local SEED = {-16.1740, 73.7630, -119.7590, -158.0520, -75.1650, 6.5180}  -- postura de referencia para elegir la solución de cinemática inversa
local TOOL = 0
local USER = 0
local SPEED = 20.0
local ACC = 50.0
local BLEND_R = 10.0
local CAMERA_TIMEOUT_TICKS = 3000  -- cada tick espera 10 ms

-- El controlador ejecuta el script al subirlo para validarlo; ahí la cinemática devuelve nil y no se mueve nada
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

-- 2. Esperar a que el PC confirme que la cámara está grabando
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

-- 3. Ruta: MoveJ al primer punto y MoveL por el resto, con blending salvo en el último
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
