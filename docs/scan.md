Module ScanLHA.scan
-------------------

Classes
-------
RandomScan 
    Scan object

    Controls a scan over an n-dimensional parameter range using uniformly distributed numbers.

    Needs a Config object (see `ScanLHA.config.Config`) for initialization.

    The `'runner'` config-entry needs to specify the number `'numparas'` of randomly generated parameters.

    Ancestors (in MRO)
    ------------------
    ScanLHA.scan.RandomScan
    builtins.object

    Static methods
    --------------
    __init__(self, c, seed=None)
        Initialize self.  See help(type(self)) for accurate signature.

    generate(self)
        Generate uniformly distributed numbers for specified SLHA blocks.

        Substitute the numbers in dependend blocks, if necessary.

    save(self, filename='store.hdf', path='results')
        Saves `self.results` into the HDF file `filename` in the tree `path`.

    scan(self, numparas, pos=0)
        Register a runner using the config and generate `numparas` data samples.

        Returns a `pandas.DataFrame`.

    submit(self, num_workers=None)
        Start a scan and distribute it on `num_workers` threads.

        If `num_workers` is omitted, the value of `os.cpu_count()` is used.

        Results are stored in `self.results`.

    Instance variables
    ------------------
    config

    dependent

    getblocks

    numparas

    parallel

    randoms

    runner

    seed

Scan 
    Scan object

    Controls a scan over a n-dimensional parameter range using a grid.

    Needs a Config object (see `ScanLHA.config.Config`) for initialization.

    The `'runner'` config must be present as well.

    Ancestors (in MRO)
    ------------------
    ScanLHA.scan.Scan
    builtins.object

    Descendents
    -----------
    ScanLHA.scan.FileScan

    Static methods
    --------------
    __init__(self, c)
        Initialize self.  See help(type(self)) for accurate signature.

    addScanRange(self, block, line)
        Register a scan range for LHA entry in the block <block>.

        `'line'` must be a dict containing:

          1. the LHA id 'id' within the block `block`
          2. a scan range 'scan' consisting of a two-tuple
          3. optional: `'distribution'`
            can be `'log'`, `'linear'`, `'geom'`, `'arange'`, `'uniform'` and `'normal'`.
            default: `'linear'`

    addScanValues(self, block, line)
        Set a LHA entry to a specific list of input values in the block `block`.

        `line` must be a dict containing the:

          1. `id` of the LHA entry within the block
          2. `values` given as a list

    build(self, num_workers=4)
        Expand parameter lists and scan ranges while substituting eventual dependencies.

    save(self, filename='store.hdf', path='results')
        Saves `self.results` into the HDF file `filename` in the tree `path`.

    scan(self, dataset)
        Register an runner using the config and apply it on `dataset`

    submit(self, num_workers=None)
        Start a scan and distribute it on `num_workers` threads.

        If `num_workers` is omitted, the value of `os.cpu_count()` is used.

        Results are stored in `self.results`.

    Instance variables
    ------------------
    config

    getblocks

    runner

    scanset
