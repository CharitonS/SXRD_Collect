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

pilatus = '13PIL3'  # TODO Change here between Pilatus 1M (13PIL3) and Pilatus 300kw (13PIL300K)

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
    'pilatus': pilatus,
    'pilatus_proc': pilatus + ':Proc1',
    'pilatus_file': pilatus + ':TIFF1',
    'pilatus_control': pilatus + ':cam1',
    'pilatus_position_z': '13IDD:m5',
    'table_shutter': '13IDD:Unidig1Bi11.VAL',
    'status_message': pilatus + ':cam1:StatusMessage_RBV',
}

cycle_relative_path = '/2019/IDD_2019-1'
FILEPATH = 'T:/dac_user' + cycle_relative_path
PILATUS_FILE_PATH = '/cars5/Data/dac_user' + cycle_relative_path
