# -*- coding: utf8 -*-
# SXRD_Collect - GUI program for collection single crystal X-ray diffraction data
# Copyright (C) 2015  Clemens Prescher (clemens.prescher@gmail.com)
# GSECARS, University of Chicago
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
#     (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program.  If not, see <http://www.gnu.org/licenses/>.

import time
import logging
from functools import partial
import thread
from epics import caput, caget, PV, camonitor, camonitor_clear
from threading import Thread
from xps_trajectory.XPS_C8_drivers import XPS

__author__ = 'Clemens Prescher'


logging.basicConfig()
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

from xps_trajectory.xps_trajectory import XPSTrajectory

from config import xps_config, epics_config

HOST = xps_config['HOST']
GROUP_NAME = xps_config['GROUP NAME']
POSITIONERS = xps_config['POSITIONERS']
DEFAULT_ACCEL = xps_config['DEFAULT ACCEL']

GATHER_OUTPUTS = xps_config['GATHER OUTPUTS']


def get_sample_position():
    x_pos = caget(epics_config['sample_position_x'])
    y_pos = caget(epics_config['sample_position_y'])
    z_pos = caget(epics_config['sample_position_z'])
    return x_pos, y_pos, z_pos


def collect_step_data(detector_choice, detector_position_x, detector_position_z, omega_start, omega_end, omega_step,
                      exposure_time, x, y, z, callback_fcn=None, collect_bkg_flag=False):
    """
    Performs a single crystal step collection at the sample position x,y,z using the trajectory scan of the
    XPS motor controller. This
    :param detector_choice:
        Which detector to use (pilatus or marccd).
    :param detector_position_x:
        Detector x position. Whereby the X motor PV is defined in epics_config as "detector_position_x".
    :param detector_position_z:
        Detector z position. Whereby the Z motor PV is defined in epics_config as "detector_position_z".
    :param omega_start:
        Starting omega angle for the step scans. Whereby the omega motor PV  is defined in epics_config as
        "sample_position_omega".
    :param omega_end:
        End omega angle for the step scans. Whereby the omega motor PV  is defined in epics_config as
        "sample_position_omega".
    :param omega_step:
        Omega step for each single frame/ Whereby the omega motor PV  is defined in epics_config as
        "sample_position_omega".
    :param exposure_time:
        Exposure time per frame in seconds.
    :param x:
        Sample position x. PV is defined in epics_config as "sample_position_x".
    :param y:
        Sample position y. PV is defined in epics_config as "sample_position_y".
    :param z:
        Sample position z. PV is defined in epics_config as "sample_position_z".
    :param callback_fcn:
        A user-defined function which will be called after each collection step is performed.
        If the function returns False the step collection will be aborted. Otherwise the data collection will proceed
        until the omega_end.
    :param collect_bkg_flag:
        boolean flag which determines if a background collection should be done prior to the step collection
    """
    # performs the actual step measurement
    # prepare the stage:
    prepare_stage(detector_choice, detector_position_x, detector_position_z, omega_start, x, y, z)
    # prepare the detector
    # previous_shutter_mode = prepare_detector(detector_choice)
    previous_detector_settings = prepare_detector_settings(detector_choice)

    # perform measurements:
    num_steps = (omega_end - omega_start) / omega_step

    stage_xps = XPSTrajectory(host=HOST, group=GROUP_NAME, positioners=POSITIONERS)
    if detector_choice == 'marccd':
        stage_xps.define_line_trajectories_general(stop_values=[[0, 0, 0, omega_step]], scan_time=exposure_time,
                                                   pulse_time=0.1, accel_values=DEFAULT_ACCEL)
    elif detector_choice == 'pilatus':
        omega_range = omega_end - omega_start
        print(omega_range)
        stage_xps.define_line_trajectories_general(stop_values=[[0, 0, 0, omega_range]],
                                                   scan_time=exposure_time*num_steps,
                                                   pulse_time=exposure_time, accel_values=DEFAULT_ACCEL)

    if collect_bkg_flag:
        if callback_fcn is None or (callback_fcn is not None and callback_fcn()):
            collect_background(detector_choice)
        else:
            logger.info('Data collection was aborted!')

    if callback_fcn is None or (callback_fcn is not None and callback_fcn()):
        if detector_choice == 'pilatus':
            caput(epics_config[detector_choice] + ':cam1:AcquireTime', exposure_time-0.001, wait=True)
            caput(epics_config[detector_choice] + ':cam1:AcquirePeriod', exposure_time, wait=True)
            caput(epics_config['pilatus'] + ':cam1:NumImages', num_steps, wait=True)
            caput(epics_config['pilatus'] + ':cam1:TriggerMode', 3, wait=True)  # 3 is Multi-Trigger, 2 is External

            pilatus_trajectory_thread = Thread(target=stage_xps.run_line_trajectory_general)
            t1 = time.time()
            caput(epics_config['pilatus'] + ':cam1:Acquire', 1)
            pilatus_trajectory_thread.start()
            while caget(epics_config['pilatus'] + ':cam1:Acquire'):
                continue

            """
            # This is for running with internal trigger
            while caget(epics_config['table_shutter']):
                continue
            t2 = time.time()
            caput(epics_config['pilatus'] + ':cam1:Acquire', 1, wait=True)
            t3 = time.time()
            print("Opened table shutter after " + str(t2-t1))
            print("collected data within " + str(t3-t2))
            """
            pilatus_trajectory_thread.join()

        elif detector_choice == 'marccd':
            for step in range(int(num_steps)):
                t1 = time.time()
                longstring = 'Running Omega-Trajectory from {} deg by {} deg {} s: frame {} of {}'
                longstring = longstring.format(omega_start + step * omega_step, omega_step, exposure_time, step+1,
                                               int(num_steps))
                shortstring = 'start {} step {} time {} s'.format(omega_start + step * omega_step,
                                                     omega_step,          exposure_time)

                caput(epics_config['marccd'] + ':AcquireSequence.STRA', shortstring, wait=True)
                logging.info(longstring)

                collect_step(exposure_time, stage_xps, detector_choice)

                logger.info('Time needed for one single step collection {}.\n'.format(time.time() - t1))

                if callback_fcn is not None:
                    if callback_fcn() is False:
                        logger.info('Data collection was aborted!')
                        break
    else:
        logger.info('Data collection was aborted!')

    reset_detector_settings(previous_detector_settings)
    # caput(epics_config[detector_choice] + ':cam1:ShutterMode', previous_shutter_mode, wait=True)
    logger.info('Data collection finished.\n')
    caput(epics_config[detector_choice] + ':AcquireSequence.STRA', 'Step scan finished', wait=True)
    del stage_xps


def collect_step(exposure_time, stage_xps, detector_choice):
    detector_checker = DetectorChecker(detector_choice)

    # start data collection
    collect_data(exposure_time + 50, detector_choice)
    time.sleep(0.25)
    stage_xps.run_line_trajectory_general()
    # stop detector
    caput(epics_config[detector_choice] + ':cam1:Acquire', 0, wait=True)
    # wait for readout
    while not detector_checker.is_finished():
        time.sleep(0.01)
    del detector_checker
    logger.info("Data collection finished.")
    time.sleep(0.25)


def collect_background(detector_choice):
    if detector_choice == 'marccd':
        logger.info("Acquiring Detector Background.")
        caput(epics_config['marccd'] + ':AcquireSequence.STRA', 'Acquiring Detector Background', wait=True)
        caput(epics_config[detector_choice] + ':cam1:FrameType', 1, wait=True)
        logger.info("Changed Frame type to Background.")
        caput(epics_config[detector_choice] + ':cam1:Acquire', 1, wait=True)
        logger.info("Finished Acquiring.")
        caput(epics_config[detector_choice] + ':cam1:FrameType', 0, wait=True)
        logger.info("Acquiring Detector Background finished.\n")


def prepare_stage(detector_choice, detector_position_x, detector_pos_z, omega_start, x, y, z):
    move_to_sample_pos(x, y, z)
    move_to_omega_position(omega_start)
    move_to_detector_position(detector_position_x, detector_pos_z, detector_choice)


def prepare_detector(detector_choice):
    previous_shutter_mode = caget(epics_config[detector_choice] + ':cam1:ShutterMode')
    if detector_choice == 'marccd':
        caput(epics_config[detector_choice] + ':cam1:ShutterMode', 0, wait=True)  # 0 is None
    elif detector_choice == 'pilatus':
        caput(epics_config[detector_choice] + ':cam1:ShutterMode', 1, wait=True)  # 1 is EPICS PV
    return previous_shutter_mode


def prepare_detector_settings(detector_choice):
    previous_detector_settings = {}
    previous_shutter_mode = epics_config[detector_choice] + ':cam1:ShutterMode'
    previous_detector_settings[previous_shutter_mode] = caget(previous_shutter_mode)
    previous_exposure_time = epics_config[detector_choice] + ':cam1:AcquireTime_RBV'
    previous_detector_settings[previous_exposure_time] = caget(previous_exposure_time)
    previous_exposure_period = epics_config[detector_choice] + ':cam1:AcquirePeriod_RBV'
    previous_detector_settings[previous_exposure_period] = caget(previous_exposure_period)
    previous_num_images = epics_config[detector_choice] + ':cam1:NumImages_RBV'
    previous_detector_settings[previous_num_images] = caget(previous_num_images)
    if detector_choice == 'marccd':
        caput(epics_config[detector_choice] + ':cam1:ShutterMode', 0, wait=True)  # 0 is None
    elif detector_choice == 'pilatus':
        caput(epics_config[detector_choice] + ':cam1:ShutterMode', 1, wait=True)  # 1 is EPICS PV
        previous_trigger_mode = epics_config[detector_choice] + ':cam1:TriggerMode'
        previous_detector_settings[previous_trigger_mode] = caget(previous_trigger_mode)
    return previous_detector_settings


def reset_detector_settings(previous_detector_settings):
    for key in previous_detector_settings:
        pv_name = key.split('_RBV')[0]
        caput(pv_name, previous_detector_settings[key], wait=True)


def collect_wide_data(detector_choice, detector_position_x, detector_position_z, omega_start, omega_end, exposure_time,
                      x, y, z):
    # performs the actual wide measurement

    # prepare the stage:
    prepare_stage(detector_choice, detector_position_x, detector_position_z, omega_start, x, y, z)

    # prepare the detector
    previous_detector_settings = prepare_detector_settings(detector_choice)
    # previous_shutter_mode = prepare_detector(detector_choice)
    if detector_choice == 'marccd':
        detector_checker = DetectorChecker(detector_choice)

    # start data collection
    # perform_background_collection()

    omega_range = omega_end - omega_start

    wstring = 'start {} range {} time {} s'.format(omega_start,
                                                   omega_range,          exposure_time)

    caput(epics_config[detector_choice] + ':AcquireSequence.STRA', wstring, wait=True)
    print(omega_range)
    if detector_choice == 'marccd':
        collect_data(exposure_time + 50, detector_choice)
        # start trajectory scan
        run_omega_trajectory(omega_range, exposure_time)
        # stop detector and wait for the detector readout
        time.sleep(0.1)
        caput(epics_config[detector_choice] + ':cam1:Acquire', 0)

        while not detector_checker.is_finished():
            time.sleep(0.1)
    elif detector_choice == 'pilatus':
        stage_xps = XPSTrajectory(host=HOST, group=GROUP_NAME, positioners=POSITIONERS)

        stage_xps.define_line_trajectories_general(stop_values=[[0, 0, 0, omega_range]],
                                                   scan_time=exposure_time,
                                                   pulse_time=0.1, accel_values=DEFAULT_ACCEL)
        caput(epics_config[detector_choice] + ':cam1:AcquireTime', exposure_time-0.001, wait=True)
        caput(epics_config[detector_choice] + ':cam1:AcquirePeriod', exposure_time, wait=True)
        caput(epics_config['pilatus'] + ':cam1:NumImages', 1, wait=True)
        caput(epics_config['pilatus'] + ':cam1:TriggerMode', 2, wait=True)  # 2 is ext. trigger
        caput(epics_config['pilatus'] + ':cam1:Acquire', 1)

        pilatus_trajectory_thread = Thread(target=stage_xps.run_line_trajectory_general)
        pilatus_trajectory_thread.start()

        while caget(epics_config['pilatus'] + ':cam1:Acquire'):
            continue
        # caput(epics_config['pilatus'] + ':cam1:Acquire', 1, wait=True)
        pilatus_trajectory_thread.join()

    # caput(epics_config[detector_choice] + ':cam1:ShutterMode', previous_shutter_mode, wait=True)
    reset_detector_settings(previous_detector_settings)
    logger.info('Wide data collection finished.\n')
    # caput(epics_config['marccd'] + ':AcquireSequence.STRA', 'Wide scan finished', wait=True)
    del stage_xps
    return


class DetectorChecker(object):
    def __init__(self, detector_choice):
        self.detector_choice = detector_choice
        self.pv_name = epics_config[detector_choice] + ':cam1'

        if detector_choice == 'marccd':
            self.detector_status = self.StatusChecker(3)
            camonitor(self.pv_name + ':MarReadoutStatus_RBV',
                      writer=partial(self.detector_status.set_status, 0, 'Idle', True))
            camonitor(self.pv_name + ':MarCorrectStatus_RBV',
                      writer=partial(self.detector_status.set_status, 1, 'Idle', True))
            camonitor(self.pv_name + ':MarWritingStatus_RBV',
                      writer=partial(self.detector_status.set_status, 2, 'Idle', True))

    def is_finished(self):
        if self.detector_choice == 'marccd':
            if self.detector_status.is_true():
                camonitor_clear(self.pv_name + ':MarReadoutStatus_RBV')
                camonitor_clear(self.pv_name + ':MarCorrectStatus_RBV')
                camonitor_clear(self.pv_name + ':MarWritingStatus_RBV')
                return True
            else:
                return False
        elif self.detector_choice == 'pilatus':
            if not caget(epics_config[self.detector_choice] + ':cam1:Acquire'):
                return True
            else:
                return False

    def read_out_is_finished(self):
        if self.detector_status.status[0]:
            return True
        else:
            return False

    class StatusChecker(object):
        def __init__(self, num_status):
            self.status = []
            for ind in range(num_status):
                self.status.append(False)

        def set_status(self, ind, check_str, value, status_str):
            if status_str.split()[-1] == check_str:
                self.status[ind] = value

        def is_true(self):
            for status in self.status:
                if status is False:
                    return False
            return True


def run_omega_trajectory(omega, running_time):
    stage_xps = XPSTrajectory(host=HOST, group=GROUP_NAME, positioners=POSITIONERS)
    stage_xps.define_line_trajectories_general(stop_values=[[0, 0, 0, omega]], scan_time=running_time, pulse_time=0.1)

    logger.info("Running Omega-Trajectory: {}d {}s".format(omega, running_time))
    stage_xps.run_line_trajectory_general()
    del stage_xps


def collect_single_data(detector_choice, detector_position_x, detector_position_z, exposure_time, x, y, z, omega):
    # new commands
    # previous_shutter_mode = prepare_detector(detector_choice)
    if detector_choice == 'marccd':
        detector_checker = DetectorChecker(detector_choice)

    # performs an actual single angle measurement:
    move_to_sample_pos(x, y, z)
    move_to_omega_position(omega)
    move_to_detector_position(detector_position_x, detector_position_z, detector_choice)

    # more new commands

    if detector_choice == 'pilatus':
        caput(epics_config[detector_choice] + ':cam1:AcquireTime', exposure_time-0.001, wait=True)
        caput(epics_config[detector_choice] + ':cam1:AcquirePeriod', exposure_time, wait=True)
        caput(epics_config[detector_choice] + ':cam1:NumImages', 1, wait=True)
        caput(epics_config[detector_choice] + ':cam1:Acquire', 1, wait=True)

    if detector_choice == 'marccd':
        caput(epics_config[detector_choice] + ':cam1:AcquireTime', exposure_time, wait=True)
        caput(epics_config[detector_choice] + ':cam1:Acquire', 1, wait=True)
        time.sleep(1)
        caput(epics_config[detector_choice] + ':cam1:Acquire', 0, wait=True)

    # caput(epics_config[detector_choice] + ':cam1:ShutterMode', previous_shutter_mode, wait=True)

    if detector_choice == 'marccd':
        while not detector_checker.is_finished():
            time.sleep(0.1)
    logger.info('Still data collection finished.\n')

    return


def move_to_sample_pos(x, y, z, wait=True, callbacks=[]):
    logger.info('Moving Sample to x: {}, y: {}, z: {}'.format(x, y, z))
    motor_x = PV(epics_config['sample_position_x'])
    motor_y = PV(epics_config['sample_position_y'])
    motor_z = PV(epics_config['sample_position_z'])
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
    motor_x.put(x, wait=True)
    motor_y.put(y, wait=True)
    motor_z.put(z, wait=True)
    time.sleep(0.5)
    logger.info('Moving Sample to x: {}, y: {}, z: {} finished.\n'.format(x, y, z))
    caput(epics_config['marccd'] + ':AcquireSequence.STRA', 'Scan finished', wait=True)
    return


def move_to_omega_position(omega, wait=True):
    logger.info('Moving Sample Omega to {}'.format(omega))
    caput(epics_config['sample_position_omega'], omega, wait=wait)
    if wait:
        logger.info('Moving Sample Omega to {} finished.\n'.format(omega))


def move_to_detector_position(detector_position_x, detector_position_z, detector_choice):
    logger.info('Moving Detector X to {}'.format(detector_position_x))
    caput(epics_config['detector_position_x'], detector_position_x, wait=True, timeout=300)
    if detector_choice == 'marccd':
        logger.info('Moving MARCCD Z to {}'.format(detector_position_z))
        caput(epics_config['detector_position_z'], detector_position_z, wait=True, timeout=300)
    elif detector_choice == 'pilatus':
        logger.info('Moving Pilatus Z to {}'.format(detector_position_z))
        caput(epics_config['pilatus_position_z'], detector_position_z, wait=True, timeout=300)
    logger.info('Moving Detector finished. \n')


def collect_data(exposure_time, detector_choice, wait=False):
    caput(epics_config[detector_choice] + ':cam1:AcquireTime', exposure_time, wait=True)
    if detector_choice == 'pilatus':
        caput(epics_config[detector_choice] + ':cam1:AcquirePeriod', exposure_time+0.001, wait=True)
    logger.info('Starting data collection.')
    caput(epics_config[detector_choice] + ':cam1:Acquire', 1, wait=wait, timeout=exposure_time + 20)
    if wait:
        logger.info('Finished data collection.\n')
