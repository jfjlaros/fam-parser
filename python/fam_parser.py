"""
FAM parser.


(C) 2015 Jeroen F.J. Laros <J.F.J.Laros@lumc.nl>
"""
# NOTE: All integers are probably 2 bytes.

import argparse
import json
import sys


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

    :return str: Hexadecimal representation of {data}.
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


def _flags(data, annotation):
    """
    Explode a bitfield into flags.

    :arg int data: Bit field.
    :arg str annotation: Annotation of {data}.

    :return dict: Dictionary of flags and their values.
    """
    bitfield = ord(data)
    destination = {}

    for flag in map(lambda x: 2 ** x, range(8)):
        value = bool(flag & bitfield)

        if flag not in FLAGS[annotation]:
            if value:
                destination['FLAGS_{}_{:02x}'.format(annotation, flag)] = value
        else:
            destination[FLAGS[annotation][flag]] = value

    return destination


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
    def __init__(self, debug=False, log=sys.stdout):
        """
        Constructor.

        :arg bool debug: Enable debugging output.
        :arg stream log: Debug stream to write to.
        """
        self.data = ''
        self.parsed = {
            'METADATA': {
                'GENETIC_SYMBOLS': [],
                'ADDITIONAL_SYMBOLS': []
            },
            'FAMILY': {
                'MEMBERS': [],
                'DISEASE_LOCI': [],
                'QUANTITATIVE_VALUE_LOCI': [],
                'RELATIONSHIPS': []
            },
            'TEXT_FIELDS': [],
            'UNKNOWN_FIELDS': []
        }

        self._debug = debug
        self._log = log

        self._eof_marker = ''
        self._last_id = 0
        self._offset = 0
        self._relationship_keys = set([])


    def _get_field(self, size=0, delimiter=chr(0x0d)):
        """
        Extract a field from {self.data} using either a fixed size, or a
        delimiter. After reading, {self._offset} is set to the next field.

        :arg int size: Size of fixed size field.
        :arg str delimiter: Delimeter for variable size field.
        """
        if size:
            field = self.data[self._offset:self._offset + size]
            extracted = size
        else:
            field = self.data[self._offset:].split(delimiter)[0]
            extracted = len(field) + 1

        if self._debug:
            self._log.write('0x{:06x}: '.format(self._offset))
            if size:
                self._log.write('{} ({})\n'.format(_raw(field), size))
            else:
                self._log.write('{}\n'.format(field))

        self._offset += extracted
        return field


    def _parse_markers(self):
        """
        """
        markers = []

        while _raw(self._get_field(1)) != '01':
            markers.append({'DATA': _raw(self._get_field(439))})

        return markers


    def _parse_header(self):
        """
        Extract header information.
        """
        self.parsed['METADATA']['SOURCE'] = _trim(self._get_field(26))
        self.parsed['FAMILY']['NAME'] = self._get_field()
        self.parsed['FAMILY']['ID_NUMBER'] = self._get_field()
        self.parsed['METADATA']['FAMILY_DRAWN_BY'] = self._get_field()
        self._last_id = _int(self._get_field(2))
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
        self.parsed['MARKERS'] = self._parse_markers()
        self._get_field(9)


    def _parse_relationship(self, person_id):
        """
        Extract relationship information.

        :arg int person_id: The partner in this relationship.
        """
        relationship = {
            'MEMBERS': sorted([
                {'ID': person_id},
                {'ID': _int(self._get_field(2))}
            ])
        }

        relationship.update(_flags(self._get_field(1), 'RELATIONSHIP'))

        relationship['RELATION_NAME'] = self._get_field()

        key = str(relationship['MEMBERS'])
        if key not in self._relationship_keys:
            self.parsed['FAMILY']['RELATIONSHIPS'].append(relationship)
            self._relationship_keys.add(key)


    def _parse_chromosome(self):
        """
        Extract chromosome information.

        :return dict: Parsed info.
        """
        chromosome = {
            'LIST': []
        }

        while _raw(self._get_field(1)) != '22':
            chromosome['LIST'].append({'DATA': _raw(self._get_field(11))})

        chromosome['DATA'] = _raw(self._get_field(9))

        return chromosome


    def _parse_member(self):
        """
        Extract person information.
        """
        member = {
            'CROSSOVER': {
                'ALLELES': []
            },
            'SURNAME': self._get_field(),
            'OTHER_SURNAMES': self._get_field(),
            'FORENAMES': self._get_field(),
            'KNOWN_AS': self._get_field(),
            'MAIDEN_NAME': self._get_field(),
            'ETHNICITY': {
                'SELF': self._get_field(),
                'M_G_MOTHER': self._get_field(),
                'M_G_FATHER': self._get_field(),
                'P_G_MOTHER': self._get_field(),
                'P_G_FATHER': self._get_field()
            },
            'ORIGINS': {
                'SELF': self._get_field(),
                'M_G_MOTHER': self._get_field(),
                'M_G_FATHER': self._get_field(),
                'P_G_MOTHER': self._get_field(),
                'P_G_FATHER': self._get_field()
            },
            'ADDRESS': self._get_field(),
            'ADDITIONAL_INFORMATION': _info(self._get_field()),
            'DATE_OF_BIRTH': _date(self._get_field(4)),
            'DATE_OF_DEATH': _date(self._get_field(4)),
            'SEX': _annotate(self._get_field(1), 'SEX'),
            'ID': _int(self._get_field(2)),
            'PEDIGREE_NUMBER': _int(self._get_field(2)),
            'MOTHER_ID': _int(self._get_field(2)),
            'FATHER_ID': _int(self._get_field(2)),
            'INTERNAL_ID': _int(self._get_field(2)), # Remove?
            'NUMBER_OF_INDIVIDUALS': _int(self._get_field(2)),
            'AGE_GESTATION': self._get_field(),
            'INDIVIDUAL_ID': self._get_field()
        }

        number_of_spouses = _int(self._get_field(1))
        self._get_field(1)
        for spouse in range(number_of_spouses):
            self._parse_relationship(member['ID'])

        member.update({
            'TWIN_ID': _int(self._get_field(2)),
            'COMMENT': self._get_field(),
            'ADOPTION_TYPE': _annotate(self._get_field(1), 'ADOPTION_TYPE'),
            'GENETIC_SYMBOLS': _int(self._get_field(1))
        })
        self._get_field(1)

        member.update(_flags(self._get_field(1), 'INDIVIDUAL'))

        member.update({
            'PROBAND': _annotate(self._get_field(1), 'PROBAND'),
            'X_COORDINATE': _int(self._get_field(2)),
            'Y_COORDINATE': _int(self._get_field(2)),
            'ANNOTATION_1': _annotate(self._get_field(1), 'ANNOTATION_1'),
            'MULTIPLE_PREGNANCIES': _annotate(self._get_field(1),
                'MULTIPLE_PREGNANCIES')
        })
        self._get_field(3)

        member['CROSSOVER']['ALLELES'].append(self._parse_chromosome())
        member['CROSSOVER']['SPACER'] = _raw(self._get_field(2))
        member['CROSSOVER']['ALLELES'].append(self._parse_chromosome())

        member['ANNOTATION_2'] = _annotate(self._get_field(1), 'ANNOTATION_2')

        self._get_field(12)
        for i in range(7):
            self._get_field(24)

        member['ADDITIONAL_SYMBOLS'] = _int(self._get_field(1))

        # NOTE: DNA and BLOOD fields are switched in Cyrillic. i.e., if DNA is
        # selected, the BLOOD_LOCATION field is stored and if BLOOD is
        # selected, the DNA_LOCATION field is stored. This is probably a bug.
        if member['DNA']:
            member['DNA_LOCATION'] = self._get_field()
        if member['BLOOD']:
            member['BLOOD_LOCATION'] = self._get_field()
        if member['CELLS']:
            member['CELLS_LOCATION'] = self._get_field()

        member.update(_flags(self._get_field(1), 'SAMPLE'))

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

        self._eof_marker = self._get_field(11)
        self._get_field(15)


    def read(self, input_handle):
        """
        Read the FAM file and parse it.

        :arg stream input_handle: Open readable handle to a FAM file.
        """
        self.data = input_handle.read()

        self._parse_header()

        while self._parse_member() != self._last_id:
            pass

        self._parse_footer()

        if self._eof_marker != EOF_MARKER:
            raise Exception('No EOF marker found.')


    def write(self, output_handle):
        """
        Write the parsed FAM file to a stream.

        :arg stream output_handle: Open writable handle.
        """
        if self._debug:
            output_handle.write('\n\n--- JSON DUMP ---\n\n')

        output_handle.write(json.dumps(self.parsed, sort_keys=True, indent=4,
            separators=(',', ': ')))
        output_handle.write('\n')

        if self._debug:
            output_handle.write('\n\n--- DEBUG INFO ---\n\n')
            output_handle.write('Reached byte {} out of {}.\n'.format(
                self._offset, len(self.data)))
            output_handle.write('EOF_MARKER: {}\n'.format(self._eof_marker))


def fam_parser(input_handle, output_handle, debug=False):
    """
    Main entry point.

    :arg stream input_handle: Open readable handle to a FAM file.
    :arg stream output_handle: Open writable handle.
    :arg bool debug: Enable debugging output.
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
