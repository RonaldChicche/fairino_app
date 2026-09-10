#!/usr/bin/env python3
"""
Demo de conexion a una GoPro HERO10 por cable USB, con el SDK oficial Open GoPro.

    uv run gopro_demo.py --leer   -> conecta e informa, NO dispara
    uv run gopro_demo.py          -> conecta, toma una foto y la descarga

La camara debe estar encendida y con Conexion USB en "GoPro Connect".
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

CARPETA_CAPTURAS = Path(__file__).parent / "capturas"

# Con None el SDK descubre la camara por mDNS. Solo hace falta ponerlo si
# tienes varias GoPro enchufadas a la vez.
GOPRO_SERIAL = None


try:
    from open_gopro import WiredGoPro
    from open_gopro.models import constants, proto
except ImportError:
    print("ERROR: no se encontro el paquete 'open_gopro'.")
    print()
    print("Instala las dependencias del proyecto con:")
    print("    uv sync")
    sys.exit(1)


def _pistas_de_conexion():
    print()
    print("Cosas que revisar:")
    print("  - La camara esta ENCENDIDA (no basta con que este enchufada)")
    print("  - El cable USB-C transmite datos, no es solo de carga")
    print("  - La camara no esta en modo almacenamiento/MTP: en la GoPro,")
    print("    Preferencias > Conexiones > Conexion USB debe estar en 'GoPro Connect'")
    print("  - No hay otra app usando la camara (Quik, GoPro Webcam)")
    print("  - Prueba otro puerto USB o desconecta y vuelve a conectar")


async def mostrar_info(gopro):
    resp = await gopro.http_command.get_camera_info()
    if not resp.ok:
        print(f"ERROR: la camara no respondio a get_camera_info ({resp.status})")
        return False

    info = resp.data
    print(f"      Modelo:    {info.model_name}")
    print(f"      Firmware:  {info.firmware_version}")
    print(f"      Serial:    {info.serial_number}")

    # El estado es un dict plano indexado por StatusId, no un objeto con .status.
    estado = await gopro.http_command.get_camera_state()
    if estado.ok:
        bateria = estado.data.get(constants.StatusId.INTERNAL_BATTERY_PERCENTAGE)
        if bateria is not None:
            print(f"      Bateria:   {bateria}%")
    return True


async def tomar_foto(gopro):
    print("[3/5] Poniendo la camara en modo foto ...")
    resp = await gopro.http_command.load_preset_group(
        group=proto.EnumPresetGroup.PRESET_GROUP_ID_PHOTO
    )
    if not resp.ok:
        print(f"ERROR: no se pudo cambiar a modo foto ({resp.status})")
        return None

    # Diff de la lista de medios antes/despues, como el demo oficial del SDK:
    # mas fiable que get_last_captured_media, que devuelve algo viejo si el
    # disparo fallo.
    antes = set((await gopro.http_command.get_media_list()).data.files)

    print("[4/5] Disparando ...")
    resp = await gopro.http_command.set_shutter(shutter=constants.Toggle.ENABLE)
    if not resp.ok:
        print(f"ERROR: el disparo fallo ({resp.status})")
        return None

    despues = set((await gopro.http_command.get_media_list()).data.files)
    nuevas = despues - antes
    if not nuevas:
        print("ERROR: la camara no reporto ninguna foto nueva.")
        print("       Puede que la tarjeta SD este llena o no este insertada.")
        return None

    foto = nuevas.pop()
    CARPETA_CAPTURAS.mkdir(parents=True, exist_ok=True)
    marca = datetime.now().strftime("%Y%m%d-%H%M%S")
    destino = CARPETA_CAPTURAS / f"{marca}_{foto.filename}"

    print(f"[5/5] Descargando {foto.filename} ...")
    resp = await gopro.http_command.download_file(
        camera_file=foto.filename, local_file=destino
    )
    if not resp.ok or not destino.exists():
        print(f"ERROR: la descarga de {foto.filename} fallo ({resp.status})")
        print("       La foto si quedo grabada en la SD de la camara.")
        return None

    return destino


async def operar(gopro, solo_leer):
    print("[2/5] Leyendo informacion de la camara ...")
    if not await mostrar_info(gopro):
        return 1

    if solo_leer:
        print()
        print("Modo --leer: no se disparo ninguna foto.")
        return 0

    destino = await tomar_foto(gopro)
    if destino is None:
        return 1

    print()
    print(f"Terminado. Foto guardada en: {destino}  ({destino.stat().st_size / 1024:.0f} KB)")
    return 0


async def main():
    solo_leer = "--leer" in sys.argv

    print("[1/5] Buscando la GoPro por USB ...")
    gopro = WiredGoPro(GOPRO_SERIAL)
    try:
        await gopro.open()
    except Exception as e:
        print()
        print("ERROR: no se pudo conectar con la GoPro por USB.")
        print(f"       ({type(e).__name__}: {e})")
        _pistas_de_conexion()
        return 1

    print("      Conectada.")

    # A partir de aqui la camara ya respondio: los fallos son de operacion,
    # no de conexion, y no deben reportarse como si el cable estuviera mal.
    try:
        return await operar(gopro, solo_leer)
    except Exception as e:
        print()
        print("ERROR: la camara fallo durante la operacion.")
        print(f"       ({type(e).__name__}: {e})")
        return 1
    finally:
        await gopro.close()


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except KeyboardInterrupt:
        print("\nInterrumpido.")
        sys.exit(130)
