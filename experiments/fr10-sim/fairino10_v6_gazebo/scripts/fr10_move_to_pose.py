#!/usr/bin/env python3
"""Mueve el FR10 a una pose objetivo del efector (wrist3_link) usando MoveIt2.

Usa la acción /move_action (moveit_msgs/MoveGroup) con restricciones de posición y
orientación, es decir, un objetivo cartesiano (no articular).

Si no se pasa --xyz/--rpy, la pose objetivo se obtiene con /compute_fk a partir de la
postura 'pos2' definida por FAIRINO en el SRDF, lo que garantiza que es alcanzable.

  ros2 run fairino10_v6_gazebo fr10_move_to_pose.py
  ros2 run fairino10_v6_gazebo fr10_move_to_pose.py --xyz 0.5 0.3 0.6 --rpy 3.14159 0 0
"""
import argparse
import math
import sys

import rclpy
from geometry_msgs.msg import Pose, Quaternion
from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import (BoundingVolume, Constraints, MoveItErrorCodes,
                             OrientationConstraint, PositionConstraint)
from moveit_msgs.srv import GetPositionFK
from rclpy.action import ActionClient
from rclpy.node import Node
from sensor_msgs.msg import JointState
from shape_msgs.msg import SolidPrimitive

GROUP = "fairino10_v6_group"
EE_LINK = "wrist3_link"
FRAME = "base_link"
JOINTS = ["j1", "j2", "j3", "j4", "j5", "j6"]
POS2 = [0.9281, -1.9512, 1.9526, -1.6002, -1.2993, 0.0]  # group_state 'pos2' del SRDF
POSITION_TOLERANCE_M = 0.01


def quaternion_from_rpy(roll, pitch, yaw):
    cr, sr = math.cos(roll / 2), math.sin(roll / 2)
    cp, sp = math.cos(pitch / 2), math.sin(pitch / 2)
    cy, sy = math.cos(yaw / 2), math.sin(yaw / 2)
    return Quaternion(
        x=sr * cp * cy - cr * sp * sy,
        y=cr * sp * cy + sr * cp * sy,
        z=cr * cp * sy - sr * sp * cy,
        w=cr * cp * cy + sr * sp * sy,
    )


class Fr10MoveToPose(Node):
    def __init__(self):
        super().__init__("fr10_move_to_pose")
        self.joint_state = None
        self.create_subscription(JointState, "/joint_states", self._on_joint_state, 10)
        self.fk_client = self.create_client(GetPositionFK, "/compute_fk")
        self.move_client = ActionClient(self, MoveGroup, "/move_action")

    def _on_joint_state(self, msg):
        self.joint_state = msg

    def wait_for(self, predicate, timeout_s, what):
        end = self.get_clock().now().nanoseconds + int(timeout_s * 1e9)
        while not predicate():
            if self.get_clock().now().nanoseconds > end:
                raise RuntimeError(f"timeout esperando {what}")
            rclpy.spin_once(self, timeout_sec=0.1)

    def fresh_joint_state(self, timeout_s=10.0):
        self.joint_state = None
        self.wait_for(lambda: self.joint_state is not None, timeout_s, "/joint_states")
        return self.joint_state

    def current_positions(self):
        js = self.fresh_joint_state()
        by_name = dict(zip(js.name, js.position))
        return [by_name[j] for j in JOINTS]

    def fk(self, positions):
        req = GetPositionFK.Request()
        req.header.frame_id = FRAME
        req.fk_link_names = [EE_LINK]
        req.robot_state.joint_state.name = JOINTS
        req.robot_state.joint_state.position = list(positions)
        future = self.fk_client.call_async(req)
        rclpy.spin_until_future_complete(self, future, timeout_sec=10.0)
        res = future.result()
        if res is None or res.error_code.val != MoveItErrorCodes.SUCCESS or not res.pose_stamped:
            raise RuntimeError(f"/compute_fk falló: {None if res is None else res.error_code.val}")
        return res.pose_stamped[0].pose

    def build_goal(self, target: Pose):
        goal = MoveGroup.Goal()
        req = goal.request
        req.group_name = GROUP
        req.num_planning_attempts = 10
        req.allowed_planning_time = 10.0
        req.max_velocity_scaling_factor = 0.3
        req.max_acceleration_scaling_factor = 0.3

        region = SolidPrimitive(type=SolidPrimitive.SPHERE, dimensions=[0.002])
        pc = PositionConstraint()
        pc.header.frame_id = FRAME
        pc.link_name = EE_LINK
        pc.constraint_region = BoundingVolume(primitives=[region], primitive_poses=[Pose(position=target.position)])
        pc.weight = 1.0

        oc = OrientationConstraint()
        oc.header.frame_id = FRAME
        oc.link_name = EE_LINK
        oc.orientation = target.orientation
        oc.absolute_x_axis_tolerance = 0.01
        oc.absolute_y_axis_tolerance = 0.01
        oc.absolute_z_axis_tolerance = 0.01
        oc.weight = 1.0

        req.goal_constraints = [Constraints(position_constraints=[pc], orientation_constraints=[oc])]
        goal.planning_options.plan_only = False
        goal.planning_options.replan = True
        goal.planning_options.replan_attempts = 3
        return goal

    def move(self, target: Pose):
        if not self.move_client.wait_for_server(timeout_sec=30.0):
            raise RuntimeError("la acción /move_action no está disponible (¿move_group corriendo?)")
        send = self.move_client.send_goal_async(self.build_goal(target))
        rclpy.spin_until_future_complete(self, send, timeout_sec=30.0)
        handle = send.result()
        if handle is None or not handle.accepted:
            raise RuntimeError("move_group rechazó el objetivo")
        result_future = handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future, timeout_sec=120.0)
        if result_future.result() is None:
            raise RuntimeError("timeout esperando el resultado de /move_action")
        return result_future.result().result.error_code.val


def fmt_pose(p: Pose):
    return (f"xyz=({p.position.x:.4f}, {p.position.y:.4f}, {p.position.z:.4f}) "
            f"quat=({p.orientation.x:.4f}, {p.orientation.y:.4f}, {p.orientation.z:.4f}, {p.orientation.w:.4f})")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--xyz", type=float, nargs=3, metavar=("X", "Y", "Z"))
    parser.add_argument("--rpy", type=float, nargs=3, metavar=("R", "P", "Y"), default=[math.pi, 0.0, 0.0])
    args = parser.parse_args(rclpy.utilities.remove_ros_args(sys.argv)[1:])

    rclpy.init()
    node = Fr10MoveToPose()
    try:
        node.wait_for(lambda: node.fk_client.service_is_ready(), 30.0, "/compute_fk")
        start = node.current_positions()
        print("Articulaciones iniciales [rad]:", [round(v, 4) for v in start])
        print("Pose inicial wrist3_link:", fmt_pose(node.fk(start)))

        if args.xyz:
            target = Pose()
            target.position.x, target.position.y, target.position.z = args.xyz
            target.orientation = quaternion_from_rpy(*args.rpy)
        else:
            target = node.fk(POS2)
        print(f"Pose OBJETIVO en {FRAME}:", fmt_pose(target))

        code = node.move(target)
        print("MoveIt error_code:", code, "(1 = SUCCESS)")
        if code != MoveItErrorCodes.SUCCESS:
            raise RuntimeError(f"MoveIt no pudo planificar/ejecutar (error_code={code})")

        final = node.current_positions()
        reached = node.fk(final)
        err = math.dist((reached.position.x, reached.position.y, reached.position.z),
                        (target.position.x, target.position.y, target.position.z))
        print("Articulaciones finales [rad]:", [round(v, 4) for v in final])
        print("Pose alcanzada wrist3_link:", fmt_pose(reached))
        print(f"Error de posición: {err * 1000:.2f} mm (tolerancia {POSITION_TOLERANCE_M * 1000:.0f} mm)")
        if err > POSITION_TOLERANCE_M:
            raise RuntimeError("el brazo no llegó a la pose objetivo dentro de la tolerancia")
        print("OK: el FR10 alcanzó la pose objetivo")
        return 0
    except RuntimeError as exc:
        print("ERROR:", exc, file=sys.stderr)
        return 1
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    sys.exit(main())
