#!/usr/bin/env python3
"Perform parameter scans with tools using SLHA input and output."
from .scan import Scan
from .config import Config
from  .runner import RUNNERS,BaseRunner
from  .slha import genSLHA, parseSLHA
__version__ = '0.1'
