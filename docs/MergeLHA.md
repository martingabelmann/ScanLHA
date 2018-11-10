Module ScanLHA.MergeLHA
-----------------------

Functions
---------
Merge()
    Merges multiple HDF files into one file.

    Usage: MergeLHA mergedfile.h5 file1.h5 file2.h5 [...]

    File names may be specified using patterns compatible with python.glob (e.g. '*.h5').

    Note that it is not possible to merge different `ScanLHA.config.Config` instances i.e. the `Config`
    instance of the first file is used.

    The default H5 tree is 'results' (default of `ScanLHA.scan.Scan.save`).
    For changing the path set the environment variable `export LHPATH='/yourpath'`.
