Module ScanLHA.config
---------------------

Classes
-------
Config 
    A dict-like object that carries information about LHA file(s), programs that import/export LHA files, and plots.

      1. LHA blocks are stored in the key `'blocks'`.

      2. Information about the scan to perform and used programs is stored in the key `'runner'`.

      3. Information about the plots is stored in the key `'scatterplot'`.

    Example for accessing LHA entries:

        In [1]: from ScanLHA import Config
        In [2]: c=Config('SPheno.yml')
        In [3]: c.parameters # contains all LHA entries using unique parameter identifiers
        In [4]: c['MODSEL'] # returns the whole MODSEL block
        In [5]: c['MODSEL.1'] # line with LHA id=1 from block MODSEL
        In [6]: c['MODSEL.values.1'] # value to which the LHA id=1 in the block MODSEL is set
        In [7]: c['TanBeta'] # return the line which is associated with the parameter TanBeta
        Out[7]:
        {'id': 4,
         'latex': '$\tan\beta$',
         'lha': 'MINPAR.values.4',
         'parameter': 'TanBeta',
         'values': [1,2,3,4]}

    Example for `'runner'` (more see `ScanLHA.runner`):

        ---
        runner:
        binaries:
            - [ '/home/user/SPheno/bin/SPhenoMSSM', '{input_file}', '{output_file}']
            - [ '/home/user/HiggsBounds-4.3.1/HiggsBounds',  'LandH', 'SLHA', '3', '0', '{output_file}']
        micromegas:
            src: '/home/user/micrOMEGAS/src'
            modelname: 'MSSM'
            main: 'CalcOmegaDD.cpp'
            exec: ['CalcOmegaDD', '{output_file}']
        type: MicrOmegas
        cleanup: false
        keep_log: true
        remove_slha: true

    Example for `'blocks'`:

        ---
        blocks:
        - block: MINPAR
          lines:
              - parameter: 'MSUSY'
                id: 1
                scan:  [2e3, 2e4, 100]
                distribution: 'geom'
              - parameter: 'TanBeta'
                latex: '$\tan\beta$'
                id: 2
                value: 4
              - ..

    Example for `'scatterplot'` (more see `ScanLHA.PlotLHA`):

        ---
        scatterplot:
            conf:
                datafile: "results.h5"
                newfields:
                    TanBeta: "DATA['HMIX.values.11'].apply(abs).apply(tan)"
                    M1: "DATA['MASS.values.1000022'].apply(abs)"
                    M2: "DATA['MASS.values.1000023'].apply(abs)"
                    Mdiff: "DATA['MASS.values.1000023'].apply(abs)-DATA['MASS.values.1000022'].apply(abs)"
                dpi: 200
                x-axis: {
                    field: 'MSUSY',
                    lognorm: True,
                    label: "$m_{SUSY}$ [TeV]",
                    ticks: [[2000, 3000, 6000, 10000, 20000], ['$2$','$3$', '$6$', '$10$', '$20$']]
                    }
            plots:
                - filename: 'masses.png'
                  alpha: 0.8
                  legend: {'loc':'right'}
                  y-axis: {label: '$Mass$ [GeV]', lognorm: True }
                  textbox: {x: 0.94, y: 0.35, text: 'some info text', fontsize: 12}
                  plots:
                      - {y-axis: 'M1', label: '$m_{\chi_1^0}$'}
                      - {y-axis: 'M2', label: '$m_{\chi_2^0}$'}
                      - {vline: True, x-field: 3000, lw: 2, color: 'black', alpha: 1}
                      - {vline: True, x-field: 6000, lw: 2, color: 'black', alpha: 1}
                - filename: diff.png
                  x-axis: {field: M1, label: 'm_{\chi_1^0}'}
                  y-axis: {field: M2, label: 'm_{\chi_2^0}'}
                  z-axis: {field: Mdiff, label: '\delta_m'}

    Ancestors (in MRO)
    ------------------
    ScanLHA.config.Config
    builtins.dict
    builtins.object

    Static methods
    --------------
    __init__(self, src)
        Initialize self.  See help(type(self)) for accurate signature.

    append(self, c)
        Append information from another ScanLHA.Config instance <c>.

    getBlock(self, block)
        Blocks are stored in a list of dicts. This method is to access blocks by their name.

        Example:

            In [1]: from ScanLHA import Config
            In [2]: c=Config('SPheno.yml')
            In [3]: c.getBlock('MODSEL')
            Out[3]:
            {'block': 'MODSEL',
               'lines': [{'id': 1,
                 'value': 1,
                 'parameter': 'MODSEL.1',
                 'latex': 'MODSEL.1',
                 'lha': 'MODSEL.values.1'},
                {'id': 2,
                 'value': 1,
                 'parameter': 'MODSEL.2',
                 'latex': 'MODSEL.2',
                 'lha': 'MODSEL.values.2'},
                {'id': 6,
                 'value': 1,
                 'parameter': 'MODSEL.6',
                 'latex': 'MODSEL.6',
                 'lha': 'MODSEL.values.6'}]}

    getLine(self, block, id)
        Returns the line with the SLHA id `id` from the block `block`

        Example:

            In [1]: from ScanLHA import Config
            In [2]: c=Config('SPheno.yml')
            In [3]: c.getLine('MODSEL', 1)
            Out[3]:
            {'id': 1,
            'value': 1,
            'parameter': 'MODSEL.1',
            'latex': 'MODSEL.1',
            'lha': 'MODSEL.values.1'}

    load(self, src=None)
        Load config from source file `src`.

        If the `ScanLHA.config.Config` instance was already loaded, information from the old `src` file is overwritten.

        After successfully loading the `ScanLHA.config.Config` instance it gets validated using `ScanLHA.config.Config.validate`.

    save(self, dest=None)
        Save `ScanLHA.config.Config` instance to destination file `dest`.
        If `dest==None` (default), `Config.src` is used.

    setBlock(self, block, lines=[])
        Defines a SLHA block `block` with optional lines `lines`

        Example:

            In [1]: from ScanLHA import Config
            In [1]: c=Config('SPheno.yml')
            In [1]: Config.setBlock('MINPAR', lines=[{'id': 1, 'value': 1, 'parameter': 'TanBeta', 'latex': '\tan\beta'}, ...])

    setLine(self, block, line)
        Add the `line` to the LHA `block`

        If the line already exists, the given keys are updated.

        Example:

            In [1]: from ScanLHA import Config
            In [2]: c=Config('SPheno.yml')
            In [3]: # use 1-loop RGEs
            In [4]: c.setLine('SPhenoInput', {'id': 38, 'value': 1})

    validate(self)
        Validates the `ScanLHA.config.Config` instance and prepares further information attributes such as latex output.

        This method is applied after `ScanLHA.config.Config.load`, `ScanLHA.config.Config.setBlock`, `ScanLHA.config.Config.setLine` and `ScanLHA.config.Config.append`.

    Instance variables
    ------------------
    distribution

    parameters

    src

    valid
