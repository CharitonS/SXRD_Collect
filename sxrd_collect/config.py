__author__ = 'Clemens Prescher'

# xps_config = {
#     'HOST': '164.54.160.34',
#     'PORT': 5001,
#     'TIMEOUT': 10,
#     'GROUP NAME': 'G1',
#     'POSITIONERS': "STX STZ STY OM",
#     'USER': 'Administrator',
#     'PASSWORD': 'Administrator',
#     'TRAJ_FOLDER': 'Public/trajectories',
#     'GATHER TITLES': "# XPS Gathering Data\n#--------------",
#     'GATHER OUTPUTS': ('CurrentPosition', 'FollowingError',
#                        'SetpointPosition', 'CurrentVelocity'),
#     'DEFAULT ACCEL': [2, 2, 2, 2],
# }

epics_config = {
    'detector_position_x': None,
    'sample_position_x': '13BMD:m89',
    'sample_position_y': '13BMD:m90',
    'sample_position_z': '13BMD:m91',
    'sample_position_omega': '13BMD:m38',
    'table_shutter': '13BMD:Unidig1Bi13.VAL',
    'status_message': '13PEL1:cam1:DetectorState_RBV',
    'perkin_elmer': '13PEL1',
    'perkin_elmer_file': '13PEL1:TIFF1',
    'perkin_elmer_control': '13PEL1:cam1',
    'perkin_elmer_position_z': '13BMD:m70',
    'perkin_elmer_offset_frames': '13PEL1:cam1:PENumOffsetFrames',
    'perkin_elmer_offset_constant': '13PEL1:cam1:PEOffsetConstant',
    'perkin_elmer_acquire_offset_correction': '13PEL1:cam1:PEAcquireOffset',
    'perkin_elmer_tiff_autosave': '13PEL1:TIFF1:AutoSave',
    'perkin_elmer_shutter_mode': '13PEL1:cam1:ShutterMode',
    'SIS': '13BMD:SIS1',
}

FILEPATH = 'T:/dac_user/2019/BMD_2019-1'
