#!/usr/bin/env python3
import os
import sys
import logging
import ScanLHA
from argparse import ArgumentParser
from IPython import embed

LIBPATH = os.path.dirname(ScanLHA.__file__)
def cpath(yml):
    return os.path.join(LIBPATH,'configs',yml)

def main():
    parser = ArgumentParser(description='Perform a (S)LHA scan.')
    parser.add_argument("config", type=str,
            help="path to YAML file config.yml containing blocks to scan. Must be the very first argument.")
    parser.add_argument("output", nargs='?', default="config.h5",
            help="Optional file path to store the results. Defaults to config.h5")
    parser.add_argument("-v", "--verbose", action="store_true",
            help="increase output verbosity")

    if len(sys.argv) == 1:
        parser.parse_args(["-h"])
    if not os.path.isfile(sys.argv[1]):
        logging.error('No valid config file "{}".'.format(sys.argv[1]))
        parser.parse_args(["-h"])

    logging.getLogger().setLevel(logging.INFO)

    c = ScanLHA.Config(cpath('SPheno.yml'))
    scanc = ScanLHA.Config(sys.argv[1])
    c.append(scanc)

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
        required_paras = parser.add_argument_group("Parameters to be specified for the scan.")
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
        c[p][c[p]['argument']] = v

    HDFSTORE = args.output if args.output else args.config.replace('.yml','.h5')
    if HDFSTORE == args.config:
        print('ScanLHA.Scan config file must end with ".yml"')
        exit(1)
    HDFSTORE = os.path.abspath(HDFSTORE)

    if os.path.exists(HDFSTORE):
            if input("File {} already exists. Overwrite/append? [n/y]".format(HDFSTORE)) != "y":
                exit(0)

    if c['runner'].get('scantype', 'straight') == 'random':
        scan = ScanLHA.RandomScan(c)
    else:
        scan = ScanLHA.Scan(c)
    scan.submit()
    scan.save(filename=HDFSTORE)
