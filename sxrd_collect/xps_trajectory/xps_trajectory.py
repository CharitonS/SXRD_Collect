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
__author__ = 'Clemens Prescher'

import time
import numpy as np
import ftplib
try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO, BytesIO

from .XPS_C8_drivers import XPS
from config import xps_config

import logging
logger = logging.getLevelName(__name__)


class XPSTrajectory(object):
    """XPS trajectory....
    """

    ramp_template_xrd = "%(ramptime)f, %(xramp)f, %(xvelo)f, %(zramp)f, %(zvelo)f, %(yramp)f, %(yvelo)f, %(oramp)f, %(ovelo)f"
    move_template_xrd = "%(scantime)f, %(xdist)f, %(xvelo)f, %(zdist)f, %(zvelo)f, %(ydist)f, %(yvelo)f, %(odist)f, %(ovelo)f"
    down_template_xrd = "%(ramptime)f, %(xramp)f, %(xzero)f, %(zramp)f, %(zzero)f, %(yramp)f, %(yzero)f, %(oramp)f, %(ozero)f"

    def __init__(self, host=None, user=None, passwd=None,
                 group=None, positioners=None, mode=None, type=None,
                 default_accel=[]):
        self.host = host or xps_config['HOST']
        self.user = user or xps_config['USER']
        self.passwd = passwd or xps_config['PASSWORD']
        self.group_name = group or xps_config['GROUP NAME']
        self.positioners = positioners or xps_config['POSITIONERS']
        self.positioners = tuple(self.positioners.replace(',', ' ').split())

        gout = []
        gtit = []
        for pname in self.positioners:
            for out in xps_config['GATHER OUTPUTS']:
                gout.append('%s.%s.%s' % (self.group_name, pname, out))
                gtit.append('%s.%s' % (pname, out))
        self.gather_outputs = gout
        self.gather_titles = "%s\n#%s\n" % (xps_config['GATHER TITLES'],
                                            "  ".join(gtit))

        # self.gather_titles  = "%s %s\n" % " ".join(gtit)

        self.xps = XPS()
        self.ssid = self.xps.TCP_ConnectToServer(self.host, xps_config['PORT'], xps_config['TIMEOUT'])
        ret = self.xps.Login(self.ssid, self.user, self.passwd)
        self.trajectories = {}

        self.ftpconn = ftplib.FTP()
        self.nlines_out = 0

        self.xps.GroupMotionDisable(self.ssid, self.group_name)
        time.sleep(0.1)
        self.xps.GroupMotionEnable(self.ssid, self.group_name)

        for i in range(64):
            self.xps.EventExtendedRemove(self.ssid, i)

        self.create_templates()
        self.default_accel = default_accel

    def create_templates(self):
        self.ramp_template = "%(ramptime)f"
        self.move_template = "%(scantime)f"
        self.down_template = "%(ramptime)f"

        for positioner in self.positioners:
            self.ramp_template += ", %({0}ramp)f, %({0}velo)f".format(positioner)
            self.move_template += ", %({0}dist)f, %({0}velo)f".format(positioner)
            self.down_template += ", %({0}ramp)f, %({0}zero)f".format(positioner)

    def ftp_connect(self):
        self.ftpconn.connect(self.host)
        self.ftpconn.login(self.user, self.passwd)
        self.FTP_connected = True

    def ftp_disconnect(self):
        "close ftp connection"
        self.ftpconn.close()
        self.FTP_connected = False

    def upload_trajectory_file(self, fname, data):
        self.ftp_connect()
        self.ftpconn.cwd(xps_config['TRAJ_FOLDER'])
        self.ftpconn.storbinary('STOR %s' % fname, BytesIO(str.encode(data)))
        self.ftp_disconnect()
        #print('Uploaded trajectory ', fname)
        #print(data)

    def define_line_trajectories_general(self, name='default',
                                         start_values=None,
                                         stop_values=None,
                                         accel_values=None,
                                         pulse_time=0.1, scan_time=10.0):
        #check consistency of parameters:
        if start_values is None:
            start_values = np.zeros(len(self.positioners))
        else:
            start_values = np.array(start_values)

        if stop_values is None:
            stop_values = [np.zeros(len(self.positioners))]
        else:
            stop_values = np.array(stop_values)

        if accel_values is None:
            accel_values = []
            for positioner in self.positioners:
                response = self.xps.PositionerMaximumVelocityAndAccelerationGet(self.ssid,
                                                                                self.group_name + '.' + positioner)
                accel_values.append(response[2] / 3.0)
        accel_values = np.array(accel_values)

        distances = []
        velocities = []
        temp_start_values = start_values
        for ind, values in enumerate(stop_values):
            distances.append((values - temp_start_values) * 1.0)
            velocities.append(distances[-1] / scan_time * len(stop_values))
            temp_start_values = values

        ramp_time = np.max(abs(velocities[0] / accel_values))
        scan_time = float(abs(scan_time)) / len(stop_values)
        ramp = 0.5 * velocities[0] * ramp_time

        ramp_attr = {'ramptime': ramp_time}
        down_attr = {'ramptime': ramp_time}

        for ind, positioner in enumerate(self.positioners):
            ramp_attr[positioner + 'ramp'] = ramp[ind]
            ramp_attr[positioner + 'velo'] = velocities[0][ind]

            down_attr[positioner + 'ramp'] = ramp[ind]
            down_attr[positioner + 'zero'] = 0

        ramp_str = self.ramp_template % ramp_attr
        down_str = self.down_template % down_attr
        move_strings = []

        for ind in range(len(distances)):
            attr = {'scantime': scan_time}
            for pos_ind, positioner in enumerate(self.positioners):
                attr[positioner + 'dist'] = distances[ind][pos_ind]
                attr[positioner + 'velo'] = velocities[ind][pos_ind]
            move_strings.append(self.move_template % attr)

        #construct trajectory:
        trajectory_str = ramp_str + '\n'
        for move_string in move_strings:
            trajectory_str += move_string + '\n'
        trajectory_str += down_str + '\n'

        self.trajectories[name] = {'pulse_time': pulse_time,
                                   'step_number': len(distances)}

        for ind, positioner in enumerate(self.positioners):
            self.trajectories[name][positioner + 'ramp'] = ramp[ind]

        ret = False
        try:
            self.upload_trajectory_file(name + '.trj', trajectory_str)
            ret = True
            # logger.info('Trajectory File uploaded.')
        except:
            # logger.info('Failed to upload trajectory file')
            pass
        return trajectory_str

    def run_line_trajectory_general(self, name='default', verbose=False, save=True,
                                    outfile='Gather.dat'):
        """run trajectory in PVT mode"""
        traj = self.trajectories.get(name, None)
        if traj is None:
            logger.error('Cannot find trajectory named %s' % name)
            return

        traj_file = '%s.trj' % name
        dtime = traj['pulse_time']
        ramps = []
        for positioner in self.positioners:
            ramps.append(-traj[positioner + 'ramp'])
        ramps = np.array(ramps)

        try:
            step_number = traj['step_number']
        except KeyError:
            step_number = 1

        self.xps.GroupMoveRelative(self.ssid, self.group_name, ramps)

        self.gather_outputs = []
        gather_titles = []

        for positioner in self.positioners:
            for out in xps_config['GATHER OUTPUTS']:
                self.gather_outputs.append('%s.%s.%s' % (self.group_name, positioner, out))
                gather_titles.append('%s.%s' % (positioner, out))
        self.gather_titles = "%s\n#%s\n" % (xps_config['GATHER TITLES'],
                                            "  ".join(gather_titles))

        self.xps.GatheringReset(self.ssid)
        self.xps.GatheringConfigurationSet(self.ssid, self.gather_outputs)

        ret = self.xps.MultipleAxesPVTPulseOutputSet(self.ssid, self.group_name,
                                                     2, step_number + 1, dtime)
        ret = self.xps.MultipleAxesPVTVerification(self.ssid, self.group_name, traj_file)

        buffer = ('Always', self.group_name + '.PVT.TrajectoryPulse')
        o = self.xps.EventExtendedConfigurationTriggerSet(self.ssid, buffer,
                                                          ('0', '0'), ('0', '0'),
                                                          ('0', '0'), ('0', '0'))

        o = self.xps.EventExtendedConfigurationActionSet(self.ssid, ('GatheringOneData',),
                                                         ('',), ('',), ('',), ('',))

        eventID, m = self.xps.EventExtendedStart(self.ssid)

        ret = self.xps.MultipleAxesPVTExecution(self.ssid, self.group_name, traj_file, 1)
        o = self.xps.EventExtendedRemove(self.ssid, eventID)
        o = self.xps.GatheringStop(self.ssid)

        npulses = 0
        if save:
            npulses = self.save_results(outfile, verbose=verbose)

        self.xps.GroupMoveRelative(self.ssid, self.group_name, ramps)
        return npulses

    def save_results(self, filename, verbose=False):
        """read gathering data from XPS
        """
        # self.xps.GatheringStop(self.ssid)
        # db = debugtime()
        ret, npulses, nx = self.xps.GatheringCurrentNumberGet(self.ssid)
        counter = 0
        while npulses < 1 and counter < 5:
            counter += 1
            time.sleep(1.50)
            ret, npulses, nx = self.xps.GatheringCurrentNumberGet(self.ssid)
            print('Had to do repeat XPS Gathering: ', ret, npulses, nx)

        # db.add(' Will Save %i pulses , ret=%i ' % (npulses, ret))
        ret, buff = self.xps.GatheringDataMultipleLinesGet(self.ssid, 0, npulses)
        # db.add('MLGet ret=%i, buff_len = %i ' % (ret, len(buff)))

        if ret < 0:  # gathering too long: need to read in chunks
            print('Need to read Data in Chunks!!!')  # how many chunks are needed??
            Nchunks = 3
            nx = int((npulses - 2) / Nchunks)
            ret = 1
            while True:
                time.sleep(0.1)
                ret, xbuff = self.xps.GatheringDataMultipleLinesGet(self.ssid, 0, nx)
                if ret == 0:
                    break
                Nchunks = Nchunks + 2
                nx = int((npulses - 2) / Nchunks)
                if Nchunks > 10:
                    print('looks like something is wrong with the XPS!')
                    break
            print(' -- will use %i Chunks for %i Pulses ' % (Nchunks, npulses))
            # db.add(' Will use %i chunks ' % (Nchunks))
            buff = [xbuff]
            for i in range(1, Nchunks):
                ret, xbuff = self.xps.GatheringDataMultipleLinesGet(self.ssid, i * nx, nx)
                buff.append(xbuff)
                # db.add('   chunk %i' % (i))
            ret, xbuff = self.xps.GatheringDataMultipleLinesGet(self.ssid, Nchunks * nx,
                                                                npulses - Nchunks * nx)
            buff.append(xbuff)
            buff = ''.join(buff)
            # db.add('   chunk last')

        obuff = buff[:]
        for x in ';\r\t':
            obuff = obuff.replace(x, ' ')
        # db.add('  data fixed')
        f = open(filename, 'w')
        f.write(self.gather_titles)
        f.write(obuff)
        f.close()
        nlines = len(obuff.split('\n')) - 1
        if verbose:
            print('Wrote %i lines, %i bytes to %s' % (nlines, len(buff), filename))
        self.nlines_out = nlines
        # db.show()
        return npulses


if __name__ == '__main__':
    pass

