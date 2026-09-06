#!/usr/bin/env python3
"""
Demo minima de conexion a una GoPro HERO10 Black por cable USB, usando el
SDK oficial Open GoPro.

Por defecto: conecta, identifica la camara, toma una foto y la descarga a
la carpeta ./capturas.

Uso:
    uv run gopro_demo.py --leer   -> solo conecta e informa, NO dispara
    uv run gopro_demo.py          -> conecta, toma una foto y la descarga

Requiere la camara conectada por USB y encendida.
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# CONFIGURACION
# ---------------------------------------------------------------------------

# Carpeta donde se guardan las fotos descargadas. Esta en .gitignore: son
# binarios que no tiene sentido versionar.
CARPETA_CAPTURAS = Path(__file__).parent / "capturas"

# Serial de la camara. Con None, el SDK la descubre sola por mDNS, que es lo
# normal con un solo equipo conectado. Solo hace falta ponerlo si tienes
# varias GoPro enchufadas a la vez.
GOPRO_SERIAL = None

# ---------------------------------------------------------------------------

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
    """Imprime modelo, firmware y estado basico de la camara."""
    resp = await gopro.http_command.get_camera_info()
    if not resp.ok:
        print(f"ERROR: la camara no respondio a get_camera_info ({resp.status})")
        return False

    info = resp.data
    print(f"      Modelo:    {info.model_name}")
    print(f"      Firmware:  {info.firmware_version}")
    print(f"      Serial:    {info.serial_number}")

    # El estado llega como un dict plano indexado por StatusId / SettingId
    # (no como un objeto con .status), y trae decenas de campos. Mostramos
    # solo la bateria, que es la unica cuya unidad esta documentada sin
    # ambiguedad; el resto no aporta a una demo de conexion.
    estado = await gopro.http_command.get_camera_state()
    if estado.ok:
        bateria = estado.data.get(constants.StatusId.INTERNAL_BATTERY_PERCENTAGE)
        if bateria is not None:
            print(f"      Bateria:   {bateria}%")
    return True


async def tomar_foto(gopro):
    """Pone la camara en modo foto, dispara y descarga el archivo resultante."""
    print("[3/5] Poniendo la camara en modo foto ...")
    resp = await gopro.http_command.load_preset_group(
        group=proto.EnumPresetGroup.PRESET_GROUP_ID_PHOTO
    )
    if not resp.ok:
        print(f"ERROR: no se pudo cambiar a modo foto ({resp.status})")
        return None

    # Comparamos la lista de medios antes y despues del disparo. Es como lo
    # hace el demo oficial del SDK: mas fiable que preguntar por la ultima
    # captura, que puede devolver algo viejo si el disparo fallo.
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
    await gopro.http_command.download_file(camera_file=foto.filename, local_file=destino)
    return destino


async def main():
    solo_leer = "--leer" in sys.argv

    print("[1/5] Buscando la GoPro por USB ...")
    try:
        async with WiredGoPro(GOPRO_SERIAL) as gopro:
            print("      Conectada.")

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

            tam_kb = destino.stat().st_size / 1024
            print()
            print(f"Terminado. Foto guardada en: {destino}  ({tam_kb:.0f} KB)")
            return 0

    except Exception as e:
        print()
        print("ERROR: no se pudo conectar con la GoPro por USB.")
        print(f"       ({type(e).__name__}: {e})")
        _pistas_de_conexion()
        return 1


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except KeyboardInterrupt:
        print("\nInterrumpido.")
        sys.exit(130)
