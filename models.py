# -*- coding: utf8 -*-
# - GUI program for fast processing of 2D X-ray data
#     Copyright (C) 2014  Clemens Prescher (clemens.prescher@gmail.com)
#     GSECARS, University of Chicago
#
#     This program is free software: you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation, either version 3 of the License, or
#     (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program.  If not, see <http://www.gnu.org/licenses/>.
__author__ = 'Clemens Prescher'


class ExperimentSetup(object):
    def __init__(self, detector_pos = -333, omega_start = 0, omega_end = 0, omega_step = 0, time_per_step=0):
        self.detector_pos = detector_pos
        self.omega_start = omega_start
        self.omega_end = omega_end
        self.omega_step = omega_step
        self.time_per_step = time_per_step


class SamplePoint(object):
    def __init__(self, name = 'P', x=0, y=0, z=0):
        self.name = name
        self.x = x
        self.y = y
        self.z = z

        self.experiment_setups = []
        self.perform_wide_scan_for_setup = []
        self.perform_step_scan_for_setup = []
        self.perform_single_for_setup = []

    def set_position(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

    def register_setup(self, experiment_setup):
        self.experiment_setups.append(experiment_setup)
        self.perform_single_for_setup.append(False)
        self.perform_step_scan_for_setup.append(False)
        self.perform_wide_scan_for_setup.append(False)

    def unregister(self, experiment_setup):
        ind = self.experiment_setups.index(experiment_setup)
        del self.experiment_setups[ind]
        del self.perform_single_for_setup[ind]
        del self.perform_step_scan_for_setup[ind]
        del self.perform_wide_scan_for_setup[ind]


def collect_step_data(detector_position, omega_start, omega_end, omega_step, time, x, y, z, pv_names):
    #performs the actual step measurement
    print 'collecting step data'
    return

def collect_wide_data(detector_position, omega_start, omega_end, omega_step, time, x, y, z, pv_names):
    #performs the actual wide measurement
    print 'collecting wide data'
    return

def collect_single_data(detector_position, omega_start, omega_end, omega_step, time, x, y, z, pv_names):
    #performs an actual single angle measurement:
    print 'collecting single_data'
    return

def collect_sample_point(sample_point, pv_names):
    for ind, experiment_setup in enumerate(sample_point.experiment_setups):
        print ind
        if sample_point.perform_single_for_setup[ind]:
            collect_single_data(experiment_setup.detector_pos,
                                experiment_setup.omega_start,
                                experiment_setup.omega_end,
                                experiment_setup.omega_step,
                                experiment_setup.time_per_step,
                                sample_point.x,
                                sample_point.y,
                                sample_point.z,
                                pv_names)
        if sample_point.perform_wide_scan_for_setup[ind]:
            collect_wide_data(experiment_setup.detector_pos,
                                experiment_setup.omega_start,
                                experiment_setup.omega_end,
                                experiment_setup.omega_step,
                                experiment_setup.time_per_step,
                                sample_point.x,
                                sample_point.y,
                                sample_point.z,
                                pv_names)
        if sample_point.perform_step_scan_for_setup[ind]:
            collect_step_data(experiment_setup.detector_pos,
                                experiment_setup.omega_start,
                                experiment_setup.omega_end,
                                experiment_setup.omega_step,
                                experiment_setup.time_per_step,
                                sample_point.x,
                                sample_point.y,
                                sample_point.z,
                                pv_names)