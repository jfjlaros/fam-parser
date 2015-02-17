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


    def _set_field(self, destination, size, name='', function=_identity,
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
        elif self.debug:
            destination['_RAW_{}'.format(
                destination['_RAW_FIELDS'])] = _raw(field)
            destination['_RAW_FIELDS'] += 1


    def _parse_family(self):
        """
        Extract family information.
        """
        # TODO: Move SOURCE field.
        self._set_field(self.family_attributes, 26, 'SOURCE', _trim)
        self._set_field(self.family_attributes, 0, 'FAMILY_NAME')
        self._set_field(self.family_attributes, 0, 'FAMILY_ID')
        self._set_field(self.family_attributes, 0, 'AUTHOR')
        self._set_field(self.family_attributes, 1, 'SIZE', ord)
        self._set_field(self.family_attributes, 45)
        self._set_field(self.family_attributes, 0, 'COMMENT')
        self._set_field(self.family_attributes, 3, 'DATE_CREATED', _date)
        self._set_field(self.family_attributes, 1)
        self._set_field(self.family_attributes, 3, 'DATE_UPDATED', _date)
        self._set_field(self.family_attributes, 32)


    def _parse_member(self):
        """
        Extract person information.
        """
        # TODO: There seems to be support for more annotation (+/-).
        member = collections.defaultdict(int)
        self._set_field(member, 0, 'SURNAME')
        self._set_field(member, 1)
        self._set_field(member, 0, 'FORENAMES')
        self._set_field(member, 1)
        self._set_field(member, 0, 'MAIDEN_NAME')
        self._set_field(member, 11)
        self._set_field(member, 0, 'COMMENT', _comment)
        self._set_field(member, 3, 'DATE_OF_BIRTH', _date)
        self._set_field(member, 1)
        self._set_field(member, 3, 'DATE_OF_DEATH', _date)
        self._set_field(member, 1)
        self._set_field(member, 1, 'SEX', _sex)
        self._set_field(member, 1, 'ID', ord)
        self._set_field(member, 3)
        self._set_field(member, 1, 'MOTHER_ID', ord)
        self._set_field(member, 1)
        self._set_field(member, 1, 'FATHER_ID', ord)
        self._set_field(member, 1)
        self._set_field(member, 1, 'INTERNAL_ID', ord)
        self._set_field(member, 1)
        self._set_field(member, 1, 'NUMBER_OF_INDIVIDUALS', ord)
        self._set_field(member, 1)
        self._set_field(member, 0, 'AGE_GESTATION')
        self._set_field(member, 0, 'INDIVIDUAL_ID')
        self._set_field(member, 1, 'NUMBER_OF_SPOUSES', ord)
        self._set_field(member, 1)

        for spouse in range(member['NUMBER_OF_SPOUSES']):
            self._set_field(member, 1, 'SPOUSE_{}_ID'.format(spouse), ord)
            self._set_field(member, 3)

        self._set_field(member, 4)
        self._set_field(member, 1, 'FLAGS_1', _bit)
        self._set_field(member, 2)
        self._set_field(member, 1, 'PROBAND', _proband)
        self._set_field(member, 1, 'X_COORDINATE', ord)
        self._set_field(member, 1)
        self._set_field(member, 1, 'Y_COORDINATE', ord)
        self._set_field(member, 1)
        self._set_field(member, 1, 'FLAGS_2', _bit)
        self._set_field(member, 26)
        self._set_field(member, 1, 'FLAGS_3', _bit)
        self._set_field(member, 205)

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
        self._set_field(text, 0, 'TEXT', _text)
        self._set_field(text, 54)
        self._set_field(text, 1, 'X_COORDINATE', ord)
        self._set_field(text, 3)
        self._set_field(text, 1, 'Y_COORDINATE', ord)
        self._set_field(text, 7)

        self.text.append(text)


    def _parse_footer(self):
        """
        Extract information from the footer.
        """
        self._set_field(self.footer, 5)

        for description in range(23):
            self._set_field(self.footer, 0, 'DESC_{0:02d}'.format(description),
                _identity)

        self._set_field(self.footer, 44)
        self._set_field(self.footer, 1, 'NUMBER_OF_TEXT_FIELDS', ord)
        self._set_field(self.footer, 1)


    def _write_dictionary(self, dictionary, output_handle):
        """
        Write the content of a dictionary to a stream.

        :arg dict dictionary: Dictionary to write.
        :arg stream output_handle: Open writable handle.
        """
        for key, value in sorted(dictionary.items()):
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
