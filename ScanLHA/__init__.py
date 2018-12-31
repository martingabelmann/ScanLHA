#!/usr/bin/env python3
"""
Perform parameter scans with HEP tools that use (not only) (S)LHA in- and output.

__Use Case__

Typical tool-chains in high-energy physics (HEP) are the pass-through of one SLHA-input file from spectrum generators, e.g. [SPheno](https://spheno.hepforge.org/), to further HEP tools like [HiggsBounds](https://higgsbounds.hepforge.org/) and/or [micrOmegas](https://lapth.cnrs.fr/micromegas/) which themself return SLHA-output files.  
To provide correct input for the various tools between the different steps as well as to enable further processing (e.g. plotting) the SLHA format needs to be parsed and stored in a storage-efficient tabular format.  
In a phenomenological study, most of the physical parameters as well as config flags within a considered scenario are kept constant while only a few O(1-20) parameters are varied in different ways (grid- or randomly scanned, more sophisticated scanning techniques are planned in the future).  
Due to the large combinatorics, the scan may be done in parallel and even be distributed over different machines (using e.g. Sun Grid Engine, the usage of [dask.distributed](https://github.com/dask/distributed) is planned for the future).  
The outcome is one (or multiple) HDF files (to be merged) that may undergo further editing before the results are visualized in 2D or 3D scatter plots.


__Installing__

        pip3 install ScanLHA


__Executables__

 * [ScanLHA](https://martingabelmann.github.io/ScanLHA/ScanLHA.m.html) - Perform (S)LHA scan/s and save to HDF file/s.
 * [PlotLHA](https://martingabelmann.github.io/ScanLHA/PlotLHA.m.html) - Plot ScanLHA results from HDF file/s.
 * [EditLHA](https://martingabelmann.github.io/ScanLHA/EditLHA.m.html) - Interactively load/edit/save/plot HDF file/s.
 * [MergeLHA](https://martingabelmann.github.io/ScanLHA/MergeLHA.m.html) - Merge multiple HDF files into one file.

The executables ``ScanLHA`` and ``PlotLHA`` take a YAML input [config](https://martingabelmann.github.io/ScanLHA/config.m.html) file.


__Scanning__

The [config](https://martingabelmann.github.io/ScanLHA/config.m.html) YAML file must contain two dictionaries ``runner`` and ``blocks`` controlling
the type of scan/tools to be used as well as the SLHA blocks that have to be present/scanned in the input file.   
In order to simplify the distribution of similar scans through grid-computing software, it is possible to declare ``argument``
SLHA entries. The value/scanrange of these entries can be set from within command line arguments.  


A basic config.yml file to run SPheno and HiggsBounds may look like

        ---
        runner:
          binaries:
            - ['/bin/SPhenoMSSM', '{input_file}', '{output_file}']
            - ['./HiggsBounds', 'LandH', 'SLHA', '3', '0', '{output_file}']
          tmpfs: /dev/shm/slha
          keep_log: true
          timeout: 90
          scantype: random
          numparas: 50000
          constraints: # Higgs mass constraint
            - "result['MASS']['values']['25']<127.09"
            - "result['MASS']['values']['25']>123.09"
        blocks:
            - block: MINPAR
              lines:
                  - parameter: 'MSUSY'
                    latex: '$M_{SUSY}$ (GeV)'
                    id: 1
                    random: [500,3500]
                  - parameter: 'TanBeta'
                    latex: '$\\tan\\beta$'
                    argument: 'value'
                  - parameter: 'mu'
                    latex: '$\\mu$ (GeV)'
                    id: 2
                    value: 300

Where the ``id`` is the SLHA-id of the parameter ``parameter`` in the block ``block`` which either takes the constant value ``value``, is ``random``ly chosen or ``scan``ed in a grid.  
The presence of the new command line argument ``TanBeta`` may be  verified with ``ScanLHA config.yml --help``.  
A scan that runs the SPheno->HiggsBounds chain in 2 parallel threads is started with ``ScanLHA config.yml -p 2 --TanBeta 4 scantanbeta4.h5`` (by default os.cpucount() is used for ``-p``).  
For this purpose, 2 copies of the binaries are stored in 2 randomly named directories in ``runner['tmpfs']`` (default: ``/dev/shm/``) where the input and output files are generated.  
Alternatively one may specify ``values: [1, 2, 10]`` for the line ``TanBeta`` instead of ``argument``
or even ``scan: [1, 50, 50]`` to scan over ``TanBeta`` (from 1 to 50 in 50 steps for each random value of ``MSUSY``) and save the result into one single file (likewise, the ``argument`` option can be set to ``scan`` or ``random`` and according numbers may be provided from the command line). Grid scans can have a ``distribution`` attribute equaling ``linear,log,geom,arange,uniform`` or ``normal``.  

The executables in ``runner['binaries']`` are run subsequential for each parameter point using given arguments. For each point a randomly named ``{input_file}`` is generated and may be passed as argument
to the executables. Likewise, the ``{output_file}`` is supposed to be written by the executables and eventually parsed afterwards. One may also make direct use of Python (or C-Python) implementations instead of using executables by implementing a [runner module](https://martingabelmann.github.io/ScanLHA/runner.m.html).

__Plotting__

The config.yml used for the scan may also contain a ``scatterplot`` dictionary (but can also be contained in a separate file).

Plotting capabilities are:

 * Automatically uses the ``latex`` attribute of specified LHA ``blocks`` for labels.
  * Fields for x/y/z axes can be specified by either ``BLOCKNAME.values.LHAID`` or the specified ``parameter`` attribute.
  * New fields to plot can be computed using existing fields saved in ``DATA``
  * Optional constraints on the different fields may be specified using  ``PDATA``
  * Various options can be passed to ``matplotlib``s ``legend``, ``scatter``, ``colorbar`` functions.
  * Optional ticks, textboxes, legend-position, colors, etc... can be set manually.


The ``scatterplot`` dict must contain a ``conf`` dict that specifies at least the
HDF ``datafile`` to load. Additionaly, defaults for x/y/z axes or other plot configs may be set and need not to be
repeated in the plot definitions (but can be overwritten). In addition, the ``plots`` key contains a list of dicts
that specify the ``filename`` and data to plot.


An example configuration may look like

        ---
        scatterplot:
          conf:
            datafile: "mssm.h5"
            newfields:
              TanBeta: "DATA['HMIX.values.2'].apply(abs).apply(tan)"
                       # the string is passed to eval
            constraints:
              - "PDATA['TREELEVELUNITARITYwTRILINEARS.values.1']<0.5"
              # enforces unitarity on the sample
          plots:
              - filename: "mssm_TanBetaMSUSYmH.png"
                # one scatterplot
                y-axis: {field: TanBeta, label: '$\\tan\\beta$'}
                x-axis:
                  field: MSUSY
                  label: "$m_{SUSY}$ (TeV)$"
                  lognorm: True
                  ticks:
                    - [1000,2000,3000,4000]
                    - ['$1$','$2','$3','$4$']
                z-axis:
                  field: MASS.values.25
                  colorbar: True
                  label: "$m_h$ (GeV)"
                alpha: 0.8
                textbox: {x: 0.9, y: 0.3, text: 'some info'}
              - filename: "mssm_mhiggs.png"
                # multiple lines in one plot with legend
                constraints: [] # ignore all global constraints
                x-axis:
                  field: MSUSY,
                  label: 'Massparameter (GeV)'
                y-axis:
                  lognorm: True,
                  label: '$m_{SUSY}$ (GeV)'
                plots:
                    - y-axis: MASS.values.25
                      color: red
                      label: '$m_{h_1}$'
                    - y-axis: MASS.values.26
                      color: green
                      label: '$m_{h_2}$'
                    - y-axis: MASS.values.35
                      color: blue
                      label: '$m_{A}$'

__Editing and Merging__

See ``EditLHA --help`` and ``MergeLHA --help``.


__Scanning with other (non-)SLHA Tools__

See the API docs of the [runner module](https://martingabelmann.github.io/ScanLHA/runner.m.html).


__Related Tools__

 * [xBIT](https://github.com/fstaub/xBIT)
 * [SSP](https://sarah.hepforge.org/SSP.html)/[pySSP](https://github.com/fstaub/pySSP)
 * ask me if you wish to be listed here

"""
from .scan import Scan, RandomScan, FileScan
from .config import Config
from  .runner import RUNNERS
from  .slha import genSLHA, parseSLHA
__version__ = '0.2'
__all__ = []
