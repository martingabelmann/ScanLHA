from collections import defaultdict
import logging
from subprocess import Popen, STDOUT, PIPE, DEVNULL, TimeoutExpired
from .slha import parseSLHA
from random import randrange,randint
import os
from sys import exit
from numpy import nan
from math import *
from shutil import copy2,copytree, rmtree
from tempfile import mkdtemp
from pandas.io.json import json_normalize

class BaseRunner():
    def __init__(self,conf):
        self.config = conf
        self.rundir = os.getcwd()
        self.binaries = []
        self.binary = ""
        self.HiggsBounds = False
        self.tmp = False
        self.initialized = False

    def makedirs(self, tocopy=[]):
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
            self.binary = os.path.join(self.rundir, os.path.basename(self.config['binary']))
            tocopy.append(self.config['binary'])
        if 'HiggsBounds' in self.config:
            tocopy.append(self.config['HiggsBounds'])
            self.HiggsBounds = os.path.join(self.rundir, os.path.basename(self.config['HiggsBounds']))
        if 'binaries' in self.config:
            tocopy += self.config['binaries']
            self.binaries = [os.path.join(self.rundir, os.path.basename(b)) for b in self.config['binaries']]
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
        try:
            if not all(map(eval, self.config['constraints'])):
                return
            return True
        except KeyError:
            return True
        return

    @staticmethod
    def removeFile(f, err=True):
        try:
            os.remove(f)
        except FileNotFoundError:
            if err:
                logging.error('file {} missing?'.format(f))

    def runBinary(self, *args, cwd = None): # noqa
        proc = Popen(list(args), cwd=cwd, stderr=STDOUT, stdout=PIPE)
        try:
            stdout, stderr = proc.communicate(timeout=self.timeout)
        except TimeoutExpired:
            stdout = ''
            stderr = 'Timeout'
            return stdout, stderr
        stdout = stdout.decode('utf8').strip() if stdout else ' '
        stderr = stderr.decode('utf8').strip() if stderr else ' '
        return stdout, stderr

    def execute(self, params):
        logging.error("exec method not implemented!")

    def run(self, params):
        return json_normalize(self.execute(params))

class SLHARunner(BaseRunner):
    def __init__(self,conf):
        super().__init__(conf)
        self.timeout = conf.get('timeout', 10)
        self.tpl = conf['template']
        self.blocks = conf.get('getblocks', [])
        self.makedirs()
        self.initialized = True

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
            self.removeFile(fout, err=False)

        if self.config.get('keep_log', False) and (stdout or stderr):
            log = 'parameters: {}\nstdout: {}\nstderr: {}\n\n'.format(params,stdout, stderr)
            slha.update({ 'log': log })
            if self.config.get('logfiles', False):
                with open(flog, 'w') as logf:
                    logf.write(log)
                slha.update({ 'log': flog })
            logging.debug(log)
        return slha

class MicrOmegas(SLHARunner):
    def __init__(self,conf):
        super(SLHARunner, self).__init__(conf)
        """need to compile micromegas for each runner since it uses hard coded paths"""
        self.timeout = conf.get('timeout', 18000)
        self.tpl = conf['template']
        self.blocks = conf.get('getblocks', [])
        if 'micromegas' not in self.config or not os.path.exists(self.config['micromegas']):
            logging.error('need to specify "micromegas" sources files')
            exit(1)
        if 'modelname' not in self.config:
            logging.error('need to specify "modelname" name')
            exit(1)
        self.makedirs(tocopy = self.config['micromegas'])
        self.omegadir = os.path.join(self.rundir,os.path.basename(self.config['micromegas']))
        self.modeldir = os.path.join(self.omegadir, self.config['modelname'])
        logging.debug('running "make clean" on MicrOmegas installtion.')
        Popen('yes|make clean', shell=True, stdout=DEVNULL, stderr=DEVNULL, cwd=self.omegadir)
        logging.debug('running "make" on MicrOmegas installtion.')
        i = 0
        while not os.path.isfile(self.omegadir + '/include/microPath.h') and i < 15:
            stdout, stderr = self.runBinary('make', cwd=self.omegadir)
            i += 1
        if i >= 5:
            logging.error('Build failed')
            logging.error(stdout)
            logging.error(stderr)
        logging.debug('running "make clean" on MicrOmegas model.')
        os.chdir(self.modeldir)
        Popen(['make', 'clean'], stdout=DEVNULL, stderr=DEVNULL, shell=True, cwd=self.modeldir)
        logging.debug('running "make main={}" on MicrOmegas model.'.format(self.config['omegamain']))
        omegabin = self.config['omegamain'].replace('.cpp','')
        i = 0
        while not os.path.isfile(omegabin) and i < 15:
            stdout, stderr = self.runBinary('make', 'main='+self.config['omegamain'], cwd=self.modeldir)
            i += 1
        if os.path.isfile(omegabin):
            self.initialized = True
        else:
            logging.error(stdout)
            logging.error(stderr)
        os.chdir(self.rundir)
        self.binaries = [
                self.binary,
                os.path.join(self.modeldir, omegabin)
                ]

    def execute(self, params):
        fin, fout, flog = self.prepare(params)
        if not all([fin, fout, flog]):
            return {'log': 'Error preparing files'}

        stdoutSPheno, stderrSPheno = self.runBinary(self.binaries[0], fin, fout)
        slha = self.read(fout) # need to read twice to check constraints before running MicrOmegas
        if 'log' in slha:
            slha.pop('log')
        if os.path.isfile(fout) and slha:
            stdoutOmega, stderrOmega = self.runBinary(self.binaries[1], fout)
            if self.HiggsBounds:
                stdoutHB, stderrHB = self.runBinary(self.HiggsBounds, 'LandH', 'SLHA', '3', '0', fout)
        else:
            stdoutOmega, stderrOmega = "", ""
            stdoutHB, stderrHB = "", ""
        stdout = stdoutSPheno + stdoutOmega + stdoutHB
        stderr = stderrSPheno + stderrOmega + stdoutHB
        slha = self.read(fout)

        if self.config.get('remove_slha', True):
            self.removeFile(fin)
            self.removeFile(fout, err=False)

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
        'SLHA': SLHARunner,
        'MicrOmegas': MicrOmegas
        }
