import asyncio
import sys
from datetime import datetime
from pathlib import Path

from open_gopro import WiredGoPro
from open_gopro.models import constants, proto


CAPTURAS = Path(__file__).parent / "capturas"


async def main():
    gopro = WiredGoPro()
    await gopro.open()

    try:
        estado = await gopro.http_command.get_camera_state()
        bateria = estado.data.get(constants.StatusId.INTERNAL_BATTERY_PERCENTAGE)
        print(f"Bateria: {bateria}%")

        if "--leer" in sys.argv:
            return

        respuesta = await gopro.http_command.load_preset_group(
            group=proto.EnumPresetGroup.PRESET_GROUP_ID_PHOTO
        )
        if not respuesta.ok:
            raise RuntimeError("No se pudo seleccionar el modo foto")

        medios = await gopro.http_command.get_media_list()
        archivos_anteriores = {archivo.filename for archivo in medios.data.files}

        respuesta = await gopro.http_command.set_shutter(
            shutter=constants.Toggle.ENABLE
        )
        if not respuesta.ok:
            raise RuntimeError("No se pudo tomar la foto")

        medios = await gopro.http_command.get_media_list()
        foto = next(
            archivo
            for archivo in medios.data.files
            if archivo.filename not in archivos_anteriores
        )

        CAPTURAS.mkdir(exist_ok=True)
        nombre = Path(foto.filename).name
        marca = datetime.now().strftime("%Y%m%d-%H%M%S")
        destino = CAPTURAS / f"{marca}_{nombre}"

        respuesta = await gopro.http_command.download_file(
            camera_file=foto.filename,
            local_file=destino,
        )
        if not respuesta.ok:
            raise RuntimeError("No se pudo descargar la foto")

        print(f"Foto: {destino}")
    finally:
        await gopro.close()


if __name__ == "__main__":
    asyncio.run(main())
