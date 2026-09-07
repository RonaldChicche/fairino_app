#!/usr/bin/env python3
"""Oscilacion relativa de RX, tres veces, conservando la posicion TCP."""

import msvcrt
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from fairino import Robot


ROBOT_IP = "192.168.58.2"
VELOCIDAD = 10.0
USER = 0
REPETICIONES = 3
GIRO_RX = 20.0

POSE_CENTRO = [-691.487, -315.930, 925.368, 98.863, 52.039, 10.556]
JUNTAS_CENTRO = [4.194, -88.866, 84.742, -92.636, -5.477, 44.417]


def pose_con_giro(delta_rx):
    pose = POSE_CENTRO.copy()
    pose[3] += delta_rx
    return pose


def muestras(desde, hasta, cantidad=20):
    return [desde + (hasta - desde) * paso / cantidad for paso in range(1, cantidad + 1)]


def validar(robot):
    referencia = JUNTAS_CENTRO
    for delta in muestras(0.0, -GIRO_RX) + muestras(-GIRO_RX, GIRO_RX) + muestras(GIRO_RX, 0.0):
        error, solucion = robot.GetInverseKinRef(0, pose_con_giro(delta), referencia)
        if error != 0 or solucion is None:
            print(f"RX relativo {delta:.1f} grados no es alcanzable: codigo {error}")
            return False
        if abs(solucion[4]) < 2.0:
            print(f"RX relativo {delta:.1f}: demasiado cerca de singularidad, J5={solucion[4]:.3f}")
            return False
        referencia = solucion
    return True


def mover(robot, tool, delta_rx):
    error = robot.MoveL(
        desc_pos=pose_con_giro(delta_rx),
        tool=tool,
        user=USER,
        vel=VELOCIDAD,
        blendR=-1.0,
    )
    if error != 0:
        raise RuntimeError(f"MoveL RX {delta_rx:+.1f} fallo con codigo {error}")


def esperar_espacio():
    print("Pulsa ESPACIO para comenzar 3 oscilaciones de RX.")
    while msvcrt.getwch() != " ":
        pass
    print()


def main():
    solo_validar = "--validar" in sys.argv[1:]
    if any(arg != "--validar" for arg in sys.argv[1:]):
        print("Uso: uv run --frozen demo_mov_04.py [--validar]")
        return 2

    robot = Robot.RPC(ROBOT_IP)
    try:
        error, tool = robot.GetActualTCPNum()
        if error != 0:
            raise RuntimeError(f"No se pudo leer TOOL: {error}")
        if not validar(robot):
            print("Validacion cancelada: no se envio ningun movimiento.")
            return 3
        if solo_validar:
            print("Rango RX validado. No se envio ningun movimiento.")
            return 0

        esperar_espacio()
        for _ in range(REPETICIONES):
            mover(robot, tool, -GIRO_RX)
            mover(robot, tool, GIRO_RX)
        mover(robot, tool, 0.0)
        return 0
    finally:
        robot.CloseRPC()


if __name__ == "__main__":
    sys.exit(main())
