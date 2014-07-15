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


from views.main import MainView
from models import MainData


class MainController(object):
    def __init__(self):
        self.main_view = MainView(__version__)
        self.main_view.show()
        self.data = MainData()
        self.connect_buttons()

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

    def add_experiment_setup_btn_clicked(self):
        detector_pos, omega, exposure_time = self.get_current_setup()
        self.main_view.add_experiment_setup(detector_pos, omega - 1, omega + 1, 0.1, exposure_time)
        self.data.add_experiment_setup(detector_pos, omega - 1, omega + 1, 0.1, exposure_time)

    def delete_experiment_setup_btn_clicked(self):
        cur_ind = self.main_view.get_selected_experiment_setup()
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

    @staticmethod
    def get_current_sample_position():
        x = caget(pv_names['sample_position_x'])
        y = caget(pv_names['sample_position_y'])
        z = caget(pv_names['sample_position_z'])
        return x, y, z

    @staticmethod
    def get_current_setup():
        """
        Checks epics for the current setup setting.
        returns: detector position, omega, exposure_time
        :return: float, float, float
        """
        detector_pos = caget(pv_names['detector_position'])
        omega = caget(pv_names['sample_position_omega'])
        exposure_time = caget(pv_names['detector'] + ':AcquireTime')
        return detector_pos, omega, exposure_time

