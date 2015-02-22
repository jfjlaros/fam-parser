#!/usr/bin/env python

"""
Container that acts like an ordered default dictionary.
"""

import collections

class Container(collections.OrderedDict):
    """
    Simple ordered default dictionary.
    """
    def __getitem__(self, key):
        if key not in self.keys():
            self[key] = 0;
        return super(Container, self).__getitem__(key)
