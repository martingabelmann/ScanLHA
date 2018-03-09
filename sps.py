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
from pandas.io.json import json_normalize
from pandas import HDFStore
import json
import re

# scientific notation, see
# https://stackoverflow.com/questions/30458977/yaml-loads-5e-6-as-string-and-not-a-number
yaml.add_implicit_resolver(
    u'tag:yaml.org,2002:float',
    re.compile(u'''^(?:
     [-+]?(?:[0-9][0-9_]*)\\.[0-9_]*(?:[eE][-+]?[0-9]+)?
    |[-+]?(?:[0-9][0-9_]*)(?:[eE][-+]?[0-9]+)
    |\\.[0-9_]+(?:[eE][-+][0-9]+)?
    |[-+]?[0-9][0-9_]*(?::[0-5]?[0-9])+\\.[0-9_]*
    |[-+]?\\.(?:inf|Inf|INF)
    |\\.(?:nan|NaN|NAN))$''', re.X),
    list(u'-+0123456789.'))

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
                if not self.validate():
                    logging.error('Errorenous config file.')
                    exit(1)
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

    def setBlock(self, block, lines=[]):
        b = self.getBlock(block)
        if b:
            b['lines'] = lines
        else:
            self['blocks'].append({'block':block, 'lines': lines})

    def setLine(self, block, line):
        # add scan-parameter to config (if not already)
        b = self.getBlock(block)
        linepos = [i for i,l in enumerate(b['lines']) if 'id' in l and l['id'] == line['id']]
        if not b:
            return
        if not linepos:
            logging.info('Appending new line with ID %d.' % line['id'])
            b['lines'].append(line)
        else:
            logging.info('Updating line with ID %d.' % line['id'])
            b['lines'][linepos[0]] = line
        return self.validate()

    def validate(self):
        ok = True
        if 'blocks' not in self:
            logging.error("No 'blocks' section in config ")
            ok = False
        # check for double entries
        seen = []
        for block in self['blocks']:
            for line in block['lines']:
                if 'id' not in line:
                    logging.error('No ID set for line entry!')
                    ok = False
                if [block['block'],line['id']] in seen:
                    logging.error('Parameter {} in block {} set twice! Taking the first occurence.'.format(line['id'], block['block']))
                    ok = False
                if 'value' in line:
                    try:
                        float(line['value'])
                    except ValueError:
                        logging.error("'value' must be a number not {} ({}, {}).".format(str(type(line['value'])), block['block'], line['id']))
                        ok = False
                if 'values' in line and type(line['values']) != list and len(line['values']) < 1:
                    logging.error("'values' must be a nonemtpy list ({}, {}).".format(block['block'], line['id']))
                    ok = False
                if 'scan' in line and type(line['scan']) != list and len(line['scan']) < 2:
                    logging.error("'scan' must be a nonemtpy list ({}, {}).".format(block['block'], line['id']))
                    ok = False
                seen.append([block['block'], line['id']])
        return ok

def genSLHA(blocks):
    """generate SLHA"""
    out = ''
    for block in blocks:
        out += 'BLOCK {}\n'.format(block['block'])
        for data in block['lines']:
            data = defaultdict(str,data)
            if 'scan' in data or 'values' in data:
                data['value'] = '{%' + str(data['id']) + block['block'] + '%}'
            out += '{id} {value} #{parameter} {comment}\n'.format_map(data)
    return out

# recursively convert [1,2,3,4] to {1:{2:{3:4}}
def list2dict(l):
    if len(l) == 1:
        return l[0]
    return { l[0] : list2dict(l[1:]) }

# merge list of nested dicts
def mergedicts(l, d):
    if type(l) == list:
        d.update(l[0])
        for dct in l[1:]:
            mergedicts(dct, d)
        return d
    elif type(l) == dict:
        for k,v in l.items():
            if k in d and isinstance(d[k], dict):
                mergedicts(l[k], d[k])
            else:
                d[k] = l[k]

def parseSLHA(slhafile, blocks=[]):
    try:
        with open(slhafile,'r') as f:
            slha = pylha.load(f)
    except FileNotFoundError:
        logging.error('File %s not found.' % slhafile)
        return -2
    except:
        logging.error('Could not parse %s !' % slhafile)
        return -3
    slha_block = slha['BLOCK']
    if blocks:
        slha_block = { b : v for b,v in slha_block.items() if b in blocks }
    for b,v in slha_block.items():
        if 'values' in v:
            v['values'] = mergedicts([list2dict(l) for l in v['values']],{})
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
        self.binary = self.config.get('binary', './SPheno')
        if not os.path.isfile(self.binary):
            logging.error('SPheno binary %s not found!' % self.binary)
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

        proc = Popen([self.binary, fin, fout], stderr=STDOUT, stdout=PIPE)
        pipe = proc.communicate(timeout=self.timeout)
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
        if os.path.isfile(fout):
            slha = parseSLHA(fout, self.blocks)
            if self.config.get('keep_slha', False):
                os.remove(fout)
                os.remove(fin)
            return slha
        elif os.path.isfile(flog):
            logging.debug(log)
            return {'log':fname + '.log'}
        else:
            return {'error': -4}

class Scan():
    def __init__(self, c, getblocks=[]):
        self.config = c
        self.template = genSLHA(c['blocks'])
        self.getblocks = getblocks
        self.spheno = SPheno(c['spheno'], self.template, self.getblocks)
        self.scanset = []
        scan = None
        for block in c['blocks']:
            for line in block['lines']:
                if 'scan' in line:
                    self.addScanRange(block['block'], line)
                    scan = True
                elif 'values' in line:
                    self.addScanValues(block['block'], line)
                    scan = True
        if not scan:
            logging.warning("No scan parameters defined in config!")
            logging.warning("Register a scan range with addScanRange(<block>, {'id': <para-id>, 'scan': [<start>,<end>,<stepsize>]})")
            logging.warning("Register a list of scan values with  addScanValues(<block>,{'id': <para-id>, 'values': [1,3,6,...])")

    def addScanRange(self, block, line):
        if 'id' not in line:
            logging.error("No 'id' set for parameter.")
            return
        if 'scan' not in line or len(line['scan']) < 2:
            logging.error("No proper 'scan' option set for parameter %d." % line['id'])
            return
        dist = self.config.distribution.get(line['distribution'], linspace) if 'distribution' in line else linspace
        line['scan'] = [ eval(str(s)) for s in line['scan'] ]
        line.update({'values': dist(*line['scan'])})
        self.addScanValues(block, line)

    def addScanValues(self, block, line):
        if 'id' not in line:
            logging.error("No 'id' set for parameter.")
            return
        if 'values' not in line or len(line['values']) < 1:
            logging.error("No proper 'values' option set for paramete %d." % line['id'])
            return
        self.config.setLine(block, line)
        # update the slha template with new config
        self.template = genSLHA(self.config['blocks'])

    def _substitute(self, param_tuple):
        return { p : eval(str(v).format_map(dict(ChainMap(*param_tuple)))) for p,v in dict(ChainMap(*param_tuple)).items() }

    def build(self,num_workers=4):
        values = []
        for block in self.config['blocks']:
            for line in block['lines']:
                if 'values' in line:
                    values.append([{str(line['id']) + block['block']: num} for num in line['values']])
        self.numparas = prod([len(v) for v in values])
        logging.info('Build all %d parameter poins.' % self.numparas)
        self.scanset = [ self._substitute(s) for s in list(product(*values)) ]

        if self.scanset:
            return self.numparas
        return

    def _run(self, dataset):
        logging.info(str(len(dataset)))
        return [ self.spheno.run(d) for d in dataset ]

    def submit(self,w=None):
        w = os.cpu_count() if not w else w
        chunks = int(self.numparas/w)
        self.scanset = [self.scanset[i:i+chunks] for i in range(0, self.numparas, chunks)]
        with ThreadPoolExecutor(w) as executor:
            self.results = json_normalize(json.loads(json.dumps(
                            [ r for rset in executor.map(self._run, self.scanset) for r in rset ]
                            )))
        self.scanset = [ s for sset in self.scanset for s in sset ]

    def submit2(self,w):
        with ThreadPoolExecutor(w) as executor:
            self.results = json_normalize(json.loads(json.dumps(list(executor.map(self.spheno.run, self.scanset)))))

    def save(self, filename='store.hdf'):
        store = HDFStore(filename)
        store['results'] = self.results
        store.close()

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
