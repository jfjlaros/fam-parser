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
    DEFAULT_DATE = '01-01-9999'

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
        Decode a date.

        The date is encoded as an integer, representing the year followed by
        the (zero padded) day of the year. This integer is stored in little
        endian order.

        Decoding is done as follows:
        - Reverse the order of the bits.
        - Convert the bits to ordinals.
        - Interpret the list of ordinals as digits in base 256.

        :arg str date: Binary encoded date.

        :return object: Time object.
        """
        date_int = reduce(lambda x, y: x * 0x100 + y,
            map(lambda x: ord(x), date[::-1]))
        if date_int:
            return time.strptime(str(date_int), '%Y%j')
        return time.strptime(self.DEFAULT_DATE, '%d-%m-%Y')


    def read(self, input_handle):
        """
        :arg stream input_handle: Open readable handle to a FAM file.
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
        :arg stream output_handle: Open writable handle.
        """
        #for line, field in enumerate(self.fields):
        #    output_handle.write('{:3} {:3}: "{}" "{}"\n'.format(line,
        #        len(field), field, field.encode('hex')))
        print self.metadata


def fam_parser(input_handle, output_handle):
    """
    Main entry point.

    :arg stream input_handle: Open readable handle to a FAM file.
    :arg stream output_handle: Open writable handle.
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
