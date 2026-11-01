local SPEED = 10.0
local ACC = 50.0
local TOOL = 0
local USER = 0
local BLEND_R = 10.0

local check = GetForwardKin(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
if check == nil then
  return
end

SetSysVarValue(s_var_10, 0)
local d = GetSysVarValue(s_var_1)
local request_id = GetSysVarValue(s_var_8)
SetSysVarValue(s_var_11, request_id)
if d < 20 or d > 250 then
  SetSysVarValue(s_var_10, -2)
  return
end

local j1 = GetSysVarValue(s_var_2)
local j2 = GetSysVarValue(s_var_3)
local j3 = GetSysVarValue(s_var_4)
local j4 = GetSysVarValue(s_var_5)
local j5 = GetSysVarValue(s_var_6)
local j6 = GetSysVarValue(s_var_7)
local joints = {j1, j2, j3, j4, j5, j6}

local x, y, z, rx, ry, rz = GetForwardKin(j1, j2, j3, j4, j5, j6)
if z == nil then
  SetSysVarValue(s_var_10, -1)
  return
end

local points = {
  {x, y, z + d, rx, ry, rz},
  {x, y + d, z + d, rx, ry, rz},
  {x, y + d, z, rx, ry, rz},
  {x, y, z, rx, ry, rz}
}
local ref = joints
local solutions = {}
for i = 1, 4 do
  if GetInverseKinHasSolution(0, points[i], ref) ~= 1 then
    SetSysVarValue(s_var_10, -1)
    return
  end
  solutions[i] = GetInverseKinRef(0, points[i], ref)
  ref = solutions[i]
end

SetSysVarValue(s_var_10, 2)
for i = 1, 4 do
  local u = solutions[i]
  local p = points[i]
  local blend = BLEND_R
  if i == 4 then
    blend = -1
  end
  MoveL(u[1], u[2], u[3], u[4], u[5], u[6], p[1], p[2], p[3], p[4], p[5], p[6], TOOL, USER, SPEED, ACC, 100, blend, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 100, 0)
end
