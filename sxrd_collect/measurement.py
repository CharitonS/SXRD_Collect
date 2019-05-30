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
from epics import caput, caget, PV, camonitor, camonitor_clear
from threading import Thread
# from utils import caput
from xps_trajectory.XPS_C8_drivers import XPS

__author__ = 'Clemens Prescher'


logging.basicConfig()
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# from xps_trajectory.xps_trajectory import XPSTrajectory

from config import epics_config  # , xps_config

# HOST = xps_config['HOST']
# GROUP_NAME = xps_config['GROUP NAME']
# POSITIONERS = xps_config['POSITIONERS']
# DEFAULT_ACCEL = xps_config['DEFAULT ACCEL']
#
# GATHER_OUTPUTS = xps_config['GATHER OUTPUTS']


def get_sample_position():
    x_pos = caget(epics_config['sample_position_x'])
    y_pos = caget(epics_config['sample_position_y'])
    z_pos = caget(epics_config['sample_position_z'])
    return x_pos, y_pos, z_pos


def collect_step_data(detector_choice, detector_position_x, detector_position_z, omega_start, omega_end, omega_step,
                      actual_omega_step, exposure_time, x, y, z, callback_fcn=None, collect_bkg_flag=False):
    """
    Performs a single crystal step collection at the sample position x,y,z using the trajectory scan of the
    XPS motor controller. This
    :param detector_choice:
        Which detector to use (perkin_elmer or marccd).
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
    :param actual_omega_step:
        THe actual omega step since for perkin_elmer in step scan the step is set to 0.1 in some cases
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
    actual_num_steps = (omega_end - omega_start) / actual_omega_step
    omega_range = omega_end - omega_start

    if detector_choice == 'perkin_elmer':
        previous_omega_settings = prepare_omega_settings(omega_range, exposure_time*num_steps)
        motor_resolution = abs(caget(epics_config['sample_position_omega'] + '.MRES'))
        previous_sis_settings = prepare_sis_settings(omega_step, motor_resolution)

    # stage_xps = XPSTrajectory(host=HOST, group=GROUP_NAME, positioners=POSITIONERS)
    # if detector_choice == 'marccd':
    #     stage_xps.define_line_trajectories_general(stop_values=[[0, 0, 0, omega_step]], scan_time=exposure_time,
    #                                                pulse_time=0.1, accel_values=DEFAULT_ACCEL)
    if detector_choice == 'perkin_elmer':
        print(omega_range)
        # stage_xps.define_line_trajectories_general(stop_values=[[0, 0, 0, omega_range]],
        #                                            scan_time=exposure_time*num_steps,
        #                                            pulse_time=exposure_time, accel_values=DEFAULT_ACCEL)

    # if collect_bkg_flag:
    #     if callback_fcn is None or (callback_fcn is not None and callback_fcn()):
    #         collect_background(detector_choice)
    #     else:
    #         logger.info('Data collection was aborted!')

    if callback_fcn is None or (callback_fcn is not None and callback_fcn()):
        if detector_choice == 'perkin_elmer':
            caput(epics_config[detector_choice] + ':cam1:AcquireTime', exposure_time, wait=True)
            perkin_elmer_collect_offset_frames()
            # caput(epics_config[detector_choice] + ':cam1:AcquirePeriod', exposure_time, wait=True)
            caput(epics_config['perkin_elmer'] + ':cam1:ImageMode', 1, wait=True)  # 1 is multiple
            caput(epics_config['perkin_elmer'] + ':cam1:NumImages', num_steps, wait=True)
            caput(epics_config['perkin_elmer'] + ':cam1:TriggerMode', 1, wait=True)  # 1 is External

            actual_exposure_time = exposure_time*num_steps/actual_num_steps
            message = str(int(actual_num_steps)) + ' steps from ' + '{0:.1f}'.format(omega_start) + ' to ' + \
                      '{0:.1f}'.format(omega_end) + ', ' + '{0:.2f}'.format(actual_exposure_time) + 's'
            print(message)
            caput(epics_config[detector_choice] + ':AcquireSequence.STRA', str(message), wait=True)

            # perkin_elmer_trajectory_thread = Thread(target=stage_xps.run_line_trajectory_general)
            t1 = time.time()
            caput(epics_config['perkin_elmer'] + ':cam1:Acquire', 1)
            caput(epics_config['sample_position_omega'], omega_end, wait=False)
            # perkin_elmer_trajectory_thread.start()
            while caget(epics_config['perkin_elmer'] + ':cam1:Acquire'):
                continue

            """
            # This is for running with internal trigger
            while caget(epics_config['table_shutter']):
                continue
            t2 = time.time()
            caput(epics_config['perkin_elmer'] + ':cam1:Acquire', 1, wait=True)
            t3 = time.time()
            print("Opened table shutter after " + str(t2-t1))
            print("collected data within " + str(t3-t2))
            """
            # perkin_elmer_trajectory_thread.join()

        elif detector_choice == 'marccd':
            for step in range(int(num_steps)):
                t1 = time.time()
                longstring = 'Running Omega-Trajectory from {:.2f} deg by {:.2f} deg {:.1f} s: frame {} of {}'
                longstring = longstring.format(omega_start + step * omega_step, omega_step, exposure_time, step+1,
                                               int(num_steps))
                shortstring = 'start:{:.2f} step:{:.2f} t:{:.1f}s'.format(omega_start + step * omega_step,
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

    reset_detector_settings(previous_detector_settings, detector_choice)
    if detector_choice == 'perkin_elmer':
        reset_settings(previous_omega_settings)
        reset_settings(previous_sis_settings)
    # caput(epics_config[detector_choice] + ':cam1:ShutterMode', previous_shutter_mode, wait=True)
    logger.info('Data collection finished.\n')
    if detector_choice == 'perkin_elmer':
        pass
        # message = str(int(num_steps)) + ' steps from ' + '{0:.1f}'.format(omega_start) + ' to ' + \
        #           '{0:.1f}'.format(omega_end) + ', ' + '{0:.1f}'.format(exposure_time) + ' (s)'
        # caput(epics_config[detector_choice] + ':AcquireSequence.STRA', message, wait=True)
    else:
        caput(epics_config[detector_choice] + ':AcquireSequence.STRA', 'Step scan finished', wait=True)
    # del stage_xps


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
    elif detector_choice == 'perkin_elmer':
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
    elif detector_choice == 'perkin_elmer':
        caput(epics_config[detector_choice] + ':cam1:ShutterMode', 1, wait=True)  # 1 is EPICS PV
        previous_trigger_mode = epics_config[detector_choice] + ':cam1:TriggerMode_RBV'
        previous_detector_settings[previous_trigger_mode] = caget(previous_trigger_mode)
        previous_image_mode = epics_config[detector_choice] + ':cam1:ImageMode_RBV'
        previous_detector_settings[previous_image_mode] = caget(previous_image_mode)
    return previous_detector_settings


def prepare_omega_settings(omega_range, total_time):
    previous_omega_settings = {}
    omega_speed_pv = epics_config['sample_position_omega'] + '.VELO'
    previous_omega_settings[omega_speed_pv] = caget(omega_speed_pv)
    omega_acceleration_pv = epics_config['sample_position_omega'] + '.ACCL'
    previous_omega_settings[omega_acceleration_pv] = caget(omega_acceleration_pv)

    caput(omega_acceleration_pv, 0.1, wait=True)
    caput(omega_speed_pv, omega_range/total_time, wait=True)

    return previous_omega_settings


def prepare_sis_settings(step_size, motor_resolution):
    previous_sis_settings = {}

    ext_prescale_pv = epics_config['SIS'] + ':Prescale'
    previous_sis_settings[ext_prescale_pv] = caget(ext_prescale_pv)
    channels_used_pv = epics_config['SIS'] + ':NuseAll'
    previous_sis_settings[channels_used_pv] = caget(channels_used_pv)
    channel_advance_pv = epics_config['SIS'] + ':ChannelAdvance'
    previous_sis_settings[channel_advance_pv] = caget(channel_advance_pv)

    # TODO: maybe add more settings for polarity, and width

    caput(ext_prescale_pv, step_size/motor_resolution, wait=True)
    caput(channels_used_pv, 8192, wait=True)
    caput(channel_advance_pv, 1, wait=True)  # 1 is external
    caput(epics_config['SIS'] + ':EraseStart', 1, wait=False)

    return previous_sis_settings


def prepare_proc_settings(num_steps):
    previous_proc_settings = {}
    proc_pv = epics_config['perkin_elmer'] + ':Proc1'
    proc_reset_pv = proc_pv + ':ResetFilter'
    proc_enable_pv = proc_pv + ':EnableCallbacks'
    previous_proc_settings[proc_enable_pv] = caget(proc_enable_pv)
    proc_enable_filter_pv = proc_pv + ':EnableFilter'
    previous_proc_settings[proc_enable_filter_pv] = caget(proc_enable_filter_pv)
    proc_num_filter_pv = proc_pv + ':NumFilter'
    previous_proc_settings[proc_num_filter_pv] = caget(proc_num_filter_pv)
    proc_filter_type_pv = proc_pv + ':FilterType'
    previous_proc_settings[proc_filter_type_pv] = caget(proc_filter_type_pv)
    tiff_array_port_pv = epics_config['perkin_elmer'] + ':TIFF1:NDArrayPort'
    previous_proc_settings[tiff_array_port_pv] = caget(tiff_array_port_pv)

    caput(proc_reset_pv, 1, wait=True)
    caput(proc_enable_pv, 1, wait=True)
    caput(proc_enable_filter_pv, 1, wait=True)
    caput(proc_num_filter_pv, num_steps, wait=True)
    caput(proc_filter_type_pv, 2, wait=True)  # 2 is Sum
    caput(tiff_array_port_pv, 'PROC1', wait=True)

    return previous_proc_settings


def reset_detector_settings(previous_detector_settings, detector_choice):
    for key in previous_detector_settings:
        pv_name = key.split('_RBV')[0]
        if detector_choice == 'perkin_elmer':
            caput(pv_name, previous_detector_settings[key], wait=True)
        else:
            caput(pv_name, previous_detector_settings[key], wait=True)


def reset_settings(previous_settings):
    for key in previous_settings:
        pv_name = key.split('_RBV')[0]
        caput(pv_name, previous_settings[key], wait=True)


def collect_wide_data(detector_choice, detector_position_x, detector_position_z, omega_start, omega_end,
                      real_exposure_time, x, y, z):
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

    wstring = 'start:{} range:{} t:{:.1f}s'.format(omega_start,
                                                   omega_range,          real_exposure_time)

    caput(epics_config[detector_choice] + ':AcquireSequence.STRA', wstring, wait=True)
    print(omega_range)
    if detector_choice == 'marccd':
        collect_data(real_exposure_time + 50, detector_choice)
        # start trajectory scan
        run_omega_trajectory(omega_range, real_exposure_time)
        # stop detector and wait for the detector readout
        time.sleep(0.1)
        caput(epics_config[detector_choice] + ':cam1:Acquire', 0)

        while not detector_checker.is_finished():
            time.sleep(0.1)
    elif detector_choice == 'perkin_elmer':
        # stage_xps = XPSTrajectory(host=HOST, group=GROUP_NAME, positioners=POSITIONERS)

        # stage_xps.define_line_trajectories_general(stop_values=[[0, 0, 0, omega_range]],
        #                                            scan_time=exposure_time,
        #                                            pulse_time=0.1, accel_values=DEFAULT_ACCEL)

        if real_exposure_time > 5.0:
            exposure_time = 5.0
            num_steps = round(real_exposure_time/exposure_time)
            omega_step = omega_range/num_steps
        else:
            exposure_time = real_exposure_time
            num_steps = 1
            omega_step = omega_range

        print("exposure time", exposure_time, " steps", num_steps, " omega_step: ", omega_step)

        previous_proc_settings = prepare_proc_settings(num_steps)
        previous_omega_settings = prepare_omega_settings(omega_range, exposure_time*num_steps)
        motor_resolution = abs(caget(epics_config['sample_position_omega'] + '.MRES'))
        previous_sis_settings = prepare_sis_settings(omega_step, motor_resolution)

        caput(epics_config[detector_choice] + ':cam1:AcquireTime', exposure_time, wait=True)
        perkin_elmer_collect_offset_frames()
        caput(epics_config['perkin_elmer'] + ':cam1:ImageMode', 1, wait=True)  # 1 is multiple
        caput(epics_config['perkin_elmer'] + ':cam1:NumImages', num_steps, wait=True)
        caput(epics_config['perkin_elmer'] + ':cam1:TriggerMode', 1, wait=True)  # 1 is ext. trigger

        caput(epics_config['perkin_elmer'] + ':cam1:Acquire', 1, wait=False)
        caput(epics_config['sample_position_omega'], omega_end, wait=False)
        time.sleep(0.5)
        # perkin_elmer_trajectory_thread = Thread(target=stage_xps.run_line_trajectory_general)
        # perkin_elmer_trajectory_thread.start()

        while caget(epics_config['perkin_elmer'] + ':cam1:Acquire'):
            continue
        print("Acquire Complete!")
        # caput(epics_config['perkin_elmer'] + ':cam1:Acquire', 1, wait=True)
        # perkin_elmer_trajectory_thread.join()
        # del stage_xps
        time.sleep(0.5)
    # caput(epics_config[detector_choice] + ':cam1:ShutterMode', previous_shutter_mode, wait=True)
    reset_detector_settings(previous_detector_settings, detector_choice)
    if detector_choice == 'perkin_elmer':
        reset_settings(previous_omega_settings)
        reset_settings(previous_sis_settings)
        reset_settings(previous_proc_settings)

    time.sleep(0.5)
    logger.info('Wide data collection finished.\n')
    # caput(epics_config['marccd'] + ':AcquireSequence.STRA', 'Wide scan finished', wait=True)
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
        elif self.detector_choice == 'perkin_elmer':
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

    if detector_choice == 'perkin_elmer':
        caput(epics_config[detector_choice] + ':cam1:AcquireTime', exposure_time, wait=True)
        # caput(epics_config[detector_choice] + ':cam1:AcquirePeriod', exposure_time, wait=True)
        caput(epics_config[detector_choice] + ':cam1:NumImages', 1, wait=True)
        perkin_elmer_collect_offset_frames()
        caput(epics_config[detector_choice] + ':cam1:Acquire', 1, wait=True, timeout=300+exposure_time)

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
    logger.info('Moving Sample to x: {:.2f}, y: {:.2f}, z: {:.2f} finished.\n'.format(x, y, z))
    # caput(epics_config['marccd'] + ':AcquireSequence.STRA', 'Scan finished', wait=True)
    return


def move_to_omega_position(omega, wait=True):
    logger.info('Moving Sample Omega to {}'.format(omega))
    caput(epics_config['sample_position_omega'], omega, wait=wait)
    if wait:
        logger.info('Moving Sample Omega to {} finished.\n'.format(omega))


def move_to_detector_position(detector_position_x, detector_position_z, detector_choice):
    # logger.info('Moving Detector X to {}'.format(detector_position_x))
    # caput(epics_config['detector_position_x'], detector_position_x, wait=True, timeout=300)
    if detector_choice == 'marccd':
        logger.info('Moving MARCCD Z to {}'.format(detector_position_z))
        caput(epics_config['detector_position_z'], detector_position_z, wait=True, timeout=300)
    elif detector_choice == 'perkin_elmer':
        logger.info('Moving perkin_elmer Z to {}'.format(detector_position_z))
        caput(epics_config['perkin_elmer_position_z'], detector_position_z, wait=True, timeout=300)
    logger.info('Moving Detector finished. \n')
    time.sleep(0.5)


def collect_data(exposure_time, detector_choice, wait=False):
    caput(epics_config[detector_choice] + ':cam1:AcquireTime', exposure_time, wait=True)
    # if detector_choice == 'perkin_elmer':
    #     caput(epics_config[detector_choice] + ':cam1:AcquirePeriod', exposure_time+0.001, wait=True)
    logger.info('Starting data collection.')
    caput(epics_config[detector_choice] + ':cam1:Acquire', 1, wait=wait, timeout=exposure_time + 20)
    if wait:
        logger.info('Finished data collection.\n')


def caput_pil3(pv, value, wait=True):
    t0 = time.time()
    time.sleep(0.02)
    caput(pv, value, wait=wait)

    while time.time() - t0 < 20.0:
        time.sleep(0.02)
        msg = caget(epics_config['status_message'], as_string=True)
        if 'OK' in msg or 'Waiting for acquire command' in msg:
            return True
        print('waiting')
    return False


def perkin_elmer_collect_offset_frames():
    caput(epics_config['perkin_elmer_tiff_autosave'], 0, wait=True)
    caput(epics_config['perkin_elmer_offset_frames'], 2, wait=True)
    caput(epics_config['perkin_elmer_offset_constant'], 0, wait=True)
    caput(epics_config['perkin_elmer_acquire_offset_correction'], 1, wait=True)
    caput(epics_config['perkin_elmer_tiff_autosave'], 1, wait=True)
