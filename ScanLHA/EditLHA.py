#!/usr/bin/env python3
"""
Interactively load/edit/save/plot HDF files.
"""
from pandas import read_hdf, DataFrame # noqa: F401
from IPython import embed
from glob import glob
import os
from matplotlib import pyplot as plt # noqa: F401
from argparse import ArgumentParser

def Edit():
    """
    Usage: EditLHA [-h] h5file.h5 [h5file.h5 ...]

    Loads the hdf files and saves them into the variable DATA.

    An IPython session with imported matplotlib.pyplot is started.
    """
    parser = ArgumentParser(description='Interactively load/edit/save/plot HDF files.')
    parser.add_argument('files', metavar='h5file.h5', type=str, nargs='+',
            help='HDF file(s) to edit.')
    args = parser.parse_args()

    HDFFILES = [ k for f in args.files for k in glob(f) ]

    DATA = {}
    header = "Your data files are stored in 'DATA'"
    for f in HDFFILES:
        print('Reading %s ...' % f)
        DATA[f] = read_hdf(f)

    if len(DATA) == 1:
        HDFFILE = HDFFILES[0]
        DATA = DATA[HDFFILE]
    else:
        header += "and accessible via DATA['path/to/filename.h5']"

    if len(DATA) == 0:
        print('No valid data files specified.\n')
    else:
        HDFDIR = os.path.dirname(os.path.abspath(HDFFILES[0])) + '/'
        print('Changing working directory to {}.\n'.format(HDFDIR))
        os.chdir(HDFDIR)
    embed(header=header)
