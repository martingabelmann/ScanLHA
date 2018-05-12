from collections import defaultdict
import logging
from subprocess import Popen, STDOUT, PIPE, TimeoutExpired
from .slha import parseSLHA
from random import randrange,randint
import os
from sys import exit
from numpy import nan
from shutil import copy2,copytree, rmtree
from tempfile import mkdtemp
from pandas.io.json import json_normalize

class BaseRunner():
    def __init__(self,conf):
        self.config = conf
        self.rundir = os.getcwd()
        self.binaries = []
        self.binary = ""

    def makedirs(self, tocopy=[]):
        if 'tmpfs' not in self.config:
            if os.path.exists('/dev/shm/'):
                self.config['tmpfs'] = '/dev/shm/'
            else:
                self.config['tmpfs'] = mkdtemp()
        self.rundir = os.path.join(self.config['tmpfs'], 'run%d' % randint(100,999))
        if not os.path.exists(self.rundir):
            logging.info('Creating temporary directory {}.'.format(self.rundir))
            os.makedirs(self.rundir)
        if 'binary' in self.config:
            self.binary = os.path.join(self.rundir, os.path.basename(self.config['binary']))
            tocopy.append(self.config['binary'])
        if 'binaries' in self.config:
            tocopy += self.config['binaries']
            self.binaries = [os.path.join(self.rundir, os.path.basename(b)) for b in self.config['binaries']]
        for f in tocopy:
            if not os.path.exists(f):
                logging.error('File/dir {} not found!'.format(f))
                exit(1)
            logging.info('Copying {} into temporary directory {}.'.format(f, self.rundir))
            if os.path.isdir(f):
                copytree(f, os.path.join(self.rundir, os.path.basename(f)))
            else:
                copy2(f, self.rundir)
            logging.info('Changing directory')
            os.chdir(self.rundir)

    def cleanup(self):
        if not self.config.get('cleanup', False):
            return
        try:
            logging.info('Removing temporary directory {}'.format(self.rundir))
            os.chdir('/')
            rmtree(self.rundir)
        except FileNotFoundError:
            logging.error('Directory {} does not exist.'.format(self.rundir))
        except:
            logging.error('Could not remove directory {}.'.format(self.rundir))

    def __del__(self):
        self.cleanup()

    def constraints(self, result):
        try:
            if not all(map(eval, self.config['constraints'])):
                return
            return True
        except KeyError as e:
            logging.error('invalid constraint: {}'.format(e))
        return

    @staticmethod
    def removeFile(f):
        try:
            os.remove(f)
        except FileNotFoundError:
            logging.error('file {} missing?'.format(f))

    def runBinary(self, *args):
        proc = Popen(list(args), stderr=STDOUT, stdout=PIPE)
        try:
            stdout, stderr = proc.communicate(timeout=self.timeout)
        except TimeoutExpired:
            stdout = ''
            stderr = 'Timeout'
        stdout = stdout.decode('utf8').strip() if stdout else ' '
        stderr = stderr.decode('utf8').strip() if stderr else ' '
        return stdout, stderr

    def execute(self, params):
        logging.error("exec method not implemented!")

    def run(self, params):
        return json_normalize(self.execute(params))

class SLHARunner(BaseRunner):
    def __init__(self,conf):
        self.config = conf
        self.timeout = conf.get('timeout', 10)
        self.tpl = conf['template']
        self.blocks = conf.get('getblocks', [])
        self.rundir = os.getcwd()
        self.binaries = []
        self.binary = ""
        self.makedirs()

    def prepare(self, params):
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
        if not os.path.isfile(fout):
            return {'log': nan}
        slha = parseSLHA(fout, self.blocks)
        if self.config.get('constraints', False) and not self.constraints(slha):
            slha = {'log': nan}
        return slha

    def execute(self, params):
        fin, fout, flog = self.prepare(params)
        if not all([fin, fout, flog]):
            return {'log': 'Error preparing files'}

        stdout, stderr = self.runBinary(self.binary, fin, fout)
        slha = self.read(fout)

        if self.config.get('remove_slha', True):
            self.removeFile(fin)
            self.removeFile(fout)

        if self.config.get('keep_log', False) and (stdout or stderr):
            log = 'parameters: {}\nstdout: {}\nstderr: {}\n\n'.format(params,stdout, stderr)
            slha.update({ 'log': log })
            if self.config.get('logfiles', False):
                with open(flog, 'w') as logf:
                    logf.write(log)
                slha.update({ 'log': flog })
            logging.debug(log)
        return slha

class MICROMEGAS(SLHARunner):
    def __init_(self,conf):
        """need to compile micromegas for each runner since it uses hard coded paths"""
        self.config = conf
        self.timeout = conf.get('timeout', 10800)
        self.tpl = conf['template']
        self.blocks = conf.get('getblocks', [])
        self.rundir = os.getcwd()
        self.binaries = []
        self.binary = ""
        if 'micromegas' not in self.config or not os.path.exists(self.config['micromegas']):
            logging.error('need to specify "micromegas" sources files')
            exit(1)
        if 'modelname' not in self.config:
            logging.error('need to specify "modelname" name')
            exit(1)
        self.makedirs(tocopy = self.config['micromegas'])
        self.omegadir = os.path.join(self.rundir,os.path.basename(self.config['micromegas']))
        self.modeldir = os.path.join(self.omegadir, self.config['modelname'])
        os.chdir(self.omegadir)
        stderr, stdout = self.runBinary('make')
        os.chdir(self.modeldir)
        stderr, stdout = self.runBinary('make', 'main={}'+self.config['omegamain'])
        self.binaries = [
                self.binary,
                os.path.join(self.modeldir, self.config['omegamain'].replace('.cpp',''))
                ]

    def execute(self, params):
        fin, fout, flog = self.prepare(params)
        if not all([fin, fout, flog]):
            return {'log': 'Error preparing files'}

        stdoutSPheno, stderrSPheno = self.runBinary(self.binaries[0], fin, fout)
        if os.path.isfile(fout):
            stdoutOmega, stderrOmega = self.runBinary(self.binaries[1], fout)
        else:
            stdoutOmega, stderrOmega = "", ""
        stdout = stdoutSPheno + stdoutOmega
        stderr = stderrSPheno + stderrOmega
        slha = self.read(fout)

        if self.config.get('remove_slha', True):
            self.removeFile(fin)
            self.removeFile(fout)

        if self.config.get('keep_log', False) and (stdout or stderr):
            log = 'parameters: {}\nstdout: {}\nstderr: {}\n\n'.format(params,stdout, stderr)
            slha.update({ 'log': log })
            if self.config.get('logfiles', False):
                with open(flog, 'w') as logf:
                    logf.write(log)
                slha.update({ 'log': flog })
            logging.debug(log)
        return slha

RUNNERS = {
        'Base': BaseRunner,
        'SLHA': SLHARunner
        }
