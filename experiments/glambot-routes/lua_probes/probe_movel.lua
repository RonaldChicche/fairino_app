-- Prueba CON movimiento (solo en simulador): MoveJ a la postura inicial y MoveL 50 mm hacia abajo en Z.
-- Firmas y orden de argumentos copiados del manual FRLua (MoveJ pág. 50, MoveL pág. 52).
-- El controlador ejecuta el script al subirlo para validarlo y ahí la cinemática devuelve nil:
-- en ese caso el programa termina sin moverse.
-- Salida: s_var_20 = 1 al terminar · -1 si la cinemática inversa falla durante la ejecución real
local x, y, z, rx, ry, rz = GetForwardKin(0.0, -90.0, 90.0, -90.0, -90.0, 0.0)
if z == nil then
  return
end
-- MoveJ(j1..j6, x..rz, tool, user, speed, acc, ovl, ep1..ep4, blendT, offset, offset_x..offset_rz)
MoveJ(0.0, -90.0, 90.0, -90.0, -90.0, 0.0, x, y, z, rx, ry, rz, 0, 0, 30, 180, 100, 0.000, 0.000, 0.000, 0.000, 0, 0, 0, 0, 0, 0, 0, 0)

local tz = z - 50.0
local j1, j2, j3, j4, j5, j6 = GetInverseKin(0, x, y, tz, rx, ry, rz, -1)
if j1 == nil then
  SetSysVarValue(s_var_20, -1)
  return
end
-- MoveL(j1..j6, x..rz, tool, user, speed, acc, ovl, blendR, blendRMode, ep1..ep4, search, offset,
--       offset_x..offset_rz, oacc, velAccParamMode)
MoveL(j1, j2, j3, j4, j5, j6, x, y, tz, rx, ry, rz, 0, 0, 30, 100, 100, -1, 0, 0.000, 0.000, 0.000, 0.000, 0, 0, 0, 0, 0, 0, 0, 0, 100, 0)
SetSysVarValue(s_var_20, 1)
