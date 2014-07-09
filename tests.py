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

import unittest

from models import *
from xps_trajectory.xps_trajectory import XPSTrajectory

class SamplePointTest(unittest.TestCase):
    def setUp(self):
        self.experiment_setup1 = ExperimentSetup()
        self.experiment_setup2 = ExperimentSetup(-403, -120, -60, 0.5, 0.5)

        self.sample_point = SamplePoint()
        self.sample_point.register_setup(self.experiment_setup1)
        self.sample_point.register_setup(self.experiment_setup2)

    def test_references(self):
        self.experiment_setup1.omega_start = -110
        self.assertEqual(self.sample_point.experiment_setups[0].omega_start, -110)

    def test_measurements(self):
        collect_sample_point(self.sample_point, [])
        self.sample_point.perform_wide_scan_for_setup[1]=True
        self.sample_point.perform_single_for_setup[0]=True
        collect_sample_point(self.sample_point, [])


class TrajectoryScanTest(unittest.TestCase):
    HOST = '164.54.160.34'
    GROUP_NAME = 'G1'
    POSITIONERS = "STX STZ SLY OM"

    GATHER_OUTPUTS = ('CurrentPosition', 'FollowingError',
                      'SetpointPosition', 'CurrentVelocity')

    def test_templates(self):
        stage_xps = XPSTrajectory(host=self.HOST, group=self.GROUP_NAME, positioners=self.POSITIONERS)
