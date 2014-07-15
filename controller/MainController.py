__author__ = 'DAC_User'
__version__ = 0.1

from epics import caget

pv_names = {'detector_position': '13IDD:m8',
            'detector': '13MARCCD2:cam1',
            'sample_position_x': '13IDD:m81',
            'sample_position_y': '13IDD:m83',
            'sample_position_z': '13IDD:m82',
            'sample_position_omega': '13IDD:m96',
}


from views.MainView import MainView
from models import MainData
from measurement import move_to_sample_pos


class MainController(object):
    def __init__(self):
        self.main_view = MainView(__version__)
        self.main_view.show()
        self.data = MainData()
        self.connect_buttons()
        self.connect_tables()

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

    def connect_tables(self):
        self.main_view.setup_table.cellChanged.connect(self.setup_table_cell_changed)
        self.main_view.sample_points_table.cellChanged.connect(self.sample_points_table_cell_changed)

        self.main_view.move_sample_btn_clicked.connect(self.move_sample_btn_clicked)
        self.main_view.set_sample_btn_clicked.connect(self.set_sample_btn_clicked)

    def add_experiment_setup_btn_clicked(self):
        detector_pos, omega, exposure_time = self.get_current_setup()
        self.main_view.add_experiment_setup(detector_pos, omega - 1, omega + 1, 0.1, exposure_time)
        self.data.add_experiment_setup(detector_pos, omega - 1, omega + 1, 0.1, exposure_time)

    def delete_experiment_setup_btn_clicked(self):
        cur_ind = self.main_view.get_selected_experiment_setup()
        cur_ind.sort()
        cur_ind = cur_ind[::-1]
        for ind in cur_ind:
            self.main_view.delete_experiment_setup(ind)
            self.data.delete_experiment_setup(ind)

    def clear_experiment_setup_btn_clicked(self):
        self.main_view.clear_experiment_setups()
        self.data.clear_experiment_setups()

    def add_sample_point_btn_clicked(self):
        x, y, z = self.get_current_sample_position()
        self.main_view.add_sample_point('P', x, y, z)
        self.data.add_sample_point('P', x, y, z)

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
        if col==0:
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
        if col==0:
            self.data.sample_points[row].name = value
        elif col == 1:
            self.data.sample_points[row].x = float(value)
        elif col == 2:
            self.data.sample_points[row].y = float(value)
        elif col == 3:
            self.data.sample_points[row].z = float(value)

        print(self.data.sample_points[row])

    def move_sample_btn_clicked(self, ind):
        x,y,z = self.main_view.get_sample_point_values(ind)
        move_to_sample_pos(x,y,z, pv_names)

    def set_sample_btn_clicked(self, ind):
        x,y,z = self.get_current_sample_position()
        self.data.sample_points[ind].set_position(x,y,z)
        self.main_view.set_sample_point_values(ind, x,y,z)

    @staticmethod
    def get_current_sample_position():
        x = float("{:.4g}".format(caget(pv_names['sample_position_x'])))
        y = float("{:.4g}".format(caget(pv_names['sample_position_y'])))
        z = float("{:.4g}".format(caget(pv_names['sample_position_z'])))
        return x, y, z

    @staticmethod
    def get_current_setup():
        """
        Checks epics for the current setup setting.
        returns: detector position, omega, exposure_time
        :return: float, float, float
        """
        detector_pos = float("{:g}".format(caget(pv_names['detector_position'])))
        omega = float("{:g}".format(caget(pv_names['sample_position_omega'])))
        exposure_time = float("{:g}".format(caget(pv_names['detector'] + ':AcquireTime')))
        return detector_pos, omega, exposure_time

