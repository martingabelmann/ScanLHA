"""
Parsing and writing of (S)LHA files.
"""
from collections import defaultdict
import logging
import pylha

def genSLHA(blocks):
    """ Generate string in SLHA format from `'blocks'` entry of a `ScanLHA.config.Config` instance. """
    out = ''
    for block in blocks:
        out += 'BLOCK {}\n'.format(block['block'])
        for data in block['lines']:
            data = defaultdict(str,data)
            if any(k in ['scan','values','random','dependent'] for k in data):
                try:
                    para = data['parameter']
                except KeyError:
                    logging.info('Using {}.{} as template parameter.'.format(block, data['id']))
                    para = '{}.{}'.format(block,data['id'])
                data['value'] = '{%' + para + '%}'
            out += '{id} {value} #{parameter} {comment}\n'.format_map(data)
    return out

def list2dict(l):
    """ recursively convert [1,2,3,4] to {'1':{'2':{'3':4}} """
    if len(l) == 1:
        return l[0]
    return { str(l[0]) : list2dict(l[1:]) }

def mergedicts(l, d):
    """ merge list of nested dicts """
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
    """
    Turn the content of an SLHA file into a dictionary

    `slhafile` : path tp file

    `blocks`   : list of BLOCKs (strings) to read, if empty all blocks are read

    Uses [pylha](https://github.com/DavidMStraub/pylha pylha) but gives a more meaningful output
    the result is stored in a nested dictionary.

    Converts (i.e. reverses) non-standard SLHA entrys (such as HiggsBounds).
    """
    reversed_blocks = [
            'HiggsBoundsInputHiggsCouplingsBosons',
            'HiggsBoundsInputHiggsCouplingsFermions',
            'HiggsCouplingsFermions',
            'HiggsCouplingsBosons'
            ]

    # blocks which have more than one numerical value are joined into a "|"-separated string
    list_blocks = {
            'HiggsCouplingsFermions': 2,
            'HiggsBoundsInputHiggsCouplingsFermions': 2,
            }

    try:
        with open(slhafile,'r') as f:
            string = f.read()
            string = string.replace('DECAY1L', 'NLODECAY')
            slha = pylha.load(string)
    except FileNotFoundError:
        logging.error('File %s not found.' % slhafile)
        return {}
    except:
        logging.error('Could not parse %s !' % slhafile)
        return {}
    try:
        slha_blocks = slha['BLOCK']
    except KeyError:
        slha_blocks = {}
    if blocks:
        slha_blocks = { b : v for b,v in slha_blocks.items() if b in blocks }
    for b,v in slha_blocks.items():
        try:
            if b in list_blocks:
                v['values'] = [ ['|'.join(str(y) for y in x[:list_blocks[b]])] + x[list_blocks[b]:] for x in v['values']]
            if b in reversed_blocks:
                [x.reverse() for x in v['values']]
            v['values'] = mergedicts([list2dict(l) for l in v['values']],{})

            v['info'] = ''.join(str(i) for i in v['info'])
        except:
            pass

    if 'DECAY' not in slha and 'NLODECAY' not in slha:
        return slha_blocks

    decayblock = 'DECAYS' if 'DECAY' in slha_blocks else 'DECAY'
    slha_blocks[decayblock] = slha['DECAY']
    for d,v in slha_blocks[decayblock].items():
        try:
            v['values'] = mergedicts([list2dict(list(reversed(l))) for l in v['values']],{})
            v['info'] = ''.join(str(i) for i in v['info']) if len(v['info']) > 1 else v['info'][0]
        except:
            pass
    
    nlodecayblock = 'NLODECAYS' if 'NLODECAY' in slha_blocks else 'NLODECAY'
    slha_blocks[nlodecayblock] = slha['NLODECAY']
    for d,v in slha_blocks[nlodecayblock].items():
        try:
            v['values'] = mergedicts([list2dict(list(reversed(l))) for l in v['values']],{})
            v['info'] = ''.join(str(i) for i in v['info']) if len(v['info']) > 1 else v['info'][0]
        except:
            pass

    return slha_blocks
