# import lzma
import logging
from collections import ChainMap
import os
from numpy import linspace, prod
from concurrent.futures import ProcessPoolExecutor as Executor
from concurrent.futures import as_completed
from tqdm import tqdm
from math import * # noqa: E403
from itertools import product
from pandas import HDFStore, concat, DataFrame
from .slha import genSLHA
from .runner import RUNNERS
from numpy.random import seed, uniform
from time import time

def substitute(param_dict):
    subst = { p : str(v).format_map(param_dict) for p,v in param_dict.items() }
    if param_dict == subst:
        return { p : eval(v) for p,v in subst.items() }
    else:
        return substitute(subst)

class Scan():
    def __init__(self, c):
        self.config = c
        self.config['runner']['template'] = genSLHA(c['blocks'])
        self.getblocks = self.config.get('getblocks', [])
        self.runner = RUNNERS[self.config['runner'].get('type','SLHA')]
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
            logging.info("No scan parameters defined in config!")
            logging.info("Register a scan range with addScanRange(<block>, {'id': <para-id>, 'scan': [<start>,<end>,<stepsize>]})")
            logging.info("Register a list of scan values with  addScanValues(<block>,{'id': <para-id>, 'values': [1,3,6,...])")

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
        self.config['runner']['template'] = genSLHA(self.config['blocks'])

    def build(self,num_workers=4):
        if not self.config.validate():
            return
        values = []
        for parameter,line in self.config.parameters.items():
            if 'values' in line:
                values.append([{str(parameter): num} for num in line['values']])
            if 'dependent' in line and 'value' in line:
                valuse.append([line['parameter'], line['value']])
        self.numparas = prod([len(v) for v in values])
        logging.info('Build all %d parameter points.' % self.numparas)
        self.scanset = [ substitute(dict(ChainMap(*s))) for s in product(*values) ]
        if self.scanset:
            return self.numparas
        return

    def scan(self, dataset):
        # this is still buggy: https://github.com/tqdm/tqdm/issues/510
        # res = [ runner.run(d) for d in tqdm(dataset) ]
        runner = self.runner(self.config['runner'])
        return concat([ runner.run(d) for d in dataset ], ignore_index=True)

    def submit(self,w=None):
        w = os.cpu_count() if not w else w
        if not self.scanset:
            self.build()

        if w == 1:
            runner = self.runner(self.config['runner'])
            self.results = concat([ runner.run(d) for d in tqdm(self.scanset) ], ignore_index=True)
            return

        chunksize = min(int(self.numparas/w),1000)
        chunks = range(0, self.numparas, chunksize)
        logging.info('Running on host {}.'.format(os.getenv('HOSTNAME')))
        logging.info('Splitting dataset into %d chunks.' % len(chunks))
        logging.info('Will work on %d chunks in parallel.' % w)
        with Executor(w) as executor:
            futures = [ executor.submit(self.scan, self.scanset[i:i+chunksize]) for i in chunks ]
            progresser = tqdm(as_completed(futures), total=len(chunks), unit = 'chunk')
            self.results = [ r.result() for r in progresser ]
        self.results = concat(self.results, ignore_index=True)

    def save(self, filename='store.hdf', path='results'):
        print('Saving to {} ({})'.format(filename,path))
        if path == 'config':
            logging.error('Cant use "config" as path, using "config2" instead.i')
            path = "config2"
        store = HDFStore(filename)
        store[path] = self.results
        store.get_storer(path).attrs.config = dict(self.config)
        store.close()

class RandomScan():
    def __init__(self, c, runner='SLHA', seed=None):
        self.config = c
        self.numparas = eval(str(c['runner']['numparas']))
        self.config['runner']['template'] = genSLHA(c['blocks'])
        self.getblocks = self.config.get('getblocks', [])
        self.runner = RUNNERS[self.config['runner'].get('type','SLHA')]
        self.parallel = 1
        self.seed = round(time()) if not seed else seed
        self.randoms = { p : [eval(str(k)) for k in v['random']] for p,v in c.parameters.items() if 'random' in v }
        self.dependent = { p : v['value'] for p,v in c.parameters.items() if v.get('dependent',False) and 'value' in v }

    def generate(self):
        dataset = { p : v for p,v in self.dependent.items() }
        [ dataset.update({ p : uniform(*v)}) for p,v in self.randoms.items() ]
        return substitute(dataset)

    def scan(self, numparas, pos=0):
        numresults = 0
        runner = self.runner(self.config['runner'])
        if not runner.initialized:
            logging.error('Could not initialize runner.')
            return DataFrame()
        results = []
        seed(self.seed + pos)
        with tqdm(total=numparas, unit='point', position=pos) as bar:
            while numresults < numparas:
                result = runner.run(self.generate())
                if not result.isnull().values.all():
                    results.append(result)
                    numresults += 1
                    bar.update(1)
        return concat(results, ignore_index=True)

    def submit(self,w=None):
        w = os.cpu_count() if not w else w
        self.parallel = w
        logging.info('Running on host {}.'.format(os.getenv('HOSTNAME')))
        logging.info('Will work on %d threads in parallel.' % w)
        if w == 1:
            self.results = self.scan(self.numparas)
            return
        paras_per_thread = int(self.numparas/w)
        remainder = self.numparas % w
        numparas = [ paras_per_thread for p in range(w) ]
        numparas[-1] += remainder
        with Executor(w) as executor:
            futures = [ executor.submit(self.scan, j, i) for i,j in enumerate(numparas) ]
            self.results = [ r.result() for r in as_completed(futures) ]
        self.results = concat(self.results, ignore_index=True)

    def save(self, filename='store.hdf', path='results'):
        if self.results.empty:
            return
        print('Saving to {} ({})'.format(filename,path))
        if path == 'config':
            logging.error('Cant use "config" as path, using "config2" instead.')
            path = "config2"
        store = HDFStore(filename)
        store[path] = self.results
        store.get_storer(path).attrs.config = dict(self.config)
        store.get_storer(path).attrs.seed = self.seed
        store.get_storer(path).attrs.parallel = self.parallel
        store.close()
