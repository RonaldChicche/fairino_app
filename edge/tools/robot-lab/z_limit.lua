local SPEED = 5.0
local ACC = 50.0
local TOOL = 0
local USER = 0

local check = GetForwardKin(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
if check == nil then
  return
end

SetSysVarValue(s_var_10, 0)
local delta = GetSysVarValue(s_var_1)
local request_id = GetSysVarValue(s_var_8)
SetSysVarValue(s_var_11, request_id)
if delta < -40 or delta > 40 or delta == 0 then
  SetSysVarValue(s_var_10, -2)
  return
end

local j1 = GetSysVarValue(s_var_2)
local j2 = GetSysVarValue(s_var_3)
local j3 = GetSysVarValue(s_var_4)
local j4 = GetSysVarValue(s_var_5)
local j5 = GetSysVarValue(s_var_6)
local j6 = GetSysVarValue(s_var_7)
local target = j6 + delta

local x, y, z, rx, ry, rz = GetForwardKin(j1, j2, j3, j4, j5, target)
if z == nil then
  SetSysVarValue(s_var_10, -1)
  return
end

SetSysVarValue(s_var_10, 2)
MoveJ(j1, j2, j3, j4, j5, target, x, y, z, rx, ry, rz, TOOL, USER, SPEED, ACC, 100, 0, 0, 0, 0, -1, 0, 0, 0, 0, 0, 0, 0)
