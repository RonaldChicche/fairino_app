#!/usr/bin/env python3
"""
Demo de control de un brazo FAIRINO FR10 via el SDK oficial (XML-RPC, puerto 20003).

    uv run demo.py --leer   -> imprime la postura actual, no mueve nada
    uv run demo.py          -> mueve A -> B -> A

Requiere la carpeta "fairino" del SDK al lado de este archivo (./scripts/get_sdk.sh).
"""

import sys
import time

# IP del controlador. La de fabrica es 192.168.58.2; tu PC debe estar en su subred.
ROBOT_IP = "192.168.58.2"

# Posturas en grados [J1..J6]. Sacalas del pendant o con `uv run demo.py --leer`.
# Van en None a proposito: unos angulos inventados estrellan el brazo.
POSTURA_A = None  # <-- PONER LOS TUYOS, ej. [0.0, -30.0, 90.0, -60.0, 90.0, 0.0]
POSTURA_B = None  # <-- PONER LOS TUYOS

TOOL = 0        # herramienta; 0 = sin calibrar
USER = 0        # sistema de pieza; 0 = base del robot
VELOCIDAD = 20  # % de velocidad [0-100]

ESPERA_PREPARACION = 1  # s tras cambiar de modo / habilitar


try:
    from fairino import Robot
except ImportError:
    print("ERROR: no se encontro el paquete 'fairino'.")
    print()
    print("Este SDK no se instala con pip. Descargalo con:")
    print("    ./scripts/get_sdk.sh      (macOS / Linux)")
    print("    .\\scripts\\get_sdk.ps1    (Windows / PowerShell)")
    sys.exit(1)


def _pistas_de_red():
    print()
    print("Cosas que revisar:")
    print(f"  - El robot esta encendido y su IP es realmente {ROBOT_IP}")
    print(f"  - Hay ping:  ping {ROBOT_IP}")
    print("  - Tu PC esta en la misma subred que el robot")
    print("  - El cable de red esta en el puerto correcto del controlador")
    print("  - Ningun firewall bloquea los puertos 20003 / 20005")


def _exigir(error, que):
    """Aborta si el SDK devolvio un codigo de error."""
    if error != 0:
        print()
        print(f"ERROR: {que} fallo con codigo {error}")
        print("       Causas tipicas: robot sin habilitar, en modo manual,")
        print("       en paro de emergencia, o postura fuera de limites.")
        sys.exit(1)


def validar_posturas():
    for nombre, postura in (("POSTURA_A", POSTURA_A), ("POSTURA_B", POSTURA_B)):
        if postura is None:
            print(f"ERROR: {nombre} sigue siendo None (es un placeholder).")
            print()
            print("Abre demo.py y pon tus 6 angulos reales en grados.")
            print("Para leer la postura actual del robot, corre:")
            print("    uv run demo.py --leer")
            sys.exit(1)
        if len(postura) != 6:
            print(f"ERROR: {nombre} tiene {len(postura)} valores, se esperan 6.")
            sys.exit(1)


def conectar():
    print(f"[1/4] Conectando al robot en {ROBOT_IP} ...")
    try:
        robot = Robot.RPC(ROBOT_IP)
    except Exception as e:
        print()
        print(f"ERROR: fallo al crear la conexion RPC con {ROBOT_IP}")
        print(f"       ({type(e).__name__}: {e})")
        _pistas_de_red()
        sys.exit(1)

    # RPC() no lanza excepcion si el robot no responde: se traga el error y
    # solo deja is_connect en False. Hay que revisarlo a mano.
    if not robot.is_connect:
        print()
        print(f"ERROR: no hay respuesta del controlador en {ROBOT_IP}")
        _pistas_de_red()
        sys.exit(1)

    print("      Conectado.")
    return robot


def leer_postura(robot):
    error, joint_pos = robot.GetActualJointPosDegree()
    if error != 0 or joint_pos is None:
        print(f"ERROR: no se pudo leer la postura (codigo {error})")
        return None
    valores = ", ".join(f"{v:.3f}" for v in joint_pos)
    print()
    print("Postura actual (grados), copiala a demo.py:")
    print(f"    [{valores}]")
    print()
    return joint_pos


def mover_a(robot, nombre, postura):
    print(f"      Moviendo a {nombre}: {postura}")
    _exigir(robot.MoveJ(postura, TOOL, USER, vel=VELOCIDAD), f"MoveJ a {nombre}")
    print(f"      Llego a {nombre}.")


def main():
    if "--leer" in sys.argv:
        robot = conectar()
        postura = leer_postura(robot)
        robot.CloseRPC()
        return 0 if postura is not None else 1

    validar_posturas()
    robot = conectar()

    print("[2/4] Preparando robot (modo automatico + habilitar) ...")
    _exigir(robot.Mode(0), "cambiar a modo automatico")
    time.sleep(ESPERA_PREPARACION)
    _exigir(robot.RobotEnable(1), "habilitar los servos")
    time.sleep(ESPERA_PREPARACION)

    print("[3/4] Ejecutando movimientos ...")
    mover_a(robot, "POSTURA_A", POSTURA_A)
    mover_a(robot, "POSTURA_B", POSTURA_B)
    mover_a(robot, "POSTURA_A", POSTURA_A)

    print("[4/4] Cerrando conexion ...")
    robot.CloseRPC()
    print("Terminado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
