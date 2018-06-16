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

# recursively convert [1,2,3,4] to {'1':{'2':{'3':4}}
def list2dict(l):
    if len(l) == 1:
        return l[0]
    return { str(l[0]) : list2dict(l[1:]) }

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
    try:
        slha_blocks = slha['BLOCK']
    except KeyError:
        slha_blocks = {}
    if blocks:
        slha_blocks = { b : v for b,v in slha_blocks.items() if b in blocks }
    try:
        slha_blocks.pop('HiggsBoundsInputHiggsCouplingsBosons')
        slha_blocks.pop('HiggsBoundsInputHiggsCouplingsFermions')
    except KeyError:
        pass
    for b,v in slha_blocks.items():
        try:
            v['values'] = mergedicts([list2dict(l) for l in v['values']],{})
            v['info'] = ''.join(str(i) for i in v['info'])
        except:
            pass

    if 'DECAY' not in slha:
        return slha_blocks

    decayblock = 'DECAYS' if 'DECAY' in slha_blocks else 'DECAY'
    slha_blocks[decayblock] = slha['DECAY']
    for d,v in slha_blocks[decayblock].items():
        try:
            v['values'] = mergedicts([list2dict(list(reversed(l))) for l in v['values']],{})
            v['info'] = ''.join(str(i) for i in v['info']) if len(v['info']) > 1 else v['info'][0]
        except:
            pass
    return slha_blocks
