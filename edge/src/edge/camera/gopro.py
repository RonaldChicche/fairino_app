import asyncio
import json
import time
import urllib.request
from pathlib import Path

from open_gopro import WiredGoPro
from open_gopro.models import constants

ENCODING = constants.StatusId.ENCODING
BUSY = constants.StatusId.BUSY
TOGGLE = constants.Toggle


class CameraError(Exception):
    pass


class GoProCamera:
    def __init__(self, serial: str, stop_timeout: float = 5.0):
        # La IP por USB sale de los 3 últimos dígitos del serial. El mDNS del SDK no
        # encuentra la cámara en macOS, y la HERO10 no soporta camera_info ni last_captured.
        self._serial, self._stop_timeout = serial, stop_timeout
        self._ip = f"172.2{serial[0]}.1{serial[1:]}.51"
        self._gopro = WiredGoPro(serial=serial)

    async def open(self) -> None:
        await self._gopro.open()

    async def close(self) -> None:
        await self._gopro.close()

    async def start_recording(self) -> None:
        resp = await self._gopro.http_command.set_shutter(shutter=TOGGLE.ENABLE)
        if not resp.ok:
            raise CameraError("la cámara rechazó iniciar la grabación")

    async def is_recording(self) -> bool:
        state = (await self._gopro.http_command.get_camera_state()).data
        return bool(state.get(ENCODING))

    async def stop_recording(self) -> None:
        resp = await self._gopro.http_command.set_shutter(shutter=TOGGLE.DISABLE)
        if not resp.ok:
            raise CameraError("la cámara rechazó detener la grabación")
        # Tras parar, la cámara sigue ocupada unos 500 ms cerrando el archivo.
        deadline = time.monotonic() + self._stop_timeout
        while time.monotonic() < deadline:
            state = (await self._gopro.http_command.get_camera_state()).data
            if not state.get(ENCODING) and not state.get(BUSY):
                return
            await asyncio.sleep(0.05)
        raise CameraError("la cámara no quedó libre tras detener la grabación")

    async def last_clip(self) -> str:
        listing = await asyncio.to_thread(self._get_json, "/gopro/media/list")
        folder = listing["media"][-1]
        return f"{folder['d']}/{folder['fs'][-1]['n']}"

    async def download(self, clip: str, dest: Path) -> None:
        await asyncio.to_thread(self._download, clip, dest)

    def _get_json(self, path: str) -> dict:
        with urllib.request.urlopen(f"http://{self._ip}:8080{path}", timeout=10) as r:
            return json.load(r)

    def _download(self, clip: str, dest: Path) -> None:
        with urllib.request.urlopen(f"http://{self._ip}:8080/videos/DCIM/{clip}", timeout=30) as r:
            with open(dest, "wb") as f:
                while chunk := r.read(1 << 20):
                    f.write(chunk)
