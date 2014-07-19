__author__ = 'DAC_User'
from epics import caget



print( int(caget('13IDD:m24.RBV')))