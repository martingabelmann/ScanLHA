from collections import defaultdict
import logging
from subprocess import Popen, STDOUT, PIPE
from .slha import parseSLHA
from random import randrange
import os

class Runner():
    def __init__(self, conf, tpl, blocks=[]):
        self.config = conf
        self.timeout = conf.get('timeout', 10)
        self.tpl = tpl
        self.blocks = blocks
        if 'tmpfs' not in conf:
            self.config['tmpfs'] = '/tmp/'
        self.config['slhadir'] = self.config['tmpfs'] + 'slha/'
        if not os.path.exists(self.config['slhadir']):
            os.makedirs(self.config['slhadir'])
        if 'binary' not in self.config:
            logging.error('No binary given')
            exit(1)
        if not os.path.isfile(self.config['binary']):
            logging.error('Binary %s not found!' % self.config['binary'])
            exit(1)
        # TODO: copy binary into ram, execute from ram directory

    def run(self, params):
        slha = {}
        # TODO: Too long filenames/argument for subprocess?
        # fname = '_'.join(['{}.{}'.format(p,v) for p,v in params.items()])
        fname = '%030x' % randrange(16**30)
        fin  = "{}/{}.in".format(self.config['slhadir'], fname)
        fout = "{}/{}.out".format(self.config['slhadir'], fname)
        flog = "{}/{}.log".format(self.config['slhadir'], fname)
        with open(fin, 'w') as inputf:
            try:
                params = defaultdict(str, { '%{}%'.format(p) : v for p,v in params.items() })
                inputf.write(self.tpl.format_map(params))
            except KeyError:
                err = "Could not substitute {}.".format(params)
                logging.error(err)
                return { 'log': err }

        proc = Popen([self.config['binary'], fin, fout], stderr=STDOUT, stdout=PIPE)
        stdout, stderr = proc.communicate(timeout=self.timeout)
        if self.config.get('remove_slha', True):
            try:
                os.remove(fin)
            except FileNotFoundError:
                logging.error('Input file {} missing?'.format(fin))
        if os.path.isfile(fout):
            slha = parseSLHA(fout, self.blocks)
            try:
                os.remove(fout)
            except Exception as e:
                logging.error('Could not remove output file {}: {}'.format(fout, str(e)))

        if (stdout or stderr) and self.config.get('keep_log', True):
            stdout = stdout.decode('utf8').strip() if stdout else ' '
            stderr = stderr.decode('utf8').strip() if stderr else ' '
            log = 'parameters: {}\nstdout: {}\nstderr: {}\n\n'.format(params,stdout, stderr)
            slha.update({ 'log': log })
            if self.config.get('logfile', False):
                with open(flog, 'w') as logf:
                    logf.write(log)
                slha.update({ 'log': flog })
            logging.debug(log)
        return slha
