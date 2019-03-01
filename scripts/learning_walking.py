#!/usr/bin/env python2

import numpy as np
import rospy

from robot_learning.ros_plant import ROSPlant
from robot_learning.srv import T2VInfo


def tripod_gait(state, cmd, dt, period=1.5, offset=0.785,
                sweep_angle=1.0, duty_factor=0.685, standing=False):
    leg_angles = cmd[:6]
    slow_legs = (np.abs(
                    (leg_angles - offset + np.pi) % (2*np.pi)
                    - np.pi) < sweep_angle/2.0)
    fast_legs = np.logical_not(slow_legs)
    slow_legs = np.where(slow_legs)[0]
    fast_legs = np.where(fast_legs)[0]

    slow_speed = -(2*np.pi)/(2*period*duty_factor)
    fast_speed = -(2*np.pi)/(2*period*(1.0-duty_factor))
    cmd[6+slow_legs] = slow_speed
    cmd[slow_legs] = (cmd[slow_legs] +
                      dt*slow_speed) % (2*np.pi)

    cmd[6+fast_legs] = fast_speed
    cmd[fast_legs] = (cmd[fast_legs] +
                      dt*fast_speed) % (2*np.pi)

    if standing:
        if 1 in fast_legs and (cmd[1] - offset) % (2*np.pi) < np.pi:
            standing = False
        else:
            cmd[:6:2] = offset
    return cmd, standing


def reward(states, actions):
    # TODO make this a reasonable reward
    return states.sum() + actions.sum()


if __name__ == '__main__':
    rospy.init_node('learning_to_walk')

    gazebo_synchronous = rospy.get_param('gazebo_syncrohonous', True)

    env = ROSPlant(
        dt=rospy.get_param('~dt', 0.05),
        reward_func=reward,
        gazebo_synchronous=gazebo_synchronous)
    state = env.reset()
    t = rospy.get_time()
    command_dims_service = rospy.ServiceProxy('/rl/command_dims', T2VInfo)
    command_dims = command_dims_service().value

    cmd = np.zeros(command_dims)
    offset = 0.985
    cmd[:6] = offset

    state, reward, info, done = env.step(cmd)

    standing = True

    if gazebo_synchronous:
        env.unpause()
    rospy.sleep(1.0)
    if gazebo_synchronous:
        env.pause()

    prev_t = rospy.get_time()
    while not rospy.is_shutdown():
        t = rospy.get_time()
        dt = (t - prev_t)
        prev_t = t

        cmd, standing = tripod_gait(
            state, cmd, dt, offset=offset, standing=standing)
        state, reward, info, done = env.step(cmd)
