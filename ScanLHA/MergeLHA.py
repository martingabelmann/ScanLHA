#!/usr/bin/env python3
from pandas import read_hdf, DataFrame
from glob import glob
import sys

def main():
    if len(sys.argv) < 3:
        print('No valid filenames given!\nUsage: MergeLHA mergedfile.h5 file1.h5 file2.h5 [...]')
        sys.exit(1)

    infiles = [glob(f) for f in sys.argv[1:-1]]
    outfile = sys.argv[-1]
    print("Will concatenate into {}.".format(outfile))

    df = DataFrame()
    for fs in infiles:
        for f in fs:
            print('Reading %s ...' % f)
            tmp_df = read_hdf(f)
            df = df.append(tmp_df, ignore_index=True)
    df.to_hdf(outfile, 'results')
