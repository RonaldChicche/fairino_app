"""FR10 en Gazebo Sim (Fortress) + gz_ros2_control + MoveIt2.

Reemplaza la simulación de Gazebo Classic (gazebo_ros / gazebo_ros_control).

  ros2 launch fairino10_v6_gazebo fr10_gz_moveit.launch.py            # headless (solo servidor)
  DISPLAY=:1 ros2 launch fairino10_v6_gazebo fr10_gz_moveit.launch.py \
      gz_args:="-r -v 3 --render-engine ogre2 empty.sdf" rviz:=true   # con GUI en el escritorio noVNC
"""
import os

import xacro
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (DeclareLaunchArgument, IncludeLaunchDescription,
                            RegisterEventHandler, SetEnvironmentVariable)
from launch.conditions import IfCondition
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from moveit_configs_utils import MoveItConfigsBuilder


def generate_launch_description():
    gz_share = get_package_share_directory("fairino10_v6_gazebo")
    desc_share = get_package_share_directory("fairino_description")
    moveit_share = get_package_share_directory("fairino10_v6_moveit2_config")
    xacro_file = os.path.join(gz_share, "urdf", "fairino10_v6_gz.urdf.xacro")

    # Rutas absolutas para las mallas: Gazebo Sim, RViz y MoveIt las resuelven igual
    robot_description_xml = xacro.process_file(xacro_file).toxml().replace(
        "package://fairino_description/", "file://" + desc_share + "/")
    robot_description = {"robot_description": robot_description_xml}

    moveit_config = (
        MoveItConfigsBuilder("fairino10_v6_robot", package_name="fairino10_v6_moveit2_config")
        .robot_description(file_path=xacro_file)
        .trajectory_execution(file_path="config/moveit_controllers.yaml")
        .planning_pipelines(pipelines=["ompl"])
        .to_moveit_configs()
    )
    moveit_config.robot_description = robot_description

    declare_gz_args = DeclareLaunchArgument(
        "gz_args", default_value="-r -s -v 3 empty.sdf",
        description="Argumentos para 'ign gazebo' (por defecto: servidor headless)")
    declare_rviz = DeclareLaunchArgument("rviz", default_value="false")

    share_root = os.path.dirname(desc_share)
    resource_env = [
        SetEnvironmentVariable("IGN_GAZEBO_RESOURCE_PATH", share_root),
        SetEnvironmentVariable("GZ_SIM_RESOURCE_PATH", share_root),
    ]

    gz_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory("ros_gz_sim"), "launch", "gz_sim.launch.py")),
        launch_arguments={"gz_args": LaunchConfiguration("gz_args")}.items(),
    )

    robot_state_publisher = Node(
        package="robot_state_publisher", executable="robot_state_publisher", output="screen",
        parameters=[robot_description, {"use_sim_time": True}],
    )

    spawn_robot = Node(
        package="ros_gz_sim", executable="create", output="screen",
        arguments=["-topic", "robot_description", "-name", "fairino10_v6"],
    )

    clock_bridge = Node(
        package="ros_gz_bridge", executable="parameter_bridge", output="screen",
        arguments=["/clock@rosgraph_msgs/msg/Clock[ignition.msgs.Clock"],
    )

    def spawner(name):
        return Node(
            package="controller_manager", executable="spawner", output="screen",
            arguments=[name, "--controller-manager", "/controller_manager",
                       "--controller-manager-timeout", "120"],
        )

    joint_state_broadcaster = spawner("joint_state_broadcaster")
    arm_controller = spawner("fairino10_controller")

    move_group = Node(
        package="moveit_ros_move_group", executable="move_group", output="screen",
        parameters=[
            moveit_config.to_dict(),
            {
                "use_sim_time": True,
                "publish_robot_description_semantic": True,
                "trajectory_execution.allowed_start_tolerance": 0.05,
                "trajectory_execution.execution_duration_monitoring": False,
            },
        ],
    )

    rviz = Node(
        package="rviz2", executable="rviz2", output="log",
        condition=IfCondition(LaunchConfiguration("rviz")),
        arguments=["-d", os.path.join(moveit_share, "config", "moveit.rviz")],
        parameters=[
            moveit_config.robot_description,
            moveit_config.robot_description_semantic,
            moveit_config.robot_description_kinematics,
            moveit_config.planning_pipelines,
            moveit_config.joint_limits,
            {"use_sim_time": True},
        ],
    )

    return LaunchDescription([
        declare_gz_args,
        declare_rviz,
        *resource_env,
        gz_sim,
        robot_state_publisher,
        clock_bridge,
        spawn_robot,
        # Orden: robot en Gazebo -> joint_state_broadcaster -> controlador -> move_group
        RegisterEventHandler(OnProcessExit(target_action=spawn_robot,
                                           on_exit=[joint_state_broadcaster])),
        RegisterEventHandler(OnProcessExit(target_action=joint_state_broadcaster,
                                           on_exit=[arm_controller])),
        RegisterEventHandler(OnProcessExit(target_action=arm_controller,
                                           on_exit=[move_group, rviz])),
    ])
