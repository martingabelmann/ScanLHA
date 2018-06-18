#!/usr/bin/env python3
from pandas import HDFStore, DataFrame
from glob import glob
import sys

def main():
    if len(sys.argv) < 3:
        print('No valid filenames given!\nUsage: MergeLHA mergedfile.h5 file1.h5 file2.h5 [...]')
        sys.exit(1)

    path = 'results'

    infiles = [glob(f) for f in sys.argv[1:-1]]
    outfile = sys.argv[-1]

    print("Will concatenate into {}.".format(outfile))
    store = HDFStore(outfile)

    df = DataFrame()
    store_conf = None
    for fs in infiles:
        for f in fs:
            print('Reading %s ...' % f)
            tmp_store = HDFStore(f)
            tmp_conf = tmp_store.get_storer(path).attrs.config
            try:
                tmp_conf = tmp_store.get_storer(path).attrs.config
                if not store_conf:
                    store_conf = tmp_conf
            except AttributeError:
                print('No config attribute found in {}'.format(f))
            if store_conf and store_conf != tmp_conf:
                print('Warning: merge file with different config {}'.format(f))
            tmp_df = tmp_store['results']
            try:
                tmp_df['scan_seed'] = tmp_store.get_storer(path).attrs.seed
                tmp_df['scan_parallel'] = tmp_store.get_storer(path).attrs.parallel
            except AttributeError:
                pass
            df = df.append(tmp_df, ignore_index=True)
            tmp_store.close()

    store[path] = df
    store.get_storer(path).attrs.config = store_conf
    store.close()
