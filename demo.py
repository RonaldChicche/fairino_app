#!/usr/bin/env python3
"""
Demo minima de control de un brazo robotico FAIRINO FR10 via el SDK oficial
(RPC sobre XML-RPC, puerto 20003 del controlador).

Uso:
    uv run demo.py --leer     -> solo se conecta e imprime la postura actual
    uv run demo.py            -> ejecuta el movimiento A -> B -> A

Requiere la carpeta "fairino" del SDK oficial al lado de este archivo.
"""

import sys
import time

# ---------------------------------------------------------------------------
# CONFIGURACION  <-- lo unico que normalmente necesitas tocar
# ---------------------------------------------------------------------------

# IP del controlador del robot. La de fabrica de FAIRINO es 192.168.58.2.
# Tu PC tiene que estar en la misma subred (ej. 192.168.58.100/24).
ROBOT_IP = "192.168.58.2"

# ---------------------------------------------------------------------------
# POSTURAS  <-- PLACEHOLDERS: TIENES QUE LLENARLOS TU
# ---------------------------------------------------------------------------
#
# Son posiciones en el ESPACIO DE ARTICULACIONES: 6 valores en GRADOS,
# en el orden [J1, J2, J3, J4, J5, J6].
#
# NO invento valores aqui a proposito: unos angulos inventados pueden mandar
# el brazo contra la mesa, contra si mismo o fuera de sus limites.
#
# Como conseguir los tuyos:
#   1. Mueve el robot a la postura que quieras con el pendant (modo manual/jog).
#   2. Lee los 6 angulos en la pantalla del pendant, O
#      corre:  uv run demo.py --leer
#      que imprime la postura actual lista para copiar y pegar aqui.
#   3. Repite para la segunda postura.
#
# Ejemplo de formato (NO son valores reales, no los uses):
#   POSTURA_A = [0.0, -30.0, 90.0, -60.0, 90.0, 0.0]

POSTURA_A = None  # <-- REEMPLAZAR con tus 6 angulos reales, ej. [j1, j2, j3, j4, j5, j6]
POSTURA_B = None  # <-- REEMPLAZAR con tus 6 angulos reales

# Parametros de movimiento.
TOOL = 0        # numero de herramienta; 0 = sin herramienta calibrada
USER = 0        # numero de sistema de coordenadas de pieza; 0 = base del robot
VELOCIDAD = 20  # porcentaje de velocidad [0-100]. Bajo a proposito para la demo.

# ---------------------------------------------------------------------------


try:
    from fairino import Robot
except ImportError:
    print("ERROR: no se encontro el paquete 'fairino'.")
    print()
    print("Este SDK no se instala con pip. Tiene que existir una carpeta")
    print("'fairino' (con Robot.py adentro) al lado de este demo.py.")
    print()
    print("Para descargarlo corre:  ./scripts/get_sdk.sh")
    sys.exit(1)


def validar_posturas():
    """Frena antes de conectar si las posturas siguen siendo placeholders."""
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
    """Abre la conexion RPC y verifica que de verdad quedo conectada.

    Ojo: RPC() NO lanza excepcion si el robot no responde; se traga el error
    y solo deja is_connect en False. Por eso hay que revisarlo a mano.
    """
    print(f"[1/4] Conectando al robot en {ROBOT_IP} ...")
    try:
        robot = Robot.RPC(ROBOT_IP)
    except Exception as e:
        print()
        print(f"ERROR: fallo al crear la conexion RPC con {ROBOT_IP}")
        print(f"       ({type(e).__name__}: {e})")
        _pistas_de_red()
        sys.exit(1)

    if not robot.is_connect:
        print()
        print(f"ERROR: no hay respuesta del controlador en {ROBOT_IP}")
        _pistas_de_red()
        sys.exit(1)

    print("      Conectado.")
    return robot


def _pistas_de_red():
    print()
    print("Cosas que revisar:")
    print(f"  - El robot esta encendido y su IP es realmente {ROBOT_IP}")
    print(f"  - Hay ping:  ping {ROBOT_IP}")
    print("  - Tu PC esta en la misma subred que el robot")
    print("  - El cable de red esta en el puerto correcto del controlador")
    print("  - Ningun firewall bloquea los puertos 20003 / 20005")


def leer_postura(robot):
    """Imprime la postura actual, lista para pegar en POSTURA_A / POSTURA_B."""
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
    error = robot.MoveJ(postura, TOOL, USER, vel=VELOCIDAD)
    if error != 0:
        print()
        print(f"ERROR: MoveJ a {nombre} fallo con codigo {error}")
        print("       Causas tipicas: robot sin habilitar, en modo manual,")
        print("       en paro de emergencia, o postura fuera de limites.")
        sys.exit(1)
    print(f"      Llego a {nombre}.")


def main():
    # Modo lectura: no mueve nada, solo reporta donde esta el robot.
    if "--leer" in sys.argv:
        robot = conectar()
        leer_postura(robot)
        robot.CloseRPC()
        return

    validar_posturas()
    robot = conectar()

    print("[2/4] Preparando robot (modo automatico + habilitar) ...")
    robot.Mode(0)          # 0 = modo automatico
    time.sleep(1)
    robot.RobotEnable(1)   # 1 = habilitar servos
    time.sleep(1)

    print("[3/4] Ejecutando movimientos ...")
    mover_a(robot, "POSTURA_A", POSTURA_A)
    mover_a(robot, "POSTURA_B", POSTURA_B)
    mover_a(robot, "POSTURA_A", POSTURA_A)

    print("[4/4] Cerrando conexion ...")
    robot.CloseRPC()
    print("Terminado.")


if __name__ == "__main__":
    main()
