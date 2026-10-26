import asyncio

import pytest

from edge.camera.fake import FakeCamera
from edge.render.fake import FakeRenderer
from edge.robot.fake import FakeRobot
from edge.session.machine import Busy, SessionManager
from edge.session.states import State


def manager(robot=None, camera=None):
    return SessionManager(robot or FakeRobot(), camera or FakeCamera(), FakeRenderer(), confirm_timeout=0.1, poll_interval=0.01)


def test_happy_path_moves_after_recording_and_renders():
    robot, camera = FakeRobot(), FakeCamera()
    s = asyncio.run(manager(robot, camera).run("t1", "crane", {}))
    assert (s.state, s.output) == (State.DONE, "t1.mp4")
    assert camera.calls == ["start", "stop"] and robot.calls == ["t1"]


def test_camera_without_confirmation_never_moves_robot():
    robot, camera = FakeRobot(), FakeCamera(confirms=False)
    s = asyncio.run(manager(robot, camera).run("t1", "crane", {}))
    assert s.state == State.FAILED and robot.calls == []


def test_repeated_id_does_not_move_robot_twice():
    robot = FakeRobot()
    m = manager(robot)

    async def twice():
        return await m.run("t1", "crane", {}), await m.run("t1", "crane", {})

    first, second = asyncio.run(twice())
    assert first is second and robot.calls == ["t1"]


def test_second_session_while_busy_is_rejected():
    async def scenario():
        gate = asyncio.Event()
        robot = FakeRobot(gate=gate)
        m = manager(robot)
        running = asyncio.create_task(m.run("t1", "crane", {}))
        await asyncio.sleep(0.05)
        with pytest.raises(Busy):
            await m.run("t2", "crane", {})
        gate.set()
        await running
        return robot.calls

    assert asyncio.run(scenario()) == ["t1"]


def test_robot_failure_stops_camera_and_is_not_retried():
    robot, camera = FakeRobot(fails=True), FakeCamera()
    s = asyncio.run(manager(robot, camera).run("t1", "crane", {}))
    assert s.state == State.FAILED and camera.calls == ["start", "stop"] and robot.calls == ["t1"]
