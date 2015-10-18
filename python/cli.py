import argparse
import os

import bin_parser

from . import usage, version
from .fam_parser import FamParser


def fam_parser(input_handle, output_handle):
    """
    Main entry point.

    :arg stream input_handle: Open readable handle to a FAM file.
    :arg stream output_handle: Open writable handle.
    """
    parser = FamParser(input_handle)
    parser.write(output_handle)


def main():
    """
    Command line argument parsing.
    """
    parser = argparse.ArgumentParser(
        description=usage[0], epilog=usage[1],
        formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument(
        'input_handle', type=argparse.FileType('r'),
        help='input file in FAM format')
    parser.add_argument(
        'output_handle', type=argparse.FileType('w'), help='output file')
    parser.add_argument('-v', action='version', version=version(parser.prog))

    try:
        arguments = parser.parse_args()
    except IOError as error:
        parser.error(error)

    try:
        fam_parser(**dict(
            (k, v) for k, v in vars(arguments).items()
            if k not in ('func', 'subcommand')))
    except ValueError as error:
        parser.error(error)


if __name__ == '__main__':
    main()
