"""Graba clips cortos con combinaciones de ajustes y mide ruido, brillo, ISO y obturador de cada uno.

  uv run python tools/camera-probe/calidad.py capture --serial 058 --out data/pruebas-captura/x \\
      --modes 2_7K_4_3:120 5_3K:60 --sharpness Low --wb 5000K
  uv run --with numpy python tools/camera-probe/calidad.py measure data/pruebas-captura/x \\
      --roi 570,1360,200,140

La cámara y la escena tienen que estar quietas: el ruido se mide como variación entre fotogramas sobre una
zona estática (--roi x,y,w,h, en píxeles del video ya recortado a 1080x1920). Repite el recorte con
--roi-for nombre=x,y,w,h cuando el encuadre cambie entre modos (4:3 y 16:9 no ven lo mismo).
"""
import argparse
import asyncio
import json
import struct
import subprocess
import urllib.request
from pathlib import Path

import probe
from probe import S, WiredGoPro, proto

CATALOG = json.loads((probe.RESULTS / "catalogo_hero10.json").read_text())
# Ids de la HERO10 deducidos de las opciones del catálogo.
PROTUNE = {"color": 116, "ev": 118, "wb": 115, "sharpness": 117}


def option(setting, label):
    for value, text in CATALOG[str(setting)]["options"]:
        if text == label:
            return value
    raise SystemExit(f"{label!r} no es una opción del ajuste {setting}")


def camera_get(path):
    with urllib.request.urlopen(f"http://{probe.CAMERA_IP}:8080{path}", timeout=10) as r:
        return r.read()


def current(setting):
    return json.loads(camera_get("/gopro/camera/state"))["settings"][str(setting)]


async def put(setting, value):
    await asyncio.to_thread(camera_get, f"/gopro/camera/setting?setting={setting}&option={value}")
    return current(setting) == value


def download(path, dest):
    with urllib.request.urlopen(f"http://{probe.CAMERA_IP}:8080/videos/DCIM/{path}", timeout=60) as r, open(dest, "wb") as f:
        while chunk := r.read(1 << 20):
            f.write(chunk)


async def capture(args):
    probe.CAMERA_IP = f"172.2{args.serial[0]}.1{args.serial[1:]}.51"
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    gopro = WiredGoPro(serial=args.serial)
    await gopro.open()
    saved = {}
    original = {}
    try:
        await gopro.http_command.load_preset_group(group=proto.EnumPresetGroup.PRESET_GROUP_ID_VIDEO)
        saved = {name: current(setting) for name, setting in PROTUNE.items()}
        original = await probe.snapshot(gopro)
        for name, value, _ in probe.FIXED:
            await probe.apply(gopro, name, value)
        await probe.apply(gopro, "video_lens", S.VideoLens.WIDE)
        for name in PROTUNE:
            label = getattr(args, name)
            if label:
                print(name, label, await put(PROTUNE[name], option(PROTUNE[name], label)))
        for mode in args.modes:
            res, fps = mode.split(":")
            ok_res = await probe.apply(gopro, "video_resolution", S.VideoResolution[f"NUM_{res}"])
            ok_fps = await probe.apply(gopro, "frames_per_second", S.FramesPerSecond[f"NUM_{fps}_0"])
            if json.loads(camera_get("/gopro/camera/state"))["status"].get("6"):
                raise SystemExit("la cámara reporta sobrecalentamiento: se detiene la prueba")
            row = await asyncio.wait_for(probe.record_once(gopro, hold=args.hold), 40)
            name = f"{res}_{fps}fps" + (f"_{args.tag}" if args.tag else "")
            await asyncio.to_thread(download, row["file"], out / f"{name}.mp4")
            print(name, ok_res, ok_fps, row.get("width"), row.get("height"), row.get("frame_rate"), row.get("size_mb"), "MB", flush=True)
            await asyncio.sleep(args.cooldown)
    finally:
        try:
            await gopro.http_command.set_shutter(shutter=probe.TOGGLE.DISABLE)
        except Exception:
            pass
        for name, value in saved.items():
            await put(PROTUNE[name], value)
        for name, enum in {"video_resolution": S.VideoResolution, "frames_per_second": S.FramesPerSecond,
                           "video_lens": S.VideoLens, "hypersmooth": S.Hypersmooth}.items():
            if original.get(name) is not None:
                await probe.apply(gopro, name, enum(original[name]))
        await gopro.close()


def telemetry(path):
    """ISO, obturador y balance de blancos que la cámara guarda en cada clip (flujo GPMF)."""
    streams = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "d", "-show_entries", "stream=index,codec_tag_string",
                              "-of", "csv=p=0", str(path)], capture_output=True, text=True).stdout.split()
    index = next(line.split(",")[0] for line in streams if "gpmd" in line)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-map", f"0:{index}", "-c", "copy", "-f", "data", "-"],
                         capture_output=True).stdout
    found = {}

    def walk(data):
        i = 0
        while i + 8 <= len(data):
            key, kind, size = data[i:i + 4].decode("latin1"), data[i + 4], data[i + 5]
            count = struct.unpack(">H", data[i + 6:i + 8])[0]
            n = size * count
            body = data[i + 8:i + 8 + n]
            if kind == 0:
                walk(body)
            elif key in ("ISOE", "WBAL"):
                found.setdefault(key, []).extend(struct.unpack(f">{n // 2}H", body[:n // 2 * 2]))
            elif key == "SHUT":
                found.setdefault(key, []).extend(struct.unpack(f">{n // 4}f", body[:n // 4 * 4]))
            i += 8 + (n + 3) // 4 * 4

    walk(raw)
    return {"iso": sum(found["ISOE"]) / len(found["ISOE"]), "shutter": 1 / (sum(found["SHUT"]) / len(found["SHUT"])),
            "wb_kelvin": sum(found["WBAL"]) / len(found["WBAL"])}


def measure(args):
    import numpy as np

    default = tuple(int(v) for v in args.roi.split(","))
    special = {name: tuple(int(v) for v in roi.split(",")) for name, roi in (item.split("=") for item in args.roi_for)}
    print("%-34s %6s %8s %6s %8s %6s %9s" % ("clip", "brillo", "ruido", "SNR", "nitidez", "ISO", "obturador"))
    for path in sorted(Path(args.dir).glob("*.mp4")):
        x, y, w, h = special.get(path.stem, default)
        vf = f"crop=ih*9/16:ih,scale=1080:1920:flags=lanczos,crop={w}:{h}:{x}:{y},format=gray"
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-vf", vf, "-f", "rawvideo", "-"], capture_output=True).stdout
        frames = np.frombuffer(raw, np.uint8).reshape(-1, h, w).astype(np.float32)
        sigma = (frames[1:] - frames[:-1]).std(axis=0).mean() / np.sqrt(2)
        mean = frames.mean(axis=0)
        # La nitidez se calcula sobre la imagen promedio, sin ruido; solo compara clips con el mismo encuadre.
        sharp = np.abs(4 * mean[1:-1, 1:-1] - mean[:-2, 1:-1] - mean[2:, 1:-1] - mean[1:-1, :-2] - mean[1:-1, 2:]).mean()
        t = telemetry(path)
        print("%-34s %6.1f %8.2f %6.1f %8.2f %6.0f %9s" % (path.stem, mean.mean(), sigma, mean.mean() / sigma, sharp, t["iso"], f"1/{t['shutter']:.0f}"))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    cap = sub.add_parser("capture")
    cap.add_argument("--serial", required=True)
    cap.add_argument("--out", required=True)
    cap.add_argument("--modes", nargs="+", required=True, help="RESOLUCION:FPS, p. ej. 4K:120 2_7K_4_3:60 5_3K:60")
    cap.add_argument("--hold", type=float, default=4.0)
    cap.add_argument("--cooldown", type=float, default=10.0)
    cap.add_argument("--tag", default="")
    for name in PROTUNE:
        cap.add_argument(f"--{name}", default=None)
    mea = sub.add_parser("measure")
    mea.add_argument("dir")
    mea.add_argument("--roi", required=True)
    mea.add_argument("--roi-for", nargs="*", default=[])
    args = parser.parse_args()
    if args.command == "capture":
        asyncio.run(capture(args))
    else:
        measure(args)


if __name__ == "__main__":
    main()
