#!/usr/bin/env python

"""
FAM parser.


(C) 2015 Jeroen F.J. Laros <J.F.J.Laros@lumc.nl>
"""

import argparse
import collections
import time


def _identity(data):
    return data


def _trim(data, delimiter=chr(0x00)):
    return data.split(delimiter)[0]


def _proband(data):
    return ['NOT_A_PROBAND', 'ABOVE_LEFT', 'ABOVE_RIGHT', 'BELOW_LEFT',
        'BELOW_RIGHT', 'LEFT', 'RIGHT'][ord(data)]


def _sex(data):
    return ['MALE', 'FEMALE', 'UNKNOWN'][ord(data)]

def _raw(data):
    return data.encode('hex')

def _date(data, default_date='01-01-9999'):
    """
    Decode a date.

    The date is encoded as an integer, representing the year followed by
    the (zero padded) day of the year. This integer is stored in little
    endian order.

    Decoding is done as follows:
    - Reverse the order of the bits.
    - Convert the bits to ordinals.
    - Interpret the list of ordinals as digits in base 256.

    :arg str data: Binary encoded date.
    :arg str default_date: Return value in case of missing date.

    :return object: Time object.
    """
    date_int = reduce(lambda x, y: x * 0x100 + y,
        map(lambda x: ord(x), data[::-1]))
    if date_int:
        return time.strptime(str(date_int), '%Y%j')
    return time.strptime(default_date, '%d-%m-%Y')


class Family(object):
    """
    """
    def __init__(self):
        """
        """
        self.data = ""
        self.attributes = collections.OrderedDict()
        self.offset = 0


    def _set_field(self, name, size, function=_identity, delimiter=chr(0x0d)):
        """
        :arg str name: Field name.
        :arg int size: Size of fixed size field.
        :arg function function: Conversion function.
        :arg str delimiter: Delimeter for variable size field.
        """
        if size:
            field = self.data[self.offset:self.offset + size]
            self.offset += size
        else:
            field = self.data[self.offset:].split(delimiter)[0]
            self.offset += len(field) + 1

        if name:
            self.attributes[name] = function(field)


    def read(self, input_handle):
        """
        :arg stream input_handle: Open readable handle to a FAM file.
        """
        self.data = input_handle.read()

        self._set_field('SOURCE', 26, _trim),
        self._set_field('FAMILY_NAME', 0, _identity),
        self._set_field('FAMILY_ID', 0, _identity),
        self._set_field('AUTHOR', 0, _identity),
        self._set_field('SIZE', 1, ord),
        self._set_field('', 45, _identity),
        self._set_field('COMMENT', 0, _identity),
        self._set_field('DATE_CREATED', 3, _date),
        self._set_field('', 1, _identity),
        self._set_field('DATE_UPDATED', 3, _date),
        self._set_field('', 32, _identity),

        self._set_field('SURNAME', 0, _identity),
        self._set_field('', 0, _identity),
        self._set_field('FORENAMES', 0, _identity),
        self._set_field('', 0, _identity),
        self._set_field('MAIDEN_NAME', 0, _identity),
        self._set_field('', 12, _identity),
        self._set_field('DATE_OF_BIRTH', 3, _date),
        self._set_field('', 1, _identity),
        self._set_field('DATE_OF_DEATH', 3, _date),
        self._set_field('', 1, _identity),
        self._set_field('SEX', 1, _sex),
        self._set_field('', 4, _identity),
        self._set_field('MOTHER_ID', 1, ord),
        self._set_field('', 1, _identity),
        self._set_field('FATHER_ID', 1, ord),
        self._set_field('', 1, _identity),
        self._set_field('INTERNAL_ID', 1, ord),
        self._set_field('', 1, _identity),
        self._set_field('NUMBER_OF_INDIVIDUALS', 1, ord),
        self._set_field('', 1, _identity),
        self._set_field('AGE_GESTATION', 0, _identity),
        self._set_field('ID', 0, _identity),
        self._set_field('NUMBER_OF_SPOUSES', 1, ord),
        self._set_field('', 1, _identity),

        for spouse in range(self.attributes['NUMBER_OF_SPOUSES']):
            self._set_field(''.format(spouse), 4, _raw)

        self._set_field('', 7, _identity),
        self._set_field('PROBAND', 1, _proband),
        self._set_field('X_COORDINATE', 1, ord),
        self._set_field('', 1, _identity),
        self._set_field('Y_COORDINATE', 1, ord),
        self._set_field('_', 100, _raw),


    def write(self, output_handle):
        for key, value in self.attributes.items():
            output_handle.write("{}: {}\n".format(key, value))


def fam_parser(input_handle, output_handle):
    """
    Main entry point.

    :arg stream input_handle: Open readable handle to a FAM file.
    :arg stream output_handle: Open writable handle.
    """
    parser = Family()
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
