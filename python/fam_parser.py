"""
FAM parser.


(C) 2015 Jeroen F.J. Laros <J.F.J.Laros@lumc.nl>
"""
# NOTE: All integers are probably 2 bytes.

import argparse
import sys

from . import container


DESC_PREFIX = 'DESC_'
EOF_MARKER = 'End of File'

MAPS = {
    'PROBAND': {
        0x00: 'NOT_A_PROBAND',
        0x01: 'ABOVE_LEFT',
        0x02: 'ABOVE_RIGHT',
        0x03: 'BELOW_LEFT',
        0x04: 'BELOW_RIGHT',
        0x05: 'LEFT',
        0x06: 'RIGHT'
    },
    'SEX': {
        0x00: 'MALE',
        0x01: 'FEMALE',
        0x02: 'UNKNOWN'
    },
    'MULTIPLE_PREGNANCIES': {
        0x00: 'SINGLETON',
        0x01: 'MONOZYGOTIC_TWINS',
        0x02: 'DIZYGOTIC_TWINS',
        0x03: 'TWIN_TYPE_UNKNOWN',
        0x04: 'TRIPLET',
        0x05: 'QUADRUPLET',
        0x06: 'QUINTUPLET',
        0x07: 'SEXTUPLET'
    },
    'ADOPTION_TYPE': {
        0x00: 'ADOPTED_INTO_FAMILY',
        0x01: 'NOT_ADOPTED',
        0x02: 'POSSIBLY_ADOPTED_INTO_FAMILY',
        0x03: 'ADOPTED_OUT_OF_FAMILY'
    },
    'ANNOTATION_1': {
        0x00: 'NONE',
        0x01: 'P',
        0x02: 'SAB',
        0x03: 'TOP',
        0x04: 'SB',
        0x0b: 'BAR'
    },
    'ANNOTATION_2': {
        0x00: 'NONE',
        0x01: 'AFFECTED'
    }
}

FLAGS = {
    'INDIVIDUAL': {
        0x01: 'BLOOD',
        0x02: 'DNA',
        0x04: 'LOOP_BREAKPOINT',
        0x08: 'HIDE_INFO',
        0x10: 'COMMITTED_SUICIDE',
        0x20: 'CELLS'
    },
    'RELATIONSHIP': {
        0x01: 'INFORMAL',
        0x02: 'CONSANGUINEOUS',
        0x04: 'SEPARATED',
        0x08: 'DIVORCED'
    },
    'SAMPLE': {
        0x01: 'SAMPLE_REQUIRED'
    }
}


def _identity(data):
    return data


def _trim(data, delimiter=chr(0x00)):
    return data.split(delimiter)[0]


def _raw(data):
    """
    Return the input data in hexadecimal, grouped by bit.

    :arg str data: Input data.

    :returns str: Hexadecimal representation of {data}.
    """
    raw_data = data.encode('hex')

    return ' '.join([raw_data[x:x + 2] for x in range(0, len(raw_data), 2)])


def _bit(data):
    return '{:08b}'.format(ord(data))


def _comment(data):
    return '\n'.join(data.split(chr(0x09) + chr(0x03)))


def _text(data):
    return '\n'.join(data.split(chr(0x0b) + chr(0x0b)))


def _description(data):
    return '{}{:02d}'.format(DESC_PREFIX, ord(data))


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

    :return str: Date in format '%Y%j', 'DEFINED' or 'UNKNOWN'.
    """
    date_int = _int(data)
    if date_int:
        if date_int == 0xFFFFFFFF:
            return 'DEFINED'
        return unicode(date_int)
    return 'UNKNOWN'


def _annotate(data, annotation):
    """
    Replace a value with its annotation.

    :arg str data: Encoded data.
    :arg dict annotation: Annotation of {data}.

    :return str: Annotated representation of {data}.
    """
    index = ord(data)

    if index in MAPS[annotation]:
        return MAPS[annotation][index]
    return '{:02x}'.format(index)


def _flags(destination, bitfield, annotation):
    """
    Explode a bitfield into flags.

    :arg dict destination: Destination dictionary.
    :arg int bitfield: Bit field.
    :arg str annotation: Annotation of {bitfield}.
    """
    for flag in map(lambda x: 2 ** x, range(8)):
        value = bool(flag & bitfield)

        if flag not in FLAGS[annotation]:
            if value:
                destination['FLAGS_{}_{:02x}'.format(annotation, flag)] = value
        else:
            destination[FLAGS[annotation][flag]] = value


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
        self.data = ''
        self.offset = 0
        self.metadata = container.Container()
        self.members = []
        self.relationships = container.Container()
        self.text = []
        self.crossovers = []
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
        :arg unknown parameter: Optional parameter for {function}.
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
            if function == _annotate:
                destination[name] = _annotate(field, name)
            else:
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
        self._set_field(self.metadata, 2, 'LAST_ID', _int)
        self._set_field(self.metadata, 2, 'LAST_INTERNAL_ID', _int)

        for i in range(7):
            self._set_field(self.metadata, 0,
                'FAMILY_DISEASE_LOCUS_{:02d}'.format(i))
            self._set_field(self.metadata, 3,
                'FAMILY_DISEASE_LOCUS_COLOUR_{:02d}'.format(i), _raw)
            self._set_field(self.metadata, 2)

        self._set_field(self.metadata, 0, 'COMMENT')
        self._set_field(self.metadata, 4, 'DATE_CREATED', _date)
        self._set_field(self.metadata, 4, 'DATE_UPDATED', _date)

        self._set_field(self.metadata, 5)
        for i in range(7):
            self._set_field(self.metadata, 0,
                'QUANTITATIVE_VALUE_LOCUS_NAME_{:02d}'.format(i))

        self._set_field(self.metadata, 2, 'SELECTED_ID', _int)
        self._set_field(self.metadata, 17)


    def _parse_relationship(self, person_id):
        """
        Extract relationship information.

        :arg int person_id: The partner in this relationship.
        """
        relationship = container.Container()

        relationship['MEMBER_1_ID'] = person_id
        self._set_field(relationship, 2, 'MEMBER_2_ID', _int)

        self._set_field(relationship, 1, 'RELATION_FLAGS', _int)
        _flags(relationship, relationship['RELATION_FLAGS'], 'RELATIONSHIP')

        self._set_field(relationship, 0, 'RELATION_NAME')

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
        self._set_field(member, 0, 'OTHER_SURNAMES')
        self._set_field(member, 0, 'FORENAMES')
        self._set_field(member, 0, 'KNOWN_AS')
        self._set_field(member, 0, 'MAIDEN_NAME')
        self._set_field(member, 0, 'ETHNICITY_SELF')
        self._set_field(member, 0, 'ETHNICITY_M_G_MOTHER')
        self._set_field(member, 0, 'ETHNICITY_M_G_FATHER')
        self._set_field(member, 0, 'ETHNICITY_P_G_MOTHER')
        self._set_field(member, 0, 'ETHNICITY_P_G_FATHER')
        self._set_field(member, 0, 'ORIGINS_SELF')
        self._set_field(member, 0, 'ORIGINS_M_G_MOTHER')
        self._set_field(member, 0, 'ORIGINS_M_G_FATHER')
        self._set_field(member, 0, 'ORIGINS_P_G_MOTHER')
        self._set_field(member, 0, 'ORIGINS_P_G_FATHER')
        self._set_field(member, 0, 'ADDRESS')
        self._set_field(member, 0, 'ADDITIONAL_INFORMATION', _comment)
        self._set_field(member, 4, 'DATE_OF_BIRTH', _date)
        self._set_field(member, 4, 'DATE_OF_DEATH', _date)
        self._set_field(member, 1, 'SEX', _annotate)
        self._set_field(member, 2, 'ID', _int)
        self._set_field(member, 2, 'PEDIGREE_NUMBER', _int)
        self._set_field(member, 2, 'MOTHER_ID', _int)
        self._set_field(member, 2, 'FATHER_ID', _int)
        self._set_field(member, 2, 'INTERNAL_ID', _int)
        self._set_field(member, 1, 'NUMBER_OF_INDIVIDUALS', _int)
        self._set_field(member, 1)
        self._set_field(member, 0, 'AGE_GESTATION')
        self._set_field(member, 0, 'INDIVIDUAL_ID')
        self._set_field(member, 1, 'NUMBER_OF_SPOUSES', _int)
        self._set_field(member, 1)

        for spouse in range(member['NUMBER_OF_SPOUSES']):
            self._parse_relationship(member['ID'])

        self._set_field(member, 2, 'TWIN_ID', _int)
        self._set_field(member, 0, 'COMMENT')
        self._set_field(member, 1, 'ADOPTION_TYPE', _annotate)
        self._set_field(member, 1, 'DESCRIPTION_1', _description)
        self._set_field(member, 1)

        self._set_field(member, 1, 'INDIVIDUAL_FLAGS', _int)
        _flags(member, member['INDIVIDUAL_FLAGS'], 'INDIVIDUAL')

        self._set_field(member, 1, 'PROBAND', _annotate)
        self._set_field(member, 1, 'X_COORDINATE', _int)
        self._set_field(member, 1)
        self._set_field(member, 1, 'Y_COORDINATE', _int)
        self._set_field(member, 1)
        self._set_field(member, 1, 'ANNOTATION_1', _annotate)
        self._set_field(member, 1, 'MULTIPLE_PREGNANCIES', _annotate)
        self._set_field(member, 3)

        self._parse_crossover(member['ID'])

        self._set_field(member, 1, 'ANNOTATION_2', _annotate)

        self._set_field(member, 12)
        for i in range(7):
            self._set_field(member, 24)

        self._set_field(member, 1, 'DESCRIPTION_2', _description)

        # NOTE: DNA and BLOOD fields are switched in Cyrillic. i.e., if DNA is
        # selected, the BLOOD_LOCATION field is stored and if BLOOD is
        # selected, the DNA_LOCATION field is stored. This is probably a bug.
        if member['DNA']:
            self._set_field(member, 0, 'DNA_LOCATION')
        if member['BLOOD']:
            self._set_field(member, 0, 'BLOOD_LOCATION')
        if member['CELLS']:
            self._set_field(member, 0, 'CELLS_LOCATION')

        self._set_field(member, 1, 'SAMPLE_FLAGS', _int)
        _flags(member, member['SAMPLE_FLAGS'], 'SAMPLE')

        self._set_field(member, 0, 'SAMPLE_NUMBER')
        self._set_field(member, 22)


        self.members.append(member)

        return member['ID']


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
        self._set_field(self.metadata, 1, 'NUMBER_OF_UNKNOWN_DATA', _int)
        self._set_field(self.metadata, 2)

        for number in range(self.metadata['NUMBER_OF_UNKNOWN_DATA']):
            self._set_field(self.metadata, 12,
                '{}{:02d}'.format('UNKNOWN_DATA_', number), _raw)

        self._set_field(self.metadata, 1, 'NUMBER_OF_CUSTOM_DESC', _int)
        self._set_field(self.metadata, 1)

        for description in range(23):
            self._set_field(self.metadata, 0,
                '{}{:02d}'.format(DESC_PREFIX, description))

        for description in range(self.metadata['NUMBER_OF_CUSTOM_DESC']):
            self._set_field(self.metadata, 0,
                'CUSTOM_DESC_{:02d}'.format(description))
            self._set_field(self.metadata, 0,
                'CUSTOM_CHAR_{:02d}'.format(description))

        self._set_field(self.metadata, 14)
        self._set_field(self.metadata, 2, 'ZOOM', _int)
        self._set_field(self.metadata, 4, 'UNKNOWN_1', _raw) # Zoom.
        self._set_field(self.metadata, 4, 'UNKNOWN_2', _raw) # Zoom.
        self._set_field(self.metadata, 20)
        self._set_field(self.metadata, 1, 'NUMBER_OF_TEXT_FIELDS', _int)
        self._set_field(self.metadata, 1)

        for text in range(self.metadata['NUMBER_OF_TEXT_FIELDS']):
            self._parse_text()

        self._set_field(self.metadata, 11, 'EOF_MARKER')
        self._set_field(self.metadata, 15)


    def _write_dictionary(self, dictionary, output_handle):
        """
        Write the content of a dictionary to a stream.

        :arg dict dictionary: Dictionary to write.
        :arg stream output_handle: Open writable handle.
        """
        for key, value in dictionary.items():
            output_handle.write('{}: {}\n'.format(key, value))


    def read(self, input_handle):
        """
        Read the FAM file and parse it.

        :arg stream input_handle: Open readable handle to a FAM file.
        """
        self.data = input_handle.read()

        self._parse_header()

        current_id = 0
        while current_id != self.metadata['LAST_ID']:
            current_id = self._parse_member()

        self._parse_footer()

        if self.metadata['EOF_MARKER'] != EOF_MARKER:
            raise Exception('No EOF marker found.')


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
            output_handle.write('Reached byte {} out of {}.\n'.format(
                self.offset, len(self.data)))


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
