#!/usr/bin/env python

"""
FAM parser.


(C) 2015 Jeroen F.J. Laros <J.F.J.Laros@lumc.nl>
"""

import argparse
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


def _bit(data):
    return '{0:04b}'.format(ord(data))

def _date(data):
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

    :return object: Date in format %d-%m-%Y.
    """
    date_int = reduce(lambda x, y: x * 0x100 + y,
        map(lambda x: ord(x), data[::-1]))
    if date_int == 0xFFFFFF:
        return 'DEFINED'
    if date_int:
        return time.strftime('%d-%m-%Y', time.strptime(str(date_int), '%Y%j'))
    return 'UNKNOWN'


class Family(object):
    """
    """
    def __init__(self):
        """
        """
        self.data = ""
        self.family_attributes = {}
        self.members = []
        self.offset = 0


    def _set_field(self, destination, name, size, function=_identity,
            delimiter=chr(0x0d)):
        """
        :arg dict destination: Destination dictionary.
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
            destination[name] = function(field)


    def _parse_family(self):
        """
        """
        self._set_field(self.family_attributes, 'SOURCE', 26, _trim)
        self._set_field(self.family_attributes, 'FAMILY_NAME', 0, _identity)
        self._set_field(self.family_attributes, 'FAMILY_ID', 0, _identity)
        self._set_field(self.family_attributes, 'AUTHOR', 0, _identity)
        self._set_field(self.family_attributes, 'SIZE', 1, ord)
        self._set_field(self.family_attributes, '', 45, _raw)
        self._set_field(self.family_attributes, 'COMMENT', 0, _identity)
        self._set_field(self.family_attributes, 'DATE_CREATED', 3, _date)
        self._set_field(self.family_attributes, '', 1, _raw)
        self._set_field(self.family_attributes, 'DATE_UPDATED', 3, _date)
        self._set_field(self.family_attributes, '', 32, _raw)


    def _parse_member(self):
        """
        """
        member = {}
        self._set_field(member, 'SURNAME', 0, _identity)
        self._set_field(member, '', 0, _raw)
        self._set_field(member, 'FORENAMES', 0, _identity)
        self._set_field(member, '', 0, _raw)
        self._set_field(member, 'MAIDEN_NAME', 0, _identity)
        self._set_field(member, '', 12, _raw)
        self._set_field(member, 'DATE_OF_BIRTH', 3, _date)
        self._set_field(member, '', 1, _raw)
        self._set_field(member, 'DATE_OF_DEATH', 3, _date)
        self._set_field(member, '', 1, _raw)
        self._set_field(member, 'SEX', 1, _sex)
        self._set_field(member, 'ID', 1, ord)
        self._set_field(member, '', 3, _raw)
        self._set_field(member, 'MOTHER_ID', 1, ord)
        self._set_field(member, '', 1, _raw)
        self._set_field(member, 'FATHER_ID', 1, ord)
        self._set_field(member, '', 1, _raw)
        self._set_field(member, 'INTERNAL_ID', 1, ord)
        self._set_field(member, '', 1, _raw)
        self._set_field(member, 'NUMBER_OF_INDIVIDUALS', 1, ord)
        self._set_field(member, '', 1, _raw)
        self._set_field(member, 'AGE_GESTATION', 0, _identity)
        self._set_field(member, 'INDIVIDUAL_ID', 0, _identity)
        self._set_field(member, 'NUMBER_OF_SPOUSES', 1, ord)
        self._set_field(member, '', 1, _raw)

        for spouse in range(member['NUMBER_OF_SPOUSES']):
            self._set_field(member, 'SPOUSE_{}_ID'.format(spouse), 1, ord)
            self._set_field(member, '', 3, _raw)

        self._set_field(member, '', 4, _raw)
        self._set_field(member, 'ANNOTATION_1', 1, _bit)
        self._set_field(member, '', 2, _raw)
        self._set_field(member, 'PROBAND', 1, _proband)
        self._set_field(member, 'X_COORDINATE', 1, ord)
        self._set_field(member, '', 1, _raw)
        self._set_field(member, 'Y_COORDINATE', 1, ord)
        self._set_field(member, '', 1, _raw)
        self._set_field(member, 'ANNOTATION_2', 1, _bit)
        self._set_field(member, '', 26, _raw)
        self._set_field(member, 'ANNOTATION_3', 1, _bit)
        self._set_field(member, '', 205, _raw)

        self.members.append(member)


    def _write_dictionary(self, dictionary, output_handle):
        """
        :arg dict dictionary: Dictionary to write.
        :arg stream output_handle: Open writable handle.
        """
        for key, value in sorted(dictionary.items()):
            output_handle.write("{}: {}\n".format(key, value))


    def read(self, input_handle):
        """
        :arg stream input_handle: Open readable handle to a FAM file.
        """
        self.data = input_handle.read()

        self._parse_family()
        for member in range(self.family_attributes['SIZE']):
            self._parse_member()


    def write(self, output_handle):
        """
        :arg stream output_handle: Open writable handle.
        """
        self._write_dictionary(self.family_attributes, output_handle)

        for member in self.members:
            output_handle.write('\n---\n\n')
            self._write_dictionary(member, output_handle)


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
