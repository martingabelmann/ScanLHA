#!/usr/bin/env python3
"""
Plot ScanLHA scan results.
"""
from pandas import HDFStore
# from IPython import embed
import logging
import os
from .config import Config
from math import * # noqa: E403 F401 F403
from collections import ChainMap
from argparse import ArgumentParser
import matplotlib
from matplotlib.colors import LogNorm, Normalize
from matplotlib.colorbar import ColorbarBase
matplotlib.use('Agg')
# matplotlib.use('ps')
import matplotlib.pyplot as plt # noqa: E402

__all__ = ['Plot', 'PlotConf', 'axisdefault']

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
            'legend': {
                'loc' : 'right',
                'bbox_to_anchor' : [1.5, 0.5]
                },
            'hline': False,
            'vline': False,
            'lw': 1.0,
            's': None,
            'title': False,
            'label': None,
            'cmap': None,
            'alpha' : 1.0,
            'datafile': 'results.h5',
            'fontsize': 28,
            'rcParams': {
                'font.size': 28,
                'text.usetex': True,
                'font.weight' : 'bold',
                'text.latex.preamble': [
                    r'\usepackage{xcolor}',
                    r'\usepackage{nicefrac}',
                    r'\usepackage{amsmath}',
                    r'\usepackage{units}',
                    r'\usepackage{sfmath} \boldmath']
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
    parser.add_argument("-v", "--verbose", action="store_true",
            help="increase output verbosity")

    args = parser.parse_args()

    logging.getLogger().setLevel(logging.INFO)
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    c = Config(args.config)
    DIR = os.path.dirname(os.path.abspath(args.config)) + '/'

    if 'scatterplot' not in c:
        logging.error('config file must contain "scatterplot" dict.')
        exit(1)

    if 'plots' not in c['scatterplot']:
        logging.error('no plots to plot')
        exit(1)

    conf = PlotConf()
    conf = conf.new_child(c['scatterplot'].get('conf',{}))

    if not os.path.isfile(conf['datafile']):
        logging.error('Data file {} does not exist.'.format(conf['datafile']))
        exit(1)

    store = HDFStore(conf['datafile'])
    path = 'results' # TODO
    DATA = store[path]
    attrs = store.get_storer(path).attrs
    if hasattr(attrs, 'config') and conf.get('conf_overwrite', False):
        attrs.config['scatterplot'] = {}
        c.append(attrs.config)
    if not DATA.empty and 'newfields' in conf:
        for field,expr in conf['newfields'].items():
            logging.debug("executing DATA[{}] = {}]".format(field, expr))
            DATA[field] = eval(expr)
        logging.debug("done.")

    pcount = 0
    for p in c['scatterplot']['plots']:
        lcount = 0

        pconf = conf.new_child(p)

        plt.cla()
        plt.clf()
        plt.rcParams.update(pconf['rcParams'])
        if pconf['fontsize'] != conf['fontsize']:
            plt.rcParams.update({'font.size': pconf['fontsize']})

        if pconf['colorbar_only']:
            plt.figure(figsize=(8, 0.25))
            ax = plt.gca()
            norm = Normalize(vmin=pconf['z-axis']['vmin'], vmax=pconf['z-axis']['vmax'])
            if pconf['z-axis']['lognorm']:
                norm = LogNorm(vmin=pconf['z-axis']['vmin'], vmax=pconf['z-axis']['vmax'])
            cbar = ColorbarBase(ax,norm=norm, cmap=pconf['cmap'], orientation=pconf['z-axis']['colorbar_orientation'])
            if pconf['z-axis']['colorbar_orientation'] == 'horizontal':
                ax.xaxis.set_label_position('top')
                ax.xaxis.set_ticks_position('top')
            if pconf['z-axis']['label']:
                cbar.set_label(pconf['z-axis']['label'])
            if pconf['z-axis']['ticks']:
                cbar.set_ticks(pconf['z-axis']['ticks'])
            plt.savefig(pconf['filename'],bbox_inches='tight')
            plt.figure()
            continue

        if pconf['title']:
            plt.title(conf['title'])

        if 'plots' not in p:
            p['plots'] = [p]

        for l in p['plots']:
            lconf = pconf.new_child(l)

            label = lconf['label']
            label = label if label else None
            cmap = lconf['cmap']
            zorder = lconf.get('zorder', lcount)
            color = lconf.get('color', "C{}".format(lcount))

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
            if(lconf['datafile'] and lconf['datafile'] != conf['datafile']):
                conf['datafile'] = lconf['datafile'] # TODO
                DATA = HDFStore(lconf['datafile'])['results']  # TODO
                PDATA = DATA
                if not PDATA.empty and 'newfields' in conf:
                    for field,expr in conf['newfields'].items():
                        logging.debug("executing PATA[{}] = {}]".format(field, expr))
                        PDATA[field] = eval(expr)
                    logging.debug("done.")

            for ax,field in {'x-axis':x, 'y-axis':y, 'z-axis':z}.items():
                bounds = lconf[ax]['boundaries']
                if len(bounds) == 2:
                    PDATA = PDATA[(PDATA[field] >= bounds[0]) & (PDATA[field] <= bounds[1])]

            for constr in lconf['constraints']:
                PDATA = PDATA[eval(constr)]

            if lconf['x-axis']['lognorm']:
                plt.xscale('log')
            if lconf['y-axis']['lognorm']:
                plt.yscale('log')

            if z:
                color = PDATA[z]
                vmin = PDATA[z].min() if not lconf['z-axis']['vmin'] else lconf['z-axis']['vmin']
                vmax = PDATA[z].max() if not lconf['z-axis']['vmax'] else lconf['z-axis']['vmax']
            else:
                vmin = None
                vmax = None
            znorm = LogNorm(vmin=vmin, vmax=vmax) if lconf['z-axis']['lognorm'] else None

            cs = plt.scatter(PDATA[x], PDATA[y], zorder=zorder, label=label, cmap=cmap, c=color, vmin=vmin, vmax=vmax, norm=znorm, s=lconf['s'], alpha=lconf['alpha'])

            plt.margins(x=0.01,y=0.01)  # TODO
            if lconf['x-axis']['ticks']:
                plt.xticks(lconf['x-axis']['ticks'][0],lconf['x-axis']['ticks'][1])
            if lconf['y-axis']['ticks']:
                plt.yticks(lconf['y-axis']['ticks'][0],lconf['y-axis']['ticks'][1])

            if lconf['z-axis']['colorbar']:
                cbar = plt.colorbar(cs, orientation=lconf['z-axis']['colorbar_orientation'])
                if zlabel:
                    cbar.set_label(zlabel)
                if lconf['z-axis']['ticks']:
                    cbar.set_ticks(lconf['z-axis']['ticks'])

            lcount += 1

        if any([l.get('label', False) for l in p['plots']]):
            plt.legend(**pconf['legend'])

        if pconf['textbox'] and 'text' in pconf['textbox']:
            bbox = pconf['textbox'].get('bbox', dict(boxstyle='round', facecolor='white', alpha=0.2))
            va = pconf['textbox'].get('va', 'top')
            ha = pconf['textbox'].get('ha', 'left')
            textsize = pconf['textbox'].get('fontsize', pconf['rcParams'].get('font.size',15))
            xtext = pconf['textbox'].get('x', 0.95)
            ytext = pconf['textbox'].get('y', 0.85)
            plt.gcf().text(xtext, ytext, pconf['textbox']['text'], fontsize=textsize ,va=va, ha=ha, bbox=bbox)

        plotfile = DIR + p.get('filename', 'plot{}.png'.format(pcount))
        logging.info("Saving {}.".format(plotfile))
        plt.savefig(plotfile, bbox_inches="tight", dpi=pconf['dpi'])
        pcount += 1

    store.close()
