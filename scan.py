#!/usr/bin/env python3
from IPython import embed
from pandas import read_hdf
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
from ScanLHA import ScanLHA
from ScanLHA.ScanLHA import getKey

# Definitions
BLOCKS = ScanLHA.BLOCKS
BIN = ScanLHA.BIN
VALUES = ScanLHA.VALUES
LATEX = ScanLHA.LATEX
ScanLHA.CONF = ScanLHA.Config('ScanLHA/configs/SPheno.yml')
cmap = plt.get_cmap("tab10")

BLOCKS['NMSSM']['MINPAR']   = { 'At':1, 'LambdaS':2, 'MSUSY':3, 'TanBeta':4}
BLOCKS['MSSM']['MINPAR']    = { 'At':1, 'MSUSY':2, 'TanBeta':3 }

BIN['NMSSM'] = '../bin/SPhenoNMSSM'
BIN['MSSM'] = '../bin/SPhenoMSSM'

VALUES['At'] = { 'value': 0 }
VALUES['TanBeta'] = { 'values': [1,1.1,1.2,1.3,1.4,1.5,1.6,1.7,1.8,1.9,2,3,4] }
VALUES['MSUSY'] = { 'scan': [1e3, 1e16, 50], 'distribution': 'geom' }
VALUES['LambdaS'] = { 'values': [0,0.2,0.3,0.6] }

LATEX['At'] = "A_t"
LATEX['TanBeta'] = "\\tan\\beta"
LATEX['MSUSY'] = "M_{SUSY}"
LATEX['LambdaS'] = "\lambda_s"

HDFSTORE = 'scans/MSSMvsNMSSM/store.h5'

# Scans
ScanLHA.runAll(HDFSTORE)
results = {}
results["NMSSM"] = read_hdf(HDFSTORE,"NMSSM")
results["MSSM"] = read_hdf(HDFSTORE,"MSSM")
# Plots: one plot for each value of TanBeta
print('Generating plots.')
plt.rcParams.update({'font.size': 15})
for tanb in VALUES['TanBeta']['values']:
    c = 0
    fig = plt.figure()
    plt.rc('text', usetex=True)
    ax = plt.gca()
    ax.plot([],[],' ', marker=None, label="$\\tan\\beta=" + str(tanb) + "$")
    ax.legend()
    plt.axhline(y=125, color='r', linestyle='-', label="125 GeV", zorder=99)
    Label = ''
    for model,blocks in BLOCKS.items():
        x = getKey(model,'MSUSY')
        y = 'MASS.values.25'
        for block,minpar in blocks.items():
            if 'LambdaS' not in minpar.keys():
                r = results[model]
                r = r[ r[getKey(model,'TanBeta')] == tanb ]
                mhmsusy = r[[x, y]]
                mhmsusy = mhmsusy.sort_values(by=x)
                mhmsusy.plot(y=y, x=x, kind='scatter', ax=ax, color="C{}".format(c),zorder=c, label=model)
                c += 1
                continue
            for lams in VALUES['LambdaS']['values']:
                r = results[model]
                r = r[(r[getKey(model,'TanBeta')] == tanb) & (r[getKey(model,'LambdaS')] == lams)]
                mhmsusy = r[[x, y]]
                mhmsusy = mhmsusy.sort_values(by=x)
                Label = model + ': '
                Label = model + ': $\lambda_s = ' + str(lams) + '$'
                mhmsusy.plot(y=y, x=x, ax=ax, color="C{}".format(c), zorder=c, label=Label)
                c += 1
    plt.legend(loc='lower right')
    ax.set_xscale('log')
    ax.set(xlabel=r'$M_{SUSY}$ / GeV', ylabel=r'$m_{H}$ / GeV')
    print('TanBeta = {}'.format(tanb))
    fig.savefig('scans/MSSMvsNMSSM/TanBeta' + str(tanb) + '.svg' ,bbox_inches='tight')
print('Done.')
