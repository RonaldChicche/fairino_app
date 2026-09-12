-- Prueba: leer una variable de sistema escrita por el PC y escribir otra de vuelta (sin movimiento)
-- Entrada: s_var_1. Salida: s_var_2 = s_var_1 + 1
local v = GetSysVarValue(s_var_1)
SetSysVarValue(s_var_2, v + 1)
