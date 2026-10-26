from enum import Enum


class State(str, Enum):
    REQUESTED = "requested"
    CAMERA_STARTING = "camera_starting"
    RECORDING_CONFIRMED = "recording_confirmed"
    MOVING = "moving"
    FINISHING = "finishing"
    RENDERING = "rendering"
    DONE = "done"
    FAILED = "failed"
    ABORTED = "aborted"


TERMINAL = {State.DONE, State.FAILED, State.ABORTED}

NEXT = {
    State.REQUESTED: {State.CAMERA_STARTING, State.FAILED, State.ABORTED},
    State.CAMERA_STARTING: {State.RECORDING_CONFIRMED, State.FAILED, State.ABORTED},
    State.RECORDING_CONFIRMED: {State.MOVING, State.FAILED, State.ABORTED},
    State.MOVING: {State.FINISHING, State.FAILED},
    State.FINISHING: {State.RENDERING, State.FAILED},
    State.RENDERING: {State.DONE, State.FAILED},
}
