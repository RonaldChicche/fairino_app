-- Prueba: ¿el intérprete del controlador trae la librería math? (sin movimiento)
-- Salida: s_var_3 = 5 si math existe (sqrt(16) + cos(0)); si no existe, el programa falla con error
SetSysVarValue(s_var_3, math.sqrt(16) + math.cos(0))
