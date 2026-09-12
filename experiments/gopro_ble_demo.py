import asyncio

from open_gopro import WirelessGoPro
from open_gopro.models import constants, proto
from open_gopro.network.wifi.adapters.wireless import NetshWireless


class WifiWindowsEspanol(NetshWireless):
    def __init__(self, interface=None, password=None):
        super().__init__(interface)


async def omitir_cohn():
    pass


async def main():
    gopro = WirelessGoPro(
        target="6058",
        interfaces={WirelessGoPro.Interface.BLE},
        wifi_adapter=WifiWindowsEspanol,
    )
    gopro.cohn.wait_until_ready = omitir_cohn

    try:
        await gopro.open(timeout=15, retries=2)

        info = await gopro.ble_command.get_hardware_info()
        bateria = await gopro.ble_status.internal_battery_percentage.get_value()

        print(f"Camara: {info.data.model_name}")
        print(f"Bateria: {bateria}%")

        await gopro.ble_command.load_preset_group(
            group=proto.EnumPresetGroup.PRESET_GROUP_ID_PHOTO
        )
        respuesta = await gopro.ble_command.set_shutter(
            shutter=constants.Toggle.ENABLE
        )

        print(f"Foto tomada por BLE: {respuesta.ok}")
        print("La foto quedo en la tarjeta SD.")
    finally:
        await gopro.close()


if __name__ == "__main__":
    asyncio.run(main())
