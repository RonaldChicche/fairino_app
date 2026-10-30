import asyncio
from fractions import Fraction
from pathlib import Path

from .command import build_command
from .profile import RenderProfile


class RenderError(Exception):
    pass


class FfmpegRenderer:
    def __init__(self, data_dir: Path, profile: RenderProfile = RenderProfile(), timeout: float = 900.0,
                 ffmpeg: str = "ffmpeg", ffprobe: str = "ffprobe"):
        self._data_dir, self._profile, self._timeout = data_dir, profile, timeout
        self._ffmpeg, self._ffprobe = ffmpeg, ffprobe

    async def render(self, session_id: str) -> str:
        if Path(session_id).name != session_id or session_id in ("", ".", ".."):
            raise RenderError("ID de toma inválido")
        folder = self._data_dir / session_id
        source, final, partial = folder / "raw.mp4", folder / "final.mp4", folder / "final.part.mp4"
        if not source.exists():
            raise RenderError("no existe el crudo de la toma")
        fps = await self._source_fps(source)
        await self._run(build_command(self._profile, source, partial, fps, self._ffmpeg))
        partial.replace(final)
        return str(final)

    async def _source_fps(self, source: Path) -> float:
        out = await self._run([self._ffprobe, "-v", "error", "-select_streams", "v:0",
                               "-show_entries", "stream=avg_frame_rate", "-of", "csv=p=0", str(source)])
        # ffprobe repite la línea del flujo: se toma la primera.
        return float(Fraction(out.split()[0]))

    async def _run(self, command: list[str]) -> str:
        proc = await asyncio.create_subprocess_exec(
            *command, stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        try:
            out, err = await asyncio.wait_for(proc.communicate(), self._timeout)
        except BaseException:
            proc.kill()
            await proc.wait()
            raise
        if proc.returncode != 0:
            raise RenderError(f"{Path(command[0]).name} terminó con código {proc.returncode}: {err.decode(errors='replace')[-500:]}")
        return out.decode()
