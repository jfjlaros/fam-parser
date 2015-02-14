#!/usr/bin/env python

"""
FAM parser.


(C) 2015 Jeroen F.J. Laros <J.F.J.Laros@lumc.nl>
"""

import argparse
import time


class FamParser(object):
    """
    """
    FIELD_DELIMITER = chr(0x0d)
    END_OF_STRING = chr(0x00)
    HEADER_OFFSET = 0x1A
    MAP = {
        'FAMNAME': 0,
        'FAMID': 1,
        'AUTHOR': 2,
    }

    def __init__(self):
        """
        """
        self.data = ""
        self.fields = []
        self.metadata = {}


    def _trim(self, line):
        return line.split(self.END_OF_STRING)[0]


    def _parse_metadata(self):
        """
        """
        for key in self.MAP:
            self.metadata[key] = self._trim(self.fields[self.MAP[key]])


    def _parse_date(self, date):
        """
        """
        date_int = reduce(lambda x, y: x * 0x100 + y,
            map(lambda x: ord(x), date[::-1]), 0)
        return time.strptime(str(date_int), "%Y%j")


    def read(self, input_handle):
        """
        """
        self.metadata['SOURCE'] = self._trim(input_handle.read(
            self.HEADER_OFFSET))
        self.data = input_handle.read()
        self.fields = self.data.split(self.FIELD_DELIMITER)
        self._parse_metadata()
        self.metadata['CREATED'] = self._parse_date(self.fields[11][:3])
        self.metadata['UPDATED'] = self._parse_date(self.fields[11][4:7])


    def write(self, output_handle):
        """
        """
        #for line, field in enumerate(self.fields):
        #    output_handle.write('{:3} {:3}: "{}" "{}"\n'.format(line,
        #        len(field), field, field.encode('hex')))
        print self.metadata


def fam_parser(input_handle, output_handle):
    """
    """
    parser = FamParser()
    parser.read(input_handle)
    parser.write(output_handle)


def main():
    """
    Command line argument parsing.
    """
    usage = __doc__.split('\n\n\n')
    parser = argparse.ArgumentParser(description=usage[0], epilog=usage[1],
        formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument('input_handle', type=argparse.FileType('r'),
        help='input file in FAM format')
    parser.add_argument('output_handle', type=argparse.FileType('w'),
        help='output file')

    args = parser.parse_args()
    fam_parser(args.input_handle, args.output_handle)


if __name__ == '__main__':
    main()
