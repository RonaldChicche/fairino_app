#!/usr/bin/env python3
"""Rutina glambot: arriba, media elipse descendente y regreso."""

import math
import msvcrt
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from fairino import Robot


ROBOT_IP = "192.168.58.2"
VELOCIDAD = 10.0
USER = 0

# Coordenadas del objetivo [x, y, z] en mm, respecto de la base (USER 0).
OBJETIVO_MM = [2000, 0, 500]

POSE_INICIAL_ENSENADA = [-327.580, 109.735, 1115.048, -95.906, 24.868, 99.901]
JUNTAS_INICIALES_ENSENADAS = [-68.121, -122.584, 96.677, -124.458, -10.882, -4.205]
POSE_MEDIA_ENSENADA = [-543.792, 536.978, 739.457, -91.782, -6.519, 98.509]
JUNTAS_MEDIAS_ENSENADAS = [-64.548, -78.518, 102.335, -197.830, -17.234, -12.242]
POSE_FINAL_ENSENADA = [-1121.276, -2.335, 364.204, -93.050, -11.420, 96.223]
JUNTAS_FINAL_ENSENADAS = [-9.457, -39.357, 78.259, -215.807, -74.945, -12.240]

PUNTOS_ELIPSE = 24

# 1: la camara mira por +Z del TCP; -1: mira por -Z.
EJE_OPTICO = 1.0
ROLL_CAMARA_GRADOS = 0.0
BLEND_MM = 20.0


def producto_cruz(a, b):
    return [
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    ]


def normalizar(v):
    modulo = math.sqrt(sum(n * n for n in v))
    if modulo == 0:
        raise ValueError("La posicion TCP no puede coincidir con el objetivo")
    return [n / modulo for n in v]


def orientacion_hacia(posicion, objetivo):
    z = normalizar([(objetivo[i] - posicion[i]) * EJE_OPTICO for i in range(3)])
    referencia = [0.0, 0.0, 1.0]
    if abs(sum(z[i] * referencia[i] for i in range(3))) > 0.98:
        referencia = [0.0, 1.0, 0.0]

    x = normalizar(producto_cruz(referencia, z))
    y = producto_cruz(z, x)

    roll = math.radians(ROLL_CAMARA_GRADOS)
    c, s = math.cos(roll), math.sin(roll)
    x, y = (
        [c * x[i] + s * y[i] for i in range(3)],
        [-s * x[i] + c * y[i] for i in range(3)],
    )

    matriz = [
        [x[0], y[0], z[0]],
        [x[1], y[1], z[1]],
        [x[2], y[2], z[2]],
    ]
    ry = math.asin(max(-1.0, min(1.0, -matriz[2][0])))
    rx = math.atan2(matriz[2][1], matriz[2][2])
    rz = math.atan2(matriz[1][0], matriz[0][0])
    return [math.degrees(rx), math.degrees(ry), math.degrees(rz)]


def pose(posicion, objetivo):
    return posicion + orientacion_hacia(posicion, objetivo)


def trayectoria_tres_puntos(inicio, medio, final):
    control = [2.0 * medio[i] - (inicio[i] + final[i]) / 2.0 for i in range(3)]
    trayectoria = []
    for paso in range(PUNTOS_ELIPSE + 1):
        t = paso / PUNTOS_ELIPSE
        u = 1.0 - t
        trayectoria.append([
            u * u * inicio[i] + 2.0 * u * t * control[i] + t * t * final[i]
            for i in range(3)
        ])
    return trayectoria


def esperar_espacio(texto):
    print(texto)
    while msvcrt.getwch() != " ":
        pass
    print()


def mover_trayectoria(robot, posiciones, objetivo, tool, user):
    for indice, posicion in enumerate(posiciones):
        ultimo = indice == len(posiciones) - 1
        error = robot.MoveL(
            desc_pos=pose(posicion, objetivo),
            tool=tool,
            user=user,
            vel=VELOCIDAD,
            blendR=-1.0 if ultimo else BLEND_MM,
        )
        if error != 0:
            raise RuntimeError(f"MoveL fallo con codigo {error}")


def validar_poses(robot, poses):
    error, referencia = robot.GetActualJointPosDegree()
    if error != 0:
        raise RuntimeError(f"No se pudieron leer las articulaciones: {error}")

    for nombre, destino in poses:
        error, solucion = robot.GetInverseKinRef(0, destino, referencia)
        if error != 0 or solucion is None:
            print(f"Pose no alcanzable ({nombre}): {destino}")
            print(f"Codigo de cinematica inversa: {error}")
            return False
        referencia = solucion
    return True


def main():
    solo_validar = "--validar" in sys.argv[1:]
    if any(arg != "--validar" for arg in sys.argv[1:]):
        print("Uso: uv run --frozen demo_mov_02.py [--validar]")
        return 2

    if OBJETIVO_MM is None:
        print("Define OBJETIVO_MM = [x, y, z] antes de ejecutar.")
        return 2

    robot = Robot.RPC(ROBOT_IP)

    try:
        inicio = POSE_INICIAL_ENSENADA[:3]
        medio = POSE_MEDIA_ENSENADA[:3]
        final = POSE_FINAL_ENSENADA[:3]
        bajada = trayectoria_tres_puntos(inicio, medio, final)

        error, tool = robot.GetActualTCPNum()
        if error != 0:
            raise RuntimeError(f"No se pudo leer TOOL: {error}")

        poses_bajada = [pose(posicion, OBJETIVO_MM) for posicion in bajada]
        poses_regreso = list(reversed(poses_bajada[:-1]))
        poses_a_validar = [("arriba", poses_bajada[0])]
        poses_a_validar += [(f"bajada {i}", p) for i, p in enumerate(poses_bajada[1:], 1)]
        poses_a_validar += [(f"regreso {i}", p) for i, p in enumerate(poses_regreso, 1)]

        print(f"Inicio [mm, grados]: {poses_bajada[0]}")
        print(f"Medio  [mm]: {medio}")
        print(f"Final  [mm, grados]: {poses_bajada[-1]}")
        if not validar_poses(robot, poses_a_validar):
            print("Validacion cancelada: no se envio ningun movimiento.")
            return 3
        if solo_validar:
            print("Todas las poses tienen solucion. No se envio ningun movimiento.")
            return 0

        error = robot.MoveL(
            desc_pos=poses_bajada[0],
            tool=tool,
            user=USER,
            vel=VELOCIDAD,
            blendR=-1.0,
        )
        if error != 0:
            raise RuntimeError(f"Movimiento arriba fallo con codigo {error}")

        esperar_espacio("STOP 1: pulsa ESPACIO para ir por el punto medio hasta el final.")
        mover_trayectoria(robot, bajada[1:], OBJETIVO_MM, tool, USER)

        esperar_espacio("STOP 2: pulsa ESPACIO para regresar por el punto medio al inicio.")
        mover_trayectoria(robot, list(reversed(bajada[:-1])), OBJETIVO_MM, tool, USER)
        return 0
    finally:
        robot.CloseRPC()


if __name__ == "__main__":
    sys.exit(main())
