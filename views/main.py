# from __future__ import absolute_import
__author__ = 'DAC_User'

from PyQt4 import QtGui, QtCore
from functools import partial
import sys

from UiFiles.mainUI import Ui_SXRDCollectWidget


class MainView(QtGui.QWidget, Ui_SXRDCollectWidget):
    set_sample_btn_clicked = QtCore.pyqtSignal(int)
    move_sample_btn_clicked = QtCore.pyqtSignal(int)

    def __init__(self):
        super(MainView, self).__init__()
        self.setupUi(self)

        self.delegate = TextDoubleDelegate(self)
        self.setup_table.setItemDelegate(self.delegate)

        self.standard_show_btn.clicked.connect(self.standard_show_btn_clicked)
        self.hide_standards()

    def add_experiment_setup(self, detector_pos, omega_start, omega_end, omega_step, exposure_time):
        new_row_ind = int(self.setup_table.rowCount())
        self.setup_table.setRowCount(new_row_ind + 1)

        detector_item = QtGui.QTableWidgetItem(str(detector_pos))
        detector_item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        omega_start_item = QtGui.QTableWidgetItem(str(omega_start))
        omega_start_item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        omega_end_item = QtGui.QTableWidgetItem(str(omega_end))
        omega_end_item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        omega_step_item = QtGui.QTableWidgetItem(str(omega_step))
        omega_step_item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        exposure_time_item = QtGui.QTableWidgetItem(str(exposure_time))
        exposure_time_item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.setup_table.setItem(new_row_ind, 0, detector_item)
        self.setup_table.setItem(new_row_ind, 1, omega_start_item)
        self.setup_table.setItem(new_row_ind, 2, omega_end_item)
        self.setup_table.setItem(new_row_ind, 3, omega_step_item)
        self.setup_table.setItem(new_row_ind, 4, exposure_time_item)

        self.setup_table.setVerticalHeaderItem(new_row_ind, QtGui.QTableWidgetItem('Exp{}'.format(new_row_ind + 1)))
        self.setup_table.resizeColumnsToContents()

        #update the sample_points_table_accordingly:
        self.sample_points_table.setColumnCount(7+new_row_ind)
        for sample_point_row in range(self.sample_points_table.rowCount()):
            self.create_sample_point_checkboxes(sample_point_row, new_row_ind)

        self.sample_points_table.setHorizontalHeaderItem(6+new_row_ind,
                                                         QtGui.QTableWidgetItem('Exp{}'.format(new_row_ind + 1)))
        self.sample_points_table.resizeColumnsToContents()

    def get_selected_experiment_setup(self):
        selected = self.setup_table.selectionModel().selectedRows()
        try:
            row = selected[0].row()
        except IndexError:
            row = -1
        return row

    def del_experiment_setup(self, row_ind):
        self.setup_table.blockSignals(True)
        self.setup_table.removeRow(row_ind)
        self.setup_table.blockSignals(False)

    def add_sample_point(self, name, x, y, z):
        new_row_ind = int(self.sample_points_table.rowCount())
        self.sample_points_table.setRowCount(new_row_ind + 1)

        name_item = QtGui.QTableWidgetItem(str(name))
        name_item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        x_pos_item = QtGui.QTableWidgetItem(str(x))
        x_pos_item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        y_pos_item = QtGui.QTableWidgetItem(str(y))
        y_pos_item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        z_pos_item = QtGui.QTableWidgetItem(str(z))
        z_pos_item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.sample_points_table.setItem(new_row_ind, 0, name_item)
        self.sample_points_table.setItem(new_row_ind, 1, x_pos_item)
        self.sample_points_table.setItem(new_row_ind, 2, y_pos_item)
        self.sample_points_table.setItem(new_row_ind, 3, z_pos_item)

        set_btn = QtGui.QPushButton('Set')
        set_btn.clicked.connect(partial(self.set_sample_btn_click, new_row_ind))
        self.sample_points_table.setCellWidget(new_row_ind, 4, set_btn)

        move_btn = QtGui.QPushButton('Move')
        move_btn.clicked.connect(partial(self.move_sample_btn_click, new_row_ind))
        self.sample_points_table.setCellWidget(new_row_ind, 5, move_btn)

        for exp_row in range(self.setup_table.rowCount()):
            self.create_sample_point_checkboxes(new_row_ind, exp_row)
        self.sample_points_table.resizeColumnsToContents()

    def create_sample_point_checkboxes(self, row_index, exp_index):
        exp_widget = QtGui.QWidget()
        step_cb = QtGui.QCheckBox('step')
        wide_cb = QtGui.QCheckBox('wide')
        exp_layout = QtGui.QHBoxLayout()
        exp_layout.addWidget(step_cb)
        exp_layout.addWidget(wide_cb)
        exp_widget.setLayout(exp_layout)
        self.sample_points_table.setCellWidget(row_index, exp_index+6, exp_widget)

    def get_selected_sample_point(self):
        selected = self.sample_points_table.selectionModel().selectedRows()
        try:
            row = selected[0].row()
        except IndexError:
            row = -1
        return row

    def del_sample_point(self, row_ind):
        self.sample_points_table.blockSignals(True)
        self.sample_points_table.removeRow(row_ind)
        self.sample_points_table.blockSignals(False)

    def set_sample_btn_click(self, index):
        self.set_sample_btn_clicked.emit(index)

    def move_sample_btn_click(self, index):
        self.move_sample_btn_clicked.emit(index)

    def standard_show_btn_clicked(self):
        if self.standard_show_btn.text() == '-':
            self.hide_standards()
        else:
            self.show_standards()

    def hide_standards(self):
        self.standard_show_btn.setText('+')
        self.standard_table.hide()
        self.add_standard_btn.hide()
        self.delete_standard_btn.hide()
        self.clear_standard_btn.hide()
        self.standard_footer_2.hide()

    def show_standards(self):
        self.standard_show_btn.setText('-')
        self.standard_table.show()
        self.add_standard_btn.show()
        self.delete_standard_btn.show()
        self.clear_standard_btn.show()
        self.standard_footer_2.show()


class TextDoubleDelegate(QtGui.QStyledItemDelegate):
    def __init__(self, parent):
        super(TextDoubleDelegate, self).__init__(parent)

    def createEditor(self, parent, _, __):
        self.editor = QtGui.QLineEdit(parent)
        self.editor.setFrame(False)
        self.editor.setValidator(QtGui.QDoubleValidator())
        self.editor.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        return self.editor

    def setEditorData(self, parent, index):
        value = index.model().data(index, QtCore.Qt.EditRole)
        self.editor.setText(str(value))

    def setModelData(self, parent, model, index):
        value = self.editor.text()
        model.setData(index, value, QtCore.Qt.EditRole)

    def updateEditorGeometry(self, editor, option, _):
        editor.setGeometry(option.rect)


if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    view = MainView()
    view.show()
    view.add_sample_point('lbaslfjag', 3, 2, 4)
    view.add_experiment_setup(-333, -100, -90, 0.5, 0.4)
    view.add_sample_point('huhu', 0, 4, 3)
    view.add_experiment_setup(-333, -100, -90, 0.2, 0.4)
    view.add_sample_point('lbaslfjag', 3, 2, 4)
    view.add_sample_point('lbaslfjag', 3, 2, 4)
    view.add_sample_point('lbaslfjag', 3, 2, 4)
    view.add_sample_point('lbaslfjag', 3, 2, 4)
    view.add_experiment_setup(-333, -100, -90, 0.2, 0.4)
    view.add_experiment_setup(-333, -100, -90, 0.2, 0.4)
    view.add_experiment_setup(-333, -100, -90, 0.2, 0.4)
    view.add_experiment_setup(-333, -100, -90, 0.2, 0.4)
    app.exec_()