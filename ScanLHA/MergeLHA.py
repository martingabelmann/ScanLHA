#!/usr/bin/env python3
"""
Merges multiple HDF files into one file.
"""
from pandas import HDFStore, DataFrame
from glob import glob
import sys
from os import getenv
__pdoc__ = {}
__pdoc__['Merge'] = """
Merges multiple HDF files into one file.

Usage: MergeLHA mergedfile.h5 file1.h5 file2.h5 [...]

File names may be specified using patterns compatible with python.glob (e.g. '*.h5').

Note that it is not possible to merge different `ScanLHA.config.Config` instances i.e. the `Config`
instance of the first file is used.


The default H5 tree is 'results' (default of `ScanLHA.scan.Scan.save`).
For changing the path set the environment variable `export LHPATH='/yourpath'`.
"""

def Merge():
    if len(sys.argv) < 3:
        print('No valid filenames given!')
        print(__pdoc__['Merge'])
        sys.exit(1)

    infiles = [glob(f) for f in sys.argv[1:-1]]
    outfile = sys.argv[-1]

    LHAPATH = getenv('LHAPATH') if getenv('LHAPATH') else 'results'

    print("Will concatenate into {}.".format(outfile))
    store = HDFStore(outfile)

    df = DataFrame()
    store_conf = None
    for fs in infiles:
        for f in fs:
            print('Reading %s ...' % f)
            tmp_store = HDFStore(f)
            tmp_conf = tmp_store.get_storer(LHAPATH).attrs.config
            try:
                tmp_conf = tmp_store.get_storer(LHAPATH).attrs.config
                if not store_conf:
                    store_conf = tmp_conf
            except AttributeError:
                print('No config attribute found in {}'.format(f))
            if 'scatterplot' in store_conf:
                tmp_conf['scatterplot'] = store_conf['scatterplot']
            if store_conf and store_conf != tmp_conf:
                print('Warning: merge file with different config {}'.format(f))
            tmp_df = tmp_store['results']
            try:
                tmp_df['scan_seed'] = tmp_store.get_storer(LHAPATH).attrs.seed
                tmp_df['scan_parallel'] = tmp_store.get_storer(LHAPATH).attrs.parallel
            except AttributeError:
                pass
            df = df.append(tmp_df, ignore_index=True)
            tmp_store.close()

    store[LHAPATH] = df
    store.get_storer(LHAPATH).attrs.config = store_conf
    store.close()
