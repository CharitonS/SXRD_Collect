__author__ = 'DAC_User'
__version__ = 0.1

import time
from threading import Thread
import logging

from epics import caget, caput
import epics

from PyQt4 import QtGui, QtCore

from config import epics_config
from views.MainView import MainView
from models import SxrdModel
from measurement import move_to_sample_pos, collect_step_data, collect_wide_data

logger = logging.getLogger()


class MainController(object):
    def __init__(self):
        self.widget = MainView(__version__)
        self.widget.show()
        self.model = SxrdModel()
        self.connect_buttons()
        self.connect_tables()
        self.connect_txt()
        self.populate_filename()

        self.abort_collection = False
        self.logging_handler = InfoLoggingHandler(self.update_status_txt)
        logger.addHandler(self.logging_handler)

        self.status_txt_scrollbar_is_at_max = True

    def connect_buttons(self):
        self.widget.add_setup_btn.clicked.connect(self.add_experiment_setup_btn_clicked)
        self.widget.delete_setup_btn.clicked.connect(self.delete_experiment_setup_btn_clicked)
        self.widget.clear_setup_btn.clicked.connect(self.clear_experiment_setup_btn_clicked)

        self.widget.add_sample_btn.clicked.connect(self.add_sample_point_btn_clicked)
        self.widget.delete_sample_btn.clicked.connect(self.delete_sample_point_btn_clicked)
        self.widget.clear_sample_btn.clicked.connect(self.clear_sample_point_btn_clicked)
        self.widget.create_map_btn.clicked.connect(self.create_map_btn_clicked)

        self.widget.get_folder_btn.clicked.connect(self.get_folder_btn_clicked)
        self.widget.collect_btn.clicked.connect(self.collect_data)

    def connect_tables(self):
        self.widget.setup_table.cellChanged.connect(self.setup_table_cell_changed)
        self.widget.sample_points_table.cellChanged.connect(self.sample_points_table_cell_changed)

        self.widget.move_sample_btn_clicked.connect(self.move_sample_btn_clicked)
        self.widget.set_sample_btn_clicked.connect(self.set_sample_btn_clicked)

        self.widget.step_cb_status_changed.connect(self.step_cb_status_changed)
        self.widget.wide_cb_status_changed.connect(self.wide_cb_status_changed)

    def connect_txt(self):
        self.widget.filename_txt.editingFinished.connect(self.basename_txt_changed)
        self.widget.filepath_txt.editingFinished.connect(self.filepath_txt_changed)

        self.widget.status_txt.textChanged.connect(self.update_status_txt_scrollbar)
        self.widget.status_txt.verticalScrollBar().valueChanged.connect(self.update_status_txt_scrollbar_value)

    def populate_filename(self):
        self.prev_filepath, self.prev_filename, self.prev_file_number = self.get_filename_info()

        self.filepath = self.prev_filepath
        self.basename = self.prev_filename

        self.widget.filename_txt.setText(self.prev_filename)
        self.widget.filepath_txt.setText(self.prev_filepath)

        self.set_example_lbl()

    def update_status_txt(self, msg):
        self.widget.status_txt.append(msg)

    def update_status_txt_scrollbar(self):
        if self.status_txt_scrollbar_is_at_max:
            self.widget.status_txt.verticalScrollBar().setValue(
                self.widget.status_txt.verticalScrollBar().maximum()
            )

    def get_folder_btn_clicked(self):
        self.prev_filepath, _, _ = self.get_filename_info()
        self.filepath = self.prev_filepath
        self.widget.filepath_txt.setText(self.prev_filepath)

        self.set_example_lbl()

    def update_status_txt_scrollbar_value(self, value):
        self.status_txt_scrollbar_is_at_max = value == self.widget.status_txt.verticalScrollBar().maximum()

    def add_experiment_setup_btn_clicked(self):
        detector_pos_x, detector_pos_z, omega, exposure_time = self.get_current_setup()
        default_name = 'E{}'.format(len(self.model.experiment_setups) + 1)
        self.model.add_experiment_setup(default_name, detector_pos_x, detector_pos_z,
                                       omega - 1, omega + 1, 0.1, exposure_time)
        self.widget.add_experiment_setup(default_name, detector_pos_x, detector_pos_z,
                                            omega - 1, omega + 1, 0.1, exposure_time)

    def delete_experiment_setup_btn_clicked(self):
        cur_ind = self.widget.get_selected_experiment_setup()
        cur_ind.sort()
        cur_ind = cur_ind[::-1]
        if cur_ind is None or (len(cur_ind) == 0):
            return
        msgBox = QtGui.QMessageBox()
        msgBox.setText('Do you really want to delete the selected experiment(s).')
        msgBox.setWindowTitle('Confirmation')
        msgBox.setStandardButtons(QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
        msgBox.setDefaultButton(QtGui.QMessageBox.Yes)
        response = msgBox.exec_()
        if response == QtGui.QMessageBox.Yes:
            for ind in cur_ind:
                self.widget.delete_experiment_setup(ind)
                self.model.delete_experiment_setup(ind)
            self.widget.recreate_sample_point_checkboxes(self.model.get_experiment_state())

    def clear_experiment_setup_btn_clicked(self):
        self.widget.clear_experiment_setups()
        self.model.clear_experiment_setups()

    def add_sample_point_btn_clicked(self):
        x, y, z = self.get_current_sample_position()
        num = len(self.model.sample_points)
        self.widget.add_sample_point('S{}'.format(num + 1), x, y, z)
        self.model.add_sample_point('S{}'.format(num + 1), x, y, z)

    def delete_sample_point_btn_clicked(self):
        cur_ind = self.widget.get_selected_sample_point()
        cur_ind.sort()
        cur_ind = cur_ind[::-1]
        for ind in cur_ind:
            self.widget.delete_sample_point(ind)
            self.model.delete_sample_point(ind)

    def clear_sample_point_btn_clicked(self):
        self.widget.clear_sample_points()
        self.model.clear_sample_points()

    def create_map_btn_clicked(self):
        cur_ind = self.widget.get_selected_sample_point()[-1]

        x_min = float(str(self.widget.x_min_txt.text()))
        x_max = float(str(self.widget.x_max_txt.text()))
        x_step = float(str(self.widget.x_step_txt.text()))

        y_min = float(str(self.widget.y_min_txt.text()))
        y_max = float(str(self.widget.y_max_txt.text()))
        y_step = float(str(self.widget.y_step_txt.text()))

        map = self.model.create_map(cur_ind, x_min, x_max, x_step, y_min, y_max, y_step)

        for name, position in map.iteritems():
            x, y, z = position
            self.widget.add_sample_point(name, x, y, z)

    def setup_table_cell_changed(self, row, col):
        label_item = self.widget.setup_table.item(row, col)
        value = str(label_item.text())
        self.widget.setup_table.blockSignals(True)
        if col == 0:
            if not self.model.setup_name_existent(value):
                self.model.experiment_setups[row].name = str(value)
                self.widget.update_sample_table_setup_header(
                    self.model.get_experiment_setup_names()
                )
                self.widget.sample_points_table.resizeColumnsToContents()
            else:
                self.create_name_existent_msg('Experiment setup')
                name_item = self.widget.setup_table.item(row, 0)
                name_item.setText(self.model.experiment_setups[row].name)
        else:
            value = float(value)
            if col == 1:
                self.model.experiment_setups[row].detector_pos_x = value
            elif col == 2:
                self.model.experiment_setups[row].detector_pos_z = value
            elif col == 3:
                self.model.experiment_setups[row].omega_start = value
                self.update_total_exposure_time(row)
            elif col == 4:
                self.model.experiment_setups[row].omega_end = value
                self.update_total_exposure_time(row)
            elif col == 5:
                self.model.experiment_setups[row].omega_step = value
                self.update_total_exposure_time(row)
            elif col == 6:
                self.model.experiment_setups[row].time_per_step = value
                self.update_total_exposure_time(row)
            elif col == 7:
                step_time = self.model.experiment_setups[row].get_step_exposure_time(value)
                step_exposure_time_item = self.widget.setup_table.item(row, 6)
                step_exposure_time_item.setText(str(step_time))
                self.model.experiment_setups[row].time_per_step = step_time

        self.widget.setup_table.blockSignals(False)
        self.widget.setup_table.resizeColumnsToContents()
        print(self.model.experiment_setups[row])

    def update_total_exposure_time(self, row):
        total_exposure_time_item = self.widget.setup_table.item(row, 7)
        total_exposure_time_item.setText(str(self.model.experiment_setups[row].get_total_exposure_time()))

    def sample_points_table_cell_changed(self, row, col):
        label_item = self.widget.sample_points_table.item(row, col)
        value = str(label_item.text())
        self.widget.sample_points_table.blockSignals(True)
        if col == 0:
            if not self.model.sample_name_existent(value):
                self.model.sample_points[row].name = str(value)
            else:
                self.create_name_existent_msg('Sample')
                name_item = self.widget.sample_points_table.item(row, 0)
                name_item.setText(self.model.sample_points[row].name)
        elif col == 1:
            self.model.sample_points[row].x = float(value)
        elif col == 2:
            self.model.sample_points[row].y = float(value)
        elif col == 3:
            self.model.sample_points[row].z = float(value)
        self.widget.sample_points_table.blockSignals(False)
        self.widget.sample_points_table.resizeColumnsToContents()

        print(self.model.sample_points[row])

    def move_sample_btn_clicked(self, ind):
        x, y, z = self.widget.get_sample_point_values(ind)
        move_to_sample_pos(x, y, z)

    def set_sample_btn_clicked(self, ind):
        x, y, z = self.get_current_sample_position()
        self.model.sample_points[ind].set_position(x, y, z)
        self.widget.set_sample_point_values(ind, x, y, z)

    def step_cb_status_changed(self, row_ind, exp_ind, state):
        cur_ind = self.widget.get_selected_sample_point()
        if row_ind in cur_ind:
            for ind in cur_ind:
                self.model.sample_points[ind].set_perform_step_scan_setup(exp_ind, state)
            self.widget.recreate_sample_point_checkboxes(self.model.get_experiment_state())
        else:
            self.model.sample_points[row_ind].set_perform_step_scan_setup(exp_ind, state)

    def wide_cb_status_changed(self, row_ind, exp_ind, state):
        cur_ind = self.widget.get_selected_sample_point()
        if row_ind in cur_ind:
            for ind in cur_ind:
                self.model.sample_points[ind].set_perform_wide_scan_setup(exp_ind, state)
            self.widget.recreate_sample_point_checkboxes(self.model.get_experiment_state())
        else:
            self.model.sample_points[row_ind].set_perform_wide_scan_setup(exp_ind, state)

    def basename_txt_changed(self):
        self.basename = str(self.widget.filename_txt.text())
        self.set_example_lbl()

    def filepath_txt_changed(self):
        self.filepath = str(self.widget.filepath_txt.text())
        self.set_example_lbl()

    def set_example_lbl(self):
        example_str = self.filepath + '/' + self.basename + '_' + 'S1_P1_E1_s_001'
        self.widget.example_filename_lbl.setText(example_str)

    def collect_data(self):
        # check if the current file path exists
        if self.check_filepath_exists() is False:
            self.show_error_message_box('The folder you specified does not exist. '
                                        'Please enter a valid path for saving the collected images!')
            return
        # check if all motor positions are in a correct position
        if self.check_conditions() is False:
            self.show_error_message_box('Please Move mirrors and microscope in the right positions!')
            return

        # check if sample position are not very far away from the current position (in case users forgot to update
        # positions....) maximum value is right now set to 200um distance
        if self.check_sample_point_distances() is False:
            reply = self.show_continue_abort_message_box(
                'Some measurement points are more than 200um away from the current sample ' +
                'position.<br> Do you want to continue?!')
            if reply == QtGui.QMessageBox.Abort:
                return

        # save current state to be able to restore after the measurement when the checkboxes are selected.
        previous_filepath, previous_filename, previous_filenumber = self.get_filename_info()
        previous_exposure_time = caget(epics_config['detector_control']+':AcquireTime')
        previous_detector_pos_x = caget(epics_config['detector_position_x'])
        previous_detector_pos_z = caget(epics_config['detector_position_z'])
        previous_omega_pos = caget(epics_config['sample_position_omega'])
        sample_x, sample_y, sample_z = self.get_current_sample_position()

        # prepare for for abortion of the collection procedure
        self.abort_collection = False
        self.widget.collect_btn.setText('Abort')
        self.widget.collect_btn.clicked.disconnect(self.collect_data)
        self.widget.collect_btn.clicked.connect(self.abort_data_collection)
        self.widget.status_txt.clear()
        QtGui.QApplication.processEvents()

        for exp_ind, experiment in enumerate(self.model.experiment_setups):
            for sample_point in self.model.sample_points:
                if sample_point.perform_wide_scan_for_setup[exp_ind]:
                    if self.widget.rename_files_cb.isChecked():
                        point_number = str(self.widget.point_txt.text())
                        filename = self.basename + '_' + sample_point.name + '_P' + point_number + '_' + \
                                   experiment.name + '_w'
                        print(filename)
                        caput(epics_config['detector_file']+':FilePath', str(self.filepath))
                        caput(epics_config['detector_file']+':FileName', str(filename))
                        caput(epics_config['detector_file']+':FileNumber', 1)
                    logger.info("Performing wide scan for:\n\t\t{}\n\t\t{}".format(sample_point, experiment))
                    exposure_time = abs(experiment.omega_end - experiment.omega_start) / experiment.omega_step * \
                                    experiment.time_per_step

                    collect_wide_data_thread = Thread(target=collect_wide_data,
                                                      kwargs={"detector_position_x": experiment.detector_pos_x,
                                                              "detector_position_z": experiment.detector_pos_z,
                                                              "omega_start": experiment.omega_start,
                                                              "omega_end": experiment.omega_end,
                                                              "exposure_time": abs(exposure_time),
                                                              "x": sample_point.x,
                                                              "y": sample_point.y,
                                                              "z": sample_point.z
                                                              })
                    collect_wide_data_thread.start()

                    while collect_wide_data_thread.isAlive():
                        QtGui.QApplication.processEvents()
                        time.sleep(.2)

                        # collect_wide_data(detector_position_x=experiment.detector_pos_x,
                        # detector_position_z=experiment.detector_pos_z,
                        # omega_start=experiment.omega_start,
                        # omega_end=experiment.omega_end,
                        # exposure_time=abs(exposure_time),
                        # x=sample_point.x,
                        #                   y=sample_point.y,
                        #                   z=sample_point.z,
                        #                   epics_config=epics_config)

                if not self.check_if_aborted():
                    break

                if sample_point.perform_step_scan_for_setup[exp_ind]:
                    if self.widget.rename_files_cb.isChecked():
                        point_number = str(self.widget.point_txt.text())
                        filename = self.basename + '_' + sample_point.name + '_P' + point_number + '_' + \
                                   experiment.name + '_s'
                        print filename
                    caput(epics_config['detector_file']+':FilePath', str(self.filepath))
                    caput(epics_config['detector_file']+':FileName', str(filename))
                    caput(epics_config['detector_file']+':FileNumber', 1)
                    logger.info("Performing step scan for:\n\t\t{}\n\t\t{}".format(sample_point, experiment))

                    collect_step_data_thread = Thread(target=collect_step_data,
                                                      kwargs={"detector_position_x": experiment.detector_pos_x,
                                                              "detector_position_z": experiment.detector_pos_z,
                                                              "omega_start": experiment.omega_start,
                                                              "omega_end": experiment.omega_end,
                                                              "omega_step": experiment.omega_step,
                                                              "exposure_time": experiment.time_per_step,
                                                              "x": sample_point.x,
                                                              "y": sample_point.y,
                                                              "z": sample_point.z,
                                                              "callback_fcn": self.check_if_aborted})
                    collect_step_data_thread.start()

                    while collect_step_data_thread.isAlive():
                        QtGui.QApplication.processEvents()
                        time.sleep(0.2)

                if not self.check_if_aborted():
                    break
        caput(epics_config['detector_control']+':AcquireTime', previous_exposure_time)

        # move to previous detector position:
        if self.widget.reset_detector_position_cb.isChecked():
            caput(epics_config['detector_position_x'], previous_detector_pos_x, wait=True, timeout=300)
            caput(epics_config['detector_position_z'], previous_detector_pos_z, wait=True, timeout=300)

        # move to previous sample position
        if self.widget.reset_sample_position_cb.isChecked():
            caput(epics_config['sample_position_omega'], previous_omega_pos)
            move_to_sample_pos(sample_x, sample_y, sample_z)

        caput(epics_config['detector_control'] + ':ShutterMode', 1)  # enable epics PV shutter mode

        if self.widget.rename_files_cb.isChecked():
            self.increase_point_number()

        if self.widget.rename_after_cb.isChecked():
            caput(epics_config['detector_file']+':FilePath', previous_filepath)
            caput(epics_config['detector_file']+':FileName', previous_filename)
            if self.widget.rename_files_cb.isChecked():
                caput(epics_config['detector_file']+':FileNumber', previous_filenumber)

        # reset the state of the gui:
        self.widget.collect_btn.setText('Collect')
        self.widget.collect_btn.clicked.connect(self.collect_data)
        self.widget.collect_btn.clicked.disconnect(self.abort_data_collection)

    def abort_data_collection(self):
        self.abort_collection = True

    def check_if_aborted(self):
        # QtGui.QApplication.processEvents()
        return not self.abort_collection

    def increase_point_number(self):
        cur_point_number = int(str(self.widget.point_txt.text()))
        self.widget.point_txt.setText(str(cur_point_number + 1))

    def estimate_collection_time(self, epics_config):
        total_time = 0
        det_x_speed = caget(epics_config['detector_position_x'] + '.VELO')
        det_z_speed = caget(epics_config['detector_position_z'] + '.VELO')
        det_x_pos = caget(epics_config['detector_position_x'])
        det_z_pos = caget(epics_config['detector_position_z'])

        for exp_ind, experiment in enumerate(self.model.experiment_setups):
            exp_collection = False
            for sample_point in self.model.sample_points:
                if sample_point.perform_wide_scan_for_setup[exp_ind]:
                    exposure_time = abs(experiment.omega_end - experiment.omega_start) / experiment.omega_step * \
                                    experiment.time_per_step
                    total_time += exposure_time
                    exp_collection = True
                if sample_point.perform_step_scan_for_setup[exp_ind]:
                    print("Performing step scan for {}, with setup {}".format(sample_point, experiment))
                    number_of_steps = abs(experiment.omega_end - experiment.omega_start) / experiment.omega_step
                    exposure_time = number_of_steps * (4 + experiment.time_per_step)
                    total_time += exposure_time
                    exp_collection = True
                if exp_collection:
                    det_x_move_time = abs(experiment.detector_pos_x - det_x_pos) / float(det_x_speed)
                    det_y_move_time = abs(experiment.detector_pos_z - det_z_pos) / float(det_z_speed)
                    total_time += det_x_move_time + det_y_move_time
                    det_x_pos = experiment.detector_pos_x
                    det_z_pos = experiment.detector_pos_z
        return total_time


    @staticmethod
    def create_name_existent_msg(name_type):
        msg_box = QtGui.QMessageBox()
        msg_box.setWindowFlags(QtCore.Qt.Tool)
        msg_box.setText('{} name already exists.'.format(name_type))
        msg_box.setIcon(QtGui.QMessageBox.Critical)
        msg_box.setWindowTitle('Error')
        msg_box.setStandardButtons(QtGui.QMessageBox.Ok)
        msg_box.setDefaultButton(QtGui.QMessageBox.Ok)
        msg_box.exec_()

    @staticmethod
    def get_current_sample_position():
        try:
            x = float("{:.4g}".format(caget(epics_config['sample_position_x'])))
            y = float("{:.4g}".format(caget(epics_config['sample_position_y'])))
            z = float("{:.4g}".format(caget(epics_config['sample_position_z'])))
        except epics.ca.ChannelAccessException:
            x = y = z = 0
        return x, y, z

    @staticmethod
    def get_current_setup():
        """
        Checks epics for the current setup setting.
        returns: detector position, omega, exposure_time
        :return: float, float, float
        """
        try:
            detector_pos_x = float("{:g}".format(caget(epics_config['detector_position_x'])))
            detector_pos_z = float("{:g}".format(caget(epics_config['detector_position_z'])))
            omega = float("{:g}".format(caget(epics_config['sample_position_omega'])))
            exposure_time = float("{:g}".format(caget(epics_config['detector_control'] +':AcquireTime')))
        except epics.ca.ChannelAccessException:
            detector_pos_x = 0
            detector_pos_z = 49
            omega = -90
            exposure_time = 0.5
        return detector_pos_x, detector_pos_z, omega, exposure_time

    @staticmethod
    def get_filename_info():
        path = caget(epics_config['detector_file']+':FilePath', as_string=True)
        print(path)
        filename = caget(epics_config['detector_file']+':FileName', as_string=True)
        file_number = caget(epics_config['detector_file']+':FileNumber')
        if path is None:
            path = ''
            filename = 'test'
            file_number = 0
        return path, filename, file_number

    def check_filepath_exists(self):
        cur_epics_filepath = caget(epics_config['detector_file']+':FilePath', as_string=True)
        print self.filepath
        caput(epics_config['detector_file']+'1:FilePath', self.filepath, wait=True)
        exists = caget(epics_config['detector_file']+':FilePathExists_RBV')

        caput(epics_config['detector_file']+':FilePath', cur_epics_filepath)
        return exists == 1

    @staticmethod
    def check_conditions():
        if int(caget('13IDD:m24.RBV')) > -105:
            return False
        elif int(caget('13IDD:m23.RBV')) > -105:
            return False
        elif int(caget('13IDD:m67.RBV')) > -65:
            return False
        return True

    def check_sample_point_distances(self):
        pos_x, pos_y, pos_z = self.get_current_sample_position()
        largest_distance = self.model.get_largest_largest_collecting_sample_point_distance_to(pos_x, pos_y, pos_z)

        return largest_distance < 0.2

    @staticmethod
    def show_error_message_box(msg):
        msg_box = QtGui.QMessageBox()
        msg_box.setWindowFlags(QtCore.Qt.Tool)
        msg_box.setText(msg)
        msg_box.setIcon(QtGui.QMessageBox.Critical)
        msg_box.setWindowTitle('Error')
        msg_box.setStandardButtons(QtGui.QMessageBox.Ok)
        msg_box.setDefaultButton(QtGui.QMessageBox.Ok)
        msg_box.exec_()

    @staticmethod
    def show_continue_abort_message_box(msg):
        msg_box = QtGui.QMessageBox()
        msg_box.setWindowFlags(QtCore.Qt.Tool)
        msg_box.setText("<p align='center' style='font-size:20px' >{}</p>".format(msg))
        msg_box.setIcon(QtGui.QMessageBox.Critical)
        msg_box.setWindowTitle('Continue?')
        msg_box.setStandardButtons(QtGui.QMessageBox.Yes | QtGui.QMessageBox.Abort)
        msg_box.setDefaultButton(QtGui.QMessageBox.Abort)
        msg_box.exec_()
        return msg_box.result()


class InfoLoggingHandler(logging.Handler):
    def __init__(self, return_function):
        super(InfoLoggingHandler, self).__init__()
        self.return_function = return_function

    def emit(self, log_record):
        message = str(log_record.getMessage())
        self.return_function(time.strftime('%X') + ': ' + message)


def test_dummy_function(iterations):
    print "the dummy function"
    for n in range(iterations):
        time.sleep(0.5)
        print("{} iterations".format(n + 1))


class ThreadRunner():
    def __init__(self, fcn, args):
        self.worker_thread = WorkerThread(fcn, args)
        self.worker_finished = False

        self.worker_thread.finished.connect(self.update_status)
        self.worker_thread.terminated.connect(self.update_status)

    def run(self):
        print "running something"
        self.worker_finished = False
        self.worker_thread.start()

        while not self.worker_finished:
            QtGui.QApplication.processEvents()
            time.sleep(0.1)

    def update_status(self):
        print "updating status"
        self.worker_finished = True


class WorkerThread(QtCore.QThread):
    def __init__(self, func, args):
        super(WorkerThread, self).__init__()
        self.func = func
        self.args = args

    def run(self):
        self.func(*self.args)
