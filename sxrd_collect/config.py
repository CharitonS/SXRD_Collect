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
    'pilatus_info_wavelength': pilatus + ':cam1:Wavelength',
    'pilatus_info_detector_distance': pilatus + ':cam1:DetDist',
    'pilatus_info_beam_x': pilatus + ':cam1:BeamX',
    'pilatus_info_beam_y': pilatus + ':cam1:BeamY',
    'pilatus_info_omega': pilatus + ':cam1:Omega',
    'pilatus_info_omega_increment': pilatus + ':cam1:OmegaIncr',
    '13IDA_wavelength': '13IDA:mono_pid1_incalc.N',
}

crysalis_config = {
        'set_file': 'P:\\dac_user\\beamline\\crysalis_1m\\pilatus_1m.set',
        'ccd_file': 'P:\\dac_user\\beamline\\crysalis_1m\\pilatus_1m.ccd',
        'par_file': 'P:\\dac_user\\beamline\\crysalis_1m\\pilatus_1m.par'
}

cycle_relative_path = '/2019/IDD_2019-2'
FILEPATH = 'T:/dac_user' + cycle_relative_path
# for pilatus 300kW there is no ramdisk so it writes directly to cars:
if pilatus == '13PIL3':
    PILATUS_FILE_PATH = '/ramdisk/dac_user' + cycle_relative_path
elif pilatus == '13PIL300K':
    PILATUS_FILE_PATH = '/cars5/Data/dac_user' + cycle_relative_path
