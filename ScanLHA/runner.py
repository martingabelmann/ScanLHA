from collections import defaultdict
import logging
from subprocess import Popen, STDOUT, PIPE, DEVNULL, TimeoutExpired
from .slha import parseSLHA
from random import randrange,randint
import os
from sys import exit
from math import * # noqa: F403 F401
from shutil import copy2,copytree, rmtree
from tempfile import mkdtemp
from pandas.io.json import json_normalize

__all__ = ['RUNNERS', 'BaseRunner', 'SLHARunner', 'MicrOmegas']

RUNNERS = {}
"""
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
"""

class Runner_Register(type):
    """
    Add each new runner to the `RUNNERS` variable.
    """
    def __new__(cls, clsname, bases, attrs):
        newcls = super(Runner_Register, cls).__new__(cls, clsname, bases, attrs)
        if hasattr(newcls, 'execute') and hasattr(newcls, 'run'):
            RUNNERS.update({clsname: newcls})
        return newcls

class BaseRunner(metaclass=Runner_Register):
    """
    Every runner must be a child of this.

    Needs a Config instance for initialization.
    """
    def __init__(self,conf):
        """
        Basic initialization.

        For a correct behaviour use `super().__init__(conf)` in the `__init__` of your child runner.
        """
        self.config = conf
        self.rundir = os.getcwd()
        self.binaries = []
        self.tmp = False
        self.initialized = False

    def makedirs(self, tocopy=[]):
        """
          * Create temporary directories (default: `/dev/shm/run<runnerid>`).

          * Copy all binaries listed in `self.config['binaries']` to the temporary directory
        """
        if 'tmpfs' not in self.config:
            if os.path.exists('/dev/shm/'):
                self.config['tmpfs'] = '/dev/shm/'
            else:
                self.config['tmpfs'] = mkdtemp()
        self.rundir = os.path.join(self.config['tmpfs'], 'run%d' % randint(10000,99999))
        if not os.path.exists(self.rundir):
            logging.debug('Creating temporary directory {}.'.format(self.rundir))
            os.makedirs(self.rundir)
        tocopy = tocopy if type(tocopy) == list else [tocopy]
        if 'binary' in self.config:
            self.binaries = [os.path.join(self.rundir, os.path.basename(self.config['binary'])), '{input_file}', '{output_file}']
            tocopy.append(self.config['binary'])
        elif 'binaries' in self.config:
            if type(self.config['binaries']) != list:
                logging.error("syntax: runner['binaries'] = [ ['executable', 'arg1', ...], ...]")
                exit(1)
            for binary in self.config['binaries']:
                if type(binary) != list:
                    logging.error("syntax: runner['binaries'] = [ ['executable', 'arg1', ...], ...]")
                    exit(1)
                tocopy.append(binary[0])
                self.binaries.append([os.path.join(self.rundir, os.path.basename(binary[0]))] + binary[1:])
        for f in tocopy:
            if not os.path.exists(f):
                logging.error('File/dir {} not found!'.format(f))
                exit(1)
            logging.debug('Copying {} into temporary directory {}.'.format(f, self.rundir))
            if os.path.isdir(f):
                copytree(f, os.path.join(self.rundir, os.path.basename(f)))
            else:
                copy2(f, self.rundir)
        logging.debug('Changing directory')
        os.chdir(self.rundir)
        self.tmp = True

    def cleanup(self):
        """ remove temporary directory """
        if not self.config.get('cleanup', False) or not self.tmp:
            return
        try:
            logging.debug('Removing temporary directory {}'.format(self.rundir))
            os.chdir(self.config['tmpfs'])
            rmtree(self.rundir)
        except FileNotFoundError:
            logging.error('Directory {} does not exist.'.format(self.rundir))
        except:
            logging.error('Could not remove directory {}.'.format(self.rundir))

    def __del__(self):
        self.cleanup()

    def constraints(self, result):
        """ Check if the data point `result` fulfills the constraints of the list `self.config['constraints']`."""
        try:
            if not all(map(eval, self.config['constraints'])):
                return
            return True
        except KeyError:
            return True
        return

    @staticmethod
    def removeFile(f, err=True):
        """ Removes a file `f`. """
        try:
            os.remove(f)
        except FileNotFoundError:
            if err:
                logging.error('file {} missing?'.format(f))

    def runBinary(self, args, cwd = None): # noqa
        """
        Execute `args` using `Popen`.

        Returns `(stdout, stderr)`.

        `stderr` is set to `'Timeout'` if `self.timeout` is exceeded.
        """

        proc = Popen(args, cwd=cwd, stderr=STDOUT, stdout=PIPE)
        try:
            stdout, stderr = proc.communicate(timeout=self.timeout)
        except TimeoutExpired:
            stdout = ''
            stderr = 'Timeout'
            return stdout, stderr
        stdout = stdout.decode('utf8').strip() if stdout else ''
        stderr = stderr.decode('utf8').strip() if stderr else ''

        return stdout, stderr

    def execute(self, params):
        """ This method specifies what the runner should do with the single data pint `params`. """
        pass

    def run(self, params):
        """
        Normalizes the result of `ScanLHA.runner.BaseRunner.execute`.

        It is e.g. used by `ScanLHA.scan.Scan` and should not be overwritten by child runners.

        To specify the behaviour of your custom runner overwrite the `ScanLHA.runner.BaseRunner.execute` method.
        """
        return json_normalize(self.execute(params))

class SLHARunner(BaseRunner):
    """
    Runner that runs binaries with (S)LHA input/output.
    """
    def __init__(self,conf):
        """
        `self.tpl=conf['template']` should be a string containing patterns
        compatible with `conf['template'].format_map(params)` for a
        given set of parameters `params`.
        """
        super().__init__(conf)
        self.timeout = conf.get('timeout', 10)
        """ Timeout for Popen """
        self.tpl = conf['template']
        self.blocks = conf.get('getblocks', [])
        self.makedirs()
        self.initialized = True

    def prepare(self, params):
        """
        Generate input and output file names.

        Write the input file for the parameter dict `params` using the template `self.tpl`.

        Returns the filenames `('inputfile', 'outputfile', 'logfile')`.
        """
        fname = str(randrange(10**10))
        fin  = os.path.join(self.rundir, fname + '.in')
        fout = os.path.join(self.rundir, fname + '.out')
        flog = os.path.join(self.rundir, fname + '.log')

        with open(fin, 'w') as inputf:
            try:
                params = defaultdict(str, { '%{}%'.format(p) : v for p,v in params.items() })
                inputf.write(self.tpl.format_map(params))
            except KeyError:
                logging.error("Could not substitute {}.".format(params))
                return None, None, None
        return fin, fout, flog

    def read(self, fout):
        """
        Reads the file `fout` using `ScanLHA.slha.parseSLHA` and checks if all constraints `self.constraints` are fulfilled.

        If at least one constraint is not fulfilled, an empty result (dict) is returned.
        """
        slha = parseSLHA(fout, self.blocks)
        if self.config.get('constraints', False) and not self.constraints(slha):
            return {}
        return slha

    def execute(self, params):
        """
        * Prepare all files for the run with the parameters `params` (dict).
        * iterate over the binaries in `self.binaries`
          * check for fulfilled constraints

        Example for `self.binaries` that passes results trough the different runs:

            config['runner']['binaries'] = [
                ['./SPheno', '{input_file}', '{output_file}'],
                ['./HiggsBounds', '{output_file}']
            ]

        The patterns `{input_file}`, `{output_file}` and `{log_file}` are available and are replaced by the result of `ScanLHA.runner.SLHARunner.prepare`.
        """
        fin, fout, flog = self.prepare(params)
        if not all([fin, fout, flog]):
            return {'log': 'Error preparing files for parameters: {parameters}'.format(params)}
        slha_base = {
                'log_stdout': '',
                'log_stderr': '',
                'input_parameters': params,
                'input_file': fin,
                'output_file': fout,
                'log_file': flog
                }

        slha = True
        for binary in self.binaries:
            if not slha:
                continue
            if type(binary) == list:
                # insert file names into the executable command
                binary = [ b.format(**slha_base) for b in binary ]
            else:
                binary = [binary]
            logging.debug("executing {}".format(' '.join(binary)))
            stdout, stderr = self.runBinary(binary)
            slha_base['log_stderr'] += stderr
            slha_base['log_stdout'] += stdout
            slha = self.read(fout)

        if self.config.get('remove_slha', True):
            self.removeFile(fin)
            self.removeFile(fout, err=False)

        if self.config.get('keep_log', False):
            slha.update(slha_base)
            log = 'parameters: {input_parameters}\nstdout: {log_stdout}\nstderr: {log_stderr}\n\n'.format(**slha_base)
            if self.config.get('logfiles', False):
                with open(flog, 'w') as logf:
                    logf.write(log)
                slha.update({ 'log_file': flog })
            logging.debug(log)
        return slha

class MicrOmegas(SLHARunner):
    """
    Runner for MicrOmegas based on the `ScanLHA.runner.SLHARunner`.

    Works exactly the same as `ScanLHA.runner.SLHARunner` but builds the MicrOmegas src files in the temporary runner directory during initialization.
    """

    def __init__(self,conf):
        super(SLHARunner, self).__init__(conf)
        """
        One needs to compile MicrOmegas for each runner since it uses hard coded paths.
        In order to do so, put the following information in your runner config:
            runner:
                type: MicrOmegas
                micromegas:
                    src: '/home/user/micrOMEGAS/src' # source directory to copy (run make clean before)
                    modelname: 'SplitNMSSM' # model-dir to join (run make clean before)
                    main: 'CalcOmegaDD.cpp' # cpp file to build
                    exec: ['CalcOmegaDD', '{input_file}'] # entry for runner['binaries']

        The resulting binary is appended to the list `runner['binaries']`.

        If you use e.g. SPheno to generate input for MicrOmegas, you may want to add

        `['./SPheno', '{input_file}', '{output_file}']`

        to `runner['binaries']` and change the `exec` option to use the `{output_file}` instead.

        Additional `'binaries'` may be specified as well.
        """
        self.timeout = conf.get('timeout', 18000)
        self.tpl = conf['template']
        self.blocks = conf.get('getblocks', [])
        if 'micromegas' not in self.config:
            logging.error('need to specify "micromegas" config')
            exit(1)
        omega = self.config['micromegas']
        if 'src' not in omega or not os.path.exists(omega['src']):
            logging.error('need to specify micromegas "src" directory to build from')
            exit(1)
        if 'modelname' not in omega:
            logging.error('need to specify "modelname" name')
            exit(1)
        if 'main' not in omega:
            logging.error('need to specify "main" cpp file to build')
            exit(1)
        if 'exec' not in omega:
            logging.error('need to specify "exec"utable created by the build followed by its arguments (Popen list syntax)')
            exit(1)
        self.makedirs(tocopy = omega['src'])
        self.omegadir = os.path.join(self.rundir,os.path.basename(omega['src']))
        self.modeldir = os.path.join(self.omegadir, omega['modelname'])
        logging.debug('running "make clean" on MicrOmegas installtion.')
        Popen('yes|make clean', shell=True, stdout=DEVNULL, stderr=DEVNULL, cwd=self.omegadir)
        logging.debug('running "make" on MicrOmegas installtion.')
        i = 0
        stdout, stderr = "", "MicrOmegas was already built(?)"
        while not os.path.isfile(self.omegadir + '/include/microPath.h') and i < 15:
            stdout, stderr = self.runBinary(['make'], cwd=self.omegadir)
            i += 1
        if i >= 5:
            logging.error('Build failed')
            logging.error(stdout)
            logging.error(stderr)
        logging.debug('running "make clean" on MicrOmegas model.')
        os.chdir(self.modeldir)
        Popen(['make', 'clean'], stdout=DEVNULL, stderr=DEVNULL, shell=True, cwd=self.modeldir)
        logging.debug('running "make main={}" on MicrOmegas model.'.format(omega['main']))
        i = 0
        stdout, stderr = "", "The model was already built(?)"
        while not os.path.isfile(omega['exec'][0]) and i < 15:
            stdout, stderr = self.runBinary(['make', 'main='+omega['main']], cwd=self.modeldir)
            i += 1
        if i < 15 and i != 0:
            logging.debug('file {} was build'.format(omega['exec'][0]))
            self.initialized = True
        else:
            logging.error(stdout)
            logging.error(stderr)
        os.chdir(self.rundir)
        self.binaries.append([os.path.join(self.modeldir, omega['exec'][0])] + omega['exec'][1:])
