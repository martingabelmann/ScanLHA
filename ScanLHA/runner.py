from collections import defaultdict
import logging
from subprocess import Popen, STDOUT, PIPE, TimeoutExpired
from .slha import parseSLHA
from random import randrange,randint
import os
from shutil import copy2, rmtree
from tempfile import mkdtemp

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
        if not self.config.get('constraints', False):
            return result
        try:
            if not all(map(eval, self.config['constraints'])):
                raise(ValueError)
            return result
        except KeyError as e:
            return { 'log': 'invalid constraint: {}'.format(e) }
        except ValueError:
            return
        except Exception as e:
            return {'log' : str(e)}

    def run(self, params):
        logging.error("run method not implemented!")

class SLHARunner(BaseRunner):
    def __init__(self,conf):
        self.config = conf
        self.timeout = conf.get('timeout', 10)
        self.tpl = conf['template']
        self.blocks = conf.get('getblocks', [])
        self.makedirs()

    def run(self, params):
        slha = {}
        # TODO: Too long filenames/argument for subprocess?
        # fname = '_'.join(['{}.{}'.format(p,v) for p,v in params.items()])
        fname = str(randrange(10**10))
        fin  = os.path.join(self.config['rundir'], fname + '.in')
        fout = os.path.join(self.config['rundir'], fname + '.out')
        flog = os.path.join(self.config['rundir'], fname + '.log')

        with open(fin, 'w') as inputf:
            try:
                params = defaultdict(str, { '%{}%'.format(p) : v for p,v in params.items() })
                inputf.write(self.tpl.format_map(params))
            except KeyError:
                err = "Could not substitute {}.".format(params)
                logging.error(err)
                return { 'log': err }

        proc = Popen([self.config['binary'], fin, fout], stderr=STDOUT, stdout=PIPE)
        try:
            stdout, stderr = proc.communicate(timeout=self.timeout)
        except TimeoutExpired:
            stdout = ''
            stderr = 'Timeout'
        if os.path.isfile(fout):
            slha = parseSLHA(fout, self.blocks)
            if self.config.get('remove_slha', True):
                try:
                    os.remove(fout)
                except FileNotFoundError:
                    logging.error('Output file {} missing?'.format(fout))
        if self.config.get('remove_slha', True):
            try:
                os.remove(fin)
            except FileNotFoundError:
                logging.error('Input file {} missing?'.format(fin))
        if (stdout or stderr) and self.config.get('keep_log', True):
            stdout = stdout.decode('utf8').strip() if stdout else ' '
            stderr = stderr.decode('utf8').strip() if stderr else ' '
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
