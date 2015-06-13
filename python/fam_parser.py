"""
FAM parser.


(C) 2015 Jeroen F.J. Laros <J.F.J.Laros@lumc.nl>
"""
# NOTE: All integers are probably 2 bytes.
# NOTE: Colours may be 4 bytes.

import argparse
import json
import os
import sys

import yaml


def _identity(data):
    return data


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
    def __init__(self, json_output=False, experimental=False, debug=0,
            log=sys.stdout):
        """
        Constructor.

        :arg bool json_output: Select JSON instead of YAML output.
        :arg bool experimental: Enable experimental features.
        :arg int debug: Debugging level.
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
            'TEXT_FIELDS': []
        }
        self._internal = {}

        self._json_output = json_output
        self._debug = debug
        self._experimental = experimental | bool(debug)
        self._log = log

        self._definitions = yaml.load(open(
            os.path.join(os.path.dirname(__file__), '../fam_fields.yml')))
        self._fields = self._definitions

        self._eof_marker = ''
        self._last_id = 0
        self._offset = 0
        self._raw_byte_count = 0
        self._relationship_keys = set([])


    def _get_field(self, size=0):
        """
        Extract a field from {self.data} using either a fixed size, or a
        delimiter. After reading, {self._offset} is set to the next field.

        :arg int size: Size of fixed size field.

        :return str: Content of the requested field.
        """
        if size:
            field = self.data[self._offset:self._offset + size]
            extracted = size
        else:
            field = self.data[self._offset:].split(
                chr(self._definitions['DELIMITERS']['FIELD']))[0]
            extracted = len(field) + 1

        if self._debug > 1:
            self._log.write('0x{:06x}: '.format(self._offset))
            if size:
                self._log.write('{} ({})\n'.format(_raw(field), size))
            else:
                self._log.write('{}\n'.format(field))

        self._offset += extracted
        return field


    def _trim(self, data):
        return data.split(chr(self._definitions['DELIMITERS']['TRIM']))[0]


    def _text(self, data, delimiters):
        return '\n'.join(data.split(
            chr(self._definitions['DELIMITERS'][delimiters][0]) +
            chr(self._definitions['DELIMITERS'][delimiters][1])))


    def _annotate(self, data, annotation):
        """
        Replace a value with its annotation.

        :arg str data: Encoded data.
        :arg dict annotation: Annotation of {data}.

        :return str: Annotated representation of {data}.
        """
        index = ord(data)

        if index in self._definitions['MAPS'][annotation]:
            return self._definitions['MAPS'][annotation][index]
        return '{:02x}'.format(index)


    def _flags(self, data, annotation):
        """
        Explode a bitfield into flags.

        :arg int data: Bit field.
        :arg str annotation: Annotation of {data}.

        :return dict: Dictionary of flags and their values.
        """
        bitfield = _int(data)
        flags = {}

        for flag in map(lambda x: 2 ** x, range(8)):
            value = bool(flag & bitfield)

            if flag not in self._definitions['FLAGS'][annotation]:
                if value:
                    flags['FLAGS_{}_{:02x}'.format(annotation, flag)] = value
            else:
                flags[self._definitions['FLAGS'][annotation][flag]] = value

        return flags


    def _parse_raw(self, destination, size, key='RAW'):
        """
        Stow unknown data away in a list.

        This function is needed to skip data of which the function is unknown.
        If `self._experimental` is set to `True`,  the data is placed in an
        appropriate place. This is mainly for debugging purposes.

        Ideally, this function will become obsolete (when we have finished the
        reverse engineering completely).

        :arg dict destination: Destination dictionary.
        :arg int size: Bytes to be stowed away (see `_get_field`).
        :arg str key: Name of the list to store the data in.
        """
        if self._experimental:
            if not key in destination:
                destination[key] = []
            destination[key].append({'DATA': _raw(self._get_field(size))})
        else:
            self._get_field(size)

        self._raw_byte_count += size


    def parse(self, structure, dest):
        """
        """
        for item in structure:
            if 'structure' in item:
                if self._debug > 1:
                    print '{}'.format(item['name'])
                if item['name'] not in dest:
                    if set(['size', 'delimiter', 'count']) & set(item):
                        dest[item['name']] = []
                    else:
                        dest[item['name']] = {}
                if 'size' in item:
                    for index in range(item['size']):
                        d = {}
                        self.parse(item['structure'], d)
                        dest[item['name']].append(d)
                elif 'delimiter' in item:
                    while (_int(self._get_field(1)) !=
                            self._fields['DELIMITERS'][item['delimiter']]):
                        d = {}
                        self.parse(item['structure'], d)
                        dest[item['name']].append(d)
                elif 'count' in item:
                    for index in range(self._internal[item['count']]):
                        d = {}
                        self.parse(item['structure'], d)
                        dest[item['name']].append(d)
                else:
                    self.parse(item['structure'], dest[item['name']])
            else:
                size = 0
                function = _identity
                if 'size' in item:
                    size = item['size']
                if 'type' in item:
                    if item['type'] == 'trim':
                        dest[item['name']] = self._trim(self._get_field(size))
                    elif item['type'] == 'raw':
                        dest[item['name']] = _raw(self._get_field(size))
                    elif item['type'] == 'int':
                        if 'internal' in item:
                            self._internal[item['name']] = _int(
                                self._get_field(2))
                        else:
                            dest[item['name']] = _int(self._get_field(2))
                    elif item['type'] == 'short':
                        dest[item['name']] = _int(self._get_field(1))
                    elif item['type'] == 'date':
                        dest[item['name']] = _date(self._get_field(4))
                    elif item['type'] == 'colour':
                        dest[item['name']] = _colour(self._get_field(3))
                    elif item['type'] == 'map':
                        dest[item['name']] = self._annotate(self._get_field(1),
                            item['map'])
                    elif item['type'] == 'flags':
                        dest[item['name']] = self._flags(self._get_field(1),
                            item['flags'])
                    elif item['type'] == 'text':
                        dest[item['name']] = self._text(self._get_field(),
                            item['split'])
                    elif item['type'] == 'conditional':
                        if item['condition'] in dest:
                            dest[item['name']] = _identity(
                                self._get_field(size))
                else:
                    dest[item['name']] = _identity(self._get_field(size))
                if self._debug > 1:
                    print '{}'.format(item['name'])


    def _parse_markers(self):
        """
        Extract marker information.
        """
        while _raw(self._get_field(1)) != '01':
            self._parse_raw(self.parsed['FAMILY'], 439, 'MARKERS')


    def _parse_disease_locus(self):
        """
        Extract disease locus information.
        """
        locus = {
            'NAME': self._get_field(),
            'COLOUR': _colour(self._get_field(3))
        }

        self._parse_raw(locus, 1)
        locus['PATTERN'] = self._annotate(self._get_field(1), 'PATTERN')

        self.parsed['FAMILY']['DISEASE_LOCI'].append(locus)


    def _parse_header(self):
        """
        Extract header information.
        """
        self.parsed['METADATA']['SOURCE'] = self._trim(self._get_field(26))
        self.parsed['FAMILY']['NAME'] = self._get_field()
        self.parsed['FAMILY']['ID_NUMBER'] = self._get_field()
        self.parsed['METADATA']['FAMILY_DRAWN_BY'] = self._get_field()
        self._last_id = _int(self._get_field(2))
        self._parse_raw(self.parsed, 2) # LAST_INTERNAL_ID

        for i in range(7):
            self._parse_disease_locus()

        self.parsed['FAMILY']['COMMENTS'] = self._text(self._get_field(),
            'COMMENT')
        self.parsed['METADATA']['CREATION_DATE'] = _date(self._get_field(4))
        self.parsed['METADATA']['LAST_UPDATED'] = _date(self._get_field(4))

        self._parse_raw(self.parsed, 5)
        for i in range(7):
            self.parsed['FAMILY']['QUANTITATIVE_VALUE_LOCI'].append(
                {'NAME': self._get_field()})

        self.parsed['METADATA']['SELECTED_ID'] = _int(self._get_field(2))

        self._parse_raw(self.parsed, 7)
        self._parse_markers()
        self._parse_raw(self.parsed, 9)


    def _parse_relationship(self, person_id):
        """
        Extract relationship information.

        :arg int person_id: The partner in this relationship.
        """
        relationship = {
            'MEMBERS': sorted([person_id, _int(self._get_field(2))])
        }

        relationship.update(self._flags(self._get_field(1), 'RELATIONSHIP'))

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
        chromosome = {}

        while _raw(self._get_field(1)) != '22':
            self._parse_raw(chromosome, 11, 'LIST')
        self._parse_raw(chromosome, 9)

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
            'ADDRESS': self._text(self._get_field(), 'COMMENT'),
            'ADDITIONAL_INFORMATION': self._text(self._get_field(), 'COMMENT'),
            'DATE_OF_BIRTH': _date(self._get_field(4)),
            'DATE_OF_DEATH': _date(self._get_field(4)),
            'SEX': self._annotate(self._get_field(1), 'SEX'),
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
        self._parse_raw(member, 1)
        for spouse in range(number_of_spouses):
            self._parse_relationship(member['ID'])

        member.update({
            'TWIN_ID': _int(self._get_field(2)),
            'COMMENT': self._text(self._get_field(), 'COMMENT'),
            'ADOPTION_TYPE': self._annotate(self._get_field(1),
                'ADOPTION_TYPE'),
            'GENETIC_SYMBOLS': _int(self._get_field(1))
        })
        self._parse_raw(member, 1)

        member.update(self._flags(self._get_field(1), 'INDIVIDUAL'))

        member.update({
            'PROBAND': self._annotate(self._get_field(1), 'PROBAND'),
            'X_COORDINATE': _int(self._get_field(2)),
            'Y_COORDINATE': _int(self._get_field(2)),
            'ANNOTATION_1': self._annotate(self._get_field(1), 'ANNOTATION_1'),
            'MULTIPLE_PREGNANCIES': self._annotate(self._get_field(1),
                'MULTIPLE_PREGNANCIES')
        })
        self._parse_raw(member, 3)

        member['CROSSOVER']['ALLELES'].append(self._parse_chromosome())
        self._parse_raw(member['CROSSOVER'], 2)
        member['CROSSOVER']['ALLELES'].append(self._parse_chromosome())

        member['ANNOTATION_2'] = self._annotate(self._get_field(1),
            'ANNOTATION_2')

        self._parse_raw(member, 12)
        for i in range(7):
            self._parse_raw(member, 24)

        member['ADDITIONAL_SYMBOLS'] = _int(self._get_field(1)) # -19?

        # NOTE: DNA and BLOOD fields are switched in Cyrillic. i.e., if DNA is
        # selected, the BLOOD_LOCATION field is stored and if BLOOD is
        # selected, the DNA_LOCATION field is stored. This is probably a bug.
        if member['DNA']:
            member['DNA_LOCATION'] = self._get_field()
        if member['BLOOD']:
            member['BLOOD_LOCATION'] = self._get_field()
        if member['CELLS']:
            member['CELLS_LOCATION'] = self._get_field()

        member.update(self._flags(self._get_field(1), 'SAMPLE'))

        member['SAMPLE_NUMBER'] = self._get_field()
        self._parse_raw(member, 3)  # COLOUR
        self._parse_raw(member, 17)
        self._parse_raw(member, 2)  # PATTERN

        self.parsed['FAMILY']['MEMBERS'].append(member)

        return member['ID']


    def _parse_text(self):
        """
        Extract information from a text field.
        """
        # TODO: X and Y coordinates have more digits.
        text = {}

        text['CONTENT'] = self._text(self._get_field(), 'TEXT')
        self._parse_raw(text, 54)
        text['X_COORDINATE'] = _int(self._get_field(1))
        self._parse_raw(text, 3)
        text['Y_COORDINATE'] = _int(self._get_field(1))
        self._parse_raw(text, 7)

        self.parsed['TEXT_FIELDS'].append(text)


    def _parse_footer(self):
        """
        Extract information from the footer.
        """
        number_of_unknown_data = _int(self._get_field(1))
        self._parse_raw(self.parsed, 2)

        for number in range(number_of_unknown_data):
            self._parse_raw(self.parsed, 12, 'UNKNOWN_FIELDS')

        number_of_custom_descriptions = _int(self._get_field(1))
        self._parse_raw(self.parsed, 1)

        for description in range(19):
            self.parsed['METADATA']['GENETIC_SYMBOLS'].append({
                'NAME': self._definitions['MAPS']['GENETIC_SYMBOL'][
                    description],
                'VALUE': self._get_field()})

        for description in range(4):
            self.parsed['METADATA']['ADDITIONAL_SYMBOLS'].append({
                'NAME': self._definitions['MAPS']['ADDITIONAL_SYMBOL'][
                    description],
                'VALUE': self._get_field()})

        for description in range(number_of_custom_descriptions):
            self.parsed['METADATA']['ADDITIONAL_SYMBOLS'].append({
                'NAME': self._get_field(),
                'VALUE': self._get_field()})

        self._parse_raw(self.parsed, 14)
        self.parsed['METADATA']['ZOOM'] = _int(self._get_field(2))
        self.parsed['METADATA']['UNKNOWN_1'] = _raw(self._get_field(4)) # Zoom.
        self.parsed['METADATA']['UNKNOWN_2'] = _raw(self._get_field(4)) # Zoom.
        self._parse_raw(self.parsed, 20)

        number_of_text_fields = _int(self._get_field(1))
        self._parse_raw(self.parsed, 1)
        for text in range(number_of_text_fields):
            self._parse_text()

        self._eof_marker = self._get_field(11)
        self._parse_raw(self.parsed, 15)


    def read(self, input_handle):
        """
        Read the FAM file and parse it.

        :arg stream input_handle: Open readable handle to a FAM file.
        """

        self.data = input_handle.read()

        structure = yaml.load(open('structure.yml'))
        self.parse(structure, self.parsed)
        return

        self._parse_header()

        while self._parse_member() != self._last_id:
            pass

        self._parse_footer()

        if self._eof_marker != self._definitions['EOF_MARKER']:
            raise Exception('No EOF marker found.')


    def write(self, output_handle):
        """
        Write the parsed FAM file to a stream.

        :arg stream output_handle: Open writable handle.
        """
        if self._debug > 1:
            output_handle.write('\n\n')

        if self._json_output == True:
            if self._debug:
                output_handle.write('--- JSON DUMP ---\n\n')
            output_handle.write(json.dumps(self.parsed, indent=4,
                separators=(',', ': ')))
            output_handle.write('\n')
        else:
            if self._debug:
                output_handle.write('--- YAML DUMP ---\n\n')
            yaml.dump(self.parsed, output_handle, width=76,
                default_flow_style=False)

        if self._debug:
            data_length = len(self.data)
            parsed = data_length - self._raw_byte_count

            output_handle.write('\n\n--- DEBUG INFO ---\n\n')
            output_handle.write('Reached byte {} out of {}.\n'.format(
                self._offset, data_length))
            output_handle.write('{} bytes parsed ({:d}%)\n'.format(
                parsed, parsed * 100 // len(self.data)))
            output_handle.write('EOF_MARKER: {}\n'.format(self._eof_marker))


def fam_parser(input_handle, output_handle, json_output=False,
        experimental=False, debug=0):
    """
    Main entry point.

    :arg stream input_handle: Open readable handle to a FAM file.
    :arg stream output_handle: Open writable handle.
    :arg bool json_output: Select JSON instead of YAML output.
    :arg bool experimental: Enable experimental features.
    :arg int debug: Debugging level.
    """
    parser = FamParser(json_output, experimental, debug)
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
    parser.add_argument('-d', dest='debug', type=int, help='debugging level')
    parser.add_argument('-e', dest='experimental', action='store_true',
        help='enable experimental features')
    parser.add_argument('-j', dest='json_output', action='store_true',
        help='use JSON output instead of YAML')

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
