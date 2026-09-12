-- Prueba: versión del intérprete Lua (sin movimiento)
-- Salida: s_var_4 = número de versión (p. ej. 5.3); requiere la librería string
-- El validador del controlador rechaza llamadas con comas dentro de los argumentos de SetSysVarValue,
-- por eso el valor se calcula antes en una variable local.
local version = tonumber(string.match(_VERSION, "%d+%.%d+"))
SetSysVarValue(s_var_4, version)
