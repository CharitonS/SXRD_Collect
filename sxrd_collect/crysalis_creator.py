import os
import shutil
import numpy as np
from cryio import cbfimage, crysalis, esperanto


def make_directory(filepath, basename):

    new_directory = filepath + '\\' + basename + '_crys'
    if os.path.isdir(new_directory):
        shutil.rmtree(new_directory)
    os.makedirs(new_directory)


def padarray(array):
    """
    This funcion is needed for making square images out of rectangular. Needed for esperanto format
    """
    a = np.empty((1043, 31), dtype=array.dtype)
    b = np.empty((1043, 32), dtype=array.dtype)
    a.fill(-1)
    b.fill(-1)

    array = np.hstack((array, a))
    array = np.hstack((b, array))

    c = np.empty((1,1044), dtype=array.dtype)
    c.fill(-1)
    array = np.vstack((array,c))

    return array


def transform_cbf_to_esperanto(filepath, basename, esperanto_scan_info):

    new_directory = filepath + '\\' + basename + '_crys'

    for i in range(esperanto_scan_info['count']):

        cbf_file = filepath + '\\'+basename + '_{0:05d}'.format(i + 1) + '.cbf'
        esp_file = new_directory +'\\' +  basename + '_1_'  + str(i + 1) + '.esperanto'

        image = cbfimage.CbfImage(cbf_file)

        array_trans = np.flip(image.array, 0)
        new_image_array = padarray(array_trans)

        rot = esperanto_scan_info
        rot['omega'] = rot['omega_start'] + rot['domega'] * i

        esp = esperanto.EsperantoImage()
        esp.save(esp_file, new_image_array, **rot)


def copy_set_ccd(filepath, basename, config):
    new_directory = filepath + '\\' + basename + '_crys'
    shutil.copy(config['set_file'], os.path.join(new_directory, basename+'.set'))
    shutil.copy(config['ccd_file'], os.path.join(new_directory, basename+'.ccd'))


def createCrysalis(scans, basename, filepath):

    new_directory = filepath + '\\' + basename + '_crys'

    runHeader = crysalis.RunHeader(basename.encode(), new_directory.encode(), 1)
    runname = os.path.join(new_directory, basename)
    runFile = []

    for omega_run in scans[0]:
        dscr = crysalis.RunDscr(0)
        dscr.axis = crysalis.SCAN_AXIS['OMEGA']
        dscr.kappa = omega_run['kappa']
        dscr.omegaphi = 0
        dscr.start = omega_run['omega_start']
        dscr.end = omega_run['omega_end']
        dscr.width = omega_run['domega']
        dscr.todo = dscr.done = omega_run['count']
        dscr.exposure = 1
        runFile.append(dscr)

    crysalis.saveRun(runname, runHeader, runFile)
    crysalis.saveCrysalisExpSettings(new_directory)


def create_par_file(filepath, basename, par_file):

    new_directory = filepath + '\\' + basename + '_crys'
    new_par = os.path.join(new_directory,basename+'.par')

    with open(new_par, 'w') as new_file:
        with open(par_file, 'r') as old_file:
            for line in old_file:
                if line.startswith("FILE CHIP"):
                    new_file.write("FILE CHIP" + basename + '.ccd')
                else:
                    new_file.write(line)