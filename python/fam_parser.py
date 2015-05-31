"""
FAM parser.


(C) 2015 Jeroen F.J. Laros <J.F.J.Laros@lumc.nl>
"""
# NOTE: All integers are probably 2 bytes.

import argparse
import json
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
    },
    'PATTERN': {
        0x00: 'HORIZONTAL',
        0x01: 'VERTICAL',
        0x02: 'SLANTED_BACK',
        0x03: 'SLANTED_FORWARD',
        0x04: 'GRID',
        0x05: 'DIAGONAL_GRID',
        0xff: 'FILL'
    },
    'GENETIC_SYMBOL': {
        0x00: 'CLEAR',
        0x01: 'UNAFFECTED',
        0x02: 'AFFECTED',
        0x03: 'CARRIER',
        0x04: 'POSSIBLY_AFFECTED',
        0x05: 'Q1',
        0x06: 'Q2',
        0x07: 'Q3',
        0x08: 'Q4',
        0x09: 'HETEROZYGOUS',
        0x0a: 'Q1_Q3',
        0x0b: 'Q1_Q4',
        0x0c: 'Q2_Q3',
        0x0d: 'Q2_Q4',
        0x0e: 'Q3_Q4',
        0x0f: 'Q1_Q2_Q3',
        0x10: 'Q1_Q2_Q4',
        0x11: 'Q1_Q3_Q4',
        0x12: 'Q2_Q3_Q4'
    },
    'ADDITIONAL_SYMBOL': {
        0X00: 'CROSS',
        0X01: 'PLUS',
        0X02: 'MINUS',
        0X03: 'O'
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


def _info(data):
    return '\n'.join(data.split(chr(0xe9) + chr(0xe9)))


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


def _colour(data):
    return '0x{:06x}'.format(_int(data))


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
        return str(date_int)
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
    def __init__(self, experimental=False, debug=False, log=sys.stdout):
        """
        Constructor.

        :arg bool experimental: Enable experimental features.
        :arg bool debug: Enable debugging output.
        :arg stream log: Debug stream to write to.
        """
        self.data = ''
        self.offset = 0

        # FOLLOWING BLOCK CAN GO
        self.metadata = container.Container()
        self.genetic_symbols = []
        self.additional_symbols = []
        self.family_disease_locus = []
        self.quantitative_value_locus = []
        self.markers = []
        self.unknown_data = []
        self.members = []
        self.relationships = container.Container()
        self.text = []
        self.crossovers = []

        self.debug = debug
        self.experimental = experimental
        self.last_id = 0
        self.log = log

        self.eof_marker = ''
        self.parsed = {
            'METADATA': {
                'GENETIC_SYMBOLS': [],
                'ADDITIONAL_SYMBOLS': []
            },
            'FAMILY': {
                'MEMBERS': [],
                'DISEASE_LOCI': [],
                'QUANTITATIVE_VALUE_LOCI': [],
                'RELATIONSHIPS': {}
            },
            'TEXT_FIELDS': [],
            'UNKNOWN_FIELDS': []
        }


    def _get_field(self, size=0, delimiter=chr(0x0d)):
        """
        Extract a field from {self.data} using either a fixed size, or a
        delimiter. After reading, {self.offset} is set to the next field.

        :arg int size: Size of fixed size field.
        :arg str delimiter: Delimeter for variable size field.
        """
        if size:
            field = self.data[self.offset:self.offset + size]
            extracted = size
        else:
            field = self.data[self.offset:].split(delimiter)[0]
            extracted = len(field) + 1

        if self.debug:
            self.log.write('0x{:06x}: '.format(self.offset))
            if size:
                self.log.write('{} ({})\n'.format(_raw(field), size))
            else:
                self.log.write('{}\n'.format(field))

        self.offset += extracted
        return field


    def _parse_markers(self):
        """
        """
        marker = container.Container()
        markers = 0

        while True:
            flag = 'FLAG_{:02d}'.format(markers)

            marker[flag] = _raw(self._get_field(1))
            if marker[flag] == '01':
                break

            marker['MARKER_{:02d}'.format(markers)] = self._get_field(439)
            self.markers.append(marker)
            markers += 1


    def _parse_header(self):
        """
        Extract header information.
        """
        self.parsed['METADATA']['SOURCE'] = _trim(self._get_field(26))
        self.parsed['FAMILY']['NAME'] = self._get_field()
        self.parsed['FAMILY']['ID_NUMBER'] = self._get_field()
        self.parsed['METADATA']['FAMILY_DRAWN_BY'] = self._get_field()
        self.last_id = _int(self._get_field(2))
        self._get_field(2) # LAST_INTERNAL_ID

        for i in range(7):
            locus = {}
            locus['NAME'] = self._get_field()
            locus['COLOUR'] = _colour(self._get_field(3))
            self._get_field(1)
            locus['PATTERN'] = _annotate(self._get_field(1), 'PATTERN')
            self.parsed['FAMILY']['DISEASE_LOCI'].append(locus)

        self.parsed['FAMILY']['COMMENTS'] = self._get_field()
        self.parsed['METADATA']['CREATION_DATE'] = _date(self._get_field(4))
        self.parsed['METADATA']['LAST_UPDATED'] = _date(self._get_field(4))

        self._get_field(5)
        for i in range(7):
            self.parsed['FAMILY']['QUANTITATIVE_VALUE_LOCI'].append(
                {'NAME': self._get_field()})

        self.parsed['METADATA']['SELECTED_ID'] = _int(self._get_field(2))

        self._get_field(7)
        self._parse_markers()
        self._get_field(9)


    def _parse_relationship(self, person_id):
        """
        Extract relationship information.

        :arg int person_id: The partner in this relationship.
        """
        relationship = {}

        relationship['MEMBER_1_ID'] = person_id
        relationship['MEMBER_2_ID'] = _int(self._get_field(2))

        _flags(relationship, _int(self._get_field(1)), 'RELATIONSHIP')

        relationship['RELATION_NAME'] = self._get_field()

        key = str(tuple(sorted((person_id, relationship['MEMBER_2_ID']))))
        self.parsed['FAMILY']['RELATIONSHIPS'][key] = relationship


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

            crossover[flag] = _raw(self._get_field(1))
            if crossover[flag] == '22':
                crossover['ALLELE_{:02d}'.format(alleles)] = _raw(
                    self._get_field(9))
                if not alleles:
                    crossover['SPACER_{:02d}'.format(alleles)] = _raw(
                        self._get_field(2))
                alleles += 1
            else:
                crossover['CROSSOVER_{:02d}'.format(events)] = _raw(
                    self._get_field(11))
            events += 1

        self.crossovers.append(crossover)


    def _parse_member(self):
        """
        Extract person information.
        """
        member = {
            'CROSSOVER': [],
            'ETHNICITY': {},
            'ORIGINS': {}
        }

        member['SURNAME'] = self._get_field()
        member['OTHER_SURNAMES'] = self._get_field()
        member['FORENAMES'] = self._get_field()
        member['KNOWN_AS'] = self._get_field()
        member['MAIDEN_NAME'] = self._get_field()
        member['ETHNICITY']['SELF'] = self._get_field()
        member['ETHNICITY']['M_G_MOTHER'] = self._get_field()
        member['ETHNICITY']['M_G_FATHER'] = self._get_field()
        member['ETHNICITY']['P_G_MOTHER'] = self._get_field()
        member['ETHNICITY']['P_G_FATHER'] = self._get_field()
        member['ORIGINS']['SELF'] = self._get_field()
        member['ORIGINS']['M_G_MOTHER'] = self._get_field()
        member['ORIGINS']['M_G_FATHER'] = self._get_field()
        member['ORIGINS']['P_G_MOTHER'] = self._get_field()
        member['ORIGINS']['P_G_FATHER'] = self._get_field()
        member['ADDRESS'] = self._get_field()
        member['ADDITIONAL_INFORMATION'] = _info(self._get_field())
        member['DATE_OF_BIRTH'] = _date(self._get_field(4))
        member['DATE_OF_DEATH'] = _date(self._get_field(4))
        member['SEX'] = _annotate(self._get_field(1), 'SEX')
        member['ID'] = _int(self._get_field(2))
        member['PEDIGREE_NUMBER'] = _int(self._get_field(2))
        member['MOTHER_ID'] = _int(self._get_field(2))
        member['FATHER_ID'] = _int(self._get_field(2))
        member['INTERNAL_ID'] = _int(self._get_field(2)) # Remove?

        member['NUMBER_OF_INDIVIDUALS'] = _int(self._get_field(1))
        self._get_field(1)

        member['AGE_GESTATION'] = self._get_field()
        member['INDIVIDUAL_ID'] = self._get_field()

        number_of_spouses = _int(self._get_field(1))
        self._get_field(1)
        for spouse in range(number_of_spouses):
            self._parse_relationship(member['ID'])

        member['TWIN_ID'] = _int(self._get_field(2))
        member['COMMENT'] = self._get_field()
        member['ADOPTION_TYPE'] = _annotate(self._get_field(1),
            'ADOPTION_TYPE')
        member['GENETIC_SYMBOLS'] = _description(self._get_field(1))
        self._get_field(1)

        _flags(member, _int(self._get_field(1)), 'INDIVIDUAL')

        member['PROBAND'] = _annotate(self._get_field(1), 'PROBAND')
        member['X_COORDINATE'] = _int(self._get_field(1))
        self._get_field(1)
        member['Y_COORDINATE'] = _int(self._get_field(1))
        self._get_field(1)
        member['ANNOTATION_1'] = _annotate(self._get_field(1), 'ANNOTATION_1')
        member['MULTIPLE_PREGNANCIES'] = _annotate(self._get_field(1),
            'MULTIPLE_PREGNANCIES')
        self._get_field(3)

        self._parse_crossover(member['ID'])

        member['ANNOTATION_2'] = _annotate(self._get_field(1), 'ANNOTATION_2')

        self._get_field(12)
        for i in range(7):
            self._get_field(24)

        member['ADDITIONAL_SYMBOLS'] = _description(self._get_field(1))

        # NOTE: DNA and BLOOD fields are switched in Cyrillic. i.e., if DNA is
        # selected, the BLOOD_LOCATION field is stored and if BLOOD is
        # selected, the DNA_LOCATION field is stored. This is probably a bug.
        if member['DNA']:
            member['DNA_LOCATION'] = self._get_field()
        if member['BLOOD']:
            member['BLOOD_LOCATION'] = self._get_field()
        if member['CELLS']:
            member['CELLS_LOCATION'] = self._get_field()

        _flags(member, _int(self._get_field(1)), 'SAMPLE')

        member['SAMPLE_NUMBER'] = self._get_field()
        self._get_field(3) # COLOUR
        self._get_field(17)
        self._get_field(2) # PATTERN


        self.parsed['FAMILY']['MEMBERS'].append(member)

        return member['ID']


    def _parse_text(self):
        """
        Extract information from a text field.
        """
        # TODO: X and Y coordinates have more digits.
        text = {}

        text['CONTENT'] = _text(self._get_field())
        self._get_field(54)
        text['X_COORDINATE'] = _int(self._get_field(1))
        self._get_field(3)
        text['Y_COORDINATE'] = _int(self._get_field(1))
        self._get_field(7)

        self.parsed['TEXT_FIELDS'].append(text)


    def _parse_footer(self):
        """
        Extract information from the footer.
        """
        number_of_unknown_data = _int(self._get_field(1))
        self._get_field(2)

        for number in range(number_of_unknown_data):
            self.parsed['UNKNOWN_FIELDS'].append(_raw(self._get_field(12)))

        number_of_custom_descriptions = _int(self._get_field(1))
        self._get_field(1)

        for description in range(19):
            self.parsed['METADATA']['GENETIC_SYMBOLS'].append({
                'NAME': MAPS['GENETIC_SYMBOL'][description],
                'VALUE': self._get_field()})

        for description in range(4):
            self.parsed['METADATA']['ADDITIONAL_SYMBOLS'].append({
                'NAME': MAPS['ADDITIONAL_SYMBOL'][description],
                'VALUE': self._get_field()})

        for description in range(number_of_custom_descriptions):
            self.parsed['METADATA']['ADDITIONAL_SYMBOLS'].append({
                'NAME': self._get_field(),
                'VALUE': self._get_field()})

        self._get_field(14)
        self.parsed['METADATA']['ZOOM'] = _int(self._get_field(2))
        self.parsed['METADATA']['UNKNOWN_1'] = _raw(self._get_field(4)) # Zoom.
        self.parsed['METADATA']['UNKNOWN_2'] = _raw(self._get_field(4)) # Zoom.
        self._get_field(20)

        number_of_text_fields = _int(self._get_field(1))
        self._get_field(1)
        for text in range(number_of_text_fields):
            self._parse_text()

        self.eof_marker = self._get_field(11)
        self._get_field(15)


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
        while current_id != self.last_id:
            current_id = self._parse_member()

        self._parse_footer()

        if self.eof_marker != EOF_MARKER:
            raise Exception('No EOF marker found.')


    def write(self, output_handle):
        """
        Write the parsed FAM file to a stream.

        :arg stream output_handle: Open writable handle.
        """
        output_handle.write('--- METADATA ---\n\n')
        self._write_dictionary(self.metadata, output_handle)

        for index, symbol in enumerate(self.genetic_symbols):
            output_handle.write('GENETIC_SYMBOL_{:02d}: {}\n'.format(index,
                symbol))
        for index, symbol in enumerate(self.additional_symbols):
            output_handle.write('ADDITIONAL_SYMBOL_{:02d}: {}\n'.format(index,
                symbol))

        for member in self.members:
            output_handle.write('\n\n--- MEMBER ---\n\n')
            self._write_dictionary(member, output_handle)

        for relationship in self.relationships.values():
            output_handle.write('\n\n--- RELATIONSHIP ---\n\n')
            self._write_dictionary(relationship, output_handle)

        if self.experimental:
            for locus in self.family_disease_locus:
                output_handle.write('\n\n--- FAMILY_DISEASE_LOCUS ---\n\n')
                self._write_dictionary(locus, output_handle)
            output_handle.write('\n\n--- QUANTITATIVE_VALUE_LOCUS ---\n\n')
            for index, locus in enumerate(self.quantitative_value_locus):
                output_handle.write('LOCUS_{:02d}: {}\n'.format(index, locus))
            for crossover in self.crossovers:
                output_handle.write('\n\n--- CROSSOVER ---\n\n')
                self._write_dictionary(crossover, output_handle)
            for marker in self.markers:
                output_handle.write('\n\n--- MARKER ---\n\n')
                self._write_dictionary(marker, output_handle)

        for text in self.text:
            output_handle.write('\n\n--- TEXT ---\n\n')
            self._write_dictionary(text, output_handle)

        output_handle.write('\n\n--- JSON DUMP ---\n\n')
        output_handle.write(json.dumps(self.parsed, indent=4,
            separators=(',', ': ')))
        output_handle.write('\n\n')

        if self.debug:
            output_handle.write('\n\n--- DEBUG INFO ---\n\n')
            output_handle.write('Reached byte {} out of {}.\n'.format(
                self.offset, len(self.data)))

            output_handle.write('\nEOF_MARKER: {}\n'.format(self.eof_marker))


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
