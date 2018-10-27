#!/usr/bin/env python3
"""
Perform parameter scans with tools that use (not only) SLHA input and output.

__Executables__

 * ScanLHA
 * PlotLHA
 * EditLHA
 * MergeLHA

"""
from .scan import Scan, RandomScan
from .config import Config
from  .runner import RUNNERS
from  .slha import genSLHA, parseSLHA
__version__ = '0.1'
