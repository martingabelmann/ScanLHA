#!/usr/bin/env python3
"""
Plot ScanLHA scan results.
"""
from pandas import HDFStore
import logging
import os
import sys
from .config import Config
from math import * # noqa: E403 F401 F403
from collections import ChainMap
from argparse import ArgumentParser
from numpy import nan, linspace  # noqa: F401
import matplotlib
from matplotlib.colors import LogNorm, Normalize
from matplotlib.colorbar import ColorbarBase
import importlib
matplotlib.use('Agg')
# matplotlib.use('ps')
import matplotlib.pyplot as plt # noqa: E402
from IPython import embed # noqa: F402, E402

plt.rc('text', usetex=True)
plt.rc('text.latex', preamble = r'\usepackage{amsmath,nicefrac,units,lmodern} \boldmath')


if os.path.isfile('functions.py'):
    sys.path.append(os.getcwd())
    f = importlib.import_module('functions')

__all__ = ['Plot', 'PlotConf', 'axisdefault']

def arg(re,im):
    """argument of complex number with real part re and imaginary part im """
    arg = 0
    if re > 0:
        arg = atan(im/re)       # noqa: F405
    elif re < 0 and im >= 0:
        arg = atan(im/re)+pi    # noqa: F405
    elif re < 0 and im < 0:
        arg = atan(im/re)-pi    # noqa: F405
    elif re == 0 and im > 0:
        arg = pi/2              # noqa: F405
    elif re == 0 and im < 0:
        arg = -pi/2             # noqa: F405
    elif re == 0 and im == 0:
        arg = 0
    return arg

axisdefault = {
        'boundaries' : [],
        'lognorm' : False,
        'vmin' : None,
        'vmax' : None,
        'ticks' :  [],
        'colorbar' : False,
        'colorbar_orientation': 'horizontal',
        'label' : None,
        'datafile' : None
}
"""
Default values for all axes.
"""
class PlotConf(ChainMap):
    """ Config class which allows for successively defined defaults """
    def __init__(self, *args):
        super().__init__(*args)
        self.maps.append({
            'x-axis': axisdefault,
            'y-axis': axisdefault,
            'z-axis': axisdefault,
            'colorbar_only': False,
            'constraints': [],
            'type': 'scatter',
            'legend': {
#                'loc' : 'right',
#                'bbox_to_anchor' : [1.5, 0.5]
                },
            'figsize': None,
            'hline': False,
            'vline': False,
            'exec': False,
            'lw': 1.0,
            's': None,
            'title': False,
            'label': None,
            'cmap': None,
            'alpha' : 1.0,
            'datafile': 'results.h5',
            'fontsize': 11,
#           'fontsize': 17,
            'tick_params': {},
            'rcParams': {
                'savefig.pad_inches': 0.04,
                'font.size':11,
#                'font.size': 17,
                'text.usetex': True,
                'font.weight' : 'normal',
            },
            'dpi': 300,
            'textbox': {}
            })

    def new_child(self, child = {}):
        for ax in ['x-axis','y-axis','z-axis']:
            if type(child.get(ax, {})) == str:
                child[ax] = ChainMap({ 'field': child[ax] }, self[ax])
            else:
                child[ax] = ChainMap(child.get(ax,{}), self[ax])
        return self.__class__(child, *self.maps)


def Plot():
    global PDATA, DATA, c, conf, logger, args, path, DIR, store
    """
    Basic usage: `PlotLHA --help`

    Requires a YAML config file that specifies at least the `'scatterplot'` dict with the list '`plots`'.

      * Automatically uses the `'latex'` attribute of specified LHA blocks for labels.
      * Fields for x/y/z axes can be specified by either `BLOCKNAME.values.LHAID` or the specified `'parameter'` attribute.
      * New fields to plot can be computed using existing fields
      * Optional constraints on the different fields may be specified
      * Various options can be passed to `matplotlib`s `legend`, `scatter`, `colorbar` functions.
      * Optional ticks can be set manually.

    __Example config.yml__

        ---
        scatterplot:
          conf:
            datafile: "mssm.h5"
            newfields:
              TanBeta: "DATA['HMIX.values.2'].apply(abs).apply(tan)"
            constraints:
              - "PDATA['TREELEVELUNITARITYwTRILINEARS.values.1']<0.5"
              # enforces e.g. unitarity
          plots:
              - filename: "mssm_TanBetaMSUSYmH.png"
                # one scatterplot
                y-axis: {field: TanBeta, label: '$\\tan\\beta$'}
                x-axis:
                  field: MSUSY
                  label: "$m_{SUSY}$ (TeV)$"
                  lognorm: True
                  ticks:
                    - [1000,2000,3000,4000]
                    - ['$1$','$2','$3','$4$']
                z-axis:
                  field: MASS.values.25
                  colorbar: True
                  label: "$m_h$ (GeV)"
                alpha: 0.8
                textbox: {x: 0.9, y: 0.3, text: 'some info'}
              - filename: "mssm_mhiggs.png"
                # multiple lines in one plot with legend
                constraints: [] # ignore all global constraints
                x-axis:
                  field: MSUSY,
                  label: 'Massparameter (GeV)'
                y-axis:
                  lognorm: True,
                  label: '$m_{SUSY}$ (GeV)'
                plots:
                    - y-axis: MASS.values.25
                      color: red
                      label: '$m_{h_1}$'
                    - y-axis: MASS.values.26
                      color: green
                      label: '$m_{h_2}$'
                    - y-axis: MASS.values.35
                      color: blue
                      label: '$m_{A}$'
    """
    parser = ArgumentParser(description='Plot ScanLHA results.')
    parser.add_argument("config", type=str,
            help="path to YAML file config.yml containing the plot (and optional scan) config.")
    parser.add_argument("-i", "--interactive", action="store_true",
            help="opens interactive plot environment with IPython: plot using the 'plot()' function")
    parser.add_argument("-v", "--verbose", action="count", default=0,
            help="increase output verbosity")

    args = parser.parse_args()

    logger = logging.getLogger('PlotLHA')
    logger.setLevel(logging.INFO)
    if args.verbose >= 1:
        logger.setLevel(logging.DEBUG)
        print("setting loglevel to DEBUG")
    if args.verbose >= 2:
        logging.getLogger().setLevel(logging.DEBUG)
        print("set loglevel DEBUG for matplotlib internals and all other modules")

    c = Config(args.config)
    DIR = os.path.dirname(os.path.abspath(args.config)) + '/'

    if 'scatterplot' not in c:
        logger.error('config file must contain "scatterplot" dict.')
        exit(1)

    if 'plots' not in c['scatterplot']:
        logging.error('no plots to plot')
        exit(1)

    conf = PlotConf()
    conf = conf.new_child(c['scatterplot'].get('conf',{}))

    if not os.path.isfile(conf['datafile']):
        logger.error('Data file {} does not exist.'.format(conf['datafile']))
        exit(1)

    store = HDFStore(conf['datafile'])

    path = 'results' # TODO
    DATA = store[path]

    attrs = store.get_storer(path).attrs
    if hasattr(attrs, 'config') and conf.get('conf_overwrite', False):
        attrs.config['scatterplot'] = {}
        c.append(attrs.config)

    if(args.interactive):
        embed()
    else:
        plot()

    store.close()

def plot(fig=''):
    global DATA, store
    c = Config(args.config)
    conf = PlotConf()
    conf = conf.new_child(c['scatterplot'].get('conf',{}))
    attrs = store.get_storer(path).attrs
    if hasattr(attrs, 'config') and conf.get('conf_overwrite', False):
        attrs.config['scatterplot'] = {}
        c.append(attrs.config)

    if not DATA.empty and 'newfields' in conf:
        logger.debug("generate custom newfields")
        for field,expr in conf['newfields'].items():
            logger.debug("executing DATA[{}] = {}]".format(field, expr))
            DATA[field] = eval(expr)
        logger.debug("done.")

    pcount = 0
    for p in c['scatterplot']['plots']:
        if fig and p['filename'] != fig:
            continue
        lcount = 0

        pconf = conf.new_child(p)

        plt.cla()
        plt.clf()
        plt.rcParams.update(pconf['rcParams'])
        if pconf['figsize']:
            plt.figure(figsize=pconf['figsize'])
        else:
            plt.figure()
        plt.rcParams.update({'font.size': pconf['fontsize']})

        if pconf['colorbar_only']: # TODO cleanup
            ax = plt.gca()
            norm = Normalize(vmin=pconf['z-axis']['vmin'], vmax=pconf['z-axis']['vmax'])
            if pconf['z-axis']['lognorm']:
                norm = LogNorm(vmin=pconf['z-axis']['vmin'], vmax=pconf['z-axis']['vmax'])
            cbar = ColorbarBase(ax,norm=norm, cmap=pconf['cmap'], orientation='horizontal', ticklocation='top')
            if pconf['z-axis']['ticks']:
                cbar.set_ticks(pconf['z-axis']['ticks'])
            if pconf['z-axis']['colorbar_orientation'] == 'horizontal':
                ax.xaxis.set_label_position('top')
                # ax.xaxis.set_ticks_position('top')
                # cbar.ax.tick_params(axis='x',direction='in',labeltop='on')
                # cbar.ax.xaxis.set_ticks_position('top')
            # cbar.ax.xaxis.set_label_position('top')
            if pconf['z-axis']['label']:
                ax.set_xlabel(pconf['z-axis']['label'], labelpad=15)
            cbar.update_ticks()
            plt.savefig(pconf['filename'],bbox_inches='tight')
            plt.figure()
            continue

        if pconf['title']:
            plt.title(conf['title'])

        if 'plots' not in p:
            p['plots'] = [p]

        for l in p['plots']: # noqa: E741
            lconf = pconf.new_child(l)

            label = lconf['label']
            label = label if label else None
            cmap = lconf['cmap']
            zorder = lconf.get('zorder', lcount)
            color = lconf.get('color', "C{}".format(lcount))
            if isinstance(color, int):
                color = [list(plt.cm.viridis(linspace(0,1,20))[color])]

            x = lconf.get('x-field', lconf['x-axis'].get('field', None))
            y = lconf.get('y-field', lconf['y-axis'].get('field', None))
            z = lconf.get('z-field', lconf['z-axis'].get('field', None))

            xlabel = lconf['x-axis']['label']
            ylabel = lconf['y-axis']['label']
            zlabel = lconf['z-axis']['label']
            if hasattr(c, 'parameters'):
                xlabel = c.parameters.get(x, {'latex': xlabel})['latex'] if not xlabel else xlabel
                ylabel = c.parameters.get(y, {'latex': ylabel})['latex'] if not ylabel else ylabel
                zlabel = c.parameters.get(z, {'latex': zlabel})['latex'] if not zlabel else zlabel

            if xlabel:
                plt.xlabel(xlabel)
            if ylabel:
                plt.ylabel(ylabel)

            if lconf['hline']:
                plt.axhline(y=y, color=color, linestyle='-', lw=lconf['lw'], label=label, zorder=zorder, alpha=lconf['alpha'])
                continue
            if lconf['vline']:
                plt.axvline(x=x, color=color, linestyle='-', lw=lconf['lw'], label=label, zorder=zorder, alpha=lconf['alpha'])
                continue

            if hasattr(c, 'parameters'):
                x = c.parameters.get(x,{'lha': x})['lha']
                y = c.parameters.get(y,{'lha': y})['lha']
                z = c.parameters.get(z,{'lha': z})['lha']

            PDATA = DATA
            if lconf['constraints']:
                logger.debug("Applying given constraints.")
            for constr in lconf['constraints']:
                logger.debug("executing DATA[{}] = {}]".format(field, constr))
                PDATA = PDATA[eval(constr)]

            if(lconf['datafile'] and lconf['datafile'] != conf['datafile']):
                conf['datafile'] = lconf['datafile'] # TODO
                store.close()
                logger.info("load new datafile {} (will be used for all following plots".format(conf['datafile']))
                del DATA, PDATA, store
                store = HDFStore(lconf['datafile'])  # TODO
                DATA = store['results']  # TODO
                PDATA = DATA

                if not PDATA.empty and 'newfields' in conf:
                    logger.debug("generate custom newfields for new datafile")
                    for field,expr in conf['newfields'].items():
                        logger.debug("executing PATA[{}] = {}]".format(field, expr))
                        PDATA[field] = eval(expr)
                    logger.debug("done.")

            PDATA = PDATA.replace('NaN',nan)

            for ax,field in {'x-axis':x, 'y-axis':y, 'z-axis':z}.items():
                if lconf[ax].get('rescale', None):
                    PDATA[field] = lconf[ax]['rescale']*PDATA[field]
                bounds = lconf[ax]['boundaries']
                if len(bounds) == 2:
                    logger.debug("applying boundaries [{},{}] on axis {}, field {}".format(bounds[0],bounds[1],ax,field))
                    PDATA = PDATA[(PDATA[field] >= bounds[0]) & (PDATA[field] <= bounds[1])]

            if lconf['x-axis']['lognorm']:
                if type(lconf['x-axis']['lognorm']) == str:
                    plt.xscale(lconf['x-axis']['lognorm'])
                else:
                    plt.xscale('log')

            if lconf['y-axis']['lognorm']:
                if type(lconf['y-axis']['lognorm']) == str:
                    plt.yscale(lconf['y-axis']['lognorm'])
                else:
                    plt.yscale('log')

            if z:
                PDATA = PDATA.sort_values(by=z)
                color = PDATA[z]
                vmin = PDATA[z].min() if not lconf['z-axis']['vmin'] else lconf['z-axis']['vmin']
                vmax = PDATA[z].max() if not lconf['z-axis']['vmax'] else lconf['z-axis']['vmax']
            else:
                vmin = None
                vmax = None
            znorm = LogNorm(vmin=vmin, vmax=vmax) if lconf['z-axis']['lognorm'] else None

            if lconf['exec']:
                exec(lconf['exec'])

            if len(PDATA) == 0:
                logger.error('In plot {}, x:{} , y:{}; no data to plot! (wrong boundaries or constraints?)'.format(p['filename'], x, y))
                continue

            if pconf.get('type', 'scatter') == 'scatter':
                cs = plt.scatter(PDATA[x], PDATA[y], zorder=zorder, label=label, cmap=cmap, c=color, vmin=vmin, vmax=vmax, norm=znorm, s=lconf['s'], alpha=lconf['alpha'], marker=lconf.get('marker', None), **lconf.get('kwargs',{}))
            else:
                PDATA = PDATA[[x,y]].dropna().sort_values(by=x)
                cs = plt.plot(PDATA[x], PDATA[y], lconf.get('fmt', '.'), zorder=zorder, c=color, alpha=lconf['alpha'], label=label, **lconf.get('kwargs',{}))

            plt.grid(b=True, which='major', color='#777777', linestyle='-', alpha=0.3, zorder=0)
            plt.minorticks_on()
            plt.grid(b=True, which='minor', color='#999999', linestyle='-', alpha=0.1, zorder=0)

            plt.margins(x=0.01,y=0.01)  # TODO
            if lconf['x-axis']['ticks']:
                if type(lconf['x-axis']['ticks'][0]) is not list:
                    lconf['x-axis']['ticks'] = [lconf['x-axis']['ticks'], ['${}$'.format(xt) for xt in lconf['x-axis']['ticks']]]
                plt.xticks(lconf['x-axis']['ticks'][0],lconf['x-axis']['ticks'][1])
            if lconf['y-axis']['ticks']:
                if type(lconf['y-axis']['ticks'][0]) is not list:
                    lconf['y-axis']['ticks'] = [lconf['y-axis']['ticks'], ['${}$'.format(yt) for yt in lconf['y-axis']['ticks']]]
                plt.yticks(lconf['y-axis']['ticks'][0],lconf['y-axis']['ticks'][1])

            if lconf['z-axis']['colorbar']:
                cbar = plt.colorbar(cs, orientation=lconf['z-axis']['colorbar_orientation'], **lconf['z-axis'].get('kwargs',{}))
                if zlabel:
                    cbar.set_label(zlabel)
                if lconf['z-axis']['ticks']:
                    if type(lconf['z-axis']['ticks'][0]) is not list:
                        lconf['z-axis']['ticks'] = [lconf['z-axis']['ticks'], ['${}$'.format(zt) for zt in lconf['z-axis']['ticks']]]
                    cbar.set_ticks(lconf['z-axis']['ticks'][0])
                    if lconf['z-axis']['colorbar_orientation'] == 'horizontal':
                        cbar.ax.set_xticklabels(lconf['z-axis']['ticks'][1])
                    else:
                        cbar.ax.set_yticklabels(lconf['z-axis']['ticks'][1])
                for label in cbar.ax.yaxis.get_ticklabels():
                    if lconf['z-axis']['colorbar_orientation'] == 'horizontal':
                        label.set_ha('center')
                    else:
                        label.set_va('center')

            lcount += 1

        if pconf['textbox'] and 'text' in pconf['textbox']:
            bbox = pconf['textbox'].get('bbox', dict(boxstyle='round', facecolor='white', alpha=0.2))
            va = pconf['textbox'].get('va', 'top')
            ha = pconf['textbox'].get('ha', 'left')
            textsize = pconf['textbox'].get('fontsize', pconf['rcParams'].get('font.size',15))
            xtext = pconf['textbox'].get('x', 0.95)
            ytext = pconf['textbox'].get('y', 0.85)
            plt.gcf().text(xtext, ytext, pconf['textbox']['text'], fontsize=textsize ,va=va, ha=ha, bbox=bbox)

        if pconf['tick_params']:
            plt.tick_params(**pconf['tick_params'])

        if any([lbl.get('label', False) for lbl in p['plots']]):
            plt.legend(**pconf['legend'])

        ax = plt.gca()
        for label in ax.yaxis.get_ticklabels():
            label.set_verticalalignment('center')
        for label in ax.xaxis.get_ticklabels():
            label.set_horizontalalignment('center')

        for ann in p.get('annotiations',[]):
            plt.annotate(ann['label'], ann['pos'], **ann.get('kwargs',{}))

        plotfile = DIR + p.get('filename', 'plot{}.png'.format(pcount))
        # logging.info("Saving {}.".format(plotfile))
        print("Saving {}.".format(plotfile))
        plt.savefig(plotfile, bbox_inches="tight", dpi=pconf['dpi'])
        pcount += 1
