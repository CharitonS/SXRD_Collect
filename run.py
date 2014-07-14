__author__ = 'DAC_User'
import sys
from PyQt4 import QtGui

from controller.MainController import MainController



if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    controller = MainController()
    app.exec_()