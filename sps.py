#!/usr/bin/env python3
# pylint: disable=broad-except

import pyslha
import argparse
import yaml
# import lzma
import logging
from subprocess import Popen, STDOUT, PIPE
import matplotlib.pyplot as plt

class SPhenoScan():
    def __init__(self, config='config.yml'):
        "read config from file"
        try:
            with open(config, 'r') as c:
                self.config = yaml.safe_load(c)
        except:
            logging.error("failed to load " + config)

    def check_config(self):
        pass

    def runspheno(self):
        for t in range(1,56):
            fin = '../input/SLHA.%d.in' % t
            fout = '../output/SLHA.%d.out' % t
            proc = Popen(['../bin/SPheno', fin, fout], stderr=STDOUT, stdout=PIPE)
            pipe = proc.communicate(timeout=1)
            print(pipe[0].decode('utf8').strip())

    def readspc(self):
        masses = { 25: {}, 35:{},36: {},37:{} }
        for t in range(1,56):
            try:
                out = pyslha.read('../output/SLHA.%d.out' % t)
                masses[25][t] = out.blocks['MASS'][25]
                masses[35][t] = out.blocks['MASS'][35]
                masses[36][t] = out.blocks['MASS'][36]
                masses[37][t] = out.blocks['MASS'][37]
            except:
                print('failed to load %d' % t)
        plt.plot(list(masses[25].values()), list(masses[25].keys()) )
        plt.plot(list(masses[35].values()), list(masses[35].keys()) )
        plt.plot(list(masses[36].values()), list(masses[36].keys()) )
        plt.plot(list(masses[37].values()), list(masses[37].keys()) )
        plt.show()

    def writein(self):
        tpl = open('tpl.in', 'r').read()
        for t in range(1,56):
            with open('../input/SLHA.%d.in' % t, 'w') as f:
                f.write(tpl.replace('{tanb}', '%d.000000E+00' % t))
            f.close()

    def scan(self):
        pass

def parse_args():
    parser = argparse.ArgumentParser(description="Perform a scan with SPheno.")
    parser.add_argument('config', help='yaml config file', nargs='?', default='config.yml')
    parser.add_argument('--verbose', '-v', action='count', help='more output', default=0)
    args = parser.parse_args()
    return args

def main():
    args = parse_args()
    scan = SPhenoScan(args.config)
    scan.writein()
    scan.runspheno()
    scan.readspc()

if __name__ == "__main__":
    main()
