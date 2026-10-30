from pathlib import Path

from .profile import RenderProfile

# La cámara graba 119,88 fps y no 120: sin tolerancia se interpolaría un clip que ya sirve.
FPS_TOLERANCE = 0.02


def video_filters(profile: RenderProfile, source_fps: float) -> str:
    p = profile
    needed = p.slow_factor * p.output_fps
    filters = []
    if p.denoise:
        filters.append("hqdn3d=" + ":".join(f"{v:g}" for v in p.denoise))
    filters.append(f"crop=ih*{p.output_width}/{p.output_height}:ih:(iw-ow)*{p.crop_position:g}:0")
    filters.append(f"scale={p.output_width}:{p.output_height}:flags=lanczos:out_range=tv")
    if source_fps < needed * (1 - FPS_TOLERANCE):
        filters.append(f"minterpolate=fps={needed:g}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1")
    elif source_fps > needed * (1 + FPS_TOLERANCE):
        filters.append(f"fps={needed:g}")
    if p.sharpen:
        filters.append(f"unsharp=5:5:{p.sharpen:g}:5:5:0")
    filters.append(f"eq=brightness={p.brightness:g}:contrast={p.contrast:g}:saturation={p.saturation:g}:gamma={p.gamma:g}")
    filters.append(f"setpts={p.slow_factor:g}*PTS")
    filters.append(f"fps={p.output_fps}")
    filters.append("format=yuv420p")
    return ",".join(filters)


def build_command(profile: RenderProfile, source: Path, dest: Path, source_fps: float, ffmpeg: str = "ffmpeg") -> list[str]:
    return [
        ffmpeg, "-v", "error", "-y", "-i", str(source),
        "-vf", video_filters(profile, source_fps),
        "-an", "-c:v", "libx264", "-crf", str(profile.crf), "-preset", profile.preset,
        "-movflags", "+faststart", "-f", "mp4", str(dest),
    ]
