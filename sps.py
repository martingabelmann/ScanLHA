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
from numpy import linspace, prod
from concurrent.futures import ThreadPoolExecutor
from itertools import product
from random import randrange

logging.getLogger().setLevel(logging.INFO)

class Config(dict):
    def __init__(self,src):
        self.src = src
        self.load()

    def load(self):
        try:
            with open(self.src, 'r') as c:
                self.update(yaml.safe_load(c))
        except Exception as e:
            logging.error("failed to load " + self.src)
            logging.error(str(e))

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
        logging.error('File ' + slhafile + ' not found.')
        return -2
    except:
        print('Could not parse ' + slhafile + '!')
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
        self.scanparas = defaultdict(defaultdict)
        for block in c['blocks']:
            for p in block['lines']:
                if 'scan' in p:
                    self.scanparas[block['block']][p['id']] = p['scan']
        if not self.scanparas:
            logging.warning("No scan parameters defined in condig!")
            logging.warning("Register a scan with registerScan(<block>, <para-id>, [<start>,<end>,<stepsize>])")

    def addToTemplate(self, block, paraid, scanrange, parameter=None, comment=None):
        # add scan-parameter to config (if not already)
        if len(scanrange) != 3:
            logging.error("No proper 'scan' option set for parameter: " + paraid)
            return
        if 'blocks' not in self.config:
            logging.error("No 'blocks' section in config ")
            return
        blockpos = [i for i,b in enumerate(self.config['blocks']) if b == block]
        if len(blockpos) != 1:
            logging.error('Block "' + block + ' should appear exactly once in Block ' + block)
        lines = self.config['blocks'][blockpos[0]]['lines']
        linepos = [i for i,l in enumerate(lines) if 'id' in l and l['id'] == paraid]
        if not linepos:
            lines.append({'parameter':parameter,'id':paraid,'scan':scanrange,'comment':comment})
        elif len(linepos) > 1:
            logging.error('Parameter with id ' + paraid + ' has multiple occurence in config')
            return
        else:
            if not parameter and 'parameter' in lines[linepos[0]]:
                parameter = lines[linepos[0]]['parameter']
            if not comment and 'comment' in lines[linepos[0]]:
                comment = lines[linepos[0]]['comment']
            lines[linepos[0]] = {'parameter':parameter,'id':paraid,'scan':scanrange,'comment':comment}

        # update the slha template with new config
        self.template = genSLHA(self.config['blocks'])
        return self.template

    def buildScanset(self, maxram=0.1, threads=4):
        numparas = prod([p[2] for paras in self.scanparas.values() for p in paras.values()])
        logging.info('Expanding scan ranges for scan parameters.')
        values = []
        for block,paras in self.scanparas.items():
            for p,scan in paras.items():
                values.append([{str(p) + block: num} for num in linspace(*scan)])

        logging.info('Build all ' + str(numparas) + ' combinations.')
        self.scanset = list(product(*values))
        return numparas

    def registerScan(self, block, paraid, scanrange, parameter=None, comment=None):
        if self.addToTemplate(block,paraid,scanrange,parameter,comment):
            self.scanparas[block][paraid] = scanrange
            return self.scanparas
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
