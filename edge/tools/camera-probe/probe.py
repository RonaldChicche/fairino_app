import argparse
import asyncio
import json
import socket
import statistics
import time
from datetime import datetime
from pathlib import Path

from open_gopro import WiredGoPro
from open_gopro.models import constants, proto
from open_gopro.models.constants import settings as S

SID = constants.SettingId
ST = constants.StatusId
TOGGLE = constants.Toggle
RESULTS = Path(__file__).parent / "resultados"
POLL_S = 0.025
HOLD_S = 3.0
PREVIEW_PORT = 8554

# Ajustes que fija D7 y que no se exploran: bitrate alto y HyperSmooth apagado.
FIXED = [
    ("video_bit_rate", S.VideoBitRate.HIGH, SID.VIDEO_BIT_RATE),
    ("hypersmooth", S.Hypersmooth.OFF, SID.HYPERSMOOTH),
]
TRACKED = [
    ("video_resolution", SID.VIDEO_RESOLUTION),
    ("frames_per_second", SID.FRAMES_PER_SECOND),
    ("video_lens", SID.VIDEO_LENS),
    ("hypersmooth", SID.HYPERSMOOTH),
    ("video_bit_rate", SID.VIDEO_BIT_RATE),
    ("anti_flicker", SID.ANTI_FLICKER),
    ("video_performance_mode", SID.VIDEO_PERFORMANCE_MODE),
]


async def state(gopro):
    return (await gopro.http_command.get_camera_state()).data


def raw(value):
    return getattr(value, "value", value)


async def snapshot(gopro):
    data = await state(gopro)
    return {name: raw(data.get(sid)) for name, sid in TRACKED}


async def apply(gopro, name, value):
    try:
        resp = await getattr(gopro.http_setting, name).set(value)
        return bool(resp.ok)
    except Exception:
        return False


async def wait_for(gopro, predicate, timeout=15.0):
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < timeout:
        data = await state(gopro)
        if predicate(data):
            return (time.perf_counter() - t0) * 1000
        await asyncio.sleep(POLL_S)
    return None


async def record_once(gopro, hold=HOLD_S, preview=False):
    row = {}
    t0 = time.perf_counter()
    resp = await gopro.http_command.set_shutter(shutter=TOGGLE.ENABLE)
    row["start_ack_ms"] = round((time.perf_counter() - t0) * 1000, 1)
    row["start_ok"] = bool(resp.ok)
    if not resp.ok:
        return row
    encoding = await wait_for(gopro, lambda d: bool(d.get(ST.ENCODING)))
    row["start_to_encoding_ms"] = None if encoding is None else round(row["start_ack_ms"] + encoding, 1)
    if preview:
        row["preview_while_recording"] = await preview_probe(gopro, seconds=2.0)
    await asyncio.sleep(hold)
    t1 = time.perf_counter()
    await gopro.http_command.set_shutter(shutter=TOGGLE.DISABLE)
    idle = await wait_for(gopro, lambda d: not d.get(ST.ENCODING) and not d.get(ST.BUSY))
    row["stop_to_idle_ms"] = None if idle is None else round((time.perf_counter() - t1) * 1000, 1)
    last = (await gopro.http_command.get_last_captured_media()).data
    path = f"{last.folder}/{last.file}"
    meta = (await gopro.http_command.get_media_metadata(path=path)).data
    row.update(
        file=path,
        width=meta.width,
        height=meta.height,
        duration_s=meta.duration,
        frame_rate=meta.frame_rate,
        size_mb=round(meta.file_size / 1e6, 1),
        mbps=round(meta.file_size * 8 / 1e6 / max(meta.duration, 0.1), 1),
    )
    return row


async def preview_probe(gopro, seconds=3.0):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", PREVIEW_PORT))
    sock.setblocking(False)
    loop = asyncio.get_running_loop()
    result = {"packets": 0, "bytes": 0, "first_packet_ms": None}
    try:
        t0 = time.perf_counter()
        resp = await gopro.http_command.set_preview_stream(mode=TOGGLE.ENABLE, port=PREVIEW_PORT)
        result["start_ok"] = bool(resp.ok)
        while time.perf_counter() - t0 < seconds:
            try:
                data = await asyncio.wait_for(loop.sock_recv(sock, 65535), timeout=0.2)
            except asyncio.TimeoutError:
                continue
            result["packets"] += 1
            result["bytes"] += len(data)
            if result["first_packet_ms"] is None:
                result["first_packet_ms"] = round((time.perf_counter() - t0) * 1000, 1)
    finally:
        await gopro.http_command.set_preview_stream(mode=TOGGLE.DISABLE)
        sock.close()
    return result


async def info(gopro):
    data = await state(gopro)
    out = {
        "battery_pct": data.get(ST.INTERNAL_BATTERY_PERCENTAGE),
        "sd_remaining_kb": data.get(ST.SD_CARD_REMAINING),
        "usb_controlled": data.get(ST.USB_CONTROLLED),
        "settings": await snapshot(gopro),
    }
    try:
        cam = (await gopro.http_command.get_camera_info()).data
        out["camera_info"] = json.loads(cam.model_dump_json()) if hasattr(cam, "model_dump_json") else str(cam)
    except Exception as exc:
        out["camera_info_error"] = repr(exc)
    return out


async def discover_modes(gopro, lens):
    await apply(gopro, "video_lens", lens)
    valid = []
    for res in S.VideoResolution:
        if not await apply(gopro, "video_resolution", res):
            continue
        for fps in S.FramesPerSecond:
            if not await apply(gopro, "frames_per_second", fps):
                continue
            data = await state(gopro)
            if raw(data.get(SID.VIDEO_RESOLUTION)) == res.value and raw(data.get(SID.FRAMES_PER_SECOND)) == fps.value:
                valid.append((res, fps))
    return valid


async def run(args):
    RESULTS.mkdir(exist_ok=True)
    report = {"started": datetime.now().isoformat(timespec="seconds"), "mode": args.mode}
    gopro = WiredGoPro()
    await gopro.open()
    original = None
    try:
        await gopro.http_command.load_preset_group(group=proto.EnumPresetGroup.PRESET_GROUP_ID_VIDEO)
        report["info"] = await info(gopro)
        original = report["info"]["settings"]
        print(json.dumps(report["info"], indent=2, default=str))
        if args.mode == "info":
            return report

        for name, value, _ in FIXED:
            await apply(gopro, name, value)

        if args.mode == "latency":
            await apply(gopro, "video_resolution", S.VideoResolution.NUM_4K)
            await apply(gopro, "frames_per_second", S.FramesPerSecond.NUM_120_0)
            await apply(gopro, "video_lens", S.VideoLens.WIDE)
            rows = []
            for i in range(args.repeat):
                row = await record_once(gopro, preview=(i == 0 and args.preview))
                rows.append(row)
                print(i + 1, row)
                await asyncio.sleep(2)
            vals = [r["start_to_encoding_ms"] for r in rows if r.get("start_to_encoding_ms")]
            if vals:
                report["latency_summary_ms"] = {
                    "min": min(vals),
                    "median": statistics.median(vals),
                    "max": max(vals),
                    "n": len(vals),
                }
            report["rows"] = rows

        if args.mode == "matrix":
            valid = await discover_modes(gopro, S.VideoLens.WIDE)
            report["valid_modes"] = [(r.name, f.name) for r, f in valid]
            print(f"{len(valid)} combinaciones válidas de resolución y fps")
            rows = []
            for res, fps in valid:
                await apply(gopro, "video_resolution", res)
                await apply(gopro, "frames_per_second", fps)
                row = {"resolution": res.name, "fps": fps.name, **await record_once(gopro)}
                rows.append(row)
                print(row)
                await asyncio.sleep(args.cooldown)
            report["rows"] = rows

        if args.mode == "lens":
            await apply(gopro, "video_resolution", S.VideoResolution.NUM_4K)
            await apply(gopro, "frames_per_second", S.FramesPerSecond.NUM_120_0)
            rows = []
            for lens in S.VideoLens:
                if not await apply(gopro, "video_lens", lens):
                    continue
                row = {"lens": lens.name, **await record_once(gopro)}
                rows.append(row)
                print(row)
                await asyncio.sleep(args.cooldown)
            report["rows"] = rows

        if args.mode == "preview":
            report["preview_idle"] = await preview_probe(gopro)
            print(report["preview_idle"])
    finally:
        try:
            await gopro.http_command.set_shutter(shutter=TOGGLE.DISABLE)
        except Exception:
            pass
        if original:
            for name, sid in TRACKED:
                value = original.get(name)
                enum = {
                    "video_resolution": S.VideoResolution,
                    "frames_per_second": S.FramesPerSecond,
                    "video_lens": S.VideoLens,
                    "hypersmooth": S.Hypersmooth,
                    "video_bit_rate": S.VideoBitRate,
                    "anti_flicker": S.Anti_Flicker,
                    "video_performance_mode": S.VideoPerformanceMode,
                }[name]
                if value is not None:
                    await apply(gopro, name, enum(value))
            report["restored"] = await snapshot(gopro)
        await gopro.close()
        out = RESULTS / f"{args.mode}_{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
        out.write_text(json.dumps(report, indent=2, default=str))
        print("Guardado en", out)


def main():
    parser = argparse.ArgumentParser(description="Mide la HERO10 por USB: info, latencia de arranque, modos, lentes y vista previa.")
    parser.add_argument("mode", choices=["info", "latency", "matrix", "lens", "preview"])
    parser.add_argument("--repeat", type=int, default=10)
    parser.add_argument("--cooldown", type=float, default=4.0)
    parser.add_argument("--preview", action="store_true", help="en latency, prueba la vista previa mientras graba")
    asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    main()
