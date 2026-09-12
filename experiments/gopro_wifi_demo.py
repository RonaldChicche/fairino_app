import asyncio
from datetime import datetime
from pathlib import Path

from open_gopro import WirelessGoPro
from open_gopro.network.wifi.adapters.wireless import NetshWireless


CAPTURAS = Path(__file__).parent / "capturas"


class WifiWindowsEspanol(NetshWireless):
    def __init__(self, interface=None, password=None):
        super().__init__(interface)


async def omitir_cohn():
    pass


async def main():
    gopro = WirelessGoPro(target="6058", wifi_adapter=WifiWindowsEspanol)
    gopro.cohn.wait_until_ready = omitir_cohn
    try:
        await gopro.open(timeout=30, retries=2)
        info = await gopro.ble_command.get_hardware_info()
        print(f"Camara: {info.data.model_name}")
        print(f"IP Wi-Fi: {gopro.ip_address}")

        medios = await gopro.http_command.get_media_list()
        foto = medios.data.files[-1]

        CAPTURAS.mkdir(exist_ok=True)
        marca = datetime.now().strftime("%Y%m%d-%H%M%S")
        destino = CAPTURAS / f"{marca}_{Path(foto.filename).name}"

        await gopro.http_command.download_file(
            camera_file=foto.filename,
            local_file=destino,
        )
        print(f"Foto descargada: {destino}")
    finally:
        await gopro.close()


if __name__ == "__main__":
    asyncio.run(main())
