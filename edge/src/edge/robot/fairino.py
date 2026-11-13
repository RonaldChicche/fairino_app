import asyncio
import contextlib
import itertools
import math
import random
import statistics
import sys
import tempfile
import threading
import time
from pathlib import Path

from edge.robot.monitor import ALERT, ConnectionMonitor, Link
from edge.robot.protocol import JOG_REFS, InvalidParams, Primitive, RunFailed, check_jog, check_move_speed, check_params
from edge.robot.verdict import Observation, failures, pose_error

PROGRAM_DIR = "/fruser/"
VENDOR = Path(__file__).resolve().parents[3] / "vendor" / "fairino"
STALE_AFTER = 0.5
MIN_RUN = 1.0
START_TIMEOUT = 5.0
MOVE_MAX_SECONDS = 60.0
SAMPLES = 3
STATE_NAMES = {1: "idle", 2: "running", 3: "paused"}
JOG_ACCELERATION = 50.0


def load_sdk():
    sys.path.insert(0, str(VENDOR))
    import Robot
    return Robot.RPC


class FairinoRobot:
    """Una sola conexión al controlador y un cerrojo de hilo: dos órdenes nunca viajan a la vez, ni siquiera si cancelan una."""

    def __init__(self, primitives: dict[str, Primitive], ip: str = "192.168.58.2",
                 poll: float = 0.05, settle: float = 1.0, on_link_change=lambda link, alert: None,
                 jog_max_speed: float = 10.0, jog_max_distance: float = 30.0, move_max_speed: float = 10.0):
        self._primitives, self._ip = primitives, ip
        self._poll, self._settle, self._on_link_change = poll, settle, on_link_change
        self._jog_max_speed, self._jog_max_distance = jog_max_speed, jog_max_distance
        self._move_max_speed = move_max_speed
        self._sdk = None
        self._monitor: ConnectionMonitor | None = None
        self._monitor_task: asyncio.Task | None = None
        self._thread_lock = threading.Lock()
        self._busy = asyncio.Lock()
        self._ids = itertools.count(random.randrange(1, 2**23))

    async def connect(self) -> None:
        if self._sdk:
            return
        self._sdk = await asyncio.to_thread(load_sdk(), self._ip)
        try:
            _, labels = self._sdk.GetSDKVersion()
            controller = (await self._call(self._sdk.GetSoftwareVersion))[2]
            wanted = next((label[len("Robot:"):] for label in labels if label.startswith("Robot:")), None)
            if wanted is None or wanted.lower() != controller.lower():
                raise RuntimeError(f"el SDK es para el robot {wanted} y el controlador es {controller}")
        except Exception:
            await self.close()
            raise
        self._monitor = ConnectionMonitor(lambda: self._sdk.robot_state_pkg.frame_cnt, self._on_link_change)
        self._monitor_task = asyncio.create_task(self._monitor.run())

    async def close(self) -> None:
        if self._monitor_task:
            self._monitor_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._monitor_task
            self._monitor_task = self._monitor = None
        sdk, self._sdk = self._sdk, None
        if sdk:
            # CloseRPC falla con AttributeError al final y RPC.is_conect es de clase: reconectar en el mismo proceso da -4.
            with contextlib.suppress(AttributeError):
                await asyncio.to_thread(sdk.CloseRPC)

    @property
    def link(self) -> Link:
        return self._monitor.state if self._monitor else Link.DISCONNECTED

    def _locked(self, fn, args):
        with self._thread_lock:
            return fn(*args)

    @contextlib.asynccontextmanager
    async def _operation(self):
        if self._busy.locked():
            raise RunFailed(["hay otra operación en curso"], {})
        async with self._busy:
            yield

    async def _call(self, fn, *args, check: bool = True):
        result = await asyncio.to_thread(self._locked, fn, args)
        code = result[0] if isinstance(result, tuple) else result
        if check and code != 0:
            raise RuntimeError(f"{fn.__name__} falló con el código {code}")
        return result

    @staticmethod
    async def _try(coroutine, default):
        try:
            return await coroutine
        except Exception:
            return default

    async def _variable(self, number: int) -> float:
        return (await self._call(self._sdk.GetSysVarValue, number))[1]

    async def _stable(self, field: str) -> list[float]:
        """Mediana de tres tramas distintas: el SDK deja las tres primeras articulaciones en 0 si falla el checksum de una."""
        samples, last, deadline = [], None, time.monotonic() + 2.0
        while len(samples) < SAMPLES:
            if time.monotonic() > deadline:
                raise RuntimeError("el flujo de estado del robot no avanza")
            pkg = self._sdk.robot_state_pkg
            if pkg.frame_cnt != last:
                last = pkg.frame_cnt
                samples.append(list(getattr(pkg, field)))
            await asyncio.sleep(0.01)
        return [statistics.median(axis) for axis in zip(*samples)]

    async def set_mode(self, auto: bool) -> None:
        async with self._operation():
            await self._set_mode(auto)

    async def _set_mode(self, auto: bool) -> None:
        target = 0 if auto else 1
        await self._call(self._sdk.Mode, target)
        deadline = time.monotonic() + 3.0
        while self._sdk.robot_state_pkg.robot_mode != target:
            if time.monotonic() > deadline:
                raise RuntimeError("el controlador no confirmó el cambio de modo")
            await asyncio.sleep(0.05)

    async def run_primitive(self, session_id: str, primitive: str, params: dict) -> None:
        async with self._operation():
            await self._run(primitive, params)

    async def _run(self, primitive: str, params: dict) -> None:
        spec = self._primitives.get(primitive)
        if spec is None:
            raise InvalidParams(f"primitiva desconocida: {primitive}")
        check_params(spec, params)
        if self.link is not Link.CONNECTED:
            raise RunFailed([ALERT], {})
        if self._sdk.robot_state_pkg.robot_mode != 0:
            raise RunFailed(["el robot está en modo manual"], {})
        if self._sdk.robot_state_pkg.program_state != 1:
            raise RunFailed(["hay un programa en marcha en el controlador"], {})
        if spec.program not in await self.list_programs():
            raise RunFailed([f"el programa {spec.program} no está en el controlador"], {})
        joints = await self._stable("jt_cur_pos")
        for pose in spec.probes(params) if spec.probes else []:
            if not (await self._call(self._sdk.GetInverseKinHasSolution, 1, pose, joints))[1]:
                raise InvalidParams(f"el robot no alcanza el movimiento relativo {pose}")

        request_id = float(next(self._ids))
        start = await self._stable("flange_cur_pos")
        for number in (spec.status_variable, spec.echo_variable):
            await self._call(self._sdk.SetSysVarValue, number, 0)
        for name, value in params.items():
            await self._call(self._sdk.SetSysVarValue, spec.params[name].variable, value)
        await self._call(self._sdk.SetSysVarValue, spec.take_id_variable, request_id)
        for number, value in zip(spec.joints_variables, joints):
            await self._call(self._sdk.SetSysVarValue, number, value)
        await self._call(self._sdk.ProgramLoad, PROGRAM_DIR + spec.program)
        now = await self._stable("jt_cur_pos")
        if max(abs(a - b) for a, b in zip(joints, now)) > 0.05:
            raise RunFailed(["el brazo se movió desde que se leyó su posición"], {})
        await self._call(self._sdk.ProgramRun)

        seen_moving, stopped, alive = await self._watch(spec.max_seconds)
        # Tras un paro el controlador puede rechazar lecturas: el veredicto debe salir igual.
        end = await self._try(self._stable("flange_cur_pos"), None)
        pkg = self._sdk.robot_state_pkg
        offset = spec.end_offset(params) if spec.end_offset else None
        observation = Observation(
            status=await self._try(self._variable(spec.status_variable), math.nan), done_status=spec.done_status,
            echo=await self._try(self._variable(spec.echo_variable), math.nan), expected_id=request_id,
            seen_moving=seen_moving, stopped=stopped, error=(pkg.main_code, pkg.sub_code),
            emergency_stop=pkg.EmergencyStop, stream_alive=alive,
            pose_error_mm=(pose_error(start, end, offset) if end else math.nan) if offset else None)
        problems = failures(observation)
        if problems:
            raise RunFailed(problems, {"start": start, "end": end, "observation": observation})

    async def _watch(self, max_seconds: float) -> tuple[bool, bool, bool]:
        start = time.monotonic()
        seen_moving, started, idle_since, last_count, last_change = False, False, None, None, start
        while True:
            now = time.monotonic()
            pkg = self._sdk.robot_state_pkg
            if pkg.frame_cnt != last_count:
                last_count, last_change = pkg.frame_cnt, now
            if now - last_change > STALE_AFTER:
                return seen_moving, False, False
            moving = pkg.program_state != 1 or pkg.robot_state != 1
            seen_moving = seen_moving or pkg.robot_state == 2
            started = started or pkg.program_state == 2 or pkg.robot_state == 2
            idle_since = None if moving else (idle_since or now)
            if started and idle_since and now - idle_since >= self._settle and now - start >= MIN_RUN:
                return seen_moving, True, True
            if not started and now - start > START_TIMEOUT:
                await self._call(self._sdk.ProgramStop, check=False)
                return seen_moving, True, True
            if now - start > max_seconds:
                await self._call(self._sdk.ProgramStop, check=False)
                return seen_moving, False, True
            await asyncio.sleep(self._poll)

    async def list_programs(self) -> list[str]:
        return [n for n in (await self._call(self._sdk.GetLuaList))[2] if n]

    async def upload_program(self, name: str, lua_source: str) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / name
            path.write_text(lua_source)
            for _ in range(3):
                result = await self._call(self._sdk.LuaUpload, str(path), check=False)
                if result == 0:
                    break
                if isinstance(result, tuple):
                    await self._try(self._call(self._sdk.LuaDelete, name, check=False), None)
                    raise RuntimeError(f"el controlador rechazó {name}: {result[1]}")
                await asyncio.sleep(2)
            else:
                raise RuntimeError(f"la subida de {name} falló tres veces")
        if name not in await self.list_programs():
            raise RuntimeError(f"{name} no aparece en el controlador tras subirlo")

    async def play(self, name: str) -> None:
        async with self._operation():
            await self._call(self._sdk.ProgramLoad, PROGRAM_DIR + name)
            await self._call(self._sdk.ProgramRun)

    async def program_state(self) -> str:
        return STATE_NAMES.get(self._sdk.robot_state_pkg.program_state, "unknown")

    async def pause(self) -> None:
        await self._call(self._sdk.ProgramPause)

    async def resume(self) -> None:
        await self._call(self._sdk.ProgramResume)

    async def stop(self) -> None:
        await self._call(self._sdk.ProgramStop)

    async def jog(self, frame: str, axis: int, direction: int, max_distance: float, speed: float) -> None:
        check_jog(frame, axis, direction, max_distance, speed, self._jog_max_distance, self._jog_max_speed)
        if self.link is not Link.CONNECTED:
            raise RunFailed([ALERT], {})
        pkg = self._sdk.robot_state_pkg
        if pkg.robot_mode != 1:
            raise RunFailed(["el jog solo funciona en modo manual: pasa el robot a manual primero"], {})
        if pkg.program_state != 1:
            raise RunFailed(["hay un programa en marcha: no se puede mover con el jog"], {})
        await self._call(self._sdk.StartJOG, JOG_REFS[frame], axis, 1 if direction > 0 else 0,
                         max_distance, speed, JOG_ACCELERATION)

    async def jog_stop(self, frame: str) -> None:
        if frame not in JOG_REFS:
            raise InvalidParams(f"marco desconocido: {frame}")
        await self._call(self._sdk.StopJOG, JOG_REFS[frame] + 1)

    async def jog_halt(self) -> None:
        await self._call(self._sdk.ImmStopJOG)

    async def move_joint(self, joints: list[float], params) -> None:
        await self._move(params, self._sdk.MoveJ, joints, 0, 0, [0.0] * 6, params.velocity_pct, 0.0, 100.0,
                         [0.0] * 4, 0.0, 0, [0.0] * 6)

    async def move_linear(self, pose: list[float], params) -> None:
        await self._move(params, self._sdk.MoveL, pose, 0, 0, [0.0] * 6, params.velocity_pct, 0.0, 100.0, 0.0, 0,
                         [0.0] * 4, 0, 0, [0.0] * 6, -1, 0, 0, 10, reach=[pose])

    async def move_circular(self, via: list[float], target: list[float], params) -> None:
        await self._move(params, self._sdk.MoveC, via, 0, 0, target, 0, 0, [0.0] * 6, [0.0] * 6,
                         params.velocity_pct, 0.0, [0.0] * 4, 0, [0.0] * 6, params.velocity_pct, 0.0, [0.0] * 4, 0,
                         [0.0] * 6, 100.0, 0.0, reach=[via, target])

    async def _move(self, params, command, *args, reach=()) -> None:
        """Solo modo Studio (D38), con el operador presente. Sin bloqueo (blend 0): un movimiento bloqueante retendría el cerrojo y el paro no pasaría. Sin medir en el robot."""
        check_move_speed(params.velocity_pct, self._move_max_speed)
        if self.link is not Link.CONNECTED:
            raise RunFailed([ALERT], {})
        async with self._operation():
            pkg = self._sdk.robot_state_pkg
            if pkg.program_state != 1:
                raise RunFailed(["hay un programa en marcha en el controlador"], {})
            joints = await self._stable("jt_cur_pos")
            for pose in reach:
                if not (await self._call(self._sdk.GetInverseKinHasSolution, 0, pose, joints))[1]:
                    raise InvalidParams(f"el robot no alcanza la pose {pose}")
            await self._call(command, *args)
            seen_moving, stopped, alive = await self._watch(MOVE_MAX_SECONDS)
            pkg = self._sdk.robot_state_pkg
            problems = [text for bad, text in [
                (not alive, "se congeló el flujo de estado del robot"),
                (not stopped, "el robot no terminó en el tiempo previsto"),
                (not seen_moving, "el brazo nunca se movió"),
                (pkg.EmergencyStop, "paro de emergencia activo"),
                ((pkg.main_code, pkg.sub_code) != (0, 0), f"el controlador reporta el error {(pkg.main_code, pkg.sub_code)}"),
            ] if bad]
            if problems:
                raise RunFailed(problems, {})
