"""Registra lo que responde el controlador del FR10 a consultas cinemáticas, para validar la réplica sin robot.

  cd edge && uv run python tools/kinematics-replica/record_oracle.py golden/fr10_v386.json

No mueve el robot: solo calcula. Abre una única conexión.
"""
import json
import math
import random
import sys
import time
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "vendor" / "fairino"))
import Robot

IP = "192.168.58.2"
SEED = 11
FK_SAMPLES, IK_SAMPLES, CONFIG_SAMPLES, RAYS = 300, 200, 60, 40


def value(result):
    return result[1] if isinstance(result, tuple) and result[0] == 0 else None


def main(out):
    random.seed(SEED)
    robot = Robot.RPC(IP)
    time.sleep(1)
    limits = value(robot.GetJointSoftLimitDeg(1))
    pairs = list(zip(limits[0::2], limits[1::2]))
    current = value(robot.GetActualJointPosDegree(1))
    current_pose = value(robot.GetActualToolFlangePose(1))
    meta = {"fecha": date.today().isoformat(), "sdk": robot.GetSDKVersion()[1], "controlador": robot.GetSoftwareVersion()[1:],
            "semilla": SEED, "articulaciones_actuales": current, "pose_actual": current_pose, "herramienta": 0, "pieza": 0}

    def random_joints():
        joints = [random.uniform(lo * 0.9, hi * 0.9) for lo, hi in pairs]
        joints[2] = max(min(joints[2], 150.0), -150.0)
        return joints

    fk = []
    for _ in range(FK_SAMPLES):
        joints = random_joints()
        pose = value(robot.GetForwardKin(joints))
        if pose:
            fk.append({"joints": joints, "pose": pose})

    ik, has_solution = [], []
    for sample in fk[:IK_SAMPLES]:
        pose, joints = sample["pose"], sample["joints"]
        ik.append({"type": 0, "pose": pose, "config": -1, "ref": current, "joints": value(robot.GetInverseKin(0, pose, -1))})
        for ref in (joints, [j + random.uniform(-5, 5) for j in joints], random_joints()):
            ik.append({"type": 0, "pose": pose, "config": -1, "ref": ref, "joints": value(robot.GetInverseKinRef(0, pose, ref)), "via": "ref"})
        has_solution.append({"type": 0, "pose": pose, "ref": joints, "result": value(robot.GetInverseKinHasSolution(0, pose, joints))})
        far = [pose[0] * 1.6, pose[1] * 1.6, pose[2] * 1.6, *pose[3:]]
        has_solution.append({"type": 0, "pose": far, "ref": joints, "result": value(robot.GetInverseKinHasSolution(0, far, joints))})
    for sample in fk[:CONFIG_SAMPLES]:
        for config in range(8):
            ik.append({"type": 0, "pose": sample["pose"], "config": config, "ref": None,
                       "joints": value(robot.GetInverseKin(0, sample["pose"], config))})

    for kind in (1, 2):
        for _ in range(100):
            rel = [random.uniform(-300, 300) for _ in range(3)] + [random.uniform(-20, 20) for _ in range(3)]
            has_solution.append({"type": kind, "pose": rel, "ref": current, "result": value(robot.GetInverseKinHasSolution(kind, rel, current))})

    reach = []
    for _ in range(RAYS):
        direction = [random.gauss(0, 1) for _ in range(3)]
        norm = math.sqrt(sum(c * c for c in direction))
        direction = [c / norm for c in direction]
        low, high = 0.0, 2500.0
        for _ in range(13):
            middle = (low + high) / 2
            rel = [c * middle for c in direction] + [0, 0, 0]
            if value(robot.GetInverseKinHasSolution(1, rel, current)):
                low = middle
            else:
                high = middle
        reach.append({"origin_joints": current, "direction": direction, "max_mm": round(low, 2)})

    data = {"meta": meta, "soft_limits": limits, "fk": fk, "ik": ik, "has_solution": has_solution, "reach": reach}
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(data))
    failed_ik = sum(1 for r in ik if r["joints"] is None)
    print(f"fk={len(fk)} ik={len(ik)} (sin solución: {failed_ik}) has_solution={len(has_solution)} reach={len(reach)} -> {out}")
    sys.stdout.flush()


if __name__ == "__main__":
    main(sys.argv[1])
