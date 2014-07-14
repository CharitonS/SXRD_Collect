import time
import numpy as np
import ftplib
from io import StringIO
from .XPS_C8_drivers import XPS

# #
# # used methods for collector.py
# #    abortScan, clearabort
# #    done ftp_connect
# #    done ftp_disconnect
# #
# # mapscan:   Build (twice!)
# # linescan:  Build , clearabort
# # ExecTraj;  Execute(),   building<attribute>, executing<attribute>
## WriteTrajData:  Read_FTP(), SaveGatheringData()
##
## need to have env and ROI written during traj scan:
##   use a separate thread for ROI and ENV, allow
##   XY trajectory to block.

DEFAULT_ACCEL = {'z': 10.0, 'x': 10.0, 't': 2.0}


class config:
    # host = '164.54.160.180' #xas user xps
    host = '164.54.160.34'  #dac user xps
    port = 5001
    timeout = 10
    user = 'Administrator'
    passwd = 'Administrator'
    traj_folder = 'Public/trajectories'
    group_name = 'FINE'
    positioners = 'X Y THETA'
    gather_titles = "# XPS Gathering Data\n#--------------"
    gather_outputs = ('CurrentPosition', 'FollowingError',
                      'SetpointPosition', 'CurrentVelocity')
    #gather_outputs = ('CurrentPosition', 'SetpointPosition')


class XPSTrajectory(object):
    """XPS trajectory....
    """
    xylinetraj_text = """FirstTangent = 0
DiscontinuityAngle = 0.01

Line = %f, %f
"""

    ramp_template_xrd = "%(ramptime)f, %(xramp)f, %(xvelo)f, %(zramp)f, %(zvelo)f, %(yramp)f, %(yvelo)f, %(oramp)f, %(ovelo)f"
    move_template_xrd = "%(scantime)f, %(xdist)f, %(xvelo)f, %(zdist)f, %(zvelo)f, %(ydist)f, %(yvelo)f, %(odist)f, %(ovelo)f"
    down_template_xrd = "%(ramptime)f, %(xramp)f, %(xzero)f, %(zramp)f, %(zzero)f, %(yramp)f, %(yzero)f, %(oramp)f, %(ozero)f"

    def __init__(self, host=None, user=None, passwd=None,
                 group=None, positioners=None, mode=None, type=None,
                 default_accel=[]):
        self.host = host or config.host
        self.user = user or config.user
        self.passwd = passwd or config.passwd
        self.group_name = group or config.group_name
        self.positioners = positioners or config.positioners
        self.positioners = tuple(self.positioners.replace(',', ' ').split())

        gout = []
        gtit = []
        for pname in self.positioners:
            for out in config.gather_outputs:
                gout.append('%s.%s.%s' % (self.group_name, pname, out))
                gtit.append('%s.%s' % (pname, out))
        self.gather_outputs = gout
        self.gather_titles = "%s\n#%s\n" % (config.gather_titles,
                                            "  ".join(gtit))

        # self.gather_titles  = "%s %s\n" % " ".join(gtit)

        self.xps = XPS()
        self.ssid = self.xps.TCP_ConnectToServer(self.host, config.port, config.timeout)
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
        "close ftp connnection"
        self.ftpconn.close()
        self.FTP_connected = False

    def upload_trajectoryFile(self, fname, data):
        self.ftp_connect()
        self.ftpconn.cwd(config.traj_folder)
        self.ftpconn.storbinary('STOR %s' % fname, StringIO(data))
        self.ftp_disconnect()
        #print 'Uploaded trajectory ', fname
        #print data

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
            self.upload_trajectoryFile(name + '.trj', trajectory_str)
            ret = True
            print('uploaded')
        except:
            pass
        return trajectory_str

    def run_line_trajectory_general(self, name='default', verbose=False, save=True,
                                    outfile='Gather.dat'):
        """run trajectory in PVT mode"""
        traj = self.trajectories.get(name, None)
        if traj is None:
            print('Cannot find trajectory named %s' % name)
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
            for out in config.gather_outputs:
                self.gather_outputs.append('%s.%s.%s' % (self.group_name, positioner, out))
                gather_titles.append('%s.%s' % (positioner, out))
        self.gather_titles = "%s\n#%s\n" % (config.gather_titles,
                                            "  ".join(gather_titles))

        self.xps.GatheringReset(self.ssid)
        self.xps.GatheringConfigurationSet(self.ssid, self.gather_outputs)

        ret = self.xps.MultipleAxesPVTPulseOutputSet(self.ssid, self.group_name,
                                                     1, step_number+1, dtime)
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
            npulses = self.SaveResults(outfile, verbose=verbose)

        self.xps.GroupMoveRelative(self.ssid, self.group_name, ramps)
        return npulses


    def Move(self, xpos=None, ypos=None, tpos=None):
        "move XY positioner to supplied position"
        ret = self.xps.GroupPositionCurrentGet(self.ssid, 'FINE', 3)
        if xpos is None:  xpos = ret[1]
        if ypos is None:  ypos = ret[2]
        if tpos is None:  tpos = ret[3]
        self.xps.GroupMoveAbsolute(self.ssid, 'FINE', (xpos, ypos, tpos))


    def OLD_RunGenericTrajectory(self, name='foreward',
                                 pulse_range=1, pulse_step=0.01,
                                 speed=1.0,
                                 verbose=False, save=True,
                                 outfile='Gather.dat', debug=False):
        traj_file = '%s.trj' % name
        # print 'Run Gen Traj', pulse_range, pulse_step

        self.xps.GatheringReset(self.ssid)
        self.xps.GatheringConfigurationSet(self.ssid, self.gather_outputs)

        ret = self.xps.XYLineArcVerification(self.ssid, self.group_name, traj_file)
        self.xps.XYLineArcPulseOutputSet(self.ssid, self.group_name, 0, pulse_range, pulse_step)

        buffer = ('Always', 'FINE.XYLineArc.TrajectoryPulse',)
        self.xps.EventExtendedConfigurationTriggerSet(self.ssid, buffer,
                                                      ('0', '0'), ('0', '0'),
                                                      ('0', '0'), ('0', '0'))

        self.xps.EventExtendedConfigurationActionSet(self.ssid, ('GatheringOneData',),
                                                     ('',), ('',), ('',), ('',))

        eventID, m = self.xps.EventExtendedStart(self.ssid)
        # print 'Execute',  traj_file, eventID
        ret = self.xps.XYLineArcExecution(self.ssid, self.group_name, traj_file, speed, 1, 1)
        o = self.xps.EventExtendedRemove(self.ssid, eventID)
        o = self.xps.GatheringStop(self.ssid)

        if save:
            npulses = self.SaveResults(outfile, verbose=verbose)
        return npulses


    def SaveResults(self, fname, verbose=False):
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
            print('Need to read Data in Chunks!!!') # how many chunks are needed??
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
        f = open(fname, 'w')
        f.write(self.gather_titles)
        f.write(obuff)
        f.close()
        nlines = len(obuff.split('\n')) - 1
        if verbose:
            print('Wrote %i lines, %i bytes to %s' % (nlines, len(buff), fname))
        self.nlines_out = nlines
        # db.show()
        return npulses


if __name__ == '__main__':
    xps = XPSTrajectory()
    xps.DefineLineTrajectories(axis='x', start=-2., stop=2., scantime=20, step=0.004)
    print(xps.trajectories)
    xps.Move(-2.0, 0.1, 0)
    time.sleep(0.02)
    xps.RunLineTrajectory(name='foreward', outfile='Out.dat')

