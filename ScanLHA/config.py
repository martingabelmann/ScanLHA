from numpy import linspace, logspace, geomspace, arange
from numpy.random import uniform, normal
import logging
import re
import yaml
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

def intersect(list1,list2):
    return list(set(list1) & set(list2))

class Config(dict):
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
        self.parameters = {} # directly access a block item via 'parameter'
        self.load()

    def __getitem__(self, key):
        """ Access BLOCKs and BLOCK items (whole lines or values) """
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
        src = self.src if not src else src
        try:
            with open(src, 'r') as c:
                new = yaml.safe_load(c)
                for i in intersect(new.keys(), self.keys()):
                    logging.info('Overwriting config "{}".'.format(i))
                self.update(new)
                if not self.validate():
                    logging.error('Errorenous config file.')
                    exit(1)
        except FileNotFoundError:
            logging.error('File {} not found.' % src)
            return -2
        except Exception as e:
            logging.error("failed to load config file " + src)
            logging.error(str(e))

    def save(self, dest = None):
        dest = self.src if not dest else dest
        with open(dest, 'w') as f:
            f.write(yaml.dump(self))

    def append(self, c):
        for b in ['runner', 'contourplot', 'xyplot']:
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
        blockpos = [i for i,b in enumerate(self['blocks']) if b['block'] == block]
        if not blockpos:
            return
        return self['blocks'][blockpos[0]]

    def getLine(self, block, id):
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
        b = self.getBlock(block)
        if b:
            b['lines'] = lines
        else:
            self['blocks'].append({'block':block, 'lines': lines})
        return self.validate()

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
        lines_seen = []
        self.parameters = {}
        for block in self['blocks']:
            if block['block'].count('.') > 0:
                logging.error('Block {} contains forbiddeni character "."!'.format(block['block']))
                ok = False
            for line in block['lines']:
                if 'id' not in line:
                    logging.error('No ID set for line entry!')
                    ok = False
                if [block['block'],line['id']] in lines_seen:
                    logging.error('Parameter {} in block {} set twice! Taking the first occurence.'.format(line['id'], block['block']))
                    ok = False
                if 'parameter' not in line:
                    line['parameter'] = '{}.{}'.format(block['block'],line['id'])
                elif line['parameter'] in self.parameters.keys():
                        para = line['parameter'] + '1'
                        logging.error('Parameter {} set twice! Renaming to {}.'.format(line['parameter'], para))
                        line['parameter'] = para
                        ok = False
                self.parameters[line['parameter']] = line
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
                if 'latex' not in line:
                    line['latex'] = line['parameter']
                lines_seen.append([block['block'], line['id']])
        return ok
