__author__ = 'DAC_User'

pv_names = {'detector_position_x': '13IDD:m8',
            'detector_position_y': '13IDD:m84',
            'detector': '13MARCCD2:cam1',
            'sample_position_x': '13IDD:m81',
            'sample_position_y': '13IDD:m83',
            'sample_position_z': '13IDD:m82',
            'sample_position_omega': '13IDD:m96',
}

HOST = '164.54.160.34'
GROUP_NAME = 'G1'
POSITIONERS = "STX STZ STY OM"
DEFAULT_ACCEL = [2, 2, 2, 2]

GATHER_OUTPUTS = ('CurrentPosition', 'FollowingError',
                  'SetpointPosition', 'CurrentVelocity')

import numpy as np
import matplotlib.pyplot as plt
from measurement import perform_step_collection, move_to_omega_position
from xps_trajectory.xps_trajectory import XPSTrajectory

omega_step = 0.3
exposure_time = 1

stage_xps = XPSTrajectory(host=HOST, group=GROUP_NAME, positioners=POSITIONERS)
stage_xps.define_line_trajectories_general(stop_values=[[0, 0, 0, omega_step]], scan_time=exposure_time,
                                           pulse_time=0.001, accel_values=DEFAULT_ACCEL)
move_to_omega_position(-95, pv_names)
perform_step_collection(exposure_time, stage_xps, pv_names)
move_to_omega_position(-95, pv_names)

del stage_xps
data = np.loadtxt('Gather.dat')
plt.plot(data[:, -1])
plt.show()




