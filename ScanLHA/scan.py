# import lzma
import logging
from collections import ChainMap
import os
from numpy import linspace, prod
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
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
        # this is still buggy: https://github.com/tqdm/tqdm/issues/510
        # return [ self.spheno.run(d) for d in tqdm(dataset) ]
        return [ self.runner.run(d) for d in dataset ]

    def submit(self,w=None):
        w = 2*os.cpu_count() if not w else w
        if not self.scanset:
            self.build()
        chunksize = min(int(self.numparas/w),1000)
        chunks = range(0, self.numparas, chunksize)
        logging.info('Splitting dataset into %d chunks.' % len(chunks))
        logging.info('Will work on %d chunks in parallel.' % w)
        with ThreadPoolExecutor(w) as executor:
            futures = [ executor.submit(self._run, self.scanset[i:i+chunksize]) for i in chunks ]
            progresser = tqdm(as_completed(futures), total=len(chunks), unit = 'chunk')
            self.results = [ k for r in progresser for k in r.result() ]
        self.results = json_normalize(json.loads(json.dumps(self.results)))

    def save(self, filename='store.hdf', path='results'):
        store = HDFStore(filename)
        store[path] = self.results
        store.close()
