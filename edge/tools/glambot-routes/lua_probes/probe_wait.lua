SetSysVarValue(s_var_9, 1)
local received = false
for _ = 1, 1000 do
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
