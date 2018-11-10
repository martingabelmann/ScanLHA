Module ScanLHA.ScanLHA
----------------------

Functions
---------
ScanLHA()
    Basic usage: `ScanLHA --help`.

    Takes at least one argument that is the path to a config YAML file.

    The variety of arguments may increase if parameters in the config file are specified with the `argument` attribute.
    This way it is possible to define the values/scan ranges of specific parameters through command line arguments
    while other may be defined in the config file.

    __Basic scan.yml__

        ---
        runner:
          binaries:
            - ['/bin/SPhenoMSSM', '{input_file}', '{output_file}']
            - ['./HiggsBounds', 'LandH', 'SLHA', '3', '0', '{output_file}']
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
                    latex: '$\tan\beta$'
                    argument: 'value'

    Then start the scan e.g. with: `ScanLHA scan.yml --TanBeta 10 result10.h5`

    Alternatively one may specify `values: [1, 2, 10]` for TanBeta instead of `argument`
    or even `scan: [1, 50, 50]` to scan over TanBeta and save the result into one single file.
