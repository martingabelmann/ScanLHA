from collections import defaultdict
import logging
from subprocess import Popen, STDOUT, PIPE, TimeoutExpired
from .slha import parseSLHA
from random import randrange,randint
import os
from numpy import nan
from shutil import copy2, rmtree
from tempfile import mkdtemp
from pandas.io.json import json_normalize

class BaseRunner():
    def __init__(self,conf):
        self.config = conf

    def makedirs(self):
        if 'tmpfs' not in self.config:
            if os.path.exists('/dev/shm/'):
                self.config['tmpfs'] = '/dev/shm/'
            else:
                self.config['tmpfs'] = mkdtemp()
        self.config['rundir'] = os.path.join(self.config['tmpfs'], 'run%d' % randint(100,999))
        if not os.path.exists(self.config['rundir']):
            logging.info('Creating temporary directory {}.'.format(self.config['rundir']))
            os.makedirs(self.config['rundir'])
        if 'binary' in self.config:
            if not os.path.isfile(self.config['binary']):
                logging.error('Binary %s not found!' % self.config['binary'])
                exit(1)
            logging.info('Copying binary {} into temporary directory {}.'.format(self.config['binary'], self.config['rundir']))
            copy2(self.config['binary'], os.path.join(self.config['rundir'],'bin'))
            logging.info('Changing directory')
            os.chdir(self.config['rundir'])

    def cleanup(self):
        if not self.config.get('cleanup', False):
            return
        try:
            logging.info('Removing temporary directory {}'.format(self.config['rundir']))
            os.chdir('/')
            rmtree(self.config['rundir'])
        except FileNotFoundError:
            logging.error('Directory {} does not exist.'.format(self.config['rundir']))
        except:
            logging.error('Could not remove directory {}.'.format(self.config['rundir']))

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
        self.makedirs()

    def prepare(self, params):
        fname = str(randrange(10**10))
        fin  = os.path.join(self.config['rundir'], fname + '.in')
        fout = os.path.join(self.config['rundir'], fname + '.out')
        flog = os.path.join(self.config['rundir'], fname + '.log')

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
            return {}
        slha = parseSLHA(fout, self.blocks)
        if self.config.get('constraints', False) and not self.constraints(slha):
            slha = {}
        return slha

    def execute(self, params):
        slha = {'log': nan}
        fin, fout, flog = self.prepare(params)
        if not all([fin, fout, flog]):
            return {'log': 'Error preparing files'}

        stdout, stderr = self.runBinary(self.config['binary'], fin, fout)
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
