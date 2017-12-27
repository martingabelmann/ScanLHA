#!/usr/bin/env python3
# pylint: disable=broad-except

import argparse
import yaml
import pyslha
# import lzma
import logging
from subprocess import Popen, STDOUT, PIPE
from collections import defaultdict
import os
from numpy import arange
import pandas
from concurrent.futures import ThreadPoolExecutor
from itertools import combinations

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
        out += 'Block {}\n'.format(block['block'])
        for data in block['lines']:
            data = defaultdict(str,data)
            if 'scan' in data:
                data['value'] = '{%' + str(data['id']) + '%}'
            out += '{id} {value} #{comment}\n'.format_map(data)
    return out

def parseSLHA(slhafile):
    """TODO: use something faster"""
    try:
        rawslha = pyslha.read(slhafile)
        blocks = { ''.join(block) : pandas.Series(dict(rawslha.blocks[block].items())) for block in rawslha.blocks }
        # decays = pandas.Series({ ''.join(decay) : pandas.Series(dict(rawslha.decays[decay].items())) for decay in rawslha.decays })
        # xsections = pandas.Series({ ''.join(x)  : pandas.Series(dict(rawslha.xsectionss[x].items())) for x in rawslha.xsections })
        slha = blocks
    except Exception as e:
        print(str(e))
        slha = None
    return slha


class SPheno():
    def __init__(self, conf, tpl):
        self.config = conf
        self.tpl = tpl
        if 'slhadir' not in conf:
            self.config['slhadir'] = '/tmp/slha'
        if not os.path.exists(self.config['slhadir']):
            os.makedirs(self.config['slhadir'])

    def run(self, params):
        fname = '_'.join(['{}.{}'.format(p,v) for p,v in params.items()])
        fin  = "{}/SLHA.{}.in".format(self.config['slhadir'], fname)
        fout = "{}/SLHA.{}.out".format(self.config['slhadir'], fname)
        with open(fin, 'w') as inputf:
            params = defaultdict(str, { '%{}%'.format(p) : v for p,v in params.items() })
            inputf.write(self.tpl.format_map(params))

        proc = Popen([self.config.get('binary', './SPheno'), fin, fout], stderr=STDOUT, stdout=PIPE)
        pipe = proc.communicate(timeout=5)
        for p in pipe:
            if not p:
                continue
            with open(fout + '.log', 'w') as logf:
                logf.write('parameters: {} \nmessage: {}'.format(
                            str(params),
                            p.decode('utf8').strip()
                            ))
        if os.path.isfile(fout):
            os.remove(fin)
            return parseSLHA(fout)
        else:
            return fout + '.log'

class Scan():
    def __init__(self, c):
        self.config = c
        self.template = genSLHA(c['blocks'])
        self.spheno = SPheno(c['spheno'], self.template)
        self.scanset = []
        self.parameters = {}
        for block in c['blocks']:
            for p in block['lines']:
                if 'scan' in p:
                    self.registerscan(p['id'],p['scan'])
        if not self.parameters:
            logging.warning("No scan parameters given!")

    # TODO:
    # ability to split/parallelize scan-range over qsub
    def registerscan(self,ID,scanrange):
        """
        self.scanset = [{'param1':'value1','param2':'value2'},{'param1':'value3','param2':'value4'},...]
        """
        if len(scanrange) == 3:
            self.parameters.update({ID:scanrange})
        else:
            logging.error("No proper 'scan' option set for parameter: " + ID)
        values = [ [id,i] for id,scan in self.parameters.items() for i in arange(*scan)]
        allcombinations = combinations(values, len(self.parameters))
        self.scanset = []
        for c in allcombinations:
            s = { id:value for id,value in c}
            if len(s) < len(self.parameters):
                continue
            self.scanset.append(s)

    def submit(self,w):
        with ThreadPoolExecutor(w) as executor:
            self.results = executor.map(self.spheno.run, self.scanset)
            self.data = pandas.Series([ { 'parameter': p, 'blocks': v} for p,v in zip(self.scanset, self.results)])
        return self.data

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
