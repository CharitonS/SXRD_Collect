__author__ = 'Clemens Prescher'

xps_config = {
    'HOST': '164.54.160.34',
    'PORT': 5001,
    'TIMEOUT': 10,
    'GROUP NAME': 'G1',
    'POSITIONERS': "STX STZ STY OM",
    'USER': 'Administrator',
    'PASSWORD': 'Administrator',
    'TRAJ_FOLDER': 'Public/trajectories',
    'GATHER TITLES': "# XPS Gathering Data\n#--------------",
    'GATHER OUTPUTS': ('CurrentPosition', 'FollowingError',
                       'SetpointPosition', 'CurrentVelocity'),
    'DEFAULT ACCEL': [2, 2, 2, 2],
}

epics_config = {
    'detector_position_x': '13IDD:m8',
    'detector_position_z': '13IDD:m84',
    'marccd': '13MARCCD2',
    'detector_control': '13MARCCD2:cam1',
    'detector_file': '13MARCCD2:TIFF1',
    'sample_position_x': '13IDD:m81',
    'sample_position_y': '13IDD:m83',
    'sample_position_z': '13IDD:m82',
    'sample_position_omega': '13IDD:m96',
    'pilatus': '13PIL3',
    'pilatus_file': '13PIL3:TIFF1',
    'pilatus_control': '13PIL3:cam1',
    'pilatus_position_z': '13IDD:m5',
    'table_shutter': '13IDD:Unidig1Bi11.VAL',
    'status_message': '13PIL3:cam1:StatusMessage_RBV',
}

FILEPATH = 'T:/dac_user/2018/IDD_2019-1'