#!/usr/bin/env python3
"""Circulo completo de radio 10 cm desde la pose actual."""

import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from fairino import Robot


ROBOT_IP = "192.168.58.2"
RADIO = 100.0  # mm
VELOCIDAD = 40.0  # porcentaje


def main():
    robot = Robot.RPC(ROBOT_IP)

    try:
        error, inicio = robot.GetActualTCPPose()
        if error != 0:
            print(f"Error leyendo la pose: {error}")
            return 1

        _, tool = robot.GetActualTCPNum()
        _, user = robot.GetActualWObjNum()

        x, y, z, rx, ry, rz = inicio

        # Circulo de radio 100 mm en el plano XY.
        # La pose actual es el inicio; estos otros dos puntos definen el circulo.
        punto_p = [x + RADIO, y + RADIO, z, rx, ry, rz]
        punto_t = [x + 2 * RADIO, y, z, rx, ry, rz]

        print(f"Inicio:  {inicio}")
        print(f"Paso:    {punto_p}")
        print(f"Objetivo:{punto_t}")

        error = robot.Circle(
            desc_pos_p=punto_p,
            tool_p=tool,
            user_p=user,
            desc_pos_t=punto_t,
            tool_t=tool,
            user_t=user,
            vel_p=VELOCIDAD,
            vel_t=VELOCIDAD,
            blendR=-1.0,
        )

        print(f"Circle termino con codigo: {error}")
        return error
    finally:
        robot.CloseRPC()


if __name__ == "__main__":
    sys.exit(main())
