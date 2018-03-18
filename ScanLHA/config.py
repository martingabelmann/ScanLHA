from numpy import linspace, logspace, geomspace, arange
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
