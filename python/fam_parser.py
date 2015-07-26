"""
FAM parser.


(C) 2015 Jeroen F.J. Laros <J.F.J.Laros@lumc.nl>
"""


import os

from bin_parser import BinParser


# TODO: Make a cleaning function (restructure relationships etc.).
class FamParser(BinParser):
    def __init__(self, input_handle, experimental=False, debug=0):
        super(FamParser, self).__init__(input_handle,
            open(os.path.join(os.path.dirname(__file__), '../structure.yml')),
            open(os.path.join(os.path.dirname(__file__), '../types.yml')),
            experimental=experimental, debug=debug)
