"""
FAM parser.


(C) 2015 Jeroen F.J. Laros <J.F.J.Laros@lumc.nl>
"""
# NOTE: All IDs are probably 2 bytes.

import argparse
import sys
import time

from . import container


PROBAND = ['NOT_A_PROBAND', 'ABOVE_LEFT', 'ABOVE_RIGHT', 'BELOW_LEFT',
    'BELOW_RIGHT', 'LEFT', 'RIGHT']
SEX = ['MALE', 'FEMALE', 'UNKNOWN']
ANNOTATION_1 = {
    0b00000000: 'NONE',
    0b00000001: 'P',
    0b00000010: 'UNBORN',
    0b00000011: 'ABORTED',
    0b00000100: 'SB',
    0b00001011: 'BAR'
}
ANNOTATION_2 = {
    0b00000000: 'NONE',
    0b00000001: 'FILL',
}
RELATIONSHIP = {
    0b00000100: 'SEPARATED',
    0b00001000: 'DIVORCED'
}


def _identity(data):
    return data


def _trim(data, delimiter=chr(0x00)):
    return data.split(delimiter)[0]


def _proband(data):
    return PROBAND[ord(data)]


def _sex(data):
    return SEX[ord(data)]


def _relation(data):
    for relation in RELATIONSHIP:
        if data & relation:
            return RELATIONSHIP[data]
    return 'NORMAL'


def _raw(data):
    return data.encode('hex')


def _bit(data):
    return '{:08b}'.format(ord(data))


def _comment(data):
    return data.split(chr(0x09) + chr(0x03))


def _text(data):
    return data.split(chr(0x0b) + chr(0x0b))


def _int(data):
    """
    Decode a little-endian encoded integer.

    Decoding is done as follows:
    - Reverse the order of the bits.
    - Convert the bits to ordinals.
    - Interpret the list of ordinals as digits in base 256.

    :arg str data: Little-endian encoded integer.

    :return int: Integer representation of {data}
    """
    return reduce(lambda x, y: x * 0x100 + y,
        map(lambda x: ord(x), data[::-1]))


def _date(data):
    """
    Decode a date.

    The date is encoded as an integer, representing the year followed by
    the (zero padded) day of the year.

    :arg str data: Binary encoded date.

    :return str: Date in format '%d-%m-%Y', 'DEFINED' or 'UNKNOWN'.
    """
    date_int = _int(data)
    if date_int:
        if date_int == 0xFFFFFF:
            return 'DEFINED'

        # This is needed because strftime does not accept years before 1900.
        date = time.strptime('{:07d}'.format(date_int), '%Y%j')
        return '{}-{}-{}'.format(date.tm_mday, date.tm_mon, date.tm_year)

    return 'UNKNOWN'


def _block_write(string, block_size, stream=sys.stdout):
    """
    Write a string as a block of width {block_size}. This function is mainly
    for debugging purposes.

    :arg str string: String to be written as a block.
    :arg int block_size: Width of the block.
    :arg stream stream: Open writable handle.
    """
    for block in map(lambda x: string[x:x + block_size],
            range(0, len(string), block_size)):
        stream.write('% {}\n'.format(block))


class FamParser(object):
    """
    FAM file parsing.
    """
    def __init__(self, experimental=False, debug=False):
        """
        Constructor.

        :arg bool experimental: Enable experimental features.
        :arg bool debug: Enable debugging output.
        """
        self.data = ""
        self.offset = 0
        self.metadata = container.Container()
        self.members = []
        self.relationships = container.Container()
        self.text = []
        self.crossovers = []
        self.desc_prefix = "DESC_"
        self.debug = debug
        self.experimental = experimental
        self.extracted = 0


    def _set_field(self, destination, size, name='', function=_identity,
            delimiter=chr(0x0d)):
        """
        Extract a field from {self.data} using either a fixed size, or a
        delimiter. After reading, {self.offset} is set to the next field.

        :arg dict destination: Destination dictionary.
        :arg int size: Size of fixed size field.
        :arg str name: Field name.
        :arg function function: Conversion function.
        :arg str delimiter: Delimeter for variable size field.
        """
        # TODO: Perhaps use the file handle instead of self.data.
        if size:
            field = self.data[self.offset:self.offset + size]
            extracted = size
        else:
            field = self.data[self.offset:].split(delimiter)[0]
            extracted = len(field) + 1

        if name:
            destination[name] = function(field)
            self.extracted += extracted
        elif self.debug:
            destination['_RAW_{:02d}'.format(
                destination['_RAW_FIELDS'])] = _raw(field)
            destination['_RAW_FIELDS'] += 1

        self.offset += extracted


    def _parse_header(self):
        """
        Extract header information.
        """
        self._set_field(self.metadata, 26, 'SOURCE', _trim)
        self._set_field(self.metadata, 0, 'FAMILY_NAME')
        self._set_field(self.metadata, 0, 'FAMILY_ID')
        self._set_field(self.metadata, 0, 'AUTHOR')
        self._set_field(self.metadata, 1, 'SIZE', _int)
        self._set_field(self.metadata, 45)
        self._set_field(self.metadata, 0, 'COMMENT')
        self._set_field(self.metadata, 3, 'DATE_CREATED', _date)
        self._set_field(self.metadata, 1)
        self._set_field(self.metadata, 3, 'DATE_UPDATED', _date)
        self._set_field(self.metadata, 14)
        self._set_field(self.metadata, 1, 'SELECTED_ID', _int)
        self._set_field(self.metadata, 17)


    def _parse_relationship(self, person_id):
        """
        Extract relationship information.

        :arg int person_id: The partner in this relationship.
        """
        relationship = container.Container()

        relationship['MEMBER_1_ID'] = person_id
        self._set_field(relationship, 1, 'MEMBER_2_ID', _int)
        self._set_field(relationship, 1)
        self._set_field(relationship, 1, 'RELATION_FLAGS', _int)
        self._set_field(relationship, 0, 'RELATION_NAME')

        relation_flags = relationship['RELATION_FLAGS']
        relationship['RELATION_STATUS'] = _relation(relation_flags)
        relationship['RELATION_IS_INFORMAL'] = str(bool(relation_flags &
            0b00000001))
        relationship['RELATION_IS_CONSANGUINEOUS'] = str(bool(relation_flags &
            0b00000010))

        key = tuple(sorted((person_id, relationship['MEMBER_2_ID'])))
        if not self.relationships[key]:
            self.relationships[key] = relationship


    def _parse_crossover(self, person_id):
        """
        Extract crossover information.

        :arg int person_id: The person who has these crossovers.
        """
        crossover = container.Container()
        alleles = 0
        events = 0

        crossover['ID'] = person_id
        while alleles < 2:
            flag = 'FLAG_{:02d}'.format(events)

            self._set_field(crossover, 1, flag, _raw)
            if crossover[flag] == '22':
                self._set_field(crossover, 9,
                    'ALLELE_{:02d}'.format(alleles), _raw)
                if not alleles:
                    self._set_field(crossover, 2,
                        'SPACER_{:02d}'.format(alleles), _raw)
                alleles += 1
            else:
                self._set_field(crossover, 11,
                    'CROSSOVER_{:02d}'.format(events), _raw)
            events += 1

        self.crossovers.append(crossover)


    def _parse_member(self):
        """
        Extract person information.
        """
        member = container.Container()

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
        self._set_field(member, 1, 'ID', _int)
        self._set_field(member, 1)
        self._set_field(member, 1, 'UNKNOWN_1', _int)
        self._set_field(member, 1)
        self._set_field(member, 1, 'MOTHER_ID', _int)
        self._set_field(member, 1)
        self._set_field(member, 1, 'FATHER_ID', _int)
        self._set_field(member, 1)
        self._set_field(member, 1, 'INTERNAL_ID', _int)
        self._set_field(member, 1)
        self._set_field(member, 1, 'NUMBER_OF_INDIVIDUALS', _int)
        self._set_field(member, 1)
        self._set_field(member, 0, 'AGE_GESTATION')
        self._set_field(member, 0, 'INDIVIDUAL_ID')
        self._set_field(member, 1, 'NUMBER_OF_SPOUSES', _int)
        self._set_field(member, 1)

        for spouse in range(member['NUMBER_OF_SPOUSES']):
            self._parse_relationship(member['ID'])

        self._set_field(member, 4)
        self._set_field(member, 1, 'FLAGS_1', _int)
        self._set_field(member, 2)
        self._set_field(member, 1, 'PROBAND', _proband)
        self._set_field(member, 1, 'X_COORDINATE', _int)
        self._set_field(member, 1)
        self._set_field(member, 1, 'Y_COORDINATE', _int)
        self._set_field(member, 1)
        self._set_field(member, 1, 'FLAGS_2', _int)
        self._set_field(member, 4)

        self._parse_crossover(member['ID'])

        self._set_field(member, 1, 'FLAGS_3', _int)
        self._set_field(member, 180)
        self._set_field(member, 1, 'FLAGS_4', _int)
        self._set_field(member, 24)

        member['ANNOTATION_1'] = ANNOTATION_1[(member['FLAGS_2'])]
        member['ANNOTATION_2'] = ANNOTATION_2[(member['FLAGS_3'])]
        member['DESCRIPTION_1'] = '{}{:02d}'.format(self.desc_prefix,
            member['FLAGS_1'])
        member['DESCRIPTION_2'] = '{}{:02d}'.format(self.desc_prefix,
            member['FLAGS_4'])

        self.members.append(member)


    def _parse_text(self):
        """
        Extract information from a text field.
        """
        # TODO: X and Y coordinates have more digits.
        text = container.Container()

        self._set_field(text, 0, 'TEXT', _text)
        self._set_field(text, 54)
        self._set_field(text, 1, 'X_COORDINATE', _int)
        self._set_field(text, 3)
        self._set_field(text, 1, 'Y_COORDINATE', _int)
        self._set_field(text, 7)

        self.text.append(text)


    def _parse_footer(self):
        """
        Extract information from the footer.
        """
        self._set_field(self.metadata, 3)
        self._set_field(self.metadata, 1, 'NUMBER_OF_CUSTOM_DESC', _int)
        self._set_field(self.metadata, 1)

        for description in range(23):
            self._set_field(self.metadata, 0,
                '{}{:02d}'.format(self.desc_prefix, description), _identity)

        for description in range(self.metadata['NUMBER_OF_CUSTOM_DESC']):
            self._set_field(self.metadata, 0,
                'CUSTOM_DESC_{:02d}'.format(description), _identity)
            self._set_field(self.metadata, 0,
                'CUSTOM_CHAR_{:02d}'.format(description), _identity)

        self._set_field(self.metadata, 14)
        self._set_field(self.metadata, 2, 'ZOOM', _int)
        self._set_field(self.metadata, 4, 'UNKNOWN_1', _raw) # Zoom.
        self._set_field(self.metadata, 4, 'UNKNOWN_2', _raw) # Zoom.
        self._set_field(self.metadata, 20)
        self._set_field(self.metadata, 1, 'NUMBER_OF_TEXT_FIELDS', _int)
        self._set_field(self.metadata, 1)


    def _write_dictionary(self, dictionary, output_handle):
        """
        Write the content of a dictionary to a stream.

        :arg dict dictionary: Dictionary to write.
        :arg stream output_handle: Open writable handle.
        """
        for key, value in dictionary.items():
            output_handle.write("{}: {}\n".format(key, value))


    def read(self, input_handle):
        """
        Read the FAM file and parse it.

        :arg stream input_handle: Open readable handle to a FAM file.
        """
        self.data = input_handle.read()

        self._parse_header()
        for member in range(self.metadata['SIZE']):
            self._parse_member()

        self._parse_footer()
        for text in range(self.metadata['NUMBER_OF_TEXT_FIELDS']):
            self._parse_text()


    def write(self, output_handle):
        """
        Write the parsed FAM file to a stream.

        :arg stream output_handle: Open writable handle.
        """
        output_handle.write('--- METADATA ---\n\n')
        self._write_dictionary(self.metadata, output_handle)

        for member in self.members:
            output_handle.write('\n\n--- MEMBER ---\n\n')
            self._write_dictionary(member, output_handle)

        for relationship in self.relationships.values():
            output_handle.write('\n\n--- RELATIONSHIP ---\n\n')
            self._write_dictionary(relationship, output_handle)

        if self.experimental:
            for crossover in self.crossovers:
                output_handle.write('\n\n--- CROSSOVER ---\n\n')
                self._write_dictionary(crossover, output_handle)

        for text in self.text:
            output_handle.write('\n\n--- TEXT ---\n\n')
            self._write_dictionary(text, output_handle)

        if self.debug:
            output_handle.write('\n\n--- DEBUG INFO ---\n\n')
            output_handle.write(
                'Extracted {}/{} bits ({}%).\n'.format(
                self.extracted, len(self.data),
                self.extracted * 100 // len(self.data)))


def fam_parser(input_handle, output_handle, experimental=False, debug=False):
    """
    Main entry point.

    :arg stream input_handle: Open readable handle to a FAM file.
    :arg stream output_handle: Open writable handle.
    :arg bool experimental: Enable experimental features.
    :arg bool debug: Enable debugging output.
    """
    parser = FamParser(experimental, debug)
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
    parser.add_argument('-e', dest='experimental', action='store_true',
        help='enable experimental features')
    parser.add_argument('-d', dest='debug', action='store_true',
        help='enable debugging')

    try:
        arguments = parser.parse_args()
    except IOError as error:
        parser.error(error)

    try:
        fam_parser(**dict((k, v) for k, v in vars(arguments).items()
            if k not in ('func', 'subcommand')))
    except ValueError as error:
        parser.error(error)


if __name__ == '__main__':
    main()
