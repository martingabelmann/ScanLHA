import sps
import matplotlib
from pandas import read_hdf
from collections import OrderedDict
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from IPython import embed

# Definitions
MINPARID = OrderedDict()
MINPARID['NMSSM'] = { 'At':1, 'LambdaS':2, 'MSUSY':3, 'TanBeta':4}
# MINPARID['MSSM']  = { 'At':1, 'MSUSY':2, 'TanBeta':3 }
# MINPARID['NMSSMNoSq'] = { 'LambdaS':1, 'TanBeta':2,  'MSUSY':3}

# 79707 out of 137500 points are invalid.
MINPARVAL = {
        'At': {'value': 0},
        'TanBeta': { 'scan': [1, 56, 56] },
        'MSUSY': { 'scan': [1e3, 1e16, 500], 'distribution': 'geom' },
        'LambdaS': { 'scan': [0, 1, 22] }
        }

LATEX = {
        'At' : "A_t",
        'TanBeta':  "\\tan(\\beta)",
        'MSUSY': "M_{SUSY}",
        "LambdaS": "\lambda_s"
        }


READINMEMORY = True

HDFSTORE = 'scans/NMSSM_Contour/store.h5'

# Load default config
c = sps.Config('config.yml')

# Helper functions
def setMINPAR(c, model, para, value):
    paraid = MINPARID[model][para]
    line = { 'parameter': para, 'id': paraid }
    line.update(value)
    c.setLine('MINPAR', line)

def setbinary(c,model):
    c['spheno']['binary'] = '../bin/SPheno' + model

def runscan(c, model):
    c.setBlock('MINPAR') # clear previous entries
    for para,value in MINPARVAL.items():
        if para not in MINPARID[model]:
            print('Parameter {} skipped for {}'.format(para, model))
            continue
        setMINPAR(c, model, para, value)
    setbinary(c,model)
    print('scanning ' + model + ' ...')
    scan = sps.Scan(c,getblocks=[])
    scan.build()
    scan.submit()
    if 'log' in scan.results:
        failed = len([ r for r in scan.results['log'] if type(r) == str ])
        print("{} out of {} points are invalid.".format(failed, scan.numparas))
    return scan.results

def getSubPlot(model, filters):
    r = results[model]
    for para,value in filters.items():
        paraid = 'MINPAR.values.%d' % MINPARID[model][para]
        r = r.loc[r[paraid] == value]
    key = 'MINPAR.values.%d' % MINPARID[model]['MSUSY']
    return (list(r[key]), list(r['MASS.values.25']))

# Scans
skip = 'r'
if sps.os.path.exists(HDFSTORE):
    skip = input('Old scans found. Delete and rescan [r] or skip scans [s]? (enter = rescan)')

if skip == 'r' or skip == '':
    results = sps.HDFStore(HDFSTORE)
    [ results.put(model, runscan(c,model)) for model in MINPARID.keys() ]
    results.close()

if READINMEMORY or skip == 's':
    # read into RAM to speed up the plots
    results = { model : read_hdf(HDFSTORE, model) for model in MINPARID.keys() }
mh = 125.09
mhmin = mh-0.31
mhmax = mh+0.31
maxvalues = { i: [m,results['NMSSM']['MINPAR.values.3']] for i,m in enumerate(results['NMSSM']['MASS.values.25']) if m > mhmin and m < mhmax  }
lamtb = [[results['NMSSM']['MINPAR.values.2'][i], results['NMSSM']['MINPAR.values.4'][i],m[0],m[1]] for i,m in maxvalues.items() ]

lam = [i[0] for i in lamtb]
tb = [i[1] for i in lamtb]
m = [i[2] for i in lamtb]
msusy = [i[3] for i in lamtb]

print('Generating plots.')
plt.rcParams.update({'font.size': 15})
fig = plt.figure()
plt.rc('text', usetex=True)
plt.xlabel(r'$ \lambda_s $')
plt.ylabel(r'$\tan\beta$')
ax = plt.gca()
embed()
