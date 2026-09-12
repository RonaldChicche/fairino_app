-- Prueba: qué devuelve GetInverseKinHasSolution en Lua (sin movimiento)
-- Poses de referencia del FR5 simulado: pose TCP en la postura inicial (alcanzable) y una a 5 m (inalcanzable).
-- El controlador valida el Lua al subirlo y exige el nombre literal de la variable de sistema en cada
-- SetSysVarValue, por eso no hay una función auxiliar que reciba la variable.
-- Salidas: s_var_5 (pose alcanzable) y s_var_6 (pose inalcanzable), codificadas así:
--   1 = booleano true · 0 = booleano false · 2 = texto "True" · 3 = texto "False"
--   4 = número (el valor va en s_var_7 / s_var_8) · 9 = otro tipo
local joint_ref = {0.0, -90.0, 90.0, -90.0, -90.0, 0.0}

local reachable = GetInverseKinHasSolution(0, {-497.0, -102.0, 477.0, 180.0, 0.0, 90.0}, joint_ref)
if reachable == true then
  SetSysVarValue(s_var_5, 1)
elseif reachable == false then
  SetSysVarValue(s_var_5, 0)
elseif reachable == "True" then
  SetSysVarValue(s_var_5, 2)
elseif reachable == "False" then
  SetSysVarValue(s_var_5, 3)
elseif type(reachable) == "number" then
  SetSysVarValue(s_var_5, 4)
  SetSysVarValue(s_var_7, reachable)
else
  SetSysVarValue(s_var_5, 9)
end

local unreachable = GetInverseKinHasSolution(0, {5000.0, 0.0, 0.0, 180.0, 0.0, 90.0}, joint_ref)
if unreachable == true then
  SetSysVarValue(s_var_6, 1)
elseif unreachable == false then
  SetSysVarValue(s_var_6, 0)
elseif unreachable == "True" then
  SetSysVarValue(s_var_6, 2)
elseif unreachable == "False" then
  SetSysVarValue(s_var_6, 3)
elseif type(unreachable) == "number" then
  SetSysVarValue(s_var_6, 4)
  SetSysVarValue(s_var_8, unreachable)
else
  SetSysVarValue(s_var_6, 9)
end
