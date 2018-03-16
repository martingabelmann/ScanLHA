import sps
import matplotlib
from pandas import read_hdf
from collections import OrderedDict
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# Definitions
MINPARID = OrderedDict()
MINPARID['NMSSM'] = { 'At':1, 'LambdaS':2, 'MSUSY':3, 'TanBeta':4}
MINPARID['MSSM']  = { 'At':1, 'MSUSY':2, 'TanBeta':3 }
# MINPARID['NMSSMNoSq'] = { 'LambdaS':1, 'TanBeta':2,  'MSUSY':3}

MARKER = { 'NMSSM': 'o', 'MSSM': '+'}

MINPARVAL = {
        'At': {'value': 0},
        'TanBeta': { 'values': [1, 4] },
        'MSUSY': { 'scan': [1e3, 1e16, 50], 'distribution': 'geom' },
        'LambdaS': { 'values': [0.3, 0.2, 0] }
        }

LATEX = {
        'At' : "A_t",
        'TanBeta':  "\\tan(\\beta)",
        'MSUSY': "M_{SUSY}",
        "LambdaS": "\lambda_s"
        }


READINMEMORY = True

HDFSTORE = 'scans/MSSMvsNMSSM/store.h5'

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

# Plots: one plot for each value of TanBeta
print('Generating plots.')
plt.rcParams.update({'font.size': 15})
for tanb in MINPARVAL['TanBeta']['values']:
    fig = plt.figure()
    plt.rc('text', usetex=True)
    plt.xlabel(r'$M_{SUSY}$ / GeV')
    plt.ylabel(r'$m_{H}$ / GeV')
    ax = plt.gca()
    ax.plot([],[],' ', marker=None, label="$\\tan\\beta=" + str(tanb) + "$")
    ax.legend()
    plt.axhline(y=125, color='r', linestyle='-', label="125 GeV")
    Label = ''
    for model,minpar in MINPARID.items():
        if 'LambdaS' not in minpar.keys():
            mhmsusy = getSubPlot(model,{'TanBeta': tanb})
            Label = model
            ax.plot(mhmsusy[0],mhmsusy[1], label=Label, linewidth=2, c='black')
            continue
        for lams in MINPARVAL['LambdaS']['values']:
            Label = model + ': '
            mhmsusy = getSubPlot(model,{'TanBeta': tanb, 'LambdaS': lams})
            Label = model + ': $\lambda_s = ' + str(lams) + '$'
            ax.scatter(mhmsusy[0],mhmsusy[1], label=Label, s=25, marker=MARKER[model])
    plt.legend(loc='lower right')
    ax.set_xscale('log')
    print('TanBeta = %d'%tanb)
    fig.savefig('scans/MSSMvsNMSSM/TanBeta' + str(tanb) + '.svg' ,bbox_inches='tight')
print('Done.')
