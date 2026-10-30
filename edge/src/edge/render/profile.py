from dataclasses import dataclass


# Valores elegidos con las pruebas del 2026-10-27 sobre clips de 5.3K y 2.7K 4:3.
@dataclass(frozen=True)
class RenderProfile:
    output_width: int = 1080
    output_height: int = 1920
    output_fps: int = 30
    slow_factor: float = 4.0
    crop_position: float = 0.5
    denoise: tuple[float, float, float, float] | None = (2, 2, 6, 6)
    sharpen: float | None = 0.6
    brightness: float = 0.02
    contrast: float = 1.05
    saturation: float = 1.1
    gamma: float = 1.08
    crf: int = 18
    preset: str = "medium"
