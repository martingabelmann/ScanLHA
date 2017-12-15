#!/usr/bin/env python3
# pylint: disable=broad-except

import pyslha
import argparse
import yaml
# import lzma
import logging
from pprint import pprint
from subprocess import Popen

class SpehnoScan():
    def __init__(self, config='config.yml'):
        "read config from file"
        try:
            with open(config, 'r') as c:
                self.config = yaml.safe_load(c)
        except:
            logging.error("failed to load " + config)

    def check_config(self):
        pass

    def runspheno(self):
        pass

    def readspc(self):
        pass

    def readin(self):
        pass

    def scan(self):
        pass

def parse_args():
    parser = argparse.ArgumentParser(description="Perform a scan with SPheno.")
    parser.add_argument('config', help='yaml config file', default='config.yml')
    parser.add_argument('--verbose', '-v', action='count', help='more output', default=0)
    args = parser.parse_args()
    return args

def main():
    pass

if __name__ == "__main__":
    main()
