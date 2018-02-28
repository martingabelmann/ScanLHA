import sps
from scipy.interpolate import interp1d
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

c = sps.Config('config.yml')
s = sps.Scan(c,getblocks=[])

s.build()
s.submit()

mhSM = s.results['MASS.values.25']
msusy = s.results['MINPAR.values.14']
sm = interp1d(msusy,mhSM,kind='cubic')

s.spheno.binary = '../SM.NLO/SPhenoSM'
s.submit()

mhSMold = s.results['MASS.values.25']
msusyold = s.results['MINPAR.values.14']
smold = interp1d(msusyold,mhSMold,kind='cubic')

plt.plot(msusy, sm(msusy)-smold(msusy))
plt.savefig('plot',bbox_inches='tight')
