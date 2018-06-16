#!/usr/bin/env python3
from pandas import read_hdf
# from IPython import embed
import logging
import os
from .config import Config
from math import * # noqa: E403
from collections import ChainMap
from argparse import ArgumentParser
import matplotlib
from matplotlib.colors import LogNorm
matplotlib.use('Agg')
import matplotlib.pyplot as plt # noqa: E402

def main():
    parser = ArgumentParser(description='Plot ScanLHA results.')
    parser.add_argument("config", type=str,
            help="path to YAML file config.yml containing the plot (and optional scan) config.")
    parser.add_argument("-v", "--verbose", action="store_true",
            help="increase output verbosity")

    args = parser.parse_args()

    logging.getLogger().setLevel(logging.INFO)
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    class PlotConf(ChainMap):
        """ config class which allows for recursively defined defaults """
        axisdefault = {
                'boundaries' :  [],
                'lognorm' :  False,
                'vmin' :  'auto',
                'vmax' :  'auto',
                'ticks' :  'auto',
                'colorbar' :  False,
                'label' : None
                }

        def __init__(self, *args):
            super().__init__(*args)
            self.maps.append({
                'x-axis': self.axisdefault,
                'y-axis': self.axisdefault,
                'z-axis': self.axisdefault,
                'legend': {
                    'loc' : 'right',
                    'bbox_to_anchor' : [1.5, 0.5]
                    },
                'hline': False,
                'vline': False,
                'title': False,
                'label': None,
                'cmap': None,
                'alpha' : 1.0,
                'datafile': 'results.h5',
                'rcParams': {
                    'font.size': 15
                    },
                'dpi': 800,
                'textbox': {}
                })

        def new_child(self, child = {}):
            for ax in ['x-axis','y-axis','z-axis']:
                if type(child.get(ax, {})) == str:
                    child[ax] = ChainMap({ 'field': child[ax] }, self[ax])
                else:
                    child[ax] = ChainMap(child.get(ax,{}), self[ax])
            return self.__class__(child, *self.maps)

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

    if 'datafile' not in conf:
        logging.error('No "datafile" to plot given')
        exit(1)

    DATA = read_hdf(conf['datafile'])
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
        plt.rc('text', usetex=True)
        plt.rcParams.update(pconf['rcParams'])

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
                xlabel = c.parameters.get(x, {'latex': xlabel})['latex']
                ylabel = c.parameters.get(y, {'latex': ylabel})['latex']
                zlabel = c.parameters.get(z, {'latex': zlabel})['latex']
            if xlabel:
                plt.xlabel(xlabel)
            if ylabel:
                plt.ylabel(ylabel)

            if lconf['hline']:
                plt.axhline(y=y, color=color, linestyle='-', label=label, zorder=zorder)
                continue
            if lconf['vline']:
                plt.axvline(x=x, color=color, linestyle='-', label=label, zorder=zorder)
                continue

            if hasattr(c, 'parameters'):
                x = c.parameters.get(x,{'lha': x})['lha']
                y = c.parameters.get(y,{'lha': y})['lha']
                z = c.parameters.get(z,{'lha': z})['lha']

            PDATA = DATA
            for ax,field in {'x-axis':x, 'y-axis':y, 'z-axis':z}.items():
                bounds = lconf[ax]['boundaries']
                if len(bounds) == 2:
                    PDATA = PDATA[(PDATA[field] >= bounds[0]) & (PDATA[field] <= bounds[1])]

            if lconf['x-axis']['lognorm']:
                plt.xscale('log')
            if lconf['y-axis']['lognorm']:
                plt.yscale('log')
            znorm = LogNorm(vmin=PDATA[z].min(), vmax=PDATA[z].max()) if lconf['z-axis']['lognorm'] else None

            if z:
                color = PDATA[z]

            cs = plt.scatter(PDATA[x], PDATA[y], zorder=zorder, label=label, cmap=cmap, c=color, norm=znorm, alpha=pconf['alpha'])

            if lconf['z-axis']['colorbar']:
                cbar = plt.colorbar(cs)
                if zlabel:
                    cbar.set_label(zlabel)

            lcount += 1

        if any([l.get('legend', True) for l in p['plots']]):
            plt.legend(**pconf['legend'])

        if pconf['textbox'] and 'text' in pconf['textbox']:
            bbox = pconf['textbox'].get('bbox', dict(boxstyle='round', facecolor='white', alpha=0.5))
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
