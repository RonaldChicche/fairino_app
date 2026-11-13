import asyncio
import time
from enum import Enum
from typing import Callable

ALERT = "Robot sin conexión. Un movimiento en curso no se detendrá: pulsa el paro de emergencia."


class Link(str, Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"


class ConnectionMonitor:
    """El controlador publica su estado unas 100 veces por segundo: si el contador de tramas se congela, no hay conexión."""

    def __init__(self, read_frame: Callable[[], int], on_change: Callable[[Link, str], None],
                 stale_after: float = 0.5, interval: float = 0.1, clock: Callable[[], float] = time.monotonic):
        self._read_frame, self._on_change = read_frame, on_change
        self._stale_after, self._interval, self._clock = stale_after, interval, clock
        self._last, self._changed_at = read_frame(), clock()
        self.state = Link.CONNECTED

    def check(self) -> Link:
        now, frame = self._clock(), self._read_frame()
        if frame != self._last:
            self._last, self._changed_at = frame, now
        state = Link.CONNECTED if now - self._changed_at <= self._stale_after else Link.DISCONNECTED
        if state != self.state:
            self.state = state
            self._on_change(state, ALERT if state is Link.DISCONNECTED else "")
        return state

    async def run(self) -> None:
        while True:
            try:
                self.check()
            except Exception:
                self.state = Link.DISCONNECTED
            await asyncio.sleep(self._interval)
