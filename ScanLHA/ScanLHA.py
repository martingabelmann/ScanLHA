#!/usr/bin/env python3
import argparse
import os
from .scan import Scan
from .config import Config
from IPython import embed
from copy import deepcopy
from collections import defaultdict, OrderedDict

class keydict(defaultdict):
    def __missing__(self, key):
        return key

BLOCKS = defaultdict(OrderedDict)
"""
BLOCKS["MSSM"]["MINPAR"] = { 'At' : 1, 'TanBeta': 2, ...}
BLOCKS["NMSSM"]["MINPAR"] = { 'At' : 2, 'TanBeta': 3, 'Lambda': 1 ...}
"""
BIN = defaultdict(str)
"""
BIN["MSSM"] = 'bin/SPhenoMSSM'
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

def getPara(model, para):
    block = blockfrompara(para, BLOCKS[model])
    if block and para in BLOCKS[model][block]:
        return (block, BLOCKS[model][block][para])
    return

def getKey(model, para):
    return '{}.values.{}'.format(*getPara(model, para))

def runScan(model,HDFSTORE='store.h5',binary=None, getblocks=[], threads=None):
    c = deepcopy(CONF)
    print('preparing ' + model + ' ...')
    blocks = BLOCKS[model]
    parameters = [j for i in blocks.values() for j in i.keys()]
    if len(parameters) != len(set(parameters)):
        print('Parameters not uniquely!')
        exit(1)
    for para, value in VALUES.items():
        block = blockfrompara(para, blocks)
        if not block:
            continue
        if not c.getBlock(block):
            c.setBlock(block)
        paraid = BLOCKS[model][block][para]
        line = { 'parameter': para, 'id': paraid }
        line.update(value)
        c.setLine(block, line)
    if binary:
        c['runner']['binary'] = binary
    if getblocks:
        c['runner']['getblocks'] = getblocks
    print('scanning ' + model + ' ...')
    scan = Scan(c)
    scan.submit(threads)
    print('Saving to ' + HDFSTORE)
    scan.save(filename=HDFSTORE, path=model)
    if 'log' in scan.results:
        failed = len([ r for r in scan.results['log'] if type(r) == str ])
        print("{} out of {} points are invalid.".format(failed, scan.numparas))
    scan.results = {}
    scan.runner.cleanup()
    del scan

def runAll(HDFSTORE, skip = None, threads=None):
    if os.path.exists(HDFSTORE):
        skip = input('Old scans found. Delete and rescan? (yes/no)') if not skip else skip
        if skip == 'no':
            print('Skipping.')
            return
        elif skip == 'yes':
            print('Removing.')
            os.remove(HDFSTORE)
        else:
            print('wrong input')
            exit(1)
    for model in BLOCKS.keys():
        runScan(model, HDFSTORE=HDFSTORE, binary=BIN[model], threads=threads)

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
