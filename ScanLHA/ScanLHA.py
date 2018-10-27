#!/usr/bin/env python3
import os
import sys
import logging
import ScanLHA
from argparse import ArgumentParser
from math import * # noqa: F401 F403

def cpath(yml):
    if os.path.isfile(yml):
        return yml
    default = os.path.join(os.path.dirname(ScanLHA.__file__),'configs',yml)
    if os.path.isfile(default):
        return default
    return yml

def main():
    parser = ArgumentParser(description='Perform a (S)LHA scan.')
    parser.add_argument("config", type=str, metavar="config.yml",
            help="path to YAML file config.yml containing config for the scan. Must be the very first argument.")
    parser.add_argument("output", nargs='?', default="config.h5",
            help="optional file path to store the results, defaults to config.h5")
    parser.add_argument("-v", "--verbose", action="store_true",
            help="increase output verbosity")
    parser.add_argument("-p", "--parallel", metavar='N', type=int, default=None,
            help="parallelize on N threads")
    parser.add_argument("-o", "--overwrite", action="store_true",
            help="overwrite output files without asking")

    if len(sys.argv) == 1:
        parser.parse_args(["-h"])
    if not os.path.isfile(sys.argv[1]):
        parser.parse_args()
        logging.error('No valid config file "{}".'.format(sys.argv[1]))
        parser.parse_args(["-h"])

    logging.debug('loading config {}'.format(sys.argv[1]))
    scanconf = ScanLHA.Config(sys.argv[1])
    defaultfile = scanconf['runner'].get('defaults', 'SPheno.yml')
    if defaultfile:
        logging.debug('loading default config {}'.format(defaultfile))
        c = ScanLHA.Config(cpath(defaultfile))
        if not c.valid:
            logging.error('No valid default config.')
            sys.exit(1)
        c.append(scanconf)
    else:
        c = scanconf

    if not c.valid:
        logging.error('No valid scan config.')
        sys.exit(1)

    arg_paras = [ p for p,v in c.parameters.items() if v.get('argument', False) ]
    arg_types = {
            'help': {
                'values': 'List input: para="[value1, value2, ...]"',
                'value': 'Single number input: para=value',
                'random': 'Random number input: para=[min,max]',
                'scan': 'ScanLHA.Scan range input: para="[start, stop, num]"'
                },
            }
    if arg_paras:
        required_paras = parser.add_argument_group("Parameters to be specified for the scan")
    for p in arg_paras:
        required_paras.add_argument("--{}".format(p),
                help=arg_types['help'][c[p]['argument']],
                required=True
                )
    args = parser.parse_args()
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    for p,v in args.__dict__.items():
        if p not in arg_paras:
            continue
        c[p][c[p]['argument']] = eval(v)

    if not c.valid:
        logging.error('No valid scan config.')
        sys.exit(1)

    HDFSTORE = args.output if args.output else args.config.replace('.yml','.h5')
    if HDFSTORE == args.config:
        print('Scan config file must end with ".yml"')
        exit(1)
    HDFSTORE = os.path.abspath(HDFSTORE)

    if os.path.exists(HDFSTORE):
        if args.overwrite or input("File {} already exists. Overwrite/append [o/a] ?".format(HDFSTORE)) == "o":
            logging.info("removing {}".format(HDFSTORE))
            os.remove(HDFSTORE)

    if c['runner'].get('scantype', 'straight') == 'random':
        scan = ScanLHA.RandomScan(c)
    else:
        scan = ScanLHA.Scan(c)
    scan.submit(args.parallel)
    scan.save(filename=HDFSTORE)
