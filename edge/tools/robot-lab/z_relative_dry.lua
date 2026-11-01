local check = GetForwardKin(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
if check == nil then
  return
end

SetSysVarValue(s_var_10, 0)
local dz = GetSysVarValue(s_var_1)
local request_id = GetSysVarValue(s_var_8)
SetSysVarValue(s_var_11, request_id)
if dz < 1 or dz > 200 then
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
SetSysVarValue(s_var_12, x)
SetSysVarValue(s_var_13, y)
SetSysVarValue(s_var_14, z)

local up_z = z + dz
SetSysVarValue(s_var_15, up_z)
local up = {x, y, up_z, rx, ry, rz}
local has_up = GetInverseKinHasSolution(0, up, joints)
SetSysVarValue(s_var_16, has_up)

SetSysVarValue(s_var_10, 1)
