local x, y, z, rx, ry, rz = GetForwardKin(0.0, -90.0, 90.0, -90.0, -90.0, 0.0)
if z == nil then
  return
end
MoveJ(0.0, -90.0, 90.0, -90.0, -90.0, 0.0, x, y, z, rx, ry, rz, 0, 0, 30, 180, 100, 0.000, 0.000, 0.000, 0.000, 0, 0, 0, 0, 0, 0, 0, 0)

local tz = z - 50.0
local j1, j2, j3, j4, j5, j6 = GetInverseKin(0, x, y, tz, rx, ry, rz, -1)
if j1 == nil then
  SetSysVarValue(s_var_20, -1)
  return
end
MoveL(j1, j2, j3, j4, j5, j6, x, y, tz, rx, ry, rz, 0, 0, 30, 100, 100, -1, 0, 0.000, 0.000, 0.000, 0.000, 0, 0, 0, 0, 0, 0, 0, 0, 100, 0)
SetSysVarValue(s_var_20, 1)
