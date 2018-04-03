#!/usr/bin/env python3
import argparse
from .scan import Scan
from .config import Config
from IPython import embed
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d, interp2d
from collections import defaultdict, OrderedDict

class keydict(defaultdict):
    def __missing__(self, key):
        return key

BLOCKS = defaultdict(OrderedDict)
"""
BLOCKS["MSSM"]["MINPAR"] = { 'At' : 1, 'TanBeta': 2, ...}
BLOCKS["NMSSM"]["MINPAR"] = { 'At' : 2, 'TanBeta': 3, 'Lambda': 1 ...}
"""

VALUES = defaultdict(dict)
"""
VALUES['At'] = { 'value': 0 }
VALUES['TanBeta'] = { 'values': [1,4] }
VALUES['Lambda'] = { 'scan': [0,1,10] }
"""

LATEX = keydict()
"""
LATEX['TanBeta'] = "\\tan\\beta"
"""

CONF = None


def blockfrompara(para,blocks):
    block = [ k for k,v in blocks.items() if para in v ]
    if len(block) > 1:
        print('Parameters not uniquely!')
        exit(1)
    if len(block) == 0:
        return
    return block[0]

def getPara(para,model):
    block = blockfrompara(para, BLOCKS[model])
    if block and para in BLOCKS[model][block]:
        return (block, BLOCKS[model][block][para])
    return

def runScan(model, conf=CONF, binary=None, getblocks=[]):
    blocks = BLOCKS[model]
    parameters = [j for i in blocks.values() for j in i.keys()]
    if len(parameters) != len(set(parameters)):
        print('Parameters not uniquely!')
        exit(1)
    for block in blocks.keys():
        conf.setBlock(block)

    for para, value in VALUES.items():
        block = blockfrompara(para, blocks)
        paraid = BLOCKS[model][block][para]
        line = { 'parameter': para, 'id': paraid }
        line.update(value)
        conf.setLine('MINPAR', line)
        if binary:
            conf['spheno']['binary'] = binary
        print('scanning ' + model + ' ...')
        scan = Scan(conf,getblocks=getblocks)
        scan.submit()
        if 'log' in scan.results:
            failed = len([ r for r in scan.results['log'] if type(r) == str ])
            print("{} out of {} points are invalid.".format(failed, scan.numparas))
        return scan.results

def getSubPlot(model, r, xpara, ypara, filters):
    for para,value in filters.items():
        block = blockfrompara(para, BLOCKS[model])
        paraid = '{}.values.{}'.format(block, BLOCKS[model][block][para])
        filtered = r.loc[r[paraid] == value]
    xkey = '{}.values.{}'.format(*getPara(xpara,model))
    ykey = '{}.values.{}'.format(*getPara(ypara,model))
    return (list(filtered[xkey]), list(filtered[ykey]))

def parse_args():
    parser = argparse.ArgumentParser(description="Perform a scan with SPheno.")
    parser.add_argument('config', help='yaml config file', nargs='?', default='config.yml')
    parser.add_argument('--verbose', '-v', action='count', help='more output', default=0)
    args = parser.parse_args()
    return args

def main():
    global CONF
    if CONF:
        CONF = Config('configs/SPheno.yml')
    embed()
