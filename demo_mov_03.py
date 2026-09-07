#!/usr/bin/env python3
"""Movimiento entre dos puntos enseñados."""

import sys
import msvcrt

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from fairino import Robot


ROBOT_IP = "192.168.58.2"
VELOCIDAD = 65.0
USER = 0

XYZ_INICIAL = [-824.962, -285.978, 97.599]
XYZ_FINAL = [-436.119, -288.929, 1040.394]
ORIENTACION_FIJA = [-79.196, 35.271, -177.991]

POSE_INICIAL = XYZ_INICIAL + ORIENTACION_FIJA
POSE_FINAL = XYZ_FINAL + ORIENTACION_FIJA


def resolver_rama(robot):
    error, juntas_actuales = robot.GetActualJointPosDegree()
    if error != 0:
        raise RuntimeError(f"No se pudieron leer las articulaciones: {error}")

    candidatas = []
    for config in range(8):
        error, juntas_inicio = robot.GetInverseKin(0, POSE_INICIAL, config)
        if error != 0 or juntas_inicio is None:
            continue

        referencia = juntas_inicio
        margen_j5 = abs(juntas_inicio[4])
        valida = True
        for paso in range(1, 25):
            t = paso / 24
            xyz = [
                XYZ_INICIAL[i] + t * (XYZ_FINAL[i] - XYZ_INICIAL[i])
                for i in range(3)
            ]
            error, solucion = robot.GetInverseKinRef(
                0, xyz + ORIENTACION_FIJA, referencia
            )
            if error != 0 or solucion is None:
                valida = False
                break
            margen_j5 = min(margen_j5, abs(solucion[4]))
            referencia = solucion

        if valida and margen_j5 >= 5.0:
            distancia = sum(
                abs((juntas_inicio[i] - juntas_actuales[i] + 180) % 360 - 180)
                for i in range(6)
            )
            candidatas.append((distancia, config, juntas_inicio, referencia, margen_j5))

    if not candidatas:
        return None
    return min(candidatas, key=lambda candidata: candidata[0])


def mover_inicio_j(robot, juntas, tool):
    error = robot.MoveJ(
        joint_pos=juntas,
        desc_pos=POSE_INICIAL,
        tool=tool,
        user=USER,
        vel=VELOCIDAD,
        blendT=-1.0,
    )
    if error != 0:
        raise RuntimeError(f"MoveJ a P1 fallo con codigo {error}")


def mover_p1_p2(robot, juntas_finales, tool):
    error = robot.MoveL(
        desc_pos=POSE_FINAL,
        joint_pos=juntas_finales,
        tool=tool,
        user=USER,
        vel=VELOCIDAD,
        blendR=-1.0,
    )
    if error != 0:
        raise RuntimeError(f"MoveL fallo con codigo {error}")


def main():
    solo_validar = "--validar" in sys.argv[1:]
    if any(arg != "--validar" for arg in sys.argv[1:]):
        print("Uso: uv run --frozen demo_mov_03.py [--validar]")
        return 2

    robot = Robot.RPC(ROBOT_IP)
    try:
        error, tool = robot.GetActualTCPNum()
        if error != 0:
            raise RuntimeError(f"No se pudo leer TOOL: {error}")

        print(f"P1: {POSE_INICIAL}")
        print(f"P2: {POSE_FINAL}")
        rama = resolver_rama(robot)
        if rama is None:
            print("Validacion cancelada: no se envio ningun movimiento.")
            return 3
        _, config, juntas_inicio, juntas_finales, margen_j5 = rama
        print(f"Configuracion: {config}; margen minimo J5: {margen_j5:.3f} grados")
        if solo_validar:
            print("Toda la linea tiene solucion. No se envio ningun movimiento.")
            return 0

        mover_inicio_j(robot, juntas_inicio, tool)
        print("P1 alcanzado. Pulsa ESPACIO para ejecutar P1 -> P2.")
        while msvcrt.getwch() != " ":
            pass
        print()
        mover_p1_p2(robot, juntas_finales, tool)
        return 0
    finally:
        robot.CloseRPC()


if __name__ == "__main__":
    sys.exit(main())
