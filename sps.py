#!/usr/bin/env python3
# pylint: disable=broad-except

import argparse
import yaml
import pylha
# import lzma
import logging
from subprocess import Popen, STDOUT, PIPE
from collections import defaultdict,ChainMap
import os
from numpy import linspace, logspace, geomspace, arange, prod
from concurrent.futures import ThreadPoolExecutor
from itertools import product
from random import randrange

logging.getLogger().setLevel(logging.INFO)

class Config(dict):
    def __init__(self,src):
        self.src = src
        self.distribution = {
                'linear': linspace,
                'log': logspace,
                'geom': geomspace,
                'arange': arange
                }
        self.load()

    def load(self):
        try:
            with open(self.src, 'r') as c:
                self.update(yaml.safe_load(c))
                self.validate()
        except FileNotFoundError:
            logging.error('File {} not found.' % self.src)
            return -2
        except Exception as e:
            logging.error("failed to load config file " + self.src)
            logging.error(str(e))

    def getBlock(self, block):
        blockpos = [i for i,b in enumerate(self['blocks']) if b['block'] == block]
        if not blockpos:
            return
        return self['blocks'][blockpos[0]]

    def getLine(self, block, id):
        b = self.getBlock(block)
        if not b:
            logging.error('Block {} not present in config.' % block)
            return
        lines = b['lines']
        linepos = [i for i,l in enumerate(lines) if 'id' in l and l['id'] == id]
        if not linepos:
            return
        return lines[linepos[0]]

    def validate(self):
        if 'blocks' not in self:
            logging.error("No 'blocks' section in config ")
            return
        # check for double entries
        seen = []
        for block in self['blocks']:
            for line in block['lines']:
                if 'id' not in line:
                    logging.error('No ID set for line entry!')
                    continue
                if [block['block'],line['id']] in seen:
                    logging.error('Parameter {} in block {} set twice! Taking the first occurence.'.format(line['id'], block['block']))
                    continue
                seen.append([block['block'], line['id']])

def genSLHA(blocks):
    """generate SLHA"""
    out = ''
    for block in blocks:
        out += 'BLOCK {}\n'.format(block['block'])
        for data in block['lines']:
            data = defaultdict(str,data)
            if 'scan' in data:
                data['value'] = '{%' + str(data['id']) + block['block'] + '%}'
            out += '{id} {value} #{comment}\n'.format_map(data)
    return out

def parseSLHA(slhafile, blocks=[]):
    try:
        with open(slhafile,'r') as f:
            slha = pylha.load(f)
    except FileNotFoundError:
        logging.error('File {} not found.' % slhafile)
        return -2
    except:
        logging.error('Could not parse {} !' % slhafile)
        return -3
    slha_block = slha['BLOCK']
    if blocks:
        slha_block = { b : v for b,v in slha_block.items() if b in blocks }
    return slha_block

class SPheno():
    def __init__(self, conf, tpl, blocks=[]):
        self.config = conf
        self.timeout = conf.get('timeout', 10)
        self.tpl = tpl
        self.blocks = blocks
        if 'slhadir' not in conf:
            self.config['slhadir'] = '/tmp/slha'
        if not os.path.exists(self.config['slhadir']):
            os.makedirs(self.config['slhadir'])

    def run(self, params):
        if type(params) != dict:
            try:
                params = dict(ChainMap(*params))
            except:
                logging.error('Could not read params: ', params)
                return -5
        # TODO: Too long filenames/argument for subprocess?
        # fname = '_'.join(['{}.{}'.format(p,v) for p,v in params.items()])
        fname = '%030x' % randrange(16**30)
        fin  = "{}/{}.in".format(self.config['slhadir'], fname)
        fout = "{}/{}.out".format(self.config['slhadir'], fname)
        with open(fin, 'w') as inputf:
            params = defaultdict(str, { '%{}%'.format(p) : v for p,v in params.items() })
            inputf.write(self.tpl.format_map(params))

        proc = Popen([self.config.get('binary', './SPheno'), fin, fout], stderr=STDOUT, stdout=PIPE)
        pipe = proc.communicate(timeout=self.timeout)
        log = ''
        for p in pipe:
            if not p:
                continue
            with open(fout + '.log', 'w') as logf:
                log += 'parameters: {} \nmessage: {}\n\n'.format(
                            str(params),
                            p.decode('utf8').strip()
                        )
                logf.write(log)
        if os.path.isfile(fout):
            slha = parseSLHA(fout, self.blocks)
            if self.config.get('keep_slha', False):
                os.remove(fout)
                os.remove(fin)
            return slha
        elif os.path.isfile(fout + '.log'):
            logging.warning(log)
            return fname + '.log'
        else:
            return -4

class Scan():
    def __init__(self, c, getblocks=['MASS']):
        self.config = c
        self.template = genSLHA(c['blocks'])
        self.getblocks = getblocks
        self.spheno = SPheno(c['spheno'], self.template, self.getblocks)
        self.scanset = []
        self.values = []
        for block in c['blocks']:
            for line in block['lines']:
                if 'scan' in line:
                    self.addScanRange(block['block'], line)
                elif 'values' in line:
                    self.addValues(block['block'], line)
        if not self.values:
            logging.warning("No scan parameters defined in config!")
            logging.warning("Register a scan range with addScanRange(<block>, {'id': <para-id>, 'scan': [<start>,<end>,<stepsize>]})")
            logging.warning("Register a list of scan values with  addScanValues(<block>,{'id': <para-id>, 'values': [1,3,6,...])")

    def addScanRange(self, block, line):
        if 'id' not in line:
            logging.error("No 'id' set for parameter.")
            return
        if 'scan' not in line or len(line['scan']) != 3:
            logging.error("No proper 'scan' option set for parameter %d." % line['id'])
            return
        # add scan-parameter to config (if not already)
        b = self.config.getBlock(block)
        l = self.config.getLine(block, line['id'])
        if not b:
            return
        if not l:
            logging.debug('Appending new line with ID %d.' % line['id'])
            b['lines'].append(line)
        else:
            logging.debug('Updating line with ID %d.' % line['id'])
            l = line
        dist = self.config.distribution.get(line['distribution'], linspace) if 'distribution' in line else linspace
        l.update({'values': dist(*line['scan'])})
        self.addScanValues(block, line)

    def addScanValues(self, block, line):
        if 'id' not in line:
            logging.error("No 'id' set for parameter.")
            return
        if 'values' not in line or len(line['values']) < 1:
            logging.error("No proper 'values' option set for paramete %d." % line['id'])
            return

        # update the slha template with new config
        self.template = genSLHA(self.config['blocks'])
        self.values.append([{str(line['id']) + block: num} for num in line['values']])

    def build(self):
        numparas = prod([len(v) for v in self.values])
        logging.info('Expanding scan ranges for scan parameters.')
        logging.info('Build all %d parameter poins.' % numparas)
        self.scanset = list(product(*self.values))
        if self.scanset:
            return numparas
        return

    # TODO:
    # ability to split/parallelize scan-range over qsub
    def submit(self,w):
        with ThreadPoolExecutor(w) as executor:
            self.results = zip(self.scanset,executor.map(self.spheno.run, self.scanset))

    def save(self):
        pass

class Plot():
    def __init__(self,data):
        pass

    def show():
        pass

    def save():
        pass

def parse_args():
    parser = argparse.ArgumentParser(description="Perform a scan with SPheno.")
    parser.add_argument('config', help='yaml config file', nargs='?', default='config.yml')
    parser.add_argument('--verbose', '-v', action='count', help='more output', default=0)
    args = parser.parse_args()
    return args

def main():
    pass

if __name__ == "__main__":
    main()
