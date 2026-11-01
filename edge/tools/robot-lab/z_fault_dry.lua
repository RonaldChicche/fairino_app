local check = GetForwardKin(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
if check == nil then
  return
end

SetSysVarValue(s_var_10, 0)
local request_id = GetSysVarValue(s_var_8)
SetSysVarValue(s_var_11, request_id)

local j1 = GetSysVarValue(s_var_2)
local j2 = GetSysVarValue(s_var_3)
local j3 = GetSysVarValue(s_var_4)
local j4 = GetSysVarValue(s_var_5)
local j5 = GetSysVarValue(s_var_6)
local j6 = GetSysVarValue(s_var_7)

local x, y, z, rx, ry, rz = GetForwardKin(j1, j2, j3, j4, j5, j6)
if z == nil then
  return
end

SetSysVarValue(s_var_10, 2)
local broken = nil
local boom = broken + 1
SetSysVarValue(s_var_10, 3)
