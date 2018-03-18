# import lzma
import logging
from collections import ChainMap
import os
from numpy import linspace, prod
from concurrent.futures import ThreadPoolExecutor
from itertools import product
from pandas.io.json import json_normalize
from pandas import HDFStore
import json
from .slha import genSLHA
from .runner import Runner

logging.getLogger().setLevel(logging.INFO)

class Scan():
    def __init__(self, c, getblocks=[]):
        self.config = c
        self.template = genSLHA(c['blocks'])
        self.getblocks = getblocks
        self.runner = Runner(c['runner'], self.template, self.getblocks)
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
        return [ self.runner.run(d) for d in dataset ]

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
            self.results = json_normalize(json.loads(json.dumps(list(executor.map(self.runner.run, self.scanset)))))

    def save(self, filename='store.hdf', path='results'):
        store = HDFStore(filename)
        store[path] = self.results
        store.close()
