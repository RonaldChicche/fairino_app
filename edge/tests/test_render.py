from pathlib import Path

import pytest

from edge.render.command import build_command
from edge.render.profile import RenderProfile


@pytest.mark.parametrize("source_fps, present, absent", [
    (119.88, "setpts=4*PTS", "minterpolate"),
    (59.94, "minterpolate=fps=120:", "fps=120,"),
    (240.0, ",fps=120,", "minterpolate"),
])
def test_filters_reach_the_slow_motion_factor(source_fps, present, absent):
    command = build_command(RenderProfile(), Path("raw.mp4"), Path("final.mp4"), source_fps)
    filters = command[command.index("-vf") + 1]
    assert present in filters and absent not in filters
