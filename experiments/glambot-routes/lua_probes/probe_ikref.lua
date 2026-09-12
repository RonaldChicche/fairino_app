-- Prueba: formas de retorno de GetInverseKin y GetInverseKinRef en Lua (sin movimiento)
-- Pose TCP del FR5 simulado en la postura inicial {0, -90, 90, -90, -90, 0}.
-- Salidas: s_var_11..16 = articulaciones de GetInverseKin (-999 si no hay valor)
--          s_var_17, s_var_18 = dos primeros retornos de GetInverseKinRef
--          s_var_19 = tipo del primer retorno de GetInverseKinRef (4 número, 5 tabla, 0 nil, 9 otro)
local j1, j2, j3, j4, j5, j6 = GetInverseKin(0, -497.0, -102.0, 477.0, 180.0, 0.0, 90.0, -1)
local a1 = j1 or -999
local a2 = j2 or -999
local a3 = j3 or -999
local a4 = j4 or -999
local a5 = j5 or -999
local a6 = j6 or -999
SetSysVarValue(s_var_11, a1)
SetSysVarValue(s_var_12, a2)
SetSysVarValue(s_var_13, a3)
SetSysVarValue(s_var_14, a4)
SetSysVarValue(s_var_15, a5)
SetSysVarValue(s_var_16, a6)

local pose = {-497.0, -102.0, 477.0, 180.0, 0.0, 90.0}
local joint_ref = {0.0, -90.0, 90.0, -90.0, -90.0, 0.0}
local r1, r2 = GetInverseKinRef(0, pose, joint_ref)
local kind = 9
if r1 == nil then
  kind = 0
elseif type(r1) == "number" then
  kind = 4
elseif type(r1) == "table" then
  kind = 5
end
SetSysVarValue(s_var_19, kind)
local first = -999
if type(r1) == "number" then
  first = r1
elseif type(r1) == "table" and type(r1[1]) == "number" then
  first = r1[1]
end
local second = -999
if type(r2) == "number" then
  second = r2
end
SetSysVarValue(s_var_17, first)
SetSysVarValue(s_var_18, second)
