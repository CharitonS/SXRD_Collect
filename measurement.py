__author__ = 'DAC_User'
from epics import caput, caget, PV
import time
import logging
import os

logging.basicConfig()
mylog = logging.getLogger()
mylog.setLevel(logging.DEBUG)


def collect_step_data(detector_position, omega_start, omega_end, omega_step, time, x, y, z, pv_names):
    # performs the actual step measurement
    print 'collecting step data'
    return


def collect_wide_data(detector_position, omega_start, omega_end, omega_step, time, x, y, z, pv_names):
    # performs the actual wide measurement
    print 'collecting wide data'
    return


def collect_single_data(filename, detector_position, exposure_time, x, y, z, omega, pv_names):
    # performs an actual single angle measurement:
    move_to_sample_pos(x, y, z, pv_names)
    move_to_sample_omega_position(omega, pv_names)
    move_to_detector_position(detector_position, pv_names)
    collect_data(filename, exposure_time, pv_names)
    return


def move_to_sample_pos(x, y, z, pv_names, wait=True, callbacks=[]):
    mylog.info('Moving Sample to x: {}, y: {}, z: {}'.format(x, y, z))
    motor_x = PV(pv_names['sample_position_x'])
    motor_y = PV(pv_names['sample_position_y'])
    motor_z = PV(pv_names['sample_position_z'])
    motor_x.put(x, use_complete=True)
    motor_y.put(y, use_complete=True)
    motor_z.put(z, use_complete=True)

    if wait:
        while not motor_x.put_complete and \
                not motor_y.put_complete and \
                not motor_z.put_complete:
            time.sleep(0.1)
        for callback in callbacks:
            callback()
    time.sleep(0.5)
    mylog.info('Moving Sample to x: {}, y: {}, z: {} finished.\n'.format(x, y, z))
    return


def move_to_sample_omega_position(omega, pv_names):
    mylog.info('Moving Sample Omega to {}'.format(omega))
    caput(pv_names['sample_position_omega'], omega, wait=True)
    mylog.info('Moving Sample Omega to {} finished.\n'.format(omega))


def move_to_detector_position(detector_position, pv_names):
    mylog.info('Moving Detector to {}'.format(detector_position))
    caput(pv_names['detector_position'], detector_position, wait=True)
    mylog.info('Moving Detector to {} finished.\n'.format(detector_position))


def collect_data(file_name, exposure_time, pv_names):
    path_name = os.path.dirname(file_name)
    base_name = os.path.basename(file_name)
    caput(pv_names['detector'] + ':AcquireTime', exposure_time)
    caput(pv_names['detector'] + ':FilePath', path_name)
    caput(pv_names['detector'] + ':FileName', base_name)

    mylog.info('Start data collection.')
    caput(pv_names['detector'] + ':Acquire', 1, wait=True)
    mylog.info('Finished data collection.\n')


if __name__ == '__main__':
    pv_names = {'detector_position': '13IDD:m8',
                'detector': '13MARCCD2:cam1',
                'sample_position_x': '13IDD:m81',
                'sample_position_y': '13IDD:m83',
                'sample_position_z': '13IDD:m82',
                'sample_position_omega': '13IDD:m96',
    }

    collect_single_data(filename='/dac/temp',
                        detector_position=-336,
                        exposure_time=2,
                        x=-1.5, y=-1.5, z=-1.5,
                        omega=-94,
                        pv_names=pv_names)

    collect_single_data(filename='/dac/temp2',
                        detector_position=-333,
                        exposure_time=2,
                        x=-3, y=1.5, z=-3,
                        omega=-90,
                        pv_names=pv_names)