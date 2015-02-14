#!/usr/bin/env python

"""
FAM parser.


(C) 2015 Jeroen F.J. Laros <J.F.J.Laros@lumc.nl>
"""

import argparse


class FamParser(object):
    """
    """
    FIELD_DELIMITER = chr(0x0d)

    def __init__(self):
        """
        """
        self.fields = []


    def read(self, input_handle):
        """
        """
        self.fields = input_handle.read().split(self.FIELD_DELIMITER)


    def write(self, output_handle):
        """
        """
        for field in self.fields:
            output_handle.write('{:3}: "{}" "{}"\n'.format(len(field),
                field, field.encode('hex')))


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
