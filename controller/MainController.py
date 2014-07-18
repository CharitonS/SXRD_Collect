__author__ = 'DAC_User'
__version__ = 0.1

import time

from epics import caget, caput
import epics
from PyQt4 import QtGui

pv_names = {'detector_position': '13IDD:m8',
            'detector': '13MARCCD2:cam1',
            'sample_position_x': '13IDD:m81',
            'sample_position_y': '13IDD:m83',
            'sample_position_z': '13IDD:m82',
            'sample_position_omega': '13IDD:m96',
}

from views.MainView import MainView
from models import MainData
from measurement import move_to_sample_pos, collect_step_data, collect_wide_data


class MainController(object):
    def __init__(self):
        self.main_view = MainView(__version__)
        self.main_view.show()
        self.data = MainData()
        self.connect_buttons()
        self.connect_tables()
        self.connect_txt()
        self.populate_filename()

    def connect_buttons(self):
        self.main_view.add_setup_btn.clicked.connect(self.add_experiment_setup_btn_clicked)
        self.main_view.delete_setup_btn.clicked.connect(self.delete_experiment_setup_btn_clicked)
        self.main_view.clear_setup_btn.clicked.connect(self.clear_experiment_setup_btn_clicked)

        self.main_view.add_sample_btn.clicked.connect(self.add_sample_point_btn_clicked)
        self.main_view.delete_sample_btn.clicked.connect(self.delete_sample_point_btn_clicked)
        self.main_view.clear_sample_btn.clicked.connect(self.clear_sample_point_btn_clicked)

        self.main_view.add_standard_btn.clicked.connect(self.add_standard_btn_clicked)
        self.main_view.delete_standard_btn.clicked.connect(self.delete_standard_btn_clicked)
        self.main_view.clear_standard_btn.clicked.connect(self.clear_standard_btn_clicked)

        self.main_view.collect_btn.clicked.connect(self.collect_data)

    def connect_tables(self):
        self.main_view.setup_table.cellChanged.connect(self.setup_table_cell_changed)
        self.main_view.sample_points_table.cellChanged.connect(self.sample_points_table_cell_changed)

        self.main_view.move_sample_btn_clicked.connect(self.move_sample_btn_clicked)
        self.main_view.set_sample_btn_clicked.connect(self.set_sample_btn_clicked)

        self.main_view.step_cb_status_changed.connect(self.step_cb_status_changed)
        self.main_view.wide_cb_status_changed.connect(self.wide_cb_status_changed)

    def connect_txt(self):
        self.main_view.filename_txt.editingFinished.connect(self.basename_txt_changed)
        self.main_view.filepath_txt.editingFinished.connect(self.filepath_txt_changed)

    def populate_filename(self):
        self.prev_filepath, self.prev_filename, self.prev_file_number = self.get_filename_info()

        self.filepath = self.prev_filepath
        self.basename = self.prev_filename

        self.main_view.filename_txt.setText(self.prev_filename)
        self.main_view.filepath_txt.setText(self.prev_filepath)

        self.set_example_lbl()


    def add_experiment_setup_btn_clicked(self):
        detector_pos, omega, exposure_time = self.get_current_setup()
        self.main_view.add_experiment_setup(detector_pos, omega - 1, omega + 1, 0.1, exposure_time)
        self.data.add_experiment_setup(detector_pos, omega - 1, omega + 1, 0.1, exposure_time)

    def delete_experiment_setup_btn_clicked(self):
        cur_ind = self.main_view.get_selected_experiment_setup()
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
                self.main_view.delete_experiment_setup(ind)
                self.data.delete_experiment_setup(ind)
            self.main_view.recreate_sample_point_checkboxes(self.data.get_experiment_state())

    def clear_experiment_setup_btn_clicked(self):
        self.main_view.clear_experiment_setups()
        self.data.clear_experiment_setups()

    def add_sample_point_btn_clicked(self):
        x, y, z = self.get_current_sample_position()
        num = len(self.data.sample_points)
        self.main_view.add_sample_point('S{}'.format(num + 1), x, y, z)
        self.data.add_sample_point('S{}'.format(num + 1), x, y, z)

    def delete_sample_point_btn_clicked(self):
        cur_ind = self.main_view.get_selected_sample_point()
        cur_ind.sort()
        cur_ind = cur_ind[::-1]
        for ind in cur_ind:
            self.main_view.delete_sample_point(ind)
            self.data.delete_sample_point(ind)

    def clear_sample_point_btn_clicked(self):
        self.main_view.clear_sample_points()
        self.data.clear_sample_points()

    def add_standard_btn_clicked(self):
        pass

    def delete_standard_btn_clicked(self):
        pass

    def clear_standard_btn_clicked(self):
        pass

    def setup_table_cell_changed(self, row, col):
        label_item = self.main_view.setup_table.item(row, col)
        value = float(str(label_item.text()))
        if col == 0:
            self.data.experiment_setups[row].detector_pos = value
        elif col == 1:
            self.data.experiment_setups[row].omega_start = value
        elif col == 2:
            self.data.experiment_setups[row].omega_end = value
        elif col == 3:
            self.data.experiment_setups[row].omega_step = value
        elif col == 4:
            self.data.experiment_setups[row].time_per_step = value
        self.main_view.setup_table.resizeColumnsToContents()

        print(self.data.experiment_setups[row])

    def sample_points_table_cell_changed(self, row, col):
        label_item = self.main_view.sample_points_table.item(row, col)
        value = str(label_item.text())
        if col == 0:
            self.data.sample_points[row].name = value
        elif col == 1:
            self.data.sample_points[row].x = float(value)
        elif col == 2:
            self.data.sample_points[row].y = float(value)
        elif col == 3:
            self.data.sample_points[row].z = float(value)
        self.main_view.sample_points_table.resizeColumnsToContents()

        print(self.data.sample_points[row])

    def move_sample_btn_clicked(self, ind):
        x, y, z = self.main_view.get_sample_point_values(ind)
        move_to_sample_pos(x, y, z, pv_names)

    def set_sample_btn_clicked(self, ind):
        x, y, z = self.get_current_sample_position()
        self.data.sample_points[ind].set_position(x, y, z)
        self.main_view.set_sample_point_values(ind, x, y, z)

    def step_cb_status_changed(self, row_ind, exp_ind, state):
        cur_ind = self.main_view.get_selected_sample_point()
        if row_ind in cur_ind:
            for ind in cur_ind:
                self.data.sample_points[ind].set_perform_step_scan_setup(exp_ind, state)
            self.main_view.recreate_sample_point_checkboxes(self.data.get_experiment_state())
        else:
            self.data.sample_points[row_ind].set_perform_step_scan_setup(exp_ind, state)

    def wide_cb_status_changed(self, row_ind, exp_ind, state):
        cur_ind = self.main_view.get_selected_sample_point()
        if row_ind in cur_ind:
            for ind in cur_ind:
                self.data.sample_points[ind].set_perform_wide_scan_setup(exp_ind, state)
            self.main_view.recreate_sample_point_checkboxes(self.data.get_experiment_state())
        else:
            self.data.sample_points[row_ind].set_perform_wide_scan_setup(exp_ind, state)

    def basename_txt_changed(self):
        self.basename = self.main_view.filename_txt.text()
        self.set_example_lbl()

    def filepath_txt_changed(self):
        self.filepath = self.main_view.filepath_txt.text()
        self.set_example_lbl()

    def set_example_lbl(self):
        example_str = self.filepath + '/' + self.basename + '_' + 'S1_P1_E1_s_001'
        self.main_view.example_filename_lbl.setText(example_str)

    def collect_data(self):
        previous_filepath, previous_filename, previous_filenumber = self.get_filename_info()
        previous_exposure_time = caget(pv_names['detector'] + ':AcquireTime')
        previous_detector_pos = caget(pv_names['detector_position'])

        for exp_ind, experiment in enumerate(self.data.experiment_setups):
            for sample_point in self.data.sample_points:
                if sample_point.perform_wide_scan_for_setup[exp_ind]:
                    if self.main_view.rename_files_cb.isChecked():
                        point_number = str(self.main_view.point_txt.text())
                        filename = self.basename + '_' + sample_point.name + '_P' + point_number + '_E' + str(
                            exp_ind + 1) + '_w'
                        caput(pv_names['detector'] + ':FilePath', self.filepath)
                        caput(pv_names['detector'] + ':FileName', filename)
                        caput(pv_names['detector'] + ':FileNumber', 1)
                    print("Performing wide scan for {}, with setup {}".format(sample_point, experiment))
                    exposure_time = abs(experiment.omega_end - experiment.omega_start) / experiment.omega_step * \
                                    experiment.time_per_step
                    collect_wide_data(detector_position=experiment.detector_pos,
                                      omega_start=experiment.omega_start,
                                      omega_end=experiment.omega_end,
                                      exposure_time=exposure_time,
                                      x=sample_point.x,
                                      y=sample_point.y,
                                      z=sample_point.z,
                                      pv_names=pv_names)
                if sample_point.perform_step_scan_for_setup[exp_ind]:
                    if self.main_view.rename_files_cb.isChecked():
                        point_number = str(self.main_view.point_txt.text())
                        filename = self.basename + '_' + sample_point.name + '_P' + point_number + '_E' + str(
                            exp_ind + 1) + '_s'
                        caput(pv_names['detector'] + ':FilePath', self.filepath)
                        caput(pv_names['detector'] + ':FileName', filename)
                        caput(pv_names['detector'] + ':FileNumber', 1)
                    print("Performing step scan for {}, with setup {}".format(sample_point, experiment))
                    collect_step_data(detector_position=experiment.detector_pos,
                                      omega_start=experiment.omega_start,
                                      omega_end=experiment.omega_end,
                                      omega_step=experiment.omega_step,
                                      exposure_time=experiment.time_per_step,
                                      x=sample_point.x,
                                      y=sample_point.y,
                                      z=sample_point.z,
                                      pv_names=pv_names)

        caput(pv_names['detector'] + ':AcquireTime', previous_exposure_time)
        self.increase_point_number()

        #move to previous detector position:
        caput(pv_names['detector_position'], previous_detector_pos, wait=True, timeout=300)

        if self.main_view.rename_after_cb.isChecked():
            caput(pv_names['detector'] + ':FilePath', previous_filepath)
            caput(pv_names['detector'] + ':FileName', previous_filename)
            if self.main_view.rename_files_cb.isChecked():
                caput(pv_names['detector'] + ':FileNumber', previous_filenumber)

    def increase_point_number(self):
        cur_point_number = int(str(self.main_view.point_txt.text()))
        self.main_view.point_txt.setText(str(cur_point_number + 1))

    @staticmethod
    def get_current_sample_position():
        try:
            x = float("{:.4g}".format(caget(pv_names['sample_position_x'])))
            y = float("{:.4g}".format(caget(pv_names['sample_position_y'])))
            z = float("{:.4g}".format(caget(pv_names['sample_position_z'])))
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
            detector_pos = float("{:g}".format(caget(pv_names['detector_position'])))
            omega = float("{:g}".format(caget(pv_names['sample_position_omega'])))
            exposure_time = float("{:g}".format(caget(pv_names['detector'] + ':AcquireTime')))
        except epics.ca.ChannelAccessException:
            detector_pos = -333
            omega = -90
            exposure_time = 0.5
        return detector_pos, omega, exposure_time

    @staticmethod
    def get_filename_info():
        try:
            path = caget(pv_names['detector'] + ':FilePath', as_string=True)
            print(path)
            filename = caget(pv_names['detector'] + ':FileName', as_string=True)
            file_number = caget(pv_names['detector'] + ':FileNumber')
        except epics.ca.ChannelAccessException:
            path = ''
            filename = 'test'
            file_number = 0
        return path, filename, file_number

