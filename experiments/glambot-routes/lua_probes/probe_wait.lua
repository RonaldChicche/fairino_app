-- Prueba: espera activa de una señal del PC mientras el programa corre (sin movimiento)
-- s_var_9: estado que publica el programa (1 = esperando, 2 = recibió la señal, 3 = se agotó la espera)
-- s_var_10: señal que escribe el PC (el programa espera el valor 42)
SetSysVarValue(s_var_9, 1)
local received = false
for _ = 1, 1000 do  -- hasta ~10 s
  if GetSysVarValue(s_var_10) == 42 then
    received = true
    break
  end
  WaitMs(10)
end
if received then
  SetSysVarValue(s_var_9, 2)
else
  SetSysVarValue(s_var_9, 3)
end
