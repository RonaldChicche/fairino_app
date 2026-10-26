import asyncio


class FakeRobot:
    def __init__(self, fails: bool = False, gate: asyncio.Event | None = None):
        self.fails, self.gate, self.calls = fails, gate, []

    async def run_primitive(self, session_id: str, primitive: str, params: dict) -> None:
        self.calls.append(session_id)
        if self.gate:
            await self.gate.wait()
        if self.fails:
            raise RuntimeError("el controlador reportó un error")

    async def upload_program(self, name: str, lua_source: str) -> None:
        self.calls.append(f"upload:{name}")

    async def play(self, name: str) -> None:
        self.calls.append(f"play:{name}")

    async def program_state(self) -> str:
        return "idle"

    async def move_joint(self, joints, params) -> None:
        self.calls.append("move_joint")

    async def move_linear(self, pose, params) -> None:
        self.calls.append("move_linear")

    async def move_circular(self, via, target, params) -> None:
        self.calls.append("move_circular")

    async def pause(self) -> None:
        self.calls.append("pause")

    async def resume(self) -> None:
        self.calls.append("resume")

    async def stop(self) -> None:
        self.calls.append("stop")
