import math
from dataclasses import dataclass

POSE_TOLERANCE_MM = 2.0


@dataclass
class Observation:
    status: float
    done_status: float
    echo: float
    expected_id: float
    seen_moving: bool
    stopped: bool
    error: tuple[int, int]
    emergency_stop: int
    stream_alive: bool
    pose_error_mm: float | None


def pose_error(start: list[float], end: list[float], offset: list[float]) -> float:
    return math.dist([s + o for s, o in zip(start[:3], offset[:3])], end[:3])


def failures(o: Observation) -> list[str]:
    """Un error de Lua no deja código en el controlador: el éxito se confirma, no se supone."""
    found = []
    if not o.stream_alive:
        found.append("se congeló el flujo de estado del robot")
    if not o.stopped:
        found.append("el robot no terminó en el tiempo previsto")
    if o.echo != o.expected_id:
        found.append("el programa no leyó el ID de esta toma")
    if o.status != o.done_status:
        found.append(f"el programa no llegó a su final (estado {o.status:g}, esperado {o.done_status:g})")
    if not o.seen_moving:
        found.append("el brazo nunca se movió")
    if o.error != (0, 0):
        found.append(f"el controlador reporta el error {o.error}")
    if o.emergency_stop:
        found.append("paro de emergencia activo")
    if o.pose_error_mm is not None and not o.pose_error_mm <= POSE_TOLERANCE_MM:
        found.append(f"la pose final queda a {o.pose_error_mm:.1f} mm de la esperada")
    return found
