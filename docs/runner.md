Module ScanLHA.runner
---------------------

Variables
---------
RUNNERS
    Contains all available runner classes.

    Runners that are stored in the directory `runner_plugins` and are a child of `ScanLHA.runner.BaseRunner` are automatically added to this variable.

    To add your own custom runner create the `runner_plugins` directory in you working directory and add e.g. the file `myrunner.py` with e.g. the content:

        from ScanLHA.runner import BaseRunner

        class MyRunner(BaseRunner):
            def __init__(self, conf):
                super().__init__(conf)

            def execute(self, params):
                # do your computation using the
                # parameter set stored in the dict `params`
                return {'param1': myresult1,  ...}

    To use that runner, set

        ---
        runner:
           type: MyRunner
           ...

    in your config.

    The default runner for each scan is the `ScanLHA.runner.SLHARunner`.

Classes
-------
BaseRunner 
    Every runner must be a child of this.

    Needs a Config instance for initialization.

    Ancestors (in MRO)
    ------------------
    ScanLHA.runner.BaseRunner
    builtins.object

    Descendents
    -----------
    ScanLHA.runner.SLHARunner

    Static methods
    --------------
    __init__(self, conf)
        Basic initialization.

        For a correct behaviour use `super().__init__(conf)` in the `__init__` of your child runner.

    cleanup(self)
        remove temporary directory

    constraints(self, result)
        Check if the data point `result` fulfills the constraints of the list `self.config['constraints']`.

    execute(self, params)
        This method specifies what the runner should do with the single data pint `params`.

    makedirs(self, tocopy=[])
        * Create temporary directories (default: `/dev/shm/run<runnerid>`).

        * Copy all binaries listed in `self.config['binaries']` to the temporary directory

    removeFile(f, err=True)
        Removes a file `f`.

    run(self, params)
        Normalizes the result of `ScanLHA.runner.BaseRunner.execute`.

        It is e.g. used by `ScanLHA.scan.Scan` and should not be overwritten by child runners.

        To specify the behaviour of your custom runner overwrite the `ScanLHA.runner.BaseRunner.execute` method.

    runBinary(self, args, cwd=None)
        Execute `args` using `Popen`.

        Returns `(stdout, stderr)`.

        `stderr` is set to `'Timeout'` if `self.timeout` is exceeded.

    Instance variables
    ------------------
    binaries

    config

    initialized

    rundir

    tmp

MicrOmegas 
    Runner for MicrOmegas based on the `ScanLHA.runner.SLHARunner`.

    Works exactly the same as `ScanLHA.runner.SLHARunner` but builds the MicrOmegas src files in the temporary runner directory during initialization.

    Ancestors (in MRO)
    ------------------
    ScanLHA.runner.MicrOmegas
    ScanLHA.runner.SLHARunner
    ScanLHA.runner.BaseRunner
    builtins.object

    Static methods
    --------------
    __init__(self, conf)
        `self.tpl=conf['template']` should be a string containing patterns
        compatible with `conf['template'].format_map(params)` for a
        given set of parameters `params`.

    cleanup(self)
        remove temporary directory

    constraints(self, result)
        Check if the data point `result` fulfills the constraints of the list `self.config['constraints']`.

    execute(self, params)
        * Prepare all files for the run with the parameters `params` (dict).
        * iterate over the binaries in `self.binaries`
          * check for fulfilled constraints

        Example for `self.binaries` that passes results trough the different runs:

            config['runner']['binaries'] = [
                ['./SPheno', '{input_file}', '{output_file}'],
                ['./HiggsBounds', '{output_file}']
            ]

        The patterns `{input_file}`, `{output_file}` and `{log_file}` are available and are replaced by the result of `ScanLHA.runner.SLHARunner.prepare`.

    makedirs(self, tocopy=[])
        * Create temporary directories (default: `/dev/shm/run<runnerid>`).

        * Copy all binaries listed in `self.config['binaries']` to the temporary directory

    prepare(self, params)
        Generate input and output file names.

        Write the input file for the parameter dict `params` using the template `self.tpl`.

        Returns the filenames `('inputfile', 'outputfile', 'logfile')`.

    read(self, fout)
        Reads the file `fout` using `ScanLHA.slha.parseSLHA` and checks if all constraints `self.constraints` are fulfilled.

        If at least one constraint is not fulfilled, an empty result (dict) is returned.

    removeFile(f, err=True)
        Removes a file `f`.

    run(self, params)
        Normalizes the result of `ScanLHA.runner.BaseRunner.execute`.

        It is e.g. used by `ScanLHA.scan.Scan` and should not be overwritten by child runners.

        To specify the behaviour of your custom runner overwrite the `ScanLHA.runner.BaseRunner.execute` method.

    runBinary(self, args, cwd=None)
        Execute `args` using `Popen`.

        Returns `(stdout, stderr)`.

        `stderr` is set to `'Timeout'` if `self.timeout` is exceeded.

    Instance variables
    ------------------
    blocks

    modeldir

    omegadir

    timeout
        Timeout for Popen

    tpl

SLHARunner 
    Runner that runs binaries with (S)LHA input/output.

    Ancestors (in MRO)
    ------------------
    ScanLHA.runner.SLHARunner
    ScanLHA.runner.BaseRunner
    builtins.object

    Descendents
    -----------
    ScanLHA.runner.MicrOmegas

    Static methods
    --------------
    __init__(self, conf)
        `self.tpl=conf['template']` should be a string containing patterns
        compatible with `conf['template'].format_map(params)` for a
        given set of parameters `params`.

    cleanup(self)
        remove temporary directory

    constraints(self, result)
        Check if the data point `result` fulfills the constraints of the list `self.config['constraints']`.

    execute(self, params)
        * Prepare all files for the run with the parameters `params` (dict).
        * iterate over the binaries in `self.binaries`
          * check for fulfilled constraints

        Example for `self.binaries` that passes results trough the different runs:

            config['runner']['binaries'] = [
                ['./SPheno', '{input_file}', '{output_file}'],
                ['./HiggsBounds', '{output_file}']
            ]

        The patterns `{input_file}`, `{output_file}` and `{log_file}` are available and are replaced by the result of `ScanLHA.runner.SLHARunner.prepare`.

    makedirs(self, tocopy=[])
        * Create temporary directories (default: `/dev/shm/run<runnerid>`).

        * Copy all binaries listed in `self.config['binaries']` to the temporary directory

    prepare(self, params)
        Generate input and output file names.

        Write the input file for the parameter dict `params` using the template `self.tpl`.

        Returns the filenames `('inputfile', 'outputfile', 'logfile')`.

    read(self, fout)
        Reads the file `fout` using `ScanLHA.slha.parseSLHA` and checks if all constraints `self.constraints` are fulfilled.

        If at least one constraint is not fulfilled, an empty result (dict) is returned.

    removeFile(f, err=True)
        Removes a file `f`.

    run(self, params)
        Normalizes the result of `ScanLHA.runner.BaseRunner.execute`.

        It is e.g. used by `ScanLHA.scan.Scan` and should not be overwritten by child runners.

        To specify the behaviour of your custom runner overwrite the `ScanLHA.runner.BaseRunner.execute` method.

    runBinary(self, args, cwd=None)
        Execute `args` using `Popen`.

        Returns `(stdout, stderr)`.

        `stderr` is set to `'Timeout'` if `self.timeout` is exceeded.

    Instance variables
    ------------------
    blocks

    initialized

    timeout
        Timeout for Popen

    tpl
