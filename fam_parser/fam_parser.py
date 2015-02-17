#!/usr/bin/env python

"""
FAM parser.


(C) 2015 Jeroen F.J. Laros <J.F.J.Laros@lumc.nl>
"""

import argparse
import collections
import time

PROBAND = ['NOT_A_PROBAND', 'ABOVE_LEFT', 'ABOVE_RIGHT', 'BELOW_LEFT',
    'BELOW_RIGHT', 'LEFT', 'RIGHT']
SEX = ['MALE', 'FEMALE', 'UNKNOWN']
ANNOTATION_1 = {
    ('00000000', '00000000'): 'NONE',
    ('00000010', '00000001'): 'FILL',
    ('00000010', '00000000'): 'FILL2', # BAR in combination with P or SB?
    ('00000011', '00000000'): 'DOT',
    ('00000100', '00000000'): 'QUESTION',
    ('00000101', '00000000'): 'RIGHT-UPPER',
    ('00000110', '00000000'): 'RIGHT-LOWER',
    ('00001000', '00000000'): 'LEFT-UPPER',
    ('00000111', '00000000'): 'LEFT-LOWER',
}
ANNOTATION_2 = {
    '00000000': 'NONE',
    '00000001': 'P',  
    '00000100': 'SB', 
    '00001011': 'BAR',
    '00000010': 'UNBORN',
    '00000011': 'ABORTED',
}


def _identity(data):
    return data


def _trim(data, delimiter=chr(0x00)):
    return data.split(delimiter)[0]


def _proband(data):
    return PROBAND[ord(data)]


def _sex(data):
    return SEX[ord(data)]


def _raw(data):
    return data.encode('hex')


def _bit(data):
    return '{0:08b}'.format(ord(data))


def _comment(data):
    return data.split(chr(0x09) + chr(0x03))


def _text(data):
    return data.split(chr(0x0b) + chr(0x0b))


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


class FamParser(object):
    """
    FAM file parsing class.
    """
    def __init__(self, debug=False):
        self.data = ""
        self.offset = 0
        self.family_attributes = collections.defaultdict(int)
        self.members = []
        self.footer = collections.defaultdict(int)
        self.text = []
        self.debug = debug


    def _set_field(self, destination, name, size, function=_identity,
            delimiter=chr(0x0d)):
        """
        Extract a field from {self.data} using either a fixed size, or a
        delimiter. After reading, {self.offset} is set to the next field.

        :arg dict destination: Destination dictionary.
        :arg str name: Field name.
        :arg int size: Size of fixed size field.
        :arg function function: Conversion function.
        :arg str delimiter: Delimeter for variable size field.
        """
        # TODO: Perhaps use the file handle instead of self.data.
        if size:
            field = self.data[self.offset:self.offset + size]
            self.offset += size
        else:
            field = self.data[self.offset:].split(delimiter)[0]
            self.offset += len(field) + 1

        if name:
            destination[name] = function(field)
        else:
            destination['_RAW_{}'.format(
                destination['_RAW_FIELDS'])] = function(field)
            destination['_RAW_FIELDS'] += 1


    def _parse_family(self):
        """
        Extract family information.
        """
        # TODO: Move SOURCE field.
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
        Extract person information.
        """
        # TODO: There seems to be support for more annotation (+/-).
        member = collections.defaultdict(int)
        self._set_field(member, 'SURNAME', 0, _identity)
        self._set_field(member, '', 1, _raw)
        self._set_field(member, 'FORENAMES', 0, _identity)
        self._set_field(member, '', 1, _raw)
        self._set_field(member, 'MAIDEN_NAME', 0, _identity)
        self._set_field(member, '', 11, _raw)
        self._set_field(member, 'COMMENT', 0, _comment)
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
        self._set_field(member, 'FLAGS_1', 1, _bit)
        self._set_field(member, '', 2, _raw)
        self._set_field(member, 'PROBAND', 1, _proband)
        self._set_field(member, 'X_COORDINATE', 1, ord)
        self._set_field(member, '', 1, _raw)
        self._set_field(member, 'Y_COORDINATE', 1, ord)
        self._set_field(member, '', 1, _raw)
        self._set_field(member, 'FLAGS_2', 1, _bit)
        self._set_field(member, '', 26, _raw)
        self._set_field(member, 'FLAGS_3', 1, _bit)
        self._set_field(member, '', 205, _raw)

        member['ANNOTATION_1'] = ANNOTATION_1[(member['FLAGS_1'],
            member['FLAGS_3'])]
        member['ANNOTATION_2'] = ANNOTATION_2[(member['FLAGS_2'])]

        self.members.append(member)


    def _parse_text(self):
        """
        Extract information from a text field.
        """
        # TODO: X and Y coordinates have more digits.
        text = collections.defaultdict(int)
        self._set_field(text, 'TEXT', 0, _text)
        self._set_field(text, '', 54, _raw)
        self._set_field(text, 'X_COORDINATE', 1, ord)
        self._set_field(text, '', 3, _raw)
        self._set_field(text, 'Y_COORDINATE', 1, ord)
        self._set_field(text, '', 7, _raw)

        self.text.append(text)


    def _parse_footer(self):
        """
        Extract information from the footer.
        """
        self._set_field(self.footer, '', 5, _raw)

        for description in range(23):
            self._set_field(self.footer, 'DESC_{0:02d}'.format(description), 0,
                _identity)

        self._set_field(self.footer, '', 44, _raw)
        self._set_field(self.footer, 'NUMBER_OF_TEXT_FIELDS', 1, ord)
        self._set_field(self.footer, '', 1, _raw)


    def _write_dictionary(self, dictionary, output_handle):
        """
        Write the content of a dictionary to a stream.

        :arg dict dictionary: Dictionary to write.
        :arg stream output_handle: Open writable handle.
        """
        for key, value in sorted(dictionary.items()):
            if self.debug or not key.startswith('_RAW_'):
                output_handle.write("{}: {}\n".format(key, value))


    def read(self, input_handle):
        """
        Read the FAM file and parse it.

        :arg stream input_handle: Open readable handle to a FAM file.
        """
        self.data = input_handle.read()

        self._parse_family()
        for member in range(self.family_attributes['SIZE']):
            self._parse_member()

        self._parse_footer()
        for text in range(self.footer['NUMBER_OF_TEXT_FIELDS']):
            self._parse_text()


    def write(self, output_handle):
        """
        Write the parsed FAM file to a stream.

        :arg stream output_handle: Open writable handle.
        """
        output_handle.write('--- FAMILY ---\n\n')
        self._write_dictionary(self.family_attributes, output_handle)

        for member in self.members:
            output_handle.write('\n\n--- MEMBER ---\n\n')
            self._write_dictionary(member, output_handle)

        output_handle.write('\n\n--- FOOTER ---\n\n')
        self._write_dictionary(self.footer, output_handle)

        for text in self.text:
            output_handle.write('\n\n--- TEXT ---\n\n')
            self._write_dictionary(text, output_handle)


def fam_parser(input_handle, output_handle, debug=False):
    """
    Main entry point.

    :arg stream input_handle: Open readable handle to a FAM file.
    :arg stream output_handle: Open writable handle.
    """
    parser = FamParser(debug)
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
    parser.add_argument('-d', dest='debug', action='store_true',
        help='enable debugging')

    args = parser.parse_args()
    fam_parser(args.input_handle, args.output_handle, args.debug)


if __name__ == '__main__':
    main()
