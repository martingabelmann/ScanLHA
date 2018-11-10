Module ScanLHA.PlotLHA
----------------------

Variables
---------
axisdefault
    Default values for all axes.

Functions
---------
Plot()
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
                y-axis: {field: TanBeta, label: '$\tan\beta$'}
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

Classes
-------
PlotConf 
    Config class which allows for successively defined defaults

    Ancestors (in MRO)
    ------------------
    ScanLHA.PlotLHA.PlotConf
    collections.ChainMap
    collections.abc.MutableMapping
    collections.abc.Mapping
    collections.abc.Collection
    collections.abc.Sized
    collections.abc.Iterable
    collections.abc.Container
    builtins.object

    Static methods
    --------------
    __init__(self, *args)
        Initialize a ChainMap by setting *maps* to the given mappings.
        If no mappings are provided, a single empty dictionary is used.

    clear(self)
        Clear maps[0], leaving maps[1:] intact.

    copy(self)
        New ChainMap or subclass with a new copy of maps[0] and refs to maps[1:]

    get(self, key, default=None)
        D.get(k[,d]) -> D[k] if k in D, else d.  d defaults to None.

    items(self)
        D.items() -> a set-like object providing a view on D's items

    keys(self)
        D.keys() -> a set-like object providing a view on D's keys

    new_child(self, child={})
        New ChainMap with a new map followed by all previous maps.
        If no map is provided, an empty dict is used.

    pop(self, key, *args)
        Remove *key* from maps[0] and return its value. Raise KeyError if *key* not in maps[0].

    popitem(self)
        Remove and return an item pair from maps[0]. Raise KeyError is maps[0] is empty.

    setdefault(self, key, default=None)
        D.setdefault(k[,d]) -> D.get(k,d), also set D[k]=d if k not in D

    update(*args, **kwds)
        D.update([E, ]**F) -> None.  Update D from mapping/iterable E and F.
        If E present and has a .keys() method, does:     for k in E: D[k] = E[k]
        If E present and lacks .keys() method, does:     for (k, v) in E: D[k] = v
        In either case, this is followed by: for k, v in F.items(): D[k] = v

    values(self)
        D.values() -> an object providing a view on D's values

    Instance variables
    ------------------
    parents
        New ChainMap from maps[1:].

    Methods
    -------
    fromkeys(cls, iterable, *args)
        Create a ChainMap with a single dict created from the iterable.
