from epics import caput, caget
import time
from .config import epics_config


def caput_pil3(pv, value, wait=True):
    t0 = time.time()
    caput(pv, value, wait=wait)

    while time.time() - t0 < 20.0:
        time.sleep(0.02)
        if 'OK' in caget(epics_config['status_message'], as_string=True):
            return True
    return False
