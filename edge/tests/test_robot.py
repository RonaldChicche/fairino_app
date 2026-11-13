import pytest

from edge.robot.monitor import ConnectionMonitor, Link
from edge.robot.protocol import InvalidParams, Param, Primitive, check_jog, check_params
from edge.robot.verdict import Observation, failures

SPEC = Primitive("z.lua", {"dz": Param(1, 1, 200)}, 8, 10, 11, 2.0)
GOOD = dict(status=2, done_status=2, echo=7, expected_id=7, seen_moving=True, stopped=True,
            error=(0, 0), emergency_stop=0, stream_alive=True, pose_error_mm=0.1)


@pytest.mark.parametrize("params", [{"dz": 0}, {"dz": 350}, {"dz": float("nan")}, {"dz": "5"}, {}, {"dz": 10, "x": 1}])
def test_params_outside_the_declared_range_are_rejected_before_the_robot(params):
    with pytest.raises(InvalidParams):
        check_params(SPEC, params)


@pytest.mark.parametrize("change,reason", [
    ({}, None),
    ({"status": 0}, "no llegó a su final"),
    ({"seen_moving": False}, "nunca se movió"),
    ({"pose_error_mm": 60.0}, "de la esperada"),
    ({"pose_error_mm": float("nan")}, "de la esperada"),
    ({"error": (1, 19)}, "reporta el error"),
    ({"echo": 6}, "no leyó el ID"),
    ({"stream_alive": False}, "se congeló"),
    ({"emergency_stop": 1}, "paro de emergencia"),
])
def test_a_stopped_program_is_not_a_successful_one(change, reason):
    found = " | ".join(failures(Observation(**{**GOOD, **change})))
    assert (reason in found) if reason else not found


def test_monitor_alerts_when_the_state_stream_freezes_and_clears_when_it_returns():
    now, frame, events = [0.0], [1], []
    monitor = ConnectionMonitor(lambda: frame[0], lambda link, alert: events.append((link, bool(alert))), clock=lambda: now[0])
    for t, f in [(0.3, 2), (0.6, 2), (1.2, 2), (1.3, 3)]:
        now[0], frame[0] = t, f
        monitor.check()
    assert events == [(Link.DISCONNECTED, True), (Link.CONNECTED, False)]


@pytest.mark.parametrize("args", [("mesa", 1, 1, 5, 5), ("joint", 7, 1, 5, 5), ("joint", 1, 0, 5, 5),
                                  ("joint", 1, 1, 50, 5), ("joint", 1, 1, 5, 40), ("base", 3, -1, 0, 5)])
def test_jog_beyond_the_adapters_caps_is_rejected(args):
    with pytest.raises(InvalidParams):
        check_jog(*args, limit_distance=30, limit_speed=10)
    check_jog("joint", 6, -1, 10, 5, limit_distance=30, limit_speed=10)
