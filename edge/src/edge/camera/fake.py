class FakeCamera:
    def __init__(self, confirms: bool = True):
        self.confirms, self.recording, self.calls = confirms, False, []

    async def start_recording(self) -> None:
        self.calls.append("start")
        self.recording = self.confirms

    async def is_recording(self) -> bool:
        return self.recording

    async def stop_recording(self) -> None:
        self.calls.append("stop")
        self.recording = False
