import math
from dataclasses import dataclass
from typing import Callable

Pose = list[float]


class InvalidParams(ValueError):
    pass


class RunFailed(RuntimeError):
    def __init__(self, reasons: list[str], report: dict):
        super().__init__("; ".join(reasons))
        self.reasons, self.report = reasons, report


@dataclass(frozen=True)
class Param:
    variable: int
    low: float
    high: float


@dataclass(frozen=True)
class Primitive:
    """Una primitiva Lua ya cargada en el controlador y las variables de sistema que usa."""
    program: str
    params: dict[str, Param]
    take_id_variable: int
    status_variable: int
    echo_variable: int
    done_status: float
    max_seconds: float = 60.0
    joints_variables: tuple[int, ...] = ()
    probes: Callable[[dict], list[Pose]] | None = None
    end_offset: Callable[[dict], Pose] | None = None


def check_params(spec: Primitive, params: dict) -> None:
    unknown, missing = set(params) - set(spec.params), set(spec.params) - set(params)
    if unknown or missing:
        raise InvalidParams(f"parámetros inválidos: sobran {sorted(unknown)}, faltan {sorted(missing)}")
    for name, value in params.items():
        param = spec.params[name]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or (isinstance(value, float) and not math.isfinite(value)):
            raise InvalidParams(f"{name} no es un número")
        if not param.low <= value <= param.high:
            raise InvalidParams(f"{name} = {value}, el rango es de {param.low} a {param.high}")


JOG_REFS = {"joint": 0, "base": 2, "tool": 4, "workpiece": 8}


def check_move_speed(speed: float, limit_speed: float) -> None:
    if not 0 < speed <= limit_speed:
        raise InvalidParams(f"velocidad {speed} %, el máximo es {limit_speed} %")


def check_jog(frame: str, axis: int, direction: int, max_distance: float, speed: float,
              limit_distance: float, limit_speed: float) -> None:
    if frame not in JOG_REFS:
        raise InvalidParams(f"marco desconocido: {frame}")
    if axis not in range(1, 7) or direction not in (-1, 1):
        raise InvalidParams(f"eje {axis} y sentido {direction}: el eje va de 1 a 6 y el sentido es -1 o 1")
    if not 0 < max_distance <= limit_distance:
        raise InvalidParams(f"recorrido {max_distance}, el máximo por pulsación es {limit_distance}")
    if not 0 < speed <= limit_speed:
        raise InvalidParams(f"velocidad {speed} %, el máximo es {limit_speed} %")
