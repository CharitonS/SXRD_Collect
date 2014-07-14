__author__ = 'DAC_User'
__version__ = 0.1

from views.main import MainView
from epics import caget

pv_names = {'detector_position': '13IDD:m8',
            'detector': '13MARCCD2:cam1',
            'sample_position_x': '13IDD:m81',
            'sample_position_y': '13IDD:m83',
            'sample_position_z': '13IDD:m82',
            'sample_position_omega': '13IDD:m96',
}


class MainController(object):
    def __init__(self):
        self.main_view = MainView(__version__)
        self.main_view.show()
        self.connect_buttons()

    def connect_buttons(self):
        self.main_view.add_setup_btn.clicked.connect(self.add_setup_btn_clicked)
        self.main_view.delete_setup_btn.clicked.connect(self.delete_setup_btn_clicked)
        self.main_view.clear_setup_btn.clicked.connect(self.clear_setup_btn_clicked)

        self.main_view.add_sample_btn.clicked.connect(self.add_sample_btn_clicked)
        self.main_view.delete_sample_btn.clicked.connect(self.delete_sample_btn_clicked)
        self.main_view.clear_sample_btn.clicked.connect(self.clear_sample_btn_clicked)

        self.main_view.add_standard_btn.clicked.connect(self.add_standard_btn_clicked)
        self.main_view.delete_standard_btn.clicked.connect(self.delete_standard_btn_clicked)
        self.main_view.clear_standard_btn.clicked.connect(self.clear_standard_btn_clicked)

    def add_setup_btn_clicked(self):
        detector_pos, omega, exposure_time = self.get_current_setup()
        self.main_view.add_experiment_setup(detector_pos, omega - 1, omega + 1, 0.1, exposure_time)

    def delete_setup_btn_clicked(self):
        pass

    def clear_setup_btn_clicked(self):
        pass

    def add_sample_btn_clicked(self):
        x, y, z = self.get_current_sample_position()
        self.main_view.add_sample_point('P', x, y, z)
        pass

    def delete_sample_btn_clicked(self):
        pass

    def clear_sample_btn_clicked(self):
        pass

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

