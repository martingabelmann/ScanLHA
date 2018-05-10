from collections import defaultdict
import logging
import pylha

def genSLHA(blocks):
    """generate SLHA"""
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

# recursively convert [1,2,3,4] to {1:{2:{3:4}}
def list2dict(l):
    if len(l) == 1:
        return l[0]
    return { l[0] : list2dict(l[1:]) }

# merge list of nested dicts
def mergedicts(l, d):
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
    try:
        with open(slhafile,'r') as f:
            slha = pylha.load(f)
    except FileNotFoundError:
        logging.error('File %s not found.' % slhafile)
        return -2
    except:
        logging.error('Could not parse %s !' % slhafile)
        return -3
    slha_block = slha['BLOCK']
    if blocks:
        slha_block = { b : v for b,v in slha_block.items() if b in blocks }
    for b,v in slha_block.items():
        if 'values' in v:
            v['values'] = mergedicts([list2dict(l) for l in v['values']],{})
    return slha_block
