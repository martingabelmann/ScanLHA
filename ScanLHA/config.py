from numpy import linspace, logspace, geomspace, arange
from numpy.random import uniform, normal
import logging
import re
from sys import exit
import yaml
# scientific notation, see
# https://stackoverflow.com/questions/30458977/yaml-loads-5e-6-as-string-and-not-a-number
yaml.add_implicit_resolver(
    u'tag:yaml.org,2002:float',
    re.compile(u'''^(?:
     [-+]?(?:[0-9][0-9_]*)\\.[0-9_]*(?:[eE][-+]?[0-9]+)?
    |[-+]?(?:[0-9][0-9_]*)(?:[eE][-+]?[0-9]+)
    |\\.[0-9_]+(?:[eE][-+][0-9]+)?
    |[-+]?[0-9][0-9_]*(?:[0-5]?[0-9])+\\.[0-9_]*
    |[-+]?\\.(?:inf|Inf|INF)
    |\\.(?:nan|NaN|NAN))$''', re.X),
    list(u'-+0123456789.'))

def intersect(list1,list2):
    """ Returns intersection of two lists """
    return list(set(list1) & set(list2))
__all__ = ['Config']
class Config(dict):
    """
    A dict-like object that carries information about LHA file(s), programs that import/export LHA files, and plots.

      1. LHA blocks are stored in the key `'blocks'`.

      2. Information about the scan to perform and used programs is stored in the key `'runner'`.

      3. Information about the plots is stored in the key `'scatterplot'`.

    Example for accessing LHA entries:

        In [1]: from ScanLHA import Config
        In [2]: c=Config('SPheno.yml')
        In [3]: c.parameters # contains all LHA entries using unique parameter identifiers
        In [4]: c['MODSEL'] # returns the whole MODSEL block
        In [5]: c['MODSEL.1'] # line with LHA id=1 from block MODSEL
        In [6]: c['MODSEL.values.1'] # value to which the LHA id=1 in the block MODSEL is set
        In [7]: c['TanBeta'] # return the line which is associated with the parameter TanBeta
        Out[7]:
        {'id': 4,
         'latex': '$\\tan\\beta$',
         'lha': 'MINPAR.values.4',
         'parameter': 'TanBeta',
         'values': [1,2,3,4]}

    Example for `'runner'` (more see `ScanLHA.runner`):

        ---
        runner:
        binaries:
            - [ '/home/user/SPheno/bin/SPhenoSplitNMSSM', '{input_file}', '{output_file}']
            - [ '/home/user/HiggsBounds-4.3.1/HiggsBounds',  'LandH', 'SLHA', '3', '0', '{output_file}']
        micromegas:
            src: '/home/user/micrOMEGAS/src'
            modelname: 'SplitNMSSM'
            main: 'CalcOmegaDD.cpp'
            exec: ['CalcOmegaDD', '{output_file}']
        type: MicrOmegas
        cleanup: false
        keep_log: true
        remove_slha: true

    Example for `'blocks'`:

        ---
        blocks:
        - block: MINPAR
          lines:
              - parameter: 'MSUSY'
                id: 1
                scan:  [2e3, 2e4, 100]
                distribution: 'geom'
              - parameter: 'TanBeta'
                latex: '$\\tan\\beta$'
                id: 2
                value: 4
              - ..

    Example for `'scatterplot'` (more see `ScanLHA.PlotLHA`):

        ---
        scatterplot:
            conf:
                datafile: "results.h5"
                newfields:
                    TanBeta: "DATA['HMIX.values.11'].apply(abs).apply(tan)"
                    M1: "DATA['MASS.values.1000022'].apply(abs)"
                    M2: "DATA['MASS.values.1000023'].apply(abs)"
                    Mdiff: "DATA['MASS.values.1000023'].apply(abs)-DATA['MASS.values.1000022'].apply(abs)"
                dpi: 200
                x-axis: {
                    field: 'MSUSY',
                    lognorm: True,
                    label: "$m_{SUSY}$ [TeV]",
                    ticks: [[2000, 3000, 6000, 10000, 20000], ['$2$','$3$', '$6$', '$10$', '$20$']]
                    }
            plots:
                - filename: 'masses.png'
                  alpha: 0.8
                  legend: {'loc':'right'}
                  y-axis: {label: '$Mass$ [GeV]', lognorm: True }
                  textbox: {x: 0.94, y: 0.35, text: 'some info text', fontsize: 12}
                  plots:
                      - {y-axis: 'M1', label: '$m_{\chi_1^0}$'}
                      - {y-axis: 'M2', label: '$m_{\chi_2^0}$'}
                      - {vline: True, x-field: 3000, lw: 2, color: 'black', alpha: 1}
                      - {vline: True, x-field: 6000, lw: 2, color: 'black', alpha: 1}
                - filename: diff.png
                  x-axis: {field: M1, label: 'm_{\chi_1^0}'}
                  y-axis: {field: M2, label: 'm_{\chi_2^0}'}
                  z-axis: {field: Mdiff, label: '\delta_m'}

    """

    def __init__(self,src):
        self.src = src
        self['runner'] = {}
        self['blocks'] = []
        self.distribution = {
                'linear': linspace,
                'log': logspace,
                'geom': geomspace,
                'arange': arange,
                'uniform': uniform,
                'normal': normal
                }
        self.valid = True
        self.parameters = {} # directly access a block item via 'parameter'
        self.load()

    def __getitem__(self, key):
        if key in self.keys():
            return self.get(key)
        if self.getBlock(key):
            return self.getBlock(key)
        if key in self.parameters:
            return self.parameters[key]
        dots = key.split('.') # access line e.g. via Config["MINPAR.1"]
        if len(dots) == 2:
            return self.getLine(dots[0], dots[1])
        if len(dots) == 3: # or value/scan/values via Config["MINPAR.values.1"]
            line = self.getLine(dots[0], int(dots[2]))
            if line and dots[1] in line.keys():
                return line.get(dots[1])
        raise KeyError('No valid config parameter: {}'.format(key))

    def load(self, src = None):
        """Load config from source file `src`.

        If the `ScanLHA.config.Config` instance was already loaded, information from the old `src` file is overwritten.

        After successfully loading the `ScanLHA.config.Config` instance it gets validated using `ScanLHA.config.Config.validate`.
        """
        src = self.src if not src else src
        try:
            with open(src, 'r') as c:
                new = yaml.safe_load(c)
                for i in intersect(new.keys(), self.keys()):
                    logging.debug('Overwriting config "{}".'.format(i))
                self.update(new)
                if not self.validate():
                    logging.error('Errorenous config file.')
                    exit(1)
        except FileNotFoundError:
            logging.error('File {} not found.'.format(src))
            self.valid = False
            return -2
        except Exception as e:
            logging.error("failed to load config file {}".format(src))
            logging.error(str(e))
            self.valid = False

    def save(self, dest = None):
        """Save `ScanLHA.config.Config` instance to destination file `dest`.
        If `dest==None` (default), `Config.src` is used."""
        dest = self.src if not dest else dest
        with open(dest, 'w') as f:
            f.write(yaml.dump(self))

    def append(self, c):
        """ Append information from another ScanLHA.Config instance <c>. """
        for b in ['runner', 'scatterplot']:
            if b in c and b in self:
                self[b].update(c[b])
            elif b in c and b not in self:
                self[b] = c[b]
        for b in c['blocks']:
            if not self.getBlock(b['block']):
                self.setBlock(b['block'], b['lines'])
            else:
                for l in b['lines']:
                    self.setLine(b['block'], l)
        return self.validate()

    def getBlock(self, block):
        """ Blocks are stored in a list of dicts. This method is to access blocks by their name.

        Example:

            In [1]: from ScanLHA import Config
            In [2]: c=Config('SPheno.yml')
            In [3]: c.getBlock('MODSEL')
            Out[3]:
            {'block': 'MODSEL',
               'lines': [{'id': 1,
                 'value': 1,
                 'parameter': 'MODSEL.1',
                 'latex': 'MODSEL.1',
                 'lha': 'MODSEL.values.1'},
                {'id': 2,
                 'value': 1,
                 'parameter': 'MODSEL.2',
                 'latex': 'MODSEL.2',
                 'lha': 'MODSEL.values.2'},
                {'id': 6,
                 'value': 1,
                 'parameter': 'MODSEL.6',
                 'latex': 'MODSEL.6',
                 'lha': 'MODSEL.values.6'}]}
        """
        blockpos = [i for i,b in enumerate(self['blocks']) if b['block'] == block]
        if not blockpos:
            return
        return self['blocks'][blockpos[0]]

    def getLine(self, block, id):
        """ Returns the line with the SLHA id `id` from the block `block`

        Example:

            In [1]: from ScanLHA import Config
            In [2]: c=Config('SPheno.yml')
            In [3]: c.getLine('MODSEL', 1)
            Out[3]:
            {'id': 1,
            'value': 1,
            'parameter': 'MODSEL.1',
            'latex': 'MODSEL.1',
            'lha': 'MODSEL.values.1'}
        """
        b = self.getBlock(block)
        if not b:
            logging.error('Block {} not present in config.'.format(block))
            return
        lines = b['lines']
        linepos = [i for i,l in enumerate(lines) if 'id' in l and l['id'] == id]
        if not linepos:
            return
        return lines[linepos[0]]

    def setBlock(self, block, lines=[]):
        """ Defines a SLHA block `block` with optional lines `lines`

        Example:

            In [1]: from ScanLHA import Config
            In [1]: c=Config('SPheno.yml')
            In [1]: Config.setBlock('MINPAR', lines=[{'id': 1, 'value': 1, 'parameter': 'TanBeta', 'latex': '\\tan\\beta'}, ...])
        """
        b = self.getBlock(block)
        if b:
            b['lines'] = lines
        else:
            self['blocks'].append({'block':block, 'lines': lines})
        return self.validate()

    def setLine(self, block, line):
        """ Add the `line` to the LHA `block`

        If the line already exists, the given keys are updated.

        Example:

            In [1]: from ScanLHA import Config
            In [2]: c=Config('SPheno.yml')
            In [3]: # use 1-loop RGEs
            In [4]: c.setLine('SPhenoInput', {'id': 38, 'value': 1})
        """
        b = self.getBlock(block)
        linepos = [i for i,l in enumerate(b['lines']) if 'id' in l and l['id'] == line['id']]
        if not b:
            return
        if not linepos:
            logging.debug('Appending new line with ID %d.' % line['id'])
            b['lines'].append(line)
        else:
            logging.debug('Updating line with ID %d.' % line['id'])
            b['lines'][linepos[0]] = line
        return self.validate()

    def validate(self):
        """ Validates the `ScanLHA.config.Config` instance and prepares further information attributes such as latex output.

        This method is applied after `ScanLHA.config.Config.load`, `ScanLHA.config.Config.setBlock`, `ScanLHA.config.Config.setLine` and `ScanLHA.config.Config.append`.
        """
        self.valid = True
        if 'blocks' not in self:
            logging.error("No 'blocks' section in config ")
            self.valid = False
        # check for double entries
        lines_seen = []
        self.parameters = {}
        for block in self['blocks']:
            if block['block'].count('.') > 0:
                logging.error('Block {} contains forbiddeni character "."!'.format(block['block']))
                self.valid = False
            for line in block['lines']:
                if 'id' not in line:
                    logging.error('No ID set for line entry!')
                    self.valid = False
                if [block['block'],line['id']] in lines_seen:
                    logging.error('Parameter {} in block {} set twice! Taking the first occurence.'.format(line['id'], block['block']))
                    self.valid = False
                if 'parameter' not in line:
                    line['parameter'] = '{}.{}'.format(block['block'],line['id'])
                elif line['parameter'] in self.parameters.keys():
                        para = line['parameter'] + '1'
                        logging.error('Parameter {} set twice! Renaming to {}.'.format(line['parameter'], para))
                        line['parameter'] = para
                        self.valid = False
                self.parameters[line['parameter']] = line
                if 'value' in line and line.get('dependent', False) and type(line['value']) != str:
                    print(line.get('dependent', False))
                    logging.error("'value' with attribute 'dependent' must be string not {} ({}, {}).".format(type(line['value']), block['block'], line['id']))
                    self.valid = False
                if 'value' in line and not line.get('dependent', False):
                    try:
                        float(line['value'])
                    except ValueError:
                        logging.error("'value' must be a number not {} ({}, {}).".format(str(type(line['value'])), block['block'], line['id']))
                        self.valid = False
                if 'values' in line and type(line['values']) != list and len(line['values']) < 1:
                    logging.error("'values' must be a nonemtpy list ({}, {}).".format(block['block'], line['id']))
                    self.valid = False
                if 'scan' in line and type(line['scan']) != list and len(line['scan']) < 2:
                    logging.error("'scan' must be a nonemtpy list ({}, {}).".format(block['block'], line['id']))
                    self.valid = False
                if 'latex' not in line:
                    line['latex'] = line['parameter']
                if 'lha' not in line:
                    line['lha'] = '{}.values.{}'.format(block['block'],line['id'])
                lines_seen.append([block['block'], line['id']])
        return self.valid
