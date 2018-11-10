Module ScanLHA.slha
-------------------

Functions
---------
genSLHA(blocks)
    Generate string in SLHA format from `'blocks'` entry of a `ScanLHA.config.Config` instance.

list2dict(l)
    recursively convert [1,2,3,4] to {'1':{'2':{'3':4}}

mergedicts(l, d)
    merge list of nested dicts

parseSLHA(slhafile, blocks=[])
    Turn the content of an SLHA file into a dictionary

    `slhafile` : path tp file

    `blocks`   : list of BLOCKs (strings) to read, if empty all blocks are read

    Uses [pylha](https://github.com/DavidMStraub/pylha pylha) but gives a more meaningful output
    the result is stored in a nested dictionary.
