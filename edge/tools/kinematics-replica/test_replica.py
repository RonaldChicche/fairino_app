import math

import kinematics_replica as rep

HOME = [10.0, -100.0, 80.0, -70.0, -95.0, 15.0]


def test_forward_adds_flange_offset():
    # Con la muñeca en HOME, la brida queda 106 mm adelante en z de la pose del marco wrist3 del URDF.
    pose = rep.get_forward_kin(HOME)
    wrist = rep.kin._chain(HOME)[5][1]
    assert abs(math.dist(pose[:3], wrist) - 106.0) < 1e-9


def test_relative_tool_moves_along_tool_axes():
    pose = rep.get_forward_kin(HOME)
    joints = rep.get_inverse_kin(2, [0, 0, 50, 0, 0, 0], ref=HOME)
    moved = rep.get_forward_kin(joints)
    rot = rep.fairino_rpy_to_rotation(*pose[3:])
    expected = [pose[i] + 50.0 * rot[i][2] for i in range(3)]
    assert math.dist(moved[:3], expected) < 1e-3
