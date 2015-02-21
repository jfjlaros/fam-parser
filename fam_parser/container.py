#!/usr/bin/env python

"""
"""

import collections

class Container(collections.OrderedDict):
    def __getitem__(self, key):
        if key not in self.keys():
            self[key] = 0;
        return super(Container, self).__getitem__(key)
