local ROUTE = {
  {441.9145, -0.0000, -189.3919, -66.8014, 0.0000, 90.0000},
  {448.0581, -0.0000, -89.6116, -78.6901, 0.0000, 90.0000},
  {449.9592, -0.0000, 12.8560, -91.6366, 0.0000, 90.0000},
  {446.8493, -0.0000, 114.9041, -104.4208, 0.0000, 90.0000},
  {439.9508, -0.0000, 213.6904, -115.9065, 0.0000, 90.0000},
  {431.3733, -0.0000, 308.1238, -125.5377, 0.0000, 90.0000}
}
local SEED = {-16.1740, 73.7630, -119.7590, -158.0520, -75.1650, 6.5180}
local TOOL = 0
local USER = 0
local SPEED = 20.0
local ACC = 50.0
local BLEND_R = 10.0
local CAMERA_TIMEOUT_TICKS = 3000

local check = GetForwardKin(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
if check == nil then
  return
end

SetSysVarValue(s_var_6, 0)
local tx = GetSysVarValue(s_var_1)
local ty = GetSysVarValue(s_var_2)
local tz = GetSysVarValue(s_var_3)
local take_id = GetSysVarValue(s_var_4)
SetSysVarValue(s_var_7, take_id)

local joints = {}
local ref = SEED
for i, p in ipairs(ROUTE) do
  local pose = {tx + p[1], ty + p[2], tz + p[3], p[4], p[5], p[6]}
  if GetInverseKinHasSolution(0, pose, ref) ~= 1 then
    SetSysVarValue(s_var_6, -1)
    return
  end
  local solution = GetInverseKinRef(0, pose, ref)
  joints[i] = solution
  ref = solution
end

SetSysVarValue(s_var_6, 1)
local ready = false
for _ = 1, CAMERA_TIMEOUT_TICKS do
  if GetSysVarValue(s_var_5) == take_id then
    ready = true
    break
  end
  WaitMs(10)
end
if not ready then
  SetSysVarValue(s_var_6, -2)
  return
end

SetSysVarValue(s_var_6, 2)
local j = joints[1]
local p = ROUTE[1]
MoveJ(j[1], j[2], j[3], j[4], j[5], j[6], tx + p[1], ty + p[2], tz + p[3], p[4], p[5], p[6], TOOL, USER, SPEED, ACC, 100, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
for i = 2, #ROUTE do
  j = joints[i]
  p = ROUTE[i]
  local blend = BLEND_R
  if i == #ROUTE then
    blend = -1
  end
  MoveL(j[1], j[2], j[3], j[4], j[5], j[6], tx + p[1], ty + p[2], tz + p[3], p[4], p[5], p[6], TOOL, USER, SPEED, ACC, 100, blend, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 100, 0)
end
SetSysVarValue(s_var_6, 3)
