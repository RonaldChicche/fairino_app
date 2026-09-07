#!/usr/bin/env python3
"""Conexion y lectura de estado de un robot FAIRINO por XML-RPC.

Este programa es deliberadamente de solo lectura. No contiene llamadas de
movimiento, cambio de modo ni habilitacion de servos.
"""

import sys

# El SDK oficial imprime mensajes en chino. La consola de Windows suele usar
# cp1252 y puede lanzar UnicodeEncodeError durante la propia conexion.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROBOT_IP = "192.168.58.2"

try:
    from fairino import Robot
except ImportError:
    print("ERROR: no se encontro el SDK 'fairino'.")
    print(r"Instalalo con: powershell -ExecutionPolicy Bypass -File .\scripts\get_sdk.ps1")
    sys.exit(1)


def pistas_de_red():
    print()
    print("Cosas que revisar:")
    print(f"  - El robot esta encendido y su IP es {ROBOT_IP}")
    print(f"  - Hay conectividad: ping {ROBOT_IP}")
    print("  - La PC esta en la subred 192.168.58.0/24")
    print("  - El firewall no bloquea los puertos 20003 / 20005")


def conectar():
    print(f"Conectando al robot en {ROBOT_IP} (solo lectura) ...")
    try:
        robot = Robot.RPC(ROBOT_IP)
    except Exception as exc:
        print(f"ERROR: no se pudo crear la conexion ({type(exc).__name__}: {exc})")
        pistas_de_red()
        return None

    if not robot.is_connect:
        print("ERROR: el controlador no respondio.")
        pistas_de_red()
        return None
    print("Conectado.")
    return robot


def mostrar_lectura(nombre, respuesta, formatear=str):
    try:
        error, valor = respuesta
    except (TypeError, ValueError):
        print(f"  {nombre}: respuesta inesperada: {respuesta!r}")
        return False
    if error != 0:
        print(f"  {nombre}: error del SDK {error}")
        return False
    print(f"  {nombre}: {formatear(valor)}")
    return True


def main():
    argumentos_desconocidos = [arg for arg in sys.argv[1:] if arg != "--leer"]
    if argumentos_desconocidos:
        print(f"ERROR: argumento no permitido: {argumentos_desconocidos[0]}")
        print("Este programa solo admite --leer y nunca ejecuta movimientos.")
        return 2

    robot = conectar()
    if robot is None:
        return 1

    print("Estado actual:")
    lecturas_ok = []
    try:
        lecturas_ok.append(
            mostrar_lectura(
                "Articulaciones (grados)",
                robot.GetActualJointPosDegree(),
                lambda valores: "[" + ", ".join(f"{v:.3f}" for v in valores) + "]",
            )
        )
        lecturas_ok.append(
            mostrar_lectura(
                "Pose TCP",
                robot.GetActualTCPPose(),
                lambda valores: "[" + ", ".join(f"{v:.3f}" for v in valores) + "]",
            )
        )
        lecturas_ok.append(mostrar_lectura("Errores [principal, secundario]", robot.GetRobotErrorCode()))
        lecturas_ok.append(mostrar_lectura("Paro de emergencia", robot.GetRobotEmergencyStopState()))
        lecturas_ok.append(mostrar_lectura("Paradas de seguridad [SI0, SI1]", robot.GetSafetyStopState()))
        lecturas_ok.append(mostrar_lectura("Comunicacion SDK", robot.GetSDKComState()))
    finally:
        robot.CloseRPC()
        print("Conexion cerrada. No se envio ningun comando de movimiento.")

    return 0 if all(lecturas_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
