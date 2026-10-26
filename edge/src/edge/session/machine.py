import asyncio
from dataclasses import dataclass

from edge.session.ports import Camera, Renderer, Robot
from edge.session.states import NEXT, State


class Busy(Exception):
    pass


class NotAbortable(Exception):
    pass


@dataclass
class Session:
    id: str
    primitive: str
    params: dict
    state: State = State.REQUESTED
    error: str | None = None
    output: str | None = None


class SessionManager:
    def __init__(self, robot: Robot, camera: Camera, renderer: Renderer,
                 confirm_timeout: float = 5.0, poll_interval: float = 0.05):
        self._robot, self._camera, self._renderer = robot, camera, renderer
        self._confirm_timeout, self._poll_interval = confirm_timeout, poll_interval
        self._sessions: dict[str, Session] = {}
        self._lock = asyncio.Lock()
        self._abort = False

    def get(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)

    def abort(self) -> None:
        # Una vez en moving solo corta el paro de emergencia del robot (regla 7).
        early = (State.REQUESTED, State.CAMERA_STARTING, State.RECORDING_CONFIRMED)
        if not any(s.state in early for s in self._sessions.values()):
            raise NotAbortable()
        self._abort = True

    async def run(self, session_id: str, primitive: str, params: dict) -> Session:
        # Sin await entre la consulta y el candado: la comprobación es atómica en el event loop.
        known = self._sessions.get(session_id)
        if known:
            return known
        if self._lock.locked():
            raise Busy()
        async with self._lock:
            self._abort = False
            session = self._sessions[session_id] = Session(session_id, primitive, params)
            await self._execute(session)
            return session

    def _go(self, session: Session, state: State) -> None:
        if state not in NEXT.get(session.state, set()):
            raise RuntimeError(f"{session.state.value} -> {state.value}")
        session.state = state

    async def _execute(self, s: Session) -> None:
        try:
            self._go(s, State.CAMERA_STARTING)
            await self._camera.start_recording()
            if not await self._wait_recording():
                return await self._fail(s, "la cámara no confirmó que graba")
            self._go(s, State.RECORDING_CONFIRMED)
            if self._abort:
                await self._camera.stop_recording()
                return self._go(s, State.ABORTED)
            self._go(s, State.MOVING)
            await self._robot.run_primitive(s.id, s.primitive, s.params)
            self._go(s, State.FINISHING)
            await self._camera.stop_recording()
            self._go(s, State.RENDERING)
            s.output = await self._renderer.render(s.id)
            self._go(s, State.DONE)
        except Exception as exc:
            await self._fail(s, repr(exc))

    async def _wait_recording(self) -> bool:
        deadline = asyncio.get_running_loop().time() + self._confirm_timeout
        while asyncio.get_running_loop().time() < deadline:
            if await self._camera.is_recording():
                return True
            await asyncio.sleep(self._poll_interval)
        return False

    async def _fail(self, s: Session, error: str) -> None:
        s.error = error
        if s.state in (State.CAMERA_STARTING, State.RECORDING_CONFIRMED, State.MOVING):
            try:
                await self._camera.stop_recording()
            except Exception:
                pass
        s.state = State.FAILED
