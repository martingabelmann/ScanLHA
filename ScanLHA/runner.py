from collections import defaultdict
import logging
from subprocess import Popen, STDOUT, PIPE
from .slha import parseSLHA
from random import randrange
from numpy import nan
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
                logging.error("Could not substitute ", params)

        proc = Popen([self.config['binary'], fin, fout], stderr=STDOUT, stdout=PIPE)
        pipe = proc.communicate(timeout=self.timeout)
        if os.path.isfile(fout):
            slha = parseSLHA(fout, self.blocks)
            if not self.config.get('keep_slha', False):
                os.remove(fout)
                os.remove(fin)
            return slha
        if not self.config.get('keep_log', False):
            return { 'log': nan }
        log = ''
        for p in pipe:
            if not p:
                continue
            with open(flog, 'w') as logf:
                log += 'parameters: {} \nmessage: {}\n\n'.format(
                            str(params),
                            p.decode('utf8').strip()
                        )
                logf.write(log)
        if os.path.isfile(flog):
            logging.debug(log)
        return { 'log': flog }
