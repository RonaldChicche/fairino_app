class FakeRenderer:
    async def render(self, session_id: str) -> str:
        return f"{session_id}.mp4"
